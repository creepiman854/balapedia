"""M2 — Crear tabla unlock_factors y enlazar unlockables y achievements

Revision ID: m2_unlock_factors
Revises: m1_stickers_polymorphic
Create Date: 2026-05-17

Normaliza las condiciones de desbloqueo en una tabla catálogo. Antes
existía solo `unlockables.unlock_condition` como VARCHAR(500) de texto
libre, lo cual impedía compartir la misma condición entre un item y
su achievement asociado (ej. el joker Showman y el achievement Ante Up!
ambos se desbloquean al alcanzar Ante 4).

Tras esta migración:
- Una nueva tabla `unlock_factors(id, code, description)` actúa como
  catálogo normalizado de condiciones.
- `unlockables` recibe una FK nullable `unlock_factor_id` con
  ON DELETE SET NULL (un item sin condición compartida permanece sin
  factor; si más adelante se borra el factor, el item conserva su
  registro con el campo en NULL).
- `achievements` recibe la misma FK nullable con el mismo comportamiento.

El campo `unlockables.unlock_condition` (texto libre original) se
mantiene por ahora como fallback de display y para no romper datos
existentes; se deprecará en una migración posterior una vez que todos
los items tengan su `unlock_factor_id` populado.

El seed de los factores y el backfill de `unlockables.unlock_factor_id`
se hacen en scripts de seed posteriores (no en esta migración) para
mantener la migración puramente de esquema.
"""
from alembic import op
import sqlalchemy as sa


# identificadores de revisión, usados por Alembic.
revision = "m2_unlock_factors"
down_revision = "m1_stickers_polymorphic"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Crear catálogo de unlock_factors
    op.create_table(
        "unlock_factors",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_unlock_factors"),
        sa.UniqueConstraint("code", name="uq_unlock_factors_code"),
        mysql_engine="InnoDB",
        mysql_charset="utf8",
    )

    # 2. Añadir FK nullable a unlockables
    op.add_column(
        "unlockables",
        sa.Column("unlock_factor_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_unlockables_unlock_factor",
        source_table="unlockables",
        referent_table="unlock_factors",
        local_cols=["unlock_factor_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_unlockables_unlock_factor_id",
        "unlockables",
        ["unlock_factor_id"],
    )

    # 3. Añadir FK nullable a achievements
    op.add_column(
        "achievements",
        sa.Column("unlock_factor_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_achievements_unlock_factor",
        source_table="achievements",
        referent_table="unlock_factors",
        local_cols=["unlock_factor_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_achievements_unlock_factor_id",
        "achievements",
        ["unlock_factor_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_achievements_unlock_factor_id",
        table_name="achievements",
    )
    op.drop_constraint(
        "fk_achievements_unlock_factor",
        "achievements",
        type_="foreignkey",
    )
    op.drop_column("achievements", "unlock_factor_id")

    op.drop_index(
        "ix_unlockables_unlock_factor_id",
        table_name="unlockables",
    )
    op.drop_constraint(
        "fk_unlockables_unlock_factor",
        "unlockables",
        type_="foreignkey",
    )
    op.drop_column("unlockables", "unlock_factor_id")

    op.drop_table("unlock_factors")
