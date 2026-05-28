"""Comandos CLI personalizados de Flask para tareas de mantenimiento.

Estos comandos extienden el comando base ``flask`` y se invocan así desde
el directorio ``backend/``::

    flask --app run.py seed-db [--type=jokers|all] [--dry-run] [--limit=N]

El registro se realiza en ``create_app()`` llamando a ``register_commands(app)``,
de modo que los comandos solo existen dentro del contexto de la aplicación
Flask y tienen acceso automático a la BD.

Convenciones de salida:
  - Uso de ``click.secho`` con colores para distinguir éxito (verde),
    aviso (amarillo), error (rojo) e información (cian/blanco).
  - Los símbolos ``+`` (created), ``↻`` (updated), ``⚠`` (warning), ``✓``
    (success) y ``✗`` (error) facilitan el seguimiento visual del progreso.
"""

from __future__ import annotations

import logging

import click
from flask.cli import with_appcontext
from sqlalchemy import func, text

from app.extensions import db
from app.scrapers import steam, wiki

from app.models import (
    Achievement,
    Blind,
    BlindType,
    BoosterPack,
    BoosterPackSize,
    BoosterPackType,
    CardModifier,
    ChallengeDeck,
    Consumable,
    Deck,
    Joker,
    JokerRarity,
    ModifierType,
    Sticker,
    StickerType,
    Stake,
    Tag,
    Unlockable,
    UnlockableType,
    Voucher,
    VoucherTier,
)

from app.services.achievement_sync import (
    UserNotFoundError,
    UserNotLinkedError,
    sync_steam_achievements_for_user,
)
from app.services.steam import SteamApiError

# ──────────────────────────────────────────────────────────────────────
#  Overrides de datos para errores conocidos en la wiki fuente
# ──────────────────────────────────────────────────────────────────────

# Cuando un campo de la wiki es objetivamente incorrecto, lo corregimos aquí.
# Cada entrada DEBE incluir un comentario explicando el motivo y, si es posible,
# un enlace a la página de la wiki para verificación futura. Cuando la wiki se
# corrija, basta con eliminar la entrada correspondiente.
_WIKI_DATA_OVERRIDES = {
    # Tarot: The Hierophant tiene number=7 en la wiki, lo cual colisiona
    # con The Lovers (también number=7). Según el orden estándar del Major
    # Arcana, debe ser 6.
    # Wiki: https://balatrowiki.org/wiki/The_Hierophant
    ("tarot", "The Hierophant"): {"item_number": 6},
    # Voucher: Planet Merchant tiene la cadena Base→Upgraded invertida en
    # la wiki (usa `previous = Planet Tycoon` en lugar de `next`).
    # Forzamos el enlace correcto para que pass 2 lo resuelva.
    # Wiki: https://balatrowiki.org/wiki/Planet_Merchant
    ("voucher", "Planet Merchant"): {
        "voucher_tier": "Base",
        "next_voucher_name": "Planet Tycoon",
    },
    # Voucher: complemento defensivo del override anterior. Si la página de
    # Planet Tycoon también tiene la inversión simétrica (`next = Planet
    # Merchant`), lo limpiamos: Tycoon es Upgraded y no debe tener `next`,
    # ya que está al final de su cadena.
    # Wiki: https://balatrowiki.org/wiki/Planet_Tycoon
    ("voucher", "Planet Tycoon"): {
        "voucher_tier": "Upgraded",
        "next_voucher_name": None,
    },
}


def _apply_overrides(data: dict) -> dict:
    """Aplica correcciones para errores conocidos en la wiki fuente.

    Funciona como un parche entre el parser y el upsert: el parser sigue
    leyendo datos crudos, y aquí se aplican correcciones documentadas.
    """
    key = (data.get("type"), data.get("name"))
    if key in _WIKI_DATA_OVERRIDES:
        data = {**data, **_WIKI_DATA_OVERRIDES[key]}
    return data


logger = logging.getLogger(__name__)


def register_commands(app) -> None:
    """Registra los comandos CLI custom en la app Flask."""
    app.cli.add_command(seed_db)
    app.cli.add_command(steam_sync_command)


# ──────────────────────────────────────────────────────────────────────
#  Comando: seed-db
# ──────────────────────────────────────────────────────────────────────


@click.command("seed-db")
@click.option(
    "--type",
    "item_type",
    type=click.Choice(
        [
            "jokers",
            "consumables",
            "decks",
            "vouchers",
            "achievements",
            "booster_packs",
            "challenge_decks",
            "stakes",
            "blinds",
            "tags",
            "card_modifiers",
            "stickers",
            "all",
        ]
    ),
    default="all",
    help="Tipo de items a sembrar. 'all' = todos los disponibles.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="No escribe en la BD: procesa y muestra qué se haría sin persistir.",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Procesa solo los primeros N items por tipo (útil para tests rápidos).",
)
@with_appcontext
def seed_db(item_type: str, dry_run: bool, limit: int | None) -> None:
    """Pobla la BD con datos extraídos de la wiki de Balatro.

    Idempotente: ejecutarlo varias veces no duplica items, gracias al
    UNIQUE(type, item_number) de la tabla unlockables. Las ejecuciones
    posteriores actualizan los campos en lugar de insertar.
    """
    if dry_run:
        click.secho(
            "DRY RUN: cambios procesados pero NO persistidos en la BD",
            fg="yellow",
            bold=True,
        )

    # Pre-flight: verifica conexión a la BD antes de hacer cualquier petición
    # a la wiki. Mejor fallar pronto que tras 5 minutos de scraping.
    try:
        db.session.execute(text("SELECT 1"))
    except Exception as e:
        click.secho(f"✗ Cannot connect to database: {e}", fg="red")
        raise click.Abort()

    seeders = {
        "jokers": seed_jokers,
        "consumables": seed_consumables,
        "decks": seed_decks,
        "vouchers": seed_vouchers,
        "achievements": seed_achievements,
        "booster_packs": seed_booster_packs,
        "challenge_decks": seed_challenge_decks,
        "stakes": seed_stakes,
        "blinds": seed_blinds,
        "tags": seed_tags,
        "card_modifiers": seed_card_modifiers,
        "stickers": seed_stickers,
    }

    types_to_seed = list(seeders.keys()) if item_type == "all" else [item_type]

    for type_name in types_to_seed:
        click.echo()
        click.secho(f"━━━ Seeding {type_name} ━━━", fg="cyan", bold=True)
        try:
            count = seeders[type_name](dry_run=dry_run, limit=limit)
            click.secho(f"  ✓ {count} {type_name} processed", fg="green")
        except Exception:
            logger.exception("Failed to seed %s", type_name)
            click.secho(f"  ✗ Error seeding {type_name}", fg="red")
            raise


# ──────────────────────────────────────────────────────────────────────
#  Helpers compartidos por los seeders
# ──────────────────────────────────────────────────────────────────────


def _filter_category_index_pages(titles: list[str], category: str) -> list[str]:
    """Filtra páginas índice de una categoría de MediaWiki.

    En MediaWiki, la página titulada igual que su categoría (y sus variantes
    "List of X" / "X (List)") suele estar categorizada en sí misma como
    página overview del tema. Estas páginas no son items individuales y
    carecen de la plantilla que esperamos parsear, así que las descartamos
    antes de procesar.

    Args:
        titles: Lista de títulos devuelta por ``wiki.list_pages_in_category``.
        category: Nombre de la categoría sin prefijo ``Category:``.

    Returns:
        La lista de títulos sin las páginas índice.
    """
    index_names = {category, f"List of {category}", f"{category} (List)"}
    return [t for t in titles if t not in index_names]


# ──────────────────────────────────────────────────────────────────────
#  Seeder: jokers
# ──────────────────────────────────────────────────────────────────────


