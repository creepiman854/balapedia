"""Cliente de la MediaWiki API y parsers de plantillas de la wiki de Balatro.

Este módulo encapsula toda la extracción de datos desde balatrowiki.org y se
divide en tres capas claramente separadas:

  1. **Cliente HTTP**: funciones que hablan con la MediaWiki API
     (``fetch_wikitext``, ``list_pages_in_category``, ``resolve_image_url``).
     Son las únicas que generan tráfico de red.

  2. **Utilidades de parseo**: helpers genéricos para procesar wikitexto
     (``render_wikitext``, ``extract_leading_int``, ``_get_template``,
     ``_field``). Son funciones puras: entrada texto -> salida texto/dict.

  3. **Parsers por familia de plantilla**: ``parse_joker``,
     ``parse_consumable``, ``parse_deck``, ``parse_voucher``. Reciben el
     wikitexto de una página y devuelven un dict listo para alimentar el
     comando de seed que escribirá en la BD.

Diseño deliberado: los parsers son puros (no hacen HTTP, no tocan la BD).
Esto permite testarlos contra fixtures locales y aislar errores de parseo
de errores de red o de persistencia.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Optional
from urllib.parse import quote

import mwparserfromhell
import requests
from mwparserfromhell.nodes import Comment, HTMLEntity, Tag, Template, Wikilink

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
#  Configuración del cliente HTTP
# ──────────────────────────────────────────────────────────────────────

WIKI_API_URL = "https://balatrowiki.org/api.php"
WIKI_BASE_URL = "https://balatrowiki.org"

# El User-Agent identifica a la app ante MediaWiki. Buenas prácticas:
# incluir información de contacto (email o URL) para que la wiki pueda
# avisar si nuestro bot se comporta mal.
#
# Si no se configura, se usa un fallback genérico SIN datos personales y
# se loguea un aviso. La razón: este código es público y un fallback con
# datos personales atribuiría el tráfico de cualquier fork a quien escribió
# el código, no a quien lo ejecuta.
_default_ua = "BalapediaTFG/0.1"
_ua_from_env = (os.getenv("WIKI_USER_AGENT") or "").strip()
USER_AGENT = _ua_from_env if _ua_from_env else _default_ua

if USER_AGENT == _default_ua:
    logger.warning(
        "WIKI_USER_AGENT not configured; using generic User-Agent. "
        "Set WIKI_USER_AGENT in your .env to include contact info "
        "per MediaWiki API guidelines."
    )

REQUEST_TIMEOUT_S = 15
HEADERS = {"User-Agent": USER_AGENT}


# ──────────────────────────────────────────────────────────────────────
#  1. Cliente del MediaWiki API
# ──────────────────────────────────────────────────────────────────────


def fetch_wikitext(title: str) -> Optional[str]:
    """Descarga el wikitexto crudo de una página de la wiki.

    Args:
        title: Título exacto de la página (p.ej. ``"Joker"``, ``"Mr. Bones"``).

    Returns:
        El wikitexto completo de la página, o ``None`` si la página no existe.
    """
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "titles": title,
        "format": "json",
        "formatversion": 2,
    }
    response = requests.get(
        WIKI_API_URL, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT_S
    )
    response.raise_for_status()

    pages = response.json().get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        logger.warning("Page not found in wiki: %s", title)
        return None

    revisions = pages[0].get("revisions", [])
    if not revisions:
        return None
    return revisions[0]["slots"]["main"]["content"]


def list_pages_in_category(category: str, limit: int = 500) -> list[str]:
    """Devuelve los títulos de todas las páginas de una categoría de la wiki.

    Maneja paginación automáticamente si hay más de ``limit`` resultados.

    Args:
        category: Nombre sin prefijo (p.ej. ``"Jokers"``, no ``"Category:Jokers"``).
        limit: Tamaño de página de la API. La MediaWiki API limita a 500.

    Returns:
        Lista de títulos. Vacía si la categoría no existe.
    """
    titles: list[str] = []
    cmcontinue: Optional[str] = None

    while True:
        params: dict[str, Any] = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmlimit": limit,
            "cmtype": "page",  # excluye subcategorías
            "format": "json",
            "formatversion": 2,
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue

        response = requests.get(
            WIKI_API_URL, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT_S
        )
        response.raise_for_status()
        data = response.json()

        members = data.get("query", {}).get("categorymembers", [])
        titles.extend(m["title"] for m in members)

        cmcontinue = data.get("continue", {}).get("cmcontinue")
        if not cmcontinue:
            break

    return titles


def resolve_image_url(filename: str) -> Optional[str]:
    """Convierte un nombre de archivo (``Joker.png``) a su URL absoluta en la wiki.

    En MediaWiki las imágenes viven bajo ``/images/X/XX/<filename>`` donde
    ``X/XX`` es un fragmento del hash MD5 del filename. La API devuelve la
    URL real ya construida, evitándonos calcular el hash a mano.

    Args:
        filename: Nombre del archivo tal y como viene en la plantilla
                  (p.ej. ``"Joker.png"``).

    Returns:
        URL absoluta a la imagen en la wiki, o ``None`` si no existe.
    """
    if not filename:
        return None

    params = {
        "action": "query",
        "titles": f"File:{filename}",
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json",
        "formatversion": 2,
    }
    response = requests.get(
        WIKI_API_URL, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT_S
    )
    response.raise_for_status()

    pages = response.json().get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        logger.warning("Image file not found in wiki: %s", filename)
        return None

    imageinfo = pages[0].get("imageinfo", [])
    if not imageinfo:
        return None
    return imageinfo[0].get("url")


def page_url(title: str) -> str:
    """Construye la URL pública de una página para guardarla en ``wiki_url``.

    Reemplaza espacios por guiones bajos y URL-encodea los caracteres
    especiales, siguiendo la convención de MediaWiki.
    """
    encoded = quote(title.replace(" ", "_"))
    return f"{WIKI_BASE_URL}/wiki/{encoded}"


# ──────────────────────────────────────────────────────────────────────
#  2. Utilidades de parseo de wikitexto
# ──────────────────────────────────────────────────────────────────────


def extract_leading_int(value: Any) -> Optional[int]:
    """Extrae el primer número entero de un string posiblemente "sucio".

    Útil para campos como ``buyprice = 20 (cannot be found in shop)`` donde
    el número está mezclado con texto descriptivo.

    >>> extract_leading_int("20 (cannot be found in shop)")
    20
    >>> extract_leading_int("4")
    4
    >>> extract_leading_int(None)  # No raise: devuelve None
    """
    if value is None:
        return None
    match = re.search(r"-?\d+", str(value))
    return int(match.group()) if match else None


def render_wikitext(raw: Any) -> str:
    """Convierte wikitexto con plantillas y formato a texto plano legible.

    Plantillas reconocidas (mapeo a texto):
      - ``{{Mult|+4}}`` -> ``"+4 Mult"``
      - ``{{Chips|+30}}`` -> ``"+30 Chips"``
      - ``{{xmult|2}}`` -> ``"x2 Mult"``
      - ``{{hl|color|texto}}`` -> ``"texto"`` (descarta el color)
      - ``{{Suit|Diamond}}`` -> ``"Diamond"``
      - ``{{ph|Flush}}`` -> ``"Flush"``
      - ``{{V|Tarot Merchant|...}}`` -> ``"Tarot Merchant"``
      - ``{{J|Credit Card}}`` -> ``"Credit Card"``
      - ``{{Tarot|The Empress}}`` -> ``"The Empress"``
      - ``{{D|Plasma}}`` -> ``"Plasma"``
      - ``{{Stake|Red}}`` -> ``"Red Stake"``
      - ``{{Money|2}}`` -> ``"$2"``

    Otros nodos:
      - Wikilinks ``[[Cards|alias]]`` -> ``"alias"``.
      - Etiquetas HTML ``<br>`` -> espacio. ``<small>...</small>`` -> contenido.
      - Comentarios HTML descartados.

    Para plantillas no reconocidas, devuelve el primer argumento posicional
    como heurística razonable; si no tiene argumentos, devuelve cadena vacía.
    """
    if raw is None or str(raw).strip() == "":
        return ""

    code = mwparserfromhell.parse(str(raw))

    def render_node(node: Any) -> str:
        if isinstance(node, Template):
            name = str(node.name).strip().lower()

            def arg(n: int) -> str:
                return str(node.get(n).value).strip() if node.has(n) else ""

            # Plantillas de score
            if name == "mult":
                return f"{arg(1)} Mult"
            if name == "chips":
                return f"{arg(1)} Chips"
            if name == "xmult":
                return f"x{arg(1).lstrip('+')} Mult"
            # Highlight: descarta color, mantiene texto
            if name == "hl":
                return arg(2)
            # Referencias a entidades del juego donde el primer arg ES el nombre
            if name in (
                "suit",
                "ph",
                "v",
                "j",
                "tarot",
                "d",
                "spectral",
                "blind",
                "enhancement",
                "edition",
                "tag",
            ):
                return arg(1)
            # Sticker y Seal: si hay arg con nombre `name`, lo preferimos
            # (suele ser más legible). Si no, usamos el primer arg.
            # Ejemplos:
            #   {{Sticker|Eternal|name=Vampire}} -> "Vampire"
            #   {{Sticker|Eternal}}              -> "Eternal"
            #   {{Seal|Blue|name=Blue Seals}}    -> "Blue Seals"
            #   {{Seal|Blue}}                    -> "Blue"
            if name in ("sticker", "seal"):
                if node.has("name"):
                    inner = node.get("name").value
                    if hasattr(inner, "nodes"):
                        return "".join(render_node(n) for n in inner.nodes)
                    return str(inner)
                return arg(1)
            # Stake
            if name == "stake":
                return f"{arg(1)} Stake"
            # Money
            if name == "money":
                return f"${arg(1)}"
            # Plantilla "room" (puzzles) → descartada
            if name == "room":
                return ""
            # Plantilla desconocida: heurística → primer argumento
            return arg(1)

        if isinstance(node, Wikilink):
            # Toma el alias si existe, si no el título. Ambos pueden contener
            # plantillas anidadas (p.ej. [[Tarot Cards|{{hl|purple|Tarot}}]])
            # que deben aplanarse recursivamente, no convertirse a string crudo.
            inner = node.text if node.text else node.title
            if hasattr(inner, "nodes"):
                return "".join(render_node(n) for n in inner.nodes)
            return str(inner)

        if isinstance(node, Tag):
            tag_name = str(node.tag).lower()
            if tag_name == "br":
                return " "
            # Las contents de tags como <small>, <span>, etc. también pueden
            # contener plantillas anidadas que requieren render recursivo.
            contents = node.contents
            if hasattr(contents, "nodes"):
                return "".join(render_node(n) for n in contents.nodes)
            return str(contents) if contents else ""

        if isinstance(node, (Comment, HTMLEntity)):
            return ""

        return str(node)

    text = "".join(render_node(n) for n in code.nodes)
    # Colapsa espacios múltiples (por <br>, comentarios, etc.) en uno solo
    return re.sub(r"\s+", " ", text).strip()


def _get_template(wikitext: str, template_name: str) -> Optional[Template]:
    """Devuelve el primer template del wikitexto cuyo nombre coincide.

    La comparación es case-insensitive y respeta espacios alrededor del nombre.
    """
    code = mwparserfromhell.parse(wikitext)
    for tpl in code.filter_templates():
        if tpl.name.strip().lower() == template_name.lower():
            return tpl
    return None


def _field(tpl: Template, name: str, default: Optional[str] = None) -> Optional[str]:
    """Devuelve el valor crudo de un campo de plantilla, o ``default`` si no existe."""
    return str(tpl.get(name).value).strip() if tpl.has(name) else default


# ──────────────────────────────────────────────────────────────────────
#  3. Parsers por familia de plantilla
# ──────────────────────────────────────────────────────────────────────


def parse_joker(wikitext: str) -> Optional[dict]:
    """Parsea una página de Joker a un dict listo para inserción en BD.

    Lee la plantilla ``{{Joker info | ...}}`` y extrae todos los campos
    necesarios para crear un registro en ``unlockables`` + ``jokers``.
    """
    tpl = _get_template(wikitext, "Joker info")
    if not tpl:
        return None

    buy_raw = _field(tpl, "buyprice")
    buy = extract_leading_int(buy_raw)
    sell_raw = _field(tpl, "sellprice")
    sell = extract_leading_int(sell_raw) if sell_raw else (buy // 2 if buy else None)

    return {
        "type": "joker",
        "item_number": extract_leading_int(_field(tpl, "number")),
        "name": _field(tpl, "title"),
        "image_filename": _field(tpl, "image"),
        "negative_image_filename": _field(tpl, "negativeimage"),
        "description": render_wikitext(_field(tpl, "effect")),
        "rarity": _field(tpl, "rarity"),
        "effect_type": _field(tpl, "type"),
        "activation": _field(tpl, "activation"),
        "buy_price": buy,
        "sell_price": sell,
        "in_shop": "cannot be found in shop" not in (buy_raw or "").lower(),
        "is_copyable": _field(tpl, "compat-copyable") == "1",
        "is_perishable": _field(tpl, "compat-perishable") == "1",
        "is_eternal": _field(tpl, "compat-eternal") == "1",
        "has_negative_variant": bool(_field(tpl, "negativeimage")),
        "unlock_condition": render_wikitext(
            _field(tpl, "unlock", "Available from start.")
        ),
    }


def parse_consumable(wikitext: str) -> Optional[dict]:
    """Parsea Tarots, Planets y Spectrals (todos comparten ``Consumable info``).

    El campo ``type`` del dict se rellena con la categoría real
    (``'tarot'``, ``'planet'`` o ``'spectral'``) leída de la plantilla.
    """
    tpl = _get_template(wikitext, "Consumable info")
    if not tpl:
        return None

    buy_raw = _field(tpl, "buyprice")
    buy = extract_leading_int(buy_raw)
    sell_raw = _field(tpl, "sellprice")
    sell = extract_leading_int(sell_raw) if sell_raw else (buy // 2 if buy else None)

    consumable_type = (_field(tpl, "type") or "").lower()

    return {
        "type": consumable_type,
        "item_number": extract_leading_int(_field(tpl, "number")),
        "name": _field(tpl, "title"),
        "image_filename": _field(tpl, "image"),
        "description": render_wikitext(_field(tpl, "effect")),
        "buy_price": buy,
        "sell_price": sell,
        "in_shop": "cannot be found in shop" not in (buy_raw or "").lower(),
        "unlock_condition": render_wikitext(
            _field(tpl, "unlock", "Available from start.")
        ),
    }


def parse_deck(wikitext: str) -> Optional[dict]:
    """Parsea una página de Deck (baraja).

    Las barajas no se compran ni venden: no tienen precio. Su descripción
    funcional vive en el campo ``limit`` de la plantilla, no ``effect``.
    """
    tpl = _get_template(wikitext, "Deck info")
    if not tpl:
        return None

    return {
        "type": "deck",
        "item_number": extract_leading_int(_field(tpl, "number")),
        "name": _field(tpl, "title"),
        "image_filename": _field(tpl, "image"),
        "description": render_wikitext(_field(tpl, "limit")),
        "unlock_condition": render_wikitext(
            _field(tpl, "unlock", "Unlocked from start")
        ),
    }


def parse_voucher(wikitext: str) -> Optional[dict]:
    """Parsea una página de Voucher (vale).

    Maneja vales Base y Upgraded. ``next_voucher_name`` contendrá el nombre
    del vale al que enlaza en la cadena de mejora (``None`` si es la versión
    Upgraded, fin de cadena). El comando de seed resolverá ese nombre a un
    ``next_voucher_id`` real en una segunda pasada, una vez todos los
    vouchers estén insertados.

    La plantilla ``Voucher info`` no incluye campo ``number``: el seed
    asignará ``item_number`` secuencialmente según el orden de la categoría
    de la wiki.
    """
    tpl = _get_template(wikitext, "Voucher info")
    if not tpl:
        return None

    return {
        "type": "voucher",
        "item_number": None,  # asignado durante el seed
        "name": _field(tpl, "title"),
        "image_filename": _field(tpl, "image"),
        "voucher_tier": _field(tpl, "type"),  # 'Base' o 'Upgraded'
        "description": render_wikitext(_field(tpl, "effect")),
        "next_voucher_name": _field(tpl, "next"),
        "unlock_condition": render_wikitext(
            _field(tpl, "unlock", "Available from start.")
        ),
    }


def parse_challenge_deck(wikitext: str) -> Optional[dict]:
    """Parsea una página de Challenge Deck a un dict listo para upsert.

    Lee la plantilla ``{{Challenge info | ...}}`` y extrae los campos
    necesarios para crear un registro en ``unlockables`` + ``challenge_decks``.

    Particularidades de esta plantilla:
      - **No tiene campo ``image``**: los Challenge Decks no exponen icono
        propio en la infobox. Se devuelve ``image_filename = None``; el
        seeder dejará ``unlockable.image_url`` también a ``None``.
      - **No tiene campo ``unlock``**: la condición de desbloqueo es común
        para todos (regla del juego, no propiedad individual). Se aplica
        en el seeder con un texto descriptivo único.
      - Los campos ``starter``, ``banned`` y ``deck`` son **opcionales**
        (no todos los challenges los tienen). Se devuelven como ``None`` si
        no están presentes; los demás como texto plano renderizado.
    """
    tpl = _get_template(wikitext, "Challenge info")
    if not tpl:
        return None

    starter_raw = _field(tpl, "starter")
    banned_raw = _field(tpl, "banned")
    deck_raw = _field(tpl, "deck")

    return {
        "type": "challenge_deck",
        "item_number": extract_leading_int(_field(tpl, "number")),
        "name": _field(tpl, "title"),
        "image_filename": None,  # la plantilla no expone imagen
        "modifier": render_wikitext(_field(tpl, "modifier")),
        "starter": render_wikitext(starter_raw) if starter_raw else None,
        "banned": render_wikitext(banned_raw) if banned_raw else None,
        "deck_description": render_wikitext(deck_raw) if deck_raw else None,
    }


# ──────────────────────────────────────────────────────────────────────
#  4. Parser de tabla: Booster Packs
# ──────────────────────────────────────────────────────────────────────
#  A diferencia de los parsers de plantilla infobox, los Booster Packs
#  no tienen una página por item: viven todos en una única página
#  ('Booster Packs') estructurada como una wikitable. Esto requiere un
#  enfoque distinto: en lugar de buscar una plantilla, recorremos las
#  filas de la tabla y extraemos las celdas individualmente.
# ──────────────────────────────────────────────────────────────────────


def parse_booster_packs_page(wikitext: str) -> list[dict]:
    """Parsea la página 'Booster Packs' a una lista de dicts.

    Estructura esperada en el wikitexto::

        == List of Booster Packs ==
        {| class="wikitable" ...
        ! ... headers de columna ...
        |-
        ! colspan="4" id="Arcana Packs" | '''Arcana Packs'''
        |-
        | id="Arcana Pack" | [[File:Arcana Normal 1.png|...]] ...
        | {{Money|4}}
        | Normal
        | Choose {{hl|orange|1}} of {{hl|orange|3}} [[Tarot Cards|...]] ...
        |-
        ... más filas y secciones ...
        |}

    Args:
        wikitext: Wikitexto completo de la página 'Booster Packs'.

    Returns:
        Lista de dicts (uno por pack), con campos:
            - ``type``: siempre ``"booster_pack"``
            - ``name``: nombre del pack (del atributo ``id`` de la celda imagen)
            - ``pack_type``: Arcana / Celestial / Standard / Buffoon / Spectral
            - ``size``: Normal / Jumbo / Mega
            - ``cost``: int extraído de ``{{Money|N}}``
            - ``description``: texto del efecto (aplanado)
            - ``image_filename``: primer filename de imagen encontrado

        Si no se localiza la sección 'List of Booster Packs', devuelve
        lista vacía y emite un warning en el log.

    Notas de diseño:
        - La celda de imagen contiene múltiples File: links (variantes
          visuales de la portada). Solo se extrae el primero, ya que
          las variantes adicionales no aportan información distinta.
        - Las cabeceras de sección (``colspan="4"`` con ``id="X Packs"``)
          actúan como discriminador de ``pack_type`` para las filas
          siguientes hasta encontrar la próxima cabecera.
    """
    # 1. Aísla la wikitable concreta de "List of Booster Packs". La página
    #    contiene varias tablas (rates, traducciones por idioma...) y solo
    #    nos interesa la primera tras esa cabecera.
    section_match = re.search(
        r"==\s*List of Booster Packs\s*==\s*(\{\|.*?\|\})",
        wikitext,
        re.DOTALL,
    )
    if not section_match:
        logger.warning("Could not find 'List of Booster Packs' section in wikitext")
        return []

    table = section_match.group(1)

    # 2. Divide la tabla en filas por el separador estándar "|-".
    rows = table.split("\n|-")

    packs: list[dict] = []
    current_pack_type: Optional[str] = None

    for row in rows:
        # Salta el header de columnas (Image(s), Cost, Size, Effect).
        if "Image(s)" in row and "Cost" in row:
            continue

        # Detecta cabecera de sección: ! colspan="4" id="X Packs" | ...
        section_header = re.search(
            r'colspan="4"[^|!]*id="(\w+)\s+Packs"',
            row,
        )
        if section_header:
            current_pack_type = section_header.group(1)  # "Arcana", "Celestial"...
            continue

        # Si aún no hemos visto una cabecera de sección, ignora la fila.
        if current_pack_type is None:
            continue

        # Procesa fila normal de pack.
        cells = _split_wikitable_cells(row)
        if len(cells) < 4:
            continue

        pack = _parse_booster_pack_row(cells, current_pack_type)
        if pack is not None:
            packs.append(pack)

    return packs


def _split_wikitable_cells(row: str) -> list[str]:
    """Divide una fila de wikitable en sus celdas.

    Cada celda comienza en una línea que empieza con ``|`` (excluyendo
    ``|-`` que es el separador de filas y ``|}`` que cierra la tabla).
    Las celdas en esta tabla concreta no son multilínea, así que basta
    con una pasada por las líneas de la fila.
    """
    cells = []
    for line in row.split("\n"):
        line = line.strip()
        if not line:
            continue
        if (
            line.startswith("|")
            and not line.startswith("|-")
            and not line.startswith("|}")
        ):
            # Quita el '|' inicial y los espacios.
            cells.append(line.lstrip("|").lstrip())
    return cells


def _parse_booster_pack_row(cells: list[str], pack_type: str) -> Optional[dict]:
    """Extrae los datos de una fila de pack a un dict.

    Args:
        cells: Lista mínima de 4 celdas: imagen, cost, size, effect.
        pack_type: Categoría detectada de la cabecera de sección anterior.

    Returns:
        Dict con los campos del pack, o None si la celda imagen no tiene
        atributo ``id`` (en cuyo caso no podemos derivar el nombre).
    """
    image_cell, cost_cell, size_cell, effect_cell = cells[:4]

    # 1. Nombre del pack: del atributo id="..." de la celda imagen.
    id_match = re.search(r'id="([^"]+)"', image_cell)
    if not id_match:
        return None
    name = id_match.group(1)

    # 2. Filename de la primera imagen [[File:X.png|...]].
    img_match = re.search(r"\[\[File:([^|\]]+)", image_cell)
    image_filename = img_match.group(1).strip() if img_match else None

    # 3. Cost: número del template {{Money|N}}, ya aplanado a "$N" por
    #    render_wikitext, del que extraemos el entero líder.
    cost = extract_leading_int(render_wikitext(cost_cell))

    # 4. Size: texto plano (Normal / Jumbo / Mega).
    size = size_cell.strip()

    # 5. Description: aplanado del efecto, manejando templates anidados.
    description = render_wikitext(effect_cell)

    return {
        "type": "booster_pack",
        "name": name,
        "pack_type": pack_type,
        "size": size,
        "cost": cost,
        "description": description,
        "image_filename": image_filename,
    }
