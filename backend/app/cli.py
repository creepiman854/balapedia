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
from sqlalchemy import text

from app.extensions import db
from app.models import Joker, JokerRarity, Unlockable, UnlockableType
from app.scrapers import wiki

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
    type=click.Choice(["jokers", "all"]),
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
        # consumables, decks, vouchers, achievements: se añadirán en commits futuros
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
#  Seeder: jokers
# ──────────────────────────────────────────────────────────────────────


def seed_jokers(dry_run: bool, limit: int | None) -> int:
    """Pobla la tabla de Jokers desde ``Category:Jokers`` de la wiki.

    Returns:
        Número de jokers procesados (insertados o actualizados).
    """
    titles = wiki.list_pages_in_category("Jokers")

    # Filtra la página índice de la categoría: en MediaWiki, la página titulada
    # igual que la categoría suele estar categorizada en sí misma como overview
    # del tema. No es un Joker individual y no tiene la plantilla 'Joker info'.
    INDEX_PAGES = {"Jokers", "List of Jokers", "Jokers (List)"}
    titles = [t for t in titles if t not in INDEX_PAGES]

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
                # Página categorizada bajo Jokers pero sin plantilla Joker info
                # (puede ser una página de lista, disambig, etc.). Se ignora.
                click.secho(
                    f"  ⚠ Page lacks 'Joker info' template: {title!r}", fg="yellow"
                )
                continue

            _upsert_joker(data, title)
            count += 1
        except Exception as e:
            # Capturamos por item para que un fallo no aborte todo el seed.
            # El traceback completo va al logger; al usuario, mensaje breve.
            click.secho(f"  ✗ Error processing {title!r}: {e}", fg="red")
            logger.exception("Failed processing %s", title)
            continue

    # Persistencia o rollback según modo
    if dry_run:
        db.session.rollback()
        click.secho("  (dry-run: changes rolled back)", fg="yellow")
    else:
        db.session.commit()

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