def seed_jokers(dry_run: bool, limit: int | None) -> int:
    """Pobla la tabla de Jokers desde ``Category:Jokers`` de la wiki.

    Returns:
        Número de jokers procesados (insertados o actualizados).
    """
    titles = wiki.list_pages_in_category("Jokers")
    titles = _filter_category_index_pages(titles, "Jokers")

    if limit is not None:
        titles = titles[:limit]

    click.echo(f"  Found {len(titles)} joker pages in Category:Jokers")

    count = 0
    for title in titles:
        try:
            wikitext = wiki.fetch_wikitext(title)
            if not wikitext:
                click.secho(f"  ⚠ No wikitext for {title!r}", fg="yellow")
                continue

            data = wiki.parse_joker(wikitext)
            if not data:
                click.secho(
                    f"  ⚠ Page lacks 'Joker info' template: {title!r}",
                    fg="yellow",
                )
                continue

            data = _apply_overrides(data)

            # Defensa: items sin item_number no pueden satisfacer NOT NULL.
            # Suelen ser páginas meta o de overview categorizadas erróneamente.
            if data.get("item_number") is None:
                click.secho(f"  ⚠ Skipped (no item_number): {title!r}", fg="yellow")
                continue

            _upsert_joker(data, title)

            # Commit por item: cada uno es una transacción independiente.
            # Esto evita que un fallo posterior pierda el trabajo anterior y
            # permite que el bucle continúe tras errores aislados.
            if not dry_run:
                db.session.commit()

            count += 1
        except Exception as e:
            # Limpia la sesión envenenada antes de seguir con el siguiente item.
            # Sin esto, todas las queries posteriores fallan en cascada.
            db.session.rollback()
            click.secho(f"  ✗ Error processing {title!r}: {e}", fg="red")
            logger.exception("Failed processing %s", title)
            continue

    if dry_run:
        db.session.rollback()
        click.secho("  (dry-run: changes rolled back)", fg="yellow")

    return count


def _upsert_joker(data: dict, title: str) -> None:
    """Inserta o actualiza un Joker (más su Unlockable padre) en la BD.

    Si ya existe un Unlockable con (type=JOKER, item_number=N), se actualizan
    todos sus campos. Si no, se crea uno nuevo con el Joker asociado.

    Las URLs de imagen se resuelven mediante la API de la wiki (un round-trip
    HTTP por imagen). Si la imagen no existe, se almacena ``None`` y la app
    deberá mostrar un placeholder en la UI.
    """
    image_url = (
        wiki.resolve_image_url(data["image_filename"])
        if data.get("image_filename")
        else None
    )
    negative_image_url = (
        wiki.resolve_image_url(data["negative_image_filename"])
        if data.get("negative_image_filename")
        else None
    )

    existing = Unlockable.query.filter_by(
        type=UnlockableType.JOKER,
        item_number=data["item_number"],
    ).first()

    if existing is not None:
        # ── Actualizar registro existente ──
        existing.name = data["name"]
        existing.description = data["description"]
        existing.image_url = image_url
        existing.unlock_condition = data["unlock_condition"]
        existing.wiki_url = wiki.page_url(title)

        joker = existing.joker
        joker.rarity = JokerRarity(data["rarity"])
        joker.effect_type = data["effect_type"]
        joker.activation = data["activation"]
        joker.buy_price = data["buy_price"]
        joker.sell_price = data["sell_price"]
        joker.in_shop = data["in_shop"]
        joker.has_negative_variant = data["has_negative_variant"]
        joker.negative_image_url = negative_image_url
        joker.is_copyable = data["is_copyable"]
        joker.is_perishable = data["is_perishable"]
        joker.is_eternal = data["is_eternal"]

        click.echo(f"  ↻ Updated: #{data['item_number']:>3} {data['name']}")
    else:
        # ── Crear registro nuevo ──
        unlockable = Unlockable(
            type=UnlockableType.JOKER,
            item_number=data["item_number"],
            name=data["name"],
            description=data["description"],
            image_url=image_url,
            unlock_condition=data["unlock_condition"],
            wiki_url=wiki.page_url(title),
        )
        # La asignación a la relación + cascade='all, delete-orphan' hace que
        # SQLAlchemy inserte ambas filas (unlockables y jokers) en la misma
        # transacción, propagando el id del padre como FK del hijo.
        unlockable.joker = Joker(
            rarity=JokerRarity(data["rarity"]),
            effect_type=data["effect_type"],
            activation=data["activation"],
            buy_price=data["buy_price"],
            sell_price=data["sell_price"],
            in_shop=data["in_shop"],
            has_negative_variant=data["has_negative_variant"],
            negative_image_url=negative_image_url,
            is_copyable=data["is_copyable"],
            is_perishable=data["is_perishable"],
            is_eternal=data["is_eternal"],
        )
        db.session.add(unlockable)
        click.echo(f"  + Created: #{data['item_number']:>3} {data['name']}")


# ──────────────────────────────────────────────────────────────────────
#  Seeder: consumables (Tarots, Planets, Spectrals)
# ──────────────────────────────────────────────────────────────────────


# Categorías de la wiki que mapean a la tabla `consumables`. Las tres
# comparten la plantilla `Consumable info`, lo que permite usar un único
# parser y una única tabla; el campo `type` del padre Unlockable
# discrimina cuál es cuál.
_CONSUMABLE_CATEGORIES = [
    ("Tarot Cards", "tarot"),
    ("Planet Cards", "planet"),
    ("Spectral Cards", "spectral"),
]


def seed_consumables(dry_run: bool, limit: int | None) -> int:
    """Pobla Tarots, Planets y Spectrals desde sus categorías respectivas.

    Aunque las tres categorías comparten plantilla, viven en categorías
    separadas en la wiki. Iteramos las tres, parseamos con el mismo
    `parse_consumable` y validamos que el tipo extraído coincida con la
    categoría (sanity check defensivo contra plantillas mal categorizadas).

    Returns:
        Número total de consumibles procesados (los tres tipos sumados).
    """
    total = 0
    for category, expected_type in _CONSUMABLE_CATEGORIES:
        titles = wiki.list_pages_in_category(category)
        titles = _filter_category_index_pages(titles, category)
        if limit is not None:
            titles = titles[:limit]

        click.echo(
            f"  Found {len(titles)} {expected_type} pages in Category:{category}"
        )

        for title in titles:
            try:
                wikitext = wiki.fetch_wikitext(title)
                if not wikitext:
                    click.secho(f"  ⚠ No wikitext for {title!r}", fg="yellow")
                    continue

                data = wiki.parse_consumable(wikitext)
                if not data:
                    click.secho(
                        f"  ⚠ Page lacks 'Consumable info' template: {title!r}",
                        fg="yellow",
                    )
                    continue

                data = _apply_overrides(data)

                if data.get("item_number") is None:
                    click.secho(f"  ⚠ Skipped (no item_number): {title!r}", fg="yellow")
                    continue

                if data["type"] != expected_type:
                    click.secho(
                        f"  ⚠ Type mismatch for {title!r}: "
                        f"expected {expected_type!r}, got {data['type']!r}",
                        fg="yellow",
                    )
                    continue

                _upsert_consumable(data, title)

                if not dry_run:
                    db.session.commit()

                total += 1
            except Exception as e:
                db.session.rollback()
                click.secho(f"  ✗ Error processing {title!r}: {e}", fg="red")
                logger.exception("Failed processing %s", title)
                continue

    if dry_run:
        db.session.rollback()
        click.secho("  (dry-run: changes rolled back)", fg="yellow")

    return total


