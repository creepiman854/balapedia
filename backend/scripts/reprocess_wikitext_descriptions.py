"""One-shot migration: re-procesa descripciones con wikitext sin parsear.

Cuándo correrlo:
    Tras desplegar `fix/seed-wikitext-cleanup` (la versión arreglada de
    `render_wikitext`). Las filas ya en BD se sembraron con la versión
    antigua que dejaba wikitext literal en ciertos casos (`{{c|...}}` y
    plantillas anidadas dentro de identity). Este script las re-procesa
    con el parser arreglado.

Política:
    - Escanea las columnas de texto que `render_wikitext` debería haber
      limpiado durante el seed.
    - Solo UPDATE las filas cuyo valor actual contiene `{{` (filas con
      wikitext residual).
    - Re-aplica `render_wikitext` y guarda solo si el resultado es
      DISTINTO del valor actual — evita writes redundantes.
    - Si tras el reprocesado el campo SIGUE conteniendo `{{`, loguea un
      WARNING con el id de la fila y un fragmento del valor. Esto
      indica una plantilla que el parser sigue sin reconocer y necesita
      atención manual.

Idempotente: re-ejecutar tras un primer run limpio no toca nada
(ninguna fila cumple ya el filtro `description LIKE '%{{%'`).

Cómo correrlo:
    # Como comando Flask (recomendado, ya entra en el app_context):
    flask reprocess-wikitext

    # O directamente con el app context inicializado:
    python scripts/reprocess_wikitext_descriptions.py

Ubicación sugerida en el repo:
    scripts/reprocess_wikitext_descriptions.py   (o)
    app/cli.py                                   (como comando flask)

Output ejemplo::

    [unlockables.description] scanning 247 candidate rows...
    [unlockables.description] 23 rows cleaned, 0 still dirty.
    [achievements.description] scanning 4 candidate rows...
    [achievements.description] 4 rows cleaned, 0 still dirty.
    ...
    Total: 31 rows cleaned across 6 tables.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.extensions import db
from app.models import (
    Achievement,
    Blind,
    CardModifier,
    ChallengeDeck,
    Stake,
    Tag,
    Unlockable,
)
from app.scrapers.wiki import (
    DESCRIPTION_OVERRIDES,
    apply_description_override,
    render_wikitext,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Tabla maestra: qué columnas pueden contener wikitext
# =============================================================================
#
# Cada entrada describe una columna VARCHAR/TEXT que `render_wikitext`
# debería haber limpiado durante el seed. Añadir/quitar entradas aquí
# extiende el alcance de la migración sin tocar la lógica.


@dataclass(frozen=True)
class WikitextColumn:
    """Una columna de un modelo SQLAlchemy candidata a contener
    wikitext sucio."""

    model: Any
    column_name: str

    @property
    def label(self) -> str:
        return f"{self.model.__tablename__}.{self.column_name}"


WIKITEXT_COLUMNS: list[WikitextColumn] = [
    # Unlockable (jokers, decks, vouchers, consumables, booster_packs)
    WikitextColumn(Unlockable, "description"),
    WikitextColumn(Unlockable, "unlock_condition"),
    # Achievement
    WikitextColumn(Achievement, "description"),
    # Challenge deck — campos múltiples
    WikitextColumn(ChallengeDeck, "modifier"),
    WikitextColumn(ChallengeDeck, "starter"),
    WikitextColumn(ChallengeDeck, "banned"),
    WikitextColumn(ChallengeDeck, "deck_description"),
    # Blind
    WikitextColumn(Blind, "description"),
    # Tag
    WikitextColumn(Tag, "description"),
    WikitextColumn(Tag, "unlock_condition"),
    # Card modifier (effect en lugar de description)
    WikitextColumn(CardModifier, "effect"),
    # Stake
    WikitextColumn(Stake, "effect_description"),
]


# =============================================================================
# Migración
# =============================================================================


def reprocess_column(col: WikitextColumn) -> tuple[int, int]:
    """Re-procesa una sola columna.

    Returns:
        (cleaned, still_dirty)
        - cleaned: nº de filas que pasaron a no contener `{{`.
        - still_dirty: nº de filas que tras el reprocesado SIGUEN con
          `{{` — caso para revisión manual (template nuevo no
          reconocido por la versión actual de `render_wikitext`).
    """
    column = getattr(col.model, col.column_name)
    candidates = db.session.query(col.model).all()
    logger.info("[%s] scanning %d rows...", col.label, len(candidates))

    cleaned = 0
    still_dirty = 0

    for row in candidates:
        current = getattr(row, col.column_name)
        if not current:
            continue

        reprocessed = render_wikitext(current)

        # Aplicamos overrides si es un Unlockable
        if isinstance(row, Unlockable) and col.column_name == "description":
            reprocessed = apply_description_override(row.name, reprocessed)

        # Si tras limpiar sigue siendo igual, no hacemos update
        if reprocessed == current:
            continue

        # Si tras el reprocesado AÚN queda `{{`, también es interesante
        # de loguear pero igualmente guardamos (mejor parcial que nada).
        if "{{" in reprocessed:
            still_dirty += 1
            logger.warning(
                "[%s id=%s] partial cleanup — wikitext remains. "
                "Before: %r, after: %r",
                col.label,
                row.id,
                current[:120],
                reprocessed[:120],
            )

        setattr(row, col.column_name, reprocessed)
        cleaned += 1

    db.session.commit()
    logger.info("[%s] %d rows updated.", col.label, cleaned)
    return cleaned, still_dirty


def reprocess_all() -> dict:
    """Ejecuta la migración contra todas las columnas declaradas.

    Hace tres pasadas:

      1. Re-procesa cada columna con `render_wikitext` (limpia wikitext
         residual + post-procesado de v2).
      2. Aplica los `DESCRIPTION_OVERRIDES` hardcoded a Unlockable por
         nombre (TO DO LIST, ANAGLYPH DECK).
      3. Loguea resumen.

    Returns:
        Dict con totales agregados:
        {
          "tables_scanned": int,
          "total_cleaned": int,
          "total_still_dirty": int,
          "overrides_applied": int,
          "per_table": {"unlockables.description": (cleaned, still_dirty), ...}
        }
    """
    summary: dict[str, tuple[int, int]] = {}
    total_cleaned = 0
    total_still_dirty = 0

    # 1. Re-procesado genérico por columna
    for col in WIKITEXT_COLUMNS:
        cleaned, still_dirty = reprocess_column(col)
        summary[col.label] = (cleaned, still_dirty)
        total_cleaned += cleaned
        total_still_dirty += still_dirty

    # 2. Overrides hardcoded por nombre — escribe las descripciones de
    #    los items que no pueden representarse con la salida genérica
    #    (TO DO LIST con `<small>`, ANAGLYPH DECK con `24px`, etc.).
    overrides_applied = apply_description_overrides()

    logger.info(
        "Total: %d rows cleaned across %d tables (%d still dirty), "
        "%d overrides applied.",
        total_cleaned,
        len(WIKITEXT_COLUMNS),
        total_still_dirty,
        overrides_applied,
    )

    return {
        "tables_scanned": len(WIKITEXT_COLUMNS),
        "total_cleaned": total_cleaned,
        "total_still_dirty": total_still_dirty,
        "overrides_applied": overrides_applied,
        "per_table": summary,
    }


def apply_description_overrides() -> int:
    """Sobrescribe descripciones de items con valor hardcoded.

    Recorre `DESCRIPTION_OVERRIDES` (definido en `app.scrapers.wiki`) y
    para cada (nombre, descripción) actualiza la fila correspondiente
    en `unlockables` si existe.

    Idempotente: si ya tenía el valor target, el UPDATE no cambia nada
    (MySQL no marca la fila como modificada). El conteo devuelto puede
    incluir UPDATEs "lógicamente noop" — eso es aceptable para
    diagnóstico.

    Returns:
        Número total de UPDATEs ejecutados (uno por nombre en el dict
        que existe en BD).
    """
    n_applied = 0
    for name, new_description in DESCRIPTION_OVERRIDES.items():
        row = db.session.query(Unlockable).filter(Unlockable.name == name).one_or_none()
        if row is None:
            logger.warning(
                "Override target not found in DB: name=%r — skipping.",
                name,
            )
            continue
        if row.description == new_description:
            # No-op: la BD ya tenía el override aplicado (seguramente
            # ejecutaste este script antes).
            continue
        row.description = new_description
        n_applied += 1
        logger.info("Override applied: name=%r — description rewritten.", name)
    db.session.commit()
    return n_applied


# =============================================================================
# Integración como comando flask (sugerida — añadir a app/cli.py)
# =============================================================================
#
# Para exponer la migración como `flask reprocess-wikitext`, añadir esto
# en `app/cli.py` (donde ya se registran los otros comandos flask):
#
#     import click
#     from app.services.reprocess_wikitext_descriptions import reprocess_all
#
#     @app.cli.command("reprocess-wikitext")
#     def reprocess_wikitext_cmd():
#         """One-shot: limpia descripciones con wikitext residual en BD."""
#         summary = reprocess_all()
#         click.echo(f"Tables scanned: {summary['tables_scanned']}")
#         click.echo(f"Rows cleaned:   {summary['total_cleaned']}")
#         click.echo(f"Still dirty:    {summary['total_still_dirty']}")
#         for label, (cleaned, dirty) in summary["per_table"].items():
#             click.echo(f"  [{label}] cleaned={cleaned}, still_dirty={dirty}")
#
# Después: `flask reprocess-wikitext` lo ejecuta dentro del app_context.


# =============================================================================
# Standalone (sin Flask CLI) — solo si no quieres registrar el comando
# =============================================================================


if __name__ == "__main__":
    # Configuración mínima de logging para ver el progreso.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    from app import create_app

    app = create_app()
    with app.app_context():
        summary = reprocess_all()
        print("\n=== Resumen ===")
        print(f"Tables scanned: {summary['tables_scanned']}")
        print(f"Rows cleaned:   {summary['total_cleaned']}")
        print(f"Still dirty:    {summary['total_still_dirty']}")
