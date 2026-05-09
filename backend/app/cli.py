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
from app.models import Joker, JokerRarity, Unlockable, UnlockableType
from app.scrapers import wiki

from app.models import (
    Consumable,
    Deck,
    Joker,
    JokerRarity,
    Unlockable,
    UnlockableType,
    Voucher,
    VoucherTier,
)

# ──────────────────────────────────────────────────────────────────────
#  Overrides de datos para errores conocidos en la wiki fuente
# ──────────────────────────────────────────────────────────────────────

# Cuando un campo de la wiki es objetivamente incorrecto, lo corregimos aquí.
# Cada entrada DEBE incluir un comentario explicando el motivo y, si es posible,
# un enlace a la página de la wiki para verificación futura. Cuando la wiki se
# corrija, basta con eliminar la entrada correspondiente.
_WIKI_DATA_OVERRIDES = {
    # The Hierophant tiene number=7 en la wiki, lo cual colisiona con The Lovers
    # (también number=7). Según el orden estándar del Major Arcana y la posición
    # en el juego, The Hierophant es la 6ª carta. Aplicamos override hasta que
    # el editor de la wiki corrija el campo.
    # Wiki: https://balatrowiki.org/wiki/The_Hierophant
    ("tarot", "The Hierophant"): {"item_number": 6},
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
    """Registra los comandos CLI custom en la app Flask.

    Se invoca desde ``create_app()``. A partir del registro, los comandos
    están disponibles bajo ``flask --app run.py <command>``.
    """
    app.cli.add_command(seed_db)


# ──────────────────────────────────────────────────────────────────────
#  Comando: seed-db
# ──────────────────────────────────────────────────────────────────────


@click.command("seed-db")
@click.option(
    "--type",
    "item_type",
    type=click.Choice(["jokers", "consumables", "decks", "vouchers", "all"]),
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
        # achievements: en commit futuro
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
        )
        db.session.add(unlockable)
        click.echo(
            f"  + Created: [{voucher_tier.value:>8}] " f"#{next_num:>3} {data['name']}"
        )