def _upsert_consumable(data: dict, title: str) -> None:
    """Inserta o actualiza un Consumable (Tarot, Planet o Spectral) en la BD."""
    image_url = (
        wiki.resolve_image_url(data["image_filename"])
        if data.get("image_filename")
        else None
    )

    consumable_type = UnlockableType(data["type"])  # 'tarot'/'planet'/'spectral'

    existing = Unlockable.query.filter_by(
        type=consumable_type,
        item_number=data["item_number"],
    ).first()

    if existing is not None:
        # Detección defensiva de colisión por item_number duplicado.
        # Si el registro existente tiene OTRO nombre, es porque dos páginas de la
        # wiki comparten el mismo number (error de la fuente). Skipeamos para
        # no pisar el primer registro insertado.
        if existing.name != data["name"]:
            click.secho(
                f"  ⚠ Number collision: {data['type']} #{data['item_number']} "
                f"already taken by {existing.name!r}, skipping {data['name']!r}",
                fg="yellow",
            )
            return

        # ── Actualizar registro existente (mismo nombre = misma carta) ──
        existing.name = data["name"]
        existing.description = data["description"]
        existing.image_url = image_url
        existing.unlock_condition = data["unlock_condition"]
        existing.wiki_url = wiki.page_url(title)

        c = existing.consumable
        c.buy_price = data["buy_price"]
        c.sell_price = data["sell_price"]
        c.in_shop = data["in_shop"]

        click.echo(
            f"  ↻ Updated: [{data['type']:>8}] "
            f"#{data['item_number']:>3} {data['name']}"
        )
    else:
        unlockable = Unlockable(
            type=consumable_type,
            item_number=data["item_number"],
            name=data["name"],
            description=data["description"],
            image_url=image_url,
            unlock_condition=data["unlock_condition"],
            wiki_url=wiki.page_url(title),
        )
        unlockable.consumable = Consumable(
            buy_price=data["buy_price"],
            sell_price=data["sell_price"],
            in_shop=data["in_shop"],
        )
        db.session.add(unlockable)
        click.echo(
            f"  + Created: [{data['type']:>8}] "
            f"#{data['item_number']:>3} {data['name']}"
        )


# ──────────────────────────────────────────────────────────────────────
#  Seeder: decks
# ──────────────────────────────────────────────────────────────────────


def seed_decks(dry_run: bool, limit: int | None) -> int:
    """Pobla las Decks desde ``Category:Decks`` de la wiki.

    Returns:
        Número de decks procesados.
    """
    titles = wiki.list_pages_in_category("Decks")
    titles = _filter_category_index_pages(titles, "Decks")

    if limit is not None:
        titles = titles[:limit]

    click.echo(f"  Found {len(titles)} deck pages in Category:Decks")

    count = 0
    for title in titles:
        try:
            wikitext = wiki.fetch_wikitext(title)
            if not wikitext:
                click.secho(f"  ⚠ No wikitext for {title!r}", fg="yellow")
                continue

            data = wiki.parse_deck(wikitext)
            if not data:
                click.secho(
                    f"  ⚠ Page lacks 'Deck info' template: {title!r}",
                    fg="yellow",
                )
                continue

            data = _apply_overrides(data)

            if data.get("item_number") is None:
                click.secho(
                    f"  ⚠ Skipped meta-page (no item_number): {title!r}",
                    fg="yellow",
                )
                continue

            _upsert_deck(data, title)

            if not dry_run:
                db.session.commit()

            count += 1
        except Exception as e:
            db.session.rollback()
            click.secho(f"  ✗ Error processing {title!r}: {e}", fg="red")
            logger.exception("Failed processing %s", title)
            continue

    if dry_run:
        db.session.rollback()
        click.secho("  (dry-run: changes rolled back)", fg="yellow")

    return count


def _upsert_deck(data: dict, title: str) -> None:
    """Inserta o actualiza una Deck en la BD.

    Las Decks no tienen campos específicos en la tabla `decks` (toda la
    información cabe en el padre Unlockable). La fila hija existe solo
    para anclar el FK con tipado consistente.
    """
    image_url = (
        wiki.resolve_image_url(data["image_filename"])
        if data.get("image_filename")
        else None
    )

    existing = Unlockable.query.filter_by(
        type=UnlockableType.DECK,
        item_number=data["item_number"],
    ).first()

    if existing is not None:
        existing.name = data["name"]
        existing.description = data["description"]
        existing.image_url = image_url
        existing.unlock_condition = data["unlock_condition"]
        existing.wiki_url = wiki.page_url(title)
        click.echo(f"  ↻ Updated: #{data['item_number']:>3} {data['name']}")
    else:
        unlockable = Unlockable(
            type=UnlockableType.DECK,
            item_number=data["item_number"],
            name=data["name"],
            description=data["description"],
            image_url=image_url,
            unlock_condition=data["unlock_condition"],
            wiki_url=wiki.page_url(title),
        )
        unlockable.deck = Deck()
        db.session.add(unlockable)
        click.echo(f"  + Created: #{data['item_number']:>3} {data['name']}")


# ──────────────────────────────────────────────────────────────────────
#  Seeder: vouchers
# ──────────────────────────────────────────────────────────────────────


def seed_vouchers(dry_run: bool, limit: int | None) -> int:
    """Pobla los Vouchers desde ``Category:Vouchers`` de la wiki.

    Implementación en dos pasadas:

      1. **Pass 1**: inserta o actualiza cada Voucher con sus campos básicos
         (nombre, descripción, tier, etc.), pero deja ``next_voucher_id`` a
         ``None``. Aquí no podemos resolverlo porque el voucher al que apunta
         puede no existir todavía en la BD.

      2. **Pass 2**: con todos los vouchers ya insertados, resuelve cada
         enlace ``base.next_voucher_name`` → ``upgrade.id`` consultando por
         nombre y actualiza la columna ``next_voucher_id``.

    Particularidad: la plantilla ``Voucher info`` de la wiki **no incluye
    campo ``number``**, así que asignamos ``item_number`` nosotros con
    ``_next_voucher_number()``. Para preservar idempotencia entre runs, el
    upsert busca primero por ``name`` (estable) y reutiliza el número
    existente; solo cuando es un voucher nuevo se asigna el siguiente libre.

    Returns:
        Número de vouchers procesados (insertados o actualizados).
    """
    titles = wiki.list_pages_in_category("Vouchers")
    titles = _filter_category_index_pages(titles, "Vouchers")

    if limit is not None:
        titles = titles[:limit]

    click.echo(f"  Found {len(titles)} voucher pages in Category:Vouchers")

    # ── PASS 1: upsert básico, sin resolver la cadena ──
    click.secho("  Pass 1/2: upserting vouchers...", fg="white")

    # base_name → next_voucher_name (recolectado durante el pass 1)
    chain_links: dict[str, str] = {}
    count = 0

    for title in titles:
        try:
            wikitext = wiki.fetch_wikitext(title)
            if not wikitext:
                click.secho(f"  ⚠ No wikitext for {title!r}", fg="yellow")
                continue

            data = wiki.parse_voucher(wikitext)
            if not data:
                click.secho(
                    f"  ⚠ Page lacks 'Voucher info' template: {title!r}",
                    fg="yellow",
                )
                continue

            data = _apply_overrides(data)

            # Recolecta el enlace de cadena para el pass 2
            if data.get("next_voucher_name"):
                chain_links[data["name"]] = data["next_voucher_name"]

            _upsert_voucher(data, title)

            if not dry_run:
                db.session.commit()

            count += 1
        except Exception as e:
            db.session.rollback()
            click.secho(f"  ✗ Error processing {title!r}: {e}", fg="red")
            logger.exception("Failed processing %s", title)
            continue

    # ── PASS 2: resolver la cadena Base → Upgraded ──
    if chain_links:
        click.echo()
        click.secho(
            f"  Pass 2/2: resolving {len(chain_links)} chain links...",
            fg="white",
        )

        for base_name, next_name in chain_links.items():
            try:
                base = Unlockable.query.filter_by(
                    type=UnlockableType.VOUCHER,
                    name=base_name,
                ).first()
                nxt = Unlockable.query.filter_by(
                    type=UnlockableType.VOUCHER,
                    name=next_name,
                ).first()

                if base is None or nxt is None:
                    click.secho(
                        f"  ⚠ Cannot link {base_name!r} → {next_name!r} "
                        f"(voucher missing in DB)",
                        fg="yellow",
                    )
                    continue

                base.voucher.next_voucher_id = nxt.id

                if not dry_run:
                    db.session.commit()

                click.echo(f"  → {base_name!r} → {next_name!r}")
            except Exception as e:
                db.session.rollback()
                click.secho(f"  ✗ Error linking {base_name!r}: {e}", fg="red")
                logger.exception("Failed linking %s", base_name)
                continue

    if dry_run:
        db.session.rollback()
        click.secho("  (dry-run: changes rolled back)", fg="yellow")

    return count


def _next_item_number_for_type(type_value: UnlockableType) -> int:
    """Devuelve el siguiente item_number libre para un tipo de Unlockable.

    Generalización utilizada por los seeders cuyos items no traen ``number``
    explícito en la wiki (Vouchers y Booster Packs). Consulta el máximo
    actual en BD para ese ``type`` y devuelve ``max + 1``.
    """
    max_n = (
        db.session.query(func.max(Unlockable.item_number))
        .filter(Unlockable.type == type_value)
        .scalar()
    )
    return (max_n or 0) + 1


def _next_voucher_number() -> int:
    """Devuelve el siguiente ``item_number`` libre para un Voucher.

    Como ``Voucher info`` no expone número en la wiki, asignamos uno
    secuencial por orden de inserción. Consulta el máximo actual en BD y
    devuelve ``max + 1``. Para el primer voucher de la BD devuelve 1.
    """
    max_n = (
        db.session.query(func.max(Unlockable.item_number))
        .filter(Unlockable.type == UnlockableType.VOUCHER)
        .scalar()
    )
    return (max_n or 0) + 1


def _upsert_voucher(data: dict, title: str) -> None:
    """Inserta o actualiza un Voucher en la BD.

    A diferencia de los otros upserts, este busca primero por ``name`` (no
    por ``item_number``) porque el item_number lo asignamos nosotros y no
    queremos pisarlo en re-runs. Si el voucher es nuevo, asigna el siguiente
    número libre con ``_next_voucher_number()``.

    El campo ``next_voucher_id`` NO se rellena aquí: se gestiona en el
    pass 2 de ``seed_vouchers``, una vez todos los vouchers están en BD.
    """
    image_url = (
        wiki.resolve_image_url(data["image_filename"])
        if data.get("image_filename")
        else None
    )

    voucher_tier = VoucherTier(data["voucher_tier"])  # 'Base' o 'Upgraded'

    # Búsqueda por nombre (más estable que item_number, que asignamos nosotros)
    existing = Unlockable.query.filter_by(
        type=UnlockableType.VOUCHER,
        name=data["name"],
    ).first()

    if existing is not None:
        # Mantén el item_number ya asignado en runs anteriores
        existing.description = data["description"]
        existing.image_url = image_url
        existing.unlock_condition = data["unlock_condition"]
        existing.wiki_url = wiki.page_url(title)
        existing.voucher.voucher_tier = voucher_tier
        existing.voucher.buy_price = data.get("buy_price")
        # next_voucher_id se gestiona en el pass 2

        click.echo(
            f"  ↻ Updated: [{voucher_tier.value:>8}] "
            f"#{existing.item_number:>3} {data['name']}"
        )
    else:
        # Voucher nuevo: asigna el siguiente número disponible
        next_num = _next_voucher_number()

        unlockable = Unlockable(
            type=UnlockableType.VOUCHER,
            item_number=next_num,
            name=data["name"],
            description=data["description"],
            image_url=image_url,
            unlock_condition=data["unlock_condition"],
            wiki_url=wiki.page_url(title),
        )
        unlockable.voucher = Voucher(
            voucher_tier=voucher_tier,
            next_voucher_id=None,  # se rellena en pass 2
            buy_price=data.get("buy_price"),
        )
        db.session.add(unlockable)
        click.echo(
            f"  + Created: [{voucher_tier.value:>8}] " f"#{next_num:>3} {data['name']}"
        )


# ──────────────────────────────────────────────────────────────────────
#  Seeder: achievements (vía Steam Web API, no la wiki)
# ──────────────────────────────────────────────────────────────────────


def seed_achievements(dry_run: bool, limit: int | None) -> int:
    """Pobla la tabla de Achievements desde la Steam Web API.

    A diferencia de los otros seeders (que usan la wiki de Balatro), este
    obtiene los datos canónicos directamente de Steam. La fuente es más
    estable: los nombres internos (``BAL_01``, ``BAL_02``...) no cambian
    aunque el desarrollador renombre o reescriba la descripción visible
    de un logro.

    Returns:
        Número de achievements procesados (creados o actualizados).
    """
    click.echo("  Fetching achievement schema from Steam Web API...")

    try:
        achievements = steam.fetch_game_achievements_schema()
    except steam.SteamAPIKeyMissing as e:
        click.secho(f"  ✗ {e}", fg="red")
        raise click.Abort()
    except steam.SteamAPIError as e:
        click.secho(f"  ✗ Steam API error: {e}", fg="red")
        raise click.Abort()

    if not achievements:
        click.secho("  ⚠ Steam returned 0 achievements", fg="yellow")
        return 0

    click.echo(f"  Got {len(achievements)} achievements from Steam")

    if limit is not None:
        achievements = achievements[:limit]

    count = 0
    for ach in achievements:
        try:
            _upsert_achievement(ach)

            if not dry_run:
                db.session.commit()

            count += 1
        except Exception as e:
            db.session.rollback()
            click.secho(
                f"  ✗ Error processing {ach.get('name', '?')!r}: {e}",
                fg="red",
            )
            logger.exception("Failed processing %s", ach.get("name"))
            continue

    if dry_run:
        db.session.rollback()
        click.secho("  (dry-run: changes rolled back)", fg="yellow")

    return count


def _upsert_achievement(ach: dict) -> None:
    """Inserta o actualiza un Achievement en la BD.

    Usa el campo interno ``name`` de Steam (p.ej. ``"BAL_01"``) como clave
    estable de upsert: este identificador no cambia aunque Steam renombre
    el achievement visible. ``displayName`` se almacena como nombre humano.

    Solo se persiste el icono coloreado (``icon``); el gris (``icongray``)
    se omite. El frontend aplicará ``filter: grayscale(100%)`` mediante CSS
    para representar el estado bloqueado, evitando una columna extra en BD.
    """
    steam_name = ach["name"]
    display_name = ach.get("displayName", steam_name)
    description = ach.get("description") or ""
    icon_url = ach.get("icon")
    hidden = bool(ach.get("hidden", 0))

    existing = Achievement.query.filter_by(steam_api_name=steam_name).first()

    if existing is not None:
        existing.name = display_name
        existing.description = description
        existing.icon_url = icon_url
        existing.hidden = hidden
        click.echo(f"  ↻ Updated: {steam_name:<8} {display_name}")
    else:
        db.session.add(
            Achievement(
                steam_api_name=steam_name,
                name=display_name,
                description=description,
                icon_url=icon_url,
                hidden=hidden,
            )
        )
        click.echo(f"  + Created: {steam_name:<8} {display_name}")


# ──────────────────────────────────────────────────────────────────────
#  Seeder: booster packs (parser de wikitable, página única)
# ──────────────────────────────────────────────────────────────────────


def seed_booster_packs(dry_run: bool, limit: int | None) -> int:
    """Pobla los Booster Packs desde la página única 'Booster Packs' de la wiki.

    A diferencia del resto de seeders (que iteran páginas individuales de
    una categoría), aquí descargamos UNA sola página y el parser de
    wikitable nos devuelve la lista de los 15 packs en una sola pasada.

    Particularidades:
      - La wiki no asigna ``item_number`` a los packs, así que se asigna
        secuencialmente con ``_next_item_number_for_type()`` y se preserva
        entre runs gracias a la búsqueda por ``name`` en el upsert.
      - Todos los packs comparten ``wiki_url`` (apuntan a la misma página)
        y ``unlock_condition = "Available from start."`` (siempre disponibles).

    Returns:
        Número de packs procesados (creados o actualizados).
    """
    click.echo("  Fetching 'Booster Packs' page from wiki...")

    wikitext = wiki.fetch_wikitext("Booster Packs")
    if not wikitext:
        click.secho("  ✗ Could not fetch 'Booster Packs' page", fg="red")
        return 0

    packs = wiki.parse_booster_packs_page(wikitext)
    if not packs:
        click.secho(
            "  ⚠ Parser returned 0 packs (¿cambió el formato de la página?)",
            fg="yellow",
        )
        return 0

    click.echo(f"  Parsed {len(packs)} booster packs from the table")

    if limit is not None:
        packs = packs[:limit]

    count = 0
    for data in packs:
        try:
            _upsert_booster_pack(data)

            if not dry_run:
                db.session.commit()

            count += 1
        except Exception as e:
            db.session.rollback()
            click.secho(
                f"  ✗ Error processing {data.get('name', '?')!r}: {e}",
                fg="red",
            )
            logger.exception("Failed processing %s", data.get("name"))
            continue

    if dry_run:
        db.session.rollback()
        click.secho("  (dry-run: changes rolled back)", fg="yellow")

    return count


def _upsert_booster_pack(data: dict) -> None:
    """Inserta o actualiza un Booster Pack en la BD.

    Como la wiki no asigna ``item_number`` a los Booster Packs, la búsqueda
    de existentes se hace por ``name`` (estable entre runs). Si es un pack
    nuevo, se asigna el siguiente número disponible.

    Todos los packs son siempre comprables ("Available from start"), por lo
    que ``unlock_condition`` se rellena con ese valor constante y
    ``wiki_url`` apunta a la página común 'Booster Packs'.
    """
    image_url = (
        wiki.resolve_image_url(data["image_filename"])
        if data.get("image_filename")
        else None
    )

    pack_type = BoosterPackType(data["pack_type"])  # Arcana / Celestial / ...
    size = BoosterPackSize(data["size"])  # Normal / Jumbo / Mega

    # Búsqueda por nombre (estable: no depende del item_number autogenerado)
    existing = Unlockable.query.filter_by(
        type=UnlockableType.BOOSTER_PACK,
        name=data["name"],
    ).first()

    if existing is not None:
        existing.description = data["description"]
        existing.image_url = image_url
        existing.unlock_condition = "Available from start."
        existing.wiki_url = wiki.page_url("Booster Packs")

        bp = existing.booster_pack
        bp.pack_type = pack_type
        bp.size = size
        bp.cost = data["cost"]

        click.echo(
            f"  ↻ Updated: [{pack_type.value:>9} {size.value:>6}] "
            f"#{existing.item_number:>2} {data['name']}"
        )
    else:
        next_num = _next_item_number_for_type(UnlockableType.BOOSTER_PACK)

        unlockable = Unlockable(
            type=UnlockableType.BOOSTER_PACK,
            item_number=next_num,
            name=data["name"],
            description=data["description"],
            image_url=image_url,
            unlock_condition="Available from start.",
            wiki_url=wiki.page_url("Booster Packs"),
        )
        unlockable.booster_pack = BoosterPack(
            pack_type=pack_type,
            size=size,
            cost=data["cost"],
        )
        db.session.add(unlockable)
        click.echo(
            f"  + Created: [{pack_type.value:>9} {size.value:>6}] "
            f"#{next_num:>2} {data['name']}"
        )


# ──────────────────────────────────────────────────────────────────────
#  Seeder: challenge_decks
# ──────────────────────────────────────────────────────────────────────


# Texto común para unlock_condition de TODOS los Challenge Decks.
# La mecánica del juego es: los primeros 5 se desbloquean al ganar con
# 5 barajas distintas, los siguientes 15 al completar challenges previos.
# Esta condición no aparece en la plantilla individual; se aplica aquí
# como regla compartida.
_CHALLENGE_DECK_UNLOCK_CONDITION = (
    "Challenge Mode is unlocked by winning a regular run with five "
    "different decks. The first 5 challenges become available then; each "
    "subsequent challenge unlocks after winning a run with a previous one."
)


def seed_challenge_decks(dry_run: bool, limit: int | None) -> int:
    """Pobla los Challenge Decks desde ``Category:Challenges`` de la wiki.

    Returns:
        Número de challenge decks procesados (insertados o actualizados).
    """
    titles = wiki.list_pages_in_category("Challenges")

    # Filtra páginas índice (overview, list of...) que estén categorizadas
    # como Challenges pero no sean challenges individuales.
    titles = _filter_category_index_pages(titles, "Challenges")

    # Filtros adicionales: la página meta "Challenge Deck" usa la plantilla
    # 'Deck info' (no 'Challenge info'), está en otra categoría conceptual,
    # y describe el tema entero, no un challenge concreto. Excluida defensiva.
    EXTRA_INDEX_PAGES = {"Challenge Deck", "Challenge Decks"}
    titles = [t for t in titles if t not in EXTRA_INDEX_PAGES]

    if limit is not None:
        titles = titles[:limit]

    click.echo(f"  Found {len(titles)} challenge pages in Category:Challenges")

    count = 0
    for title in titles:
        try:
            wikitext = wiki.fetch_wikitext(title)
            if not wikitext:
                click.secho(f"  ⚠ No wikitext for {title!r}", fg="yellow")
                continue

            data = wiki.parse_challenge_deck(wikitext)
            if not data:
                click.secho(
                    f"  ⚠ Page lacks 'Challenge info' template: {title!r}",
                    fg="yellow",
                )
                continue

            data = _apply_overrides(data)

            if data.get("item_number") is None:
                click.secho(f"  ⚠ Skipped (no item_number): {title!r}", fg="yellow")
                continue

            _upsert_challenge_deck(data, title)

            if not dry_run:
                db.session.commit()

            count += 1
        except Exception as e:
            db.session.rollback()
            click.secho(f"  ✗ Error processing {title!r}: {e}", fg="red")
            logger.exception("Failed processing %s", title)
            continue

    if dry_run:
        db.session.rollback()
        click.secho("  (dry-run: changes rolled back)", fg="yellow")

    return count


def _upsert_challenge_deck(data: dict, title: str) -> None:
    """Inserta o actualiza un Challenge Deck en la BD.

    A diferencia de los items con plantillas más estándar, los Challenge Decks
    componen su ``unlockable.description`` a partir del campo ``modifier`` de
    la plantilla (que recoge las reglas modificadas; lo más equivalente a una
    "descripción funcional"). Los campos específicos (modifier, starter,
    banned, deck_description) se almacenan también en la tabla hija
    ``challenge_decks`` para queries más detalladas en el frontend.

    Como la plantilla no expone imagen y la condición de desbloqueo es común
    a todos, ``image_url = None`` y ``unlock_condition`` se rellenan con el
    texto compartido ``_CHALLENGE_DECK_UNLOCK_CONDITION``.
    """
    existing = Unlockable.query.filter_by(
        type=UnlockableType.CHALLENGE_DECK,
        item_number=data["item_number"],
    ).first()

    if existing is not None:
        # Detección defensiva de colisión (el mismo number en dos challenges)
        if existing.name != data["name"]:
            click.secho(
                f"  ⚠ Number collision: challenge_deck #{data['item_number']} "
                f"already taken by {existing.name!r}, skipping {data['name']!r}",
                fg="yellow",
            )
            return

        existing.name = data["name"]
        existing.description = data["modifier"]
        existing.image_url = None
        existing.unlock_condition = _CHALLENGE_DECK_UNLOCK_CONDITION
        existing.wiki_url = wiki.page_url(title)

        cd = existing.challenge_deck
        cd.modifier = data["modifier"]
        cd.starter = data["starter"]
        cd.banned = data["banned"]
        cd.deck_description = data["deck_description"]

        click.echo(f"  ↻ Updated: #{data['item_number']:>2} {data['name']}")
    else:
        unlockable = Unlockable(
            type=UnlockableType.CHALLENGE_DECK,
            item_number=data["item_number"],
            name=data["name"],
            description=data["modifier"],
            image_url=None,
            unlock_condition=_CHALLENGE_DECK_UNLOCK_CONDITION,
            wiki_url=wiki.page_url(title),
        )
        unlockable.challenge_deck = ChallengeDeck(
            modifier=data["modifier"],
            starter=data["starter"],
            banned=data["banned"],
            deck_description=data["deck_description"],
        )
        db.session.add(unlockable)
        click.echo(f"  + Created: #{data['item_number']:>2} {data['name']}")


# ──────────────────────────────────────────────────────────────────────
#  Seeders: stakes, blinds, tags (reference data)
# ──────────────────────────────────────────────────────────────────────


def seed_stakes(dry_run: bool, limit: int | None) -> int:
    """Pobla la tabla ``stakes`` desde la página única 'Stakes' de la wiki."""
    click.echo("  Fetching 'Stakes' page from wiki...")

    wikitext = wiki.fetch_wikitext("Stakes")
    if not wikitext:
        click.secho("  ✗ Could not fetch 'Stakes' page", fg="red")
        return 0

    stakes = wiki.parse_stakes_page(wikitext)
    if not stakes:
        click.secho("  ⚠ Parser returned 0 stakes", fg="yellow")
        return 0

    click.echo(f"  Parsed {len(stakes)} stakes from the page")

    if limit is not None:
        stakes = stakes[:limit]

    count = 0
    for data in stakes:
        try:
            _upsert_stake(data)

            if not dry_run:
                db.session.commit()

            count += 1
        except Exception as e:
            db.session.rollback()
            click.secho(
                f"  ✗ Error processing {data.get('name', '?')!r}: {e}",
                fg="red",
            )
            logger.exception("Failed processing %s", data.get("name"))
            continue

    if dry_run:
        db.session.rollback()
        click.secho("  (dry-run: changes rolled back)", fg="yellow")

    return count


def _upsert_stake(data: dict) -> None:
    """Inserta o actualiza un Stake en la BD."""
    image_url = (
        wiki.resolve_image_url(data["image_filename"])
        if data.get("image_filename")
        else None
    )

    existing = Stake.query.filter_by(name=data["name"]).first()

    if existing is not None:
        existing.stake_order = data["stake_order"]
        existing.color = data["color"]
        existing.effect_description = data["effect_description"]
        existing.image_url = image_url
        existing.unlocks_deck_name = data["unlocks_deck_name"]
        existing.wiki_url = wiki.page_url("Stakes")
        click.echo(
            f"  ↻ Updated: #{data['stake_order']} {data['name']:<15} "
            f"unlocks={data['unlocks_deck_name'] or '—'}"
        )
    else:
        stake = Stake(
            name=data["name"],
            stake_order=data["stake_order"],
            color=data["color"],
            effect_description=data["effect_description"],
            image_url=image_url,
            unlocks_deck_name=data["unlocks_deck_name"],
            wiki_url=wiki.page_url("Stakes"),
        )
        db.session.add(stake)
        click.echo(
            f"  + Created: #{data['stake_order']} {data['name']:<15} "
            f"unlocks={data['unlocks_deck_name'] or '—'}"
        )


# Small Blind y Big Blind a menudo no tienen página individual con plantilla
# Blind info; los hardcodeamos como datos canónicos del juego para garantizar
# que aparezcan en BD.
_HARDCODED_NON_BOSS_BLINDS = [
    {
        "name": "Small Blind",
        "image_filename": "Small Blind.png",
        "blind_type": "Small",
        "description": "First blind of each Ante. Skippable for a Tag.",
        "ante": "Any",
        "score_multiplier": 1.0,
        "reward_money": 3,
        "matador_compatible": True,
    },
    {
        "name": "Big Blind",
        "image_filename": "Big Blind.png",
        "blind_type": "Big",
        "description": "Second blind of each Ante. Skippable for a Tag.",
        "ante": "Any",
        "score_multiplier": 1.5,
        "reward_money": 4,
        "matador_compatible": True,
    },
]


# Nombres conocidos de Finisher Blinds (los que aparecen solo en Ante 8).
# Se incluyen explícitamente porque a veces no están en `Category:Boss Blinds`
# y la wiki los cataloga en una categoría aparte (`Category:Finisher Blinds`)
# o no los cataloga consistentemente. Añadirlos por nombre garantiza su
# presencia en la BD aunque la estructura de la wiki cambie.
_KNOWN_FINISHER_BLINDS = {
    "Amber Acorn",
    "Verdant Leaf",
    "Violet Vessel",
    "Crimson Heart",
    "Cerulean Bell",
}


def seed_blinds(dry_run: bool, limit: int | None) -> int:
    """Pobla la tabla ``blinds`` desde múltiples fuentes.

    Estrategia (más robusta que la versión inicial):
      1. Small + Big Blinds desde lista hardcoded (no tienen variedad).
      2. Boss Blinds desde ``Category:Boss Blinds``.
      3. Finisher Blinds desde ``Category:Finisher Blinds`` (si existe).
      4. Los 5 nombres conocidos de finishers (red defensiva por si la
         wiki no los cataloga en ninguna categoría).

    Los duplicados entre las distintas fuentes se eliminan por nombre
    antes del procesamiento, así que un blind cubierto por varias fuentes
    solo se procesa una vez.
    """
    # Pass 1: hardcoded Small + Big
    blinds_to_process = list(_HARDCODED_NON_BOSS_BLINDS)

    # Pass 2: recolecta títulos de todas las fuentes posibles
    click.echo("  Collecting blind page titles from wiki categories...")
    all_titles: set[str] = set()

    for category in ("Boss Blinds", "Finisher Blinds"):
        try:
            titles = wiki.list_pages_in_category(category)
            count = len(titles)
            all_titles.update(titles)
            click.echo(f"    Category:{category} -> {count} pages")
        except Exception as e:
            click.secho(f"    Category:{category} -> error: {e}", fg="yellow")

    # Red defensiva: los 5 finishers conocidos siempre se incluyen.
    all_titles.update(_KNOWN_FINISHER_BLINDS)

    # Filtra páginas índice (overview, list of...)
    titles = _filter_category_index_pages(list(all_titles), "Boss Blinds")
    titles = _filter_category_index_pages(titles, "Finisher Blinds")

    click.echo(f"  Total unique blind pages to process: {len(titles)}")

    # Pass 3: fetch + parse cada blind, acumula en blinds_to_process
    for title in titles:
        try:
            wikitext = wiki.fetch_wikitext(title)
            if not wikitext:
                click.secho(f"  ⚠ No wikitext for {title!r}", fg="yellow")
                continue
            data = wiki.parse_blind(wikitext)
            if not data:
                click.secho(f"  ⚠ {title!r}: no Blind info template", fg="yellow")
                continue
            blinds_to_process.append(data)
        except Exception as e:
            click.secho(f"  ✗ Error fetching {title!r}: {e}", fg="red")
            logger.exception("Failed fetching %s", title)
            continue

    if limit is not None:
        blinds_to_process = blinds_to_process[:limit]

    # Pass 4: upsert
    count = 0
    for data in blinds_to_process:
        try:
            _upsert_blind(data)
            if not dry_run:
                db.session.commit()
            count += 1
        except Exception as e:
            db.session.rollback()
            click.secho(
                f"  ✗ Error processing {data.get('name', '?')!r}: {e}",
                fg="red",
            )
            logger.exception("Failed processing %s", data.get("name"))
            continue

    if dry_run:
        db.session.rollback()
        click.secho("  (dry-run: changes rolled back)", fg="yellow")

    return count


def _upsert_blind(data: dict) -> None:
    """Inserta o actualiza un Blind en la BD."""
    image_url = (
        wiki.resolve_image_url(data["image_filename"])
        if data.get("image_filename")
        else None
    )

    blind_type = BlindType(data["blind_type"])

    existing = Blind.query.filter_by(name=data["name"]).first()

    if existing is not None:
        existing.blind_type = blind_type
        existing.description = data["description"]
        existing.image_url = image_url
        existing.ante = data["ante"]
        existing.score_multiplier = data["score_multiplier"]
        existing.reward_money = data["reward_money"]
        existing.matador_compatible = data["matador_compatible"]
        existing.wiki_url = (
            wiki.page_url(data["name"])
            if blind_type == BlindType.BOSS
            else wiki.page_url("Blinds and Antes")
        )
        click.echo(
            f"  ↻ Updated: [{blind_type.value:>5}] {data['name']:<25} "
            f"score={data['score_multiplier']}"
        )
    else:
        blind = Blind(
            name=data["name"],
            image_url=image_url,
            blind_type=blind_type,
            description=data["description"],
            ante=data["ante"],
            score_multiplier=data["score_multiplier"],
            reward_money=data["reward_money"],
            matador_compatible=data["matador_compatible"],
            wiki_url=(
                wiki.page_url(data["name"])
                if blind_type == BlindType.BOSS
                else wiki.page_url("Blinds and Antes")
            ),
        )
        db.session.add(blind)
        click.echo(
            f"  + Created: [{blind_type.value:>5}] {data['name']:<25} "
            f"score={data['score_multiplier']}"
        )


def seed_tags(dry_run: bool, limit: int | None) -> int:
    """Pobla la tabla ``tags`` iterando Category:Tags."""
    titles = wiki.list_pages_in_category("Tags")
    titles = _filter_category_index_pages(titles, "Tags")

    if limit is not None:
        titles = titles[:limit]

    click.echo(f"  Found {len(titles)} tag pages in Category:Tags")

    count = 0
    for title in titles:
        try:
            wikitext = wiki.fetch_wikitext(title)
            if not wikitext:
                click.secho(f"  ⚠ No wikitext for {title!r}", fg="yellow")
                continue

            data = wiki.parse_tag(wikitext)
            if not data:
                click.secho(
                    f"  ⚠ Page lacks 'Tag info' template: {title!r}",
                    fg="yellow",
                )
                continue

            _upsert_tag(data, title)

            if not dry_run:
                db.session.commit()

            count += 1
        except Exception as e:
            db.session.rollback()
            click.secho(f"  ✗ Error processing {title!r}: {e}", fg="red")
            logger.exception("Failed processing %s", title)
            continue

    if dry_run:
        db.session.rollback()
        click.secho("  (dry-run: changes rolled back)", fg="yellow")

    return count


def _upsert_tag(data: dict, title: str) -> None:
    """Inserta o actualiza un Tag en la BD."""
    image_url = (
        wiki.resolve_image_url(data["image_filename"])
        if data.get("image_filename")
        else None
    )

    existing = Tag.query.filter_by(name=data["name"]).first()

    if existing is not None:
        existing.description = data["description"]
        existing.image_url = image_url
        existing.ante = data["ante"]
        existing.unlock_condition = data["unlock_condition"]
        existing.wiki_url = wiki.page_url(title)
        click.echo(f"  ↻ Updated: {data['name']}")
    else:
        tag = Tag(
            name=data["name"],
            description=data["description"],
            image_url=image_url,
            ante=data["ante"],
            unlock_condition=data["unlock_condition"],
            wiki_url=wiki.page_url(title),
        )
        db.session.add(tag)
        click.echo(f"  + Created: {data['name']}")


# ──────────────────────────────────────────────────────────────────────
#  Seeder: card_modifiers (Enhancements, Editions, Seals)
# ──────────────────────────────────────────────────────────────────────


# Mapeo categoría wiki → valor esperado en `modifier_type` del template.
# Sirve como sanity check defensivo: si una página categorizada bajo
# Editions tiene type=Seal en su template, se reporta como anomalía.
_MODIFIER_CATEGORIES = [
    ("Enhancements", "Enhancement"),
    ("Editions", "Edition"),
    ("Seals", "Seal"),
]


def seed_card_modifiers(dry_run: bool, limit: int | None) -> int:
    """Pobla la tabla ``card_modifiers`` iterando 3 categorías wiki.

    Los tres tipos (Enhancement, Edition, Seal) comparten plantilla
    `{{Modifier info}}` y se unifican en una sola tabla discriminada
    por ``modifier_type``, replicando el patrón ya usado en consumables.

    Returns:
        Número total de modifiers procesados (los tres tipos sumados).
    """
    total = 0

    for category, expected_type in _MODIFIER_CATEGORIES:
        try:
            titles = wiki.list_pages_in_category(category)
        except Exception as e:
            click.secho(f"  ✗ Error fetching Category:{category}: {e}", fg="red")
            continue

        titles = _filter_category_index_pages(titles, category)

        if limit is not None:
            titles = titles[:limit]

        click.echo(
            f"  Found {len(titles)} {expected_type} pages " f"in Category:{category}"
        )

        for title in titles:
            try:
                wikitext = wiki.fetch_wikitext(title)
                if not wikitext:
                    click.secho(f"  ⚠ No wikitext for {title!r}", fg="yellow")
                    continue

                data = wiki.parse_card_modifier(wikitext)
                if not data:
                    click.secho(
                        f"  ⚠ Page lacks 'Modifier info' template: {title!r}",
                        fg="yellow",
                    )
                    continue

                # Sanity check: el tipo del template debe coincidir con la
                # categoría. Si no, avisar y skipear para no contaminar BD.
                if data["modifier_type"] != expected_type:
                    click.secho(
                        f"  ⚠ Type mismatch for {title!r}: "
                        f"expected {expected_type!r}, got "
                        f"{data['modifier_type']!r}",
                        fg="yellow",
                    )
                    continue

                _upsert_card_modifier(data, title)

                if not dry_run:
                    db.session.commit()

                total += 1
            except Exception as e:
                db.session.rollback()
                click.secho(f"  ✗ Error processing {title!r}: {e}", fg="red")
                logger.exception("Failed processing %s", title)
                continue

    if dry_run:
        db.session.rollback()
        click.secho("  (dry-run: changes rolled back)", fg="yellow")

    return total


def _upsert_card_modifier(data: dict, title: str) -> None:
    """Inserta o actualiza un CardModifier en la BD.

    Búsqueda por ``name`` (clave única semántica). El campo
    ``modifier_type`` se convierte de string ("Edition") al enum
    correspondiente (``ModifierType.EDITION``).
    """
    image_url = (
        wiki.resolve_image_url(data["image_filename"])
        if data.get("image_filename")
        else None
    )
    modifier_type = ModifierType(data["modifier_type"])

    existing = CardModifier.query.filter_by(name=data["name"]).first()

    if existing is not None:
        existing.modifier_type = modifier_type
        existing.effect = data["effect"]
        existing.image_url = image_url
        existing.wiki_url = wiki.page_url(title)
        click.echo(f"  ↻ Updated: [{modifier_type.value:>11}] {data['name']}")
    else:
        mod = CardModifier(
            name=data["name"],
            modifier_type=modifier_type,
            effect=data["effect"],
            image_url=image_url,
            wiki_url=wiki.page_url(title),
        )
        db.session.add(mod)
        click.echo(f"  + Created: [{modifier_type.value:>11}] {data['name']}")


# ──────────────────────────────────────────────────────────────────────
#  Seeder: stickers (hardcoded data + image URL resolution)
# ──────────────────────────────────────────────────────────────────────


# Datos canónicos de los 11 stickers de Balatro 1.0.1f+.
# Hardcodeado porque (a) son pocos y estables, (b) la página de wiki
# mezcla in-run (prosa) y stake (wikitable) en formatos heterogéneos
# que harían el parser más complejo que el beneficio aportado, y
# (c) las descripciones son cortas y se traducen mejor a mano.
_STICKERS_DATA = [
    # In-Run Stickers (3): efectos mecánicos durante partida
    {
        "name": "Eternal",
        "sticker_type": "InRun",
        "description": (
            "Jokers found in shop or booster packs during Black Stake "
            "and higher have a 30% chance of getting this sticker. "
            "Eternal Jokers cannot be sold or destroyed."
        ),
        "image_filename": "Eternal Sticker Full.png",
        "sticker_order": 1,
        "stake_link_order": None,
    },
    {
        "name": "Perishable",
        "sticker_type": "InRun",
        "description": (
            "Jokers found in shop or booster packs during Orange and "
            "Gold Stake runs have a 30% chance of getting this sticker. "
            "Perishable Jokers last for 5 rounds, then become debuffed."
        ),
        "image_filename": "Perishable Sticker Full.png",
        "sticker_order": 2,
        "stake_link_order": None,
    },
    {
        "name": "Rental",
        "sticker_type": "InRun",
        "description": (
            "Jokers found in shop or booster packs during Gold Stake "
            "runs have a 30% chance of getting this sticker. Rental "
            "Jokers cost $1 to purchase but deduct $3 at the end of "
            "every round."
        ),
        "image_filename": "Rental Sticker Full.png",
        "sticker_order": 3,
        "stake_link_order": None,
    },
    # Stake Stickers (8): marcadores de progreso por dificultad ganada.
    # ``stake_link_order`` se usará para hacer FK a stakes.id buscando
    # el Stake con ``stake_order`` igual a este valor.
    {
        "name": "White Sticker",
        "sticker_type": "Stake",
        "description": "Used this Joker/Deck to win on White Stake difficulty.",
        "image_filename": "White Sticker Full.png",
        "sticker_order": 1,
        "stake_link_order": 1,
    },
    {
        "name": "Red Sticker",
        "sticker_type": "Stake",
        "description": "Used this Joker/Deck to win on Red Stake difficulty.",
        "image_filename": "Red Sticker Full.png",
        "sticker_order": 2,
        "stake_link_order": 2,
    },
    {
        "name": "Green Sticker",
        "sticker_type": "Stake",
        "description": "Used this Joker/Deck to win on Green Stake difficulty.",
        "image_filename": "Green Sticker Full.png",
        "sticker_order": 3,
        "stake_link_order": 3,
    },
    {
        "name": "Black Sticker",
        "sticker_type": "Stake",
        "description": "Used this Joker/Deck to win on Black Stake difficulty.",
        "image_filename": "Black Sticker Full.png",
        "sticker_order": 4,
        "stake_link_order": 4,
    },
    {
        "name": "Blue Sticker",
        "sticker_type": "Stake",
        "description": "Used this Joker/Deck to win on Blue Stake difficulty.",
        "image_filename": "Blue Sticker Full.png",
        "sticker_order": 5,
        "stake_link_order": 5,
    },
    {
        "name": "Purple Sticker",
        "sticker_type": "Stake",
        "description": "Used this Joker/Deck to win on Purple Stake difficulty.",
        "image_filename": "Purple Sticker Full.png",
        "sticker_order": 6,
        "stake_link_order": 6,
    },
    {
        "name": "Orange Sticker",
        "sticker_type": "Stake",
        "description": "Used this Joker/Deck to win on Orange Stake difficulty.",
        "image_filename": "Orange Sticker Full.png",
        "sticker_order": 7,
        "stake_link_order": 7,
    },
    {
        "name": "Gold Sticker",
        "sticker_type": "Stake",
        "description": (
            "Used this Joker/Deck to win on Gold Stake difficulty. "
            "Collecting Gold Stickers on every Joker unlocks the "
            "Completionist++ achievement."
        ),
        "image_filename": "Gold Sticker Full.png",
        "sticker_order": 8,
        "stake_link_order": 8,
    },
]


def seed_stickers(dry_run: bool, limit: int | None) -> int:
    """Pobla la tabla ``stickers`` con los 11 stickers canónicos del juego.

    A diferencia del resto de seeders, los datos son hardcoded en lugar
    de extraídos por parser. Razones:
      - Son pocos (11) y estables entre versiones del juego.
      - La página wiki mezcla in-run en prosa y stake en wikitable,
        formatos heterogéneos que requerirían un parser complejo.
      - Las descripciones son cortas y se redactan mejor a mano.

    Sí se consulta la wiki para **resolver las URLs de las imágenes**,
    aprovechando la función existente ``resolve_image_url``. Si la wiki
    cambia el filename de una imagen, el seeder lo detectará (URL=None)
    y bastará con actualizar el filename hardcoded.

    Para Stake Stickers, se enlaza ``stake_id`` consultando el Stake con
    ``stake_order`` correspondiente. Requiere que la tabla ``stakes``
    esté poblada previamente.
    """
    click.echo(f"  Seeding {len(_STICKERS_DATA)} stickers (hardcoded data)...")

    # Pre-fetch de stakes para enlazar stake_id eficientemente
    stakes_by_order = {s.stake_order: s for s in Stake.query.all()}
    if not stakes_by_order:
        click.secho(
            "  ✗ No stakes in DB. Run `seed-db --type=stakes` first.",
            fg="red",
        )
        return 0

    items = _STICKERS_DATA[:limit] if limit else _STICKERS_DATA

    count = 0
    for data in items:
        try:
            _upsert_sticker(data, stakes_by_order)

            if not dry_run:
                db.session.commit()

            count += 1
        except Exception as e:
            db.session.rollback()
            click.secho(f"  ✗ Error processing {data['name']!r}: {e}", fg="red")
            logger.exception("Failed processing %s", data["name"])
            continue

    if dry_run:
        db.session.rollback()
        click.secho("  (dry-run: changes rolled back)", fg="yellow")

    return count


def _upsert_sticker(data: dict, stakes_by_order: dict[int, "Stake"]) -> None:
    """Inserta o actualiza un Sticker en la BD."""
    image_url = (
        wiki.resolve_image_url(data["image_filename"])
        if data.get("image_filename")
        else None
    )

    sticker_type = StickerType(data["sticker_type"])

    # Para Stake Stickers, busca el Stake correspondiente
    stake_id = None
    if data.get("stake_link_order") is not None:
        stake = stakes_by_order.get(data["stake_link_order"])
        if stake is None:
            click.secho(
                f"  ⚠ Stake with order {data['stake_link_order']} not found "
                f"for {data['name']!r}",
                fg="yellow",
            )
        else:
            stake_id = stake.id

    existing = Sticker.query.filter_by(name=data["name"]).first()

    if existing is not None:
        existing.sticker_type = sticker_type
        existing.description = data["description"]
        existing.image_url = image_url
        existing.stake_id = stake_id
        existing.sticker_order = data["sticker_order"]
        existing.wiki_url = wiki.page_url("Stickers")
        click.echo(
            f"  ↻ Updated: [{sticker_type.value:>5}] "
            f"#{data['sticker_order']} {data['name']}"
        )
    else:
        sticker = Sticker(
            name=data["name"],
            sticker_type=sticker_type,
            description=data["description"],
            image_url=image_url,
            stake_id=stake_id,
            sticker_order=data["sticker_order"],
            wiki_url=wiki.page_url("Stickers"),
        )
        db.session.add(sticker)
        click.echo(
            f"  + Created: [{sticker_type.value:>5}] "
            f"#{data['sticker_order']} {data['name']}"
        )


# ──────────────────────────────────────────────────────────────────────
#  Comando: steam-sync
# ──────────────────────────────────────────────────────────────────────


@click.command("steam-sync")
@click.argument("user_id", type=int)
@with_appcontext
def steam_sync_command(user_id: int) -> None:
    """Sincroniza los achievements de Steam de un usuario contra la BD.

    Útil para debugging del flujo sin pasar por HTTP, batch sync manual
    desde terminal y verificación rápida durante desarrollo.

    Ejemplo:
        $ flask --app run.py steam-sync 42
    """
    try:
        result = sync_steam_achievements_for_user(user_id)
    except UserNotFoundError as e:
        click.secho(f"  ✗ User not found: {e}", fg="red")
        raise click.Abort()
    except UserNotLinkedError as e:
        click.secho(f"  ✗ User has no Steam account linked: {e}", fg="red")
        raise click.Abort()
    except SteamApiError as e:
        click.secho(
            f"  ✗ Steam API failure ({type(e).__name__}): {e}",
            fg="red",
        )
        raise click.Abort()

    duration = (result.completed_at - result.started_at).total_seconds()

    click.secho(
        f"  ✓ Sync completed for user {result.user_id} "
        f"(Steam ID {result.steam_id})",
        fg="green",
        bold=True,
    )
    click.echo(f"    Steam achievements received: {result.steam_achievements_received}")
    click.echo(f"    Steam achievements achieved: {result.steam_achievements_achieved}")
    click.echo(f"    → Newly unlocked in DB:      {result.newly_unlocked_count}")
    click.echo(f"    → Already unlocked:          {result.already_unlocked_count}")
    click.echo(f"    → Items cascaded:            {result.total_items_cascaded}")
    click.echo(f"    → Sticker applications:      {result.total_sticker_applications}")
    if result.unknown_apinames:
        click.secho(
            f"    ⚠ Unknown apinames (extend seed?): "
            f"{', '.join(result.unknown_apinames)}",
            fg="yellow",
        )
    click.echo(f"    Sync duration: {duration:.2f}s")
