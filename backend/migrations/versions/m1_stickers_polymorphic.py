"""M1 — Consolidar las tablas de aplicación de pegatinas (stickers) en una tabla polimórfica mediante CTI (Class Table Inheritance) de unlockables

Revision ID: m1_stickers_polymorphic
Revises: 4ee5e683fb9c
Create Date: 2026-05-17

Fusiona `user_joker_stickers` y `user_deck_stickers` en una única tabla 
`user_sticker_applications`. El polimorfismo se apoya en la Herencia de Tabla 
por Clase (CTI) existente de unlockables — no se necesita una columna explícita 
target_type/target_id, ya que unlockables.type ya discrimina entre JOKER y DECK.

Se confirmó que ambas tablas de origen estaban vacías en el momento de 
la migración, por lo que no se requiere relleno de datos (el orden de eliminar+crear es seguro).

La validación a nivel de aplicación en el modelo SQLAlchemy restringe 
las inserciones a unlockables.type IN ('JOKER', 'DECK'); un trigger (disparador) 
en la base de datos es opcional y no se añade aquí para mantener la migración portable.

ENUM `unlock_source` se reutiliza intencionalmente (mismo nombre que en user_unlocks y user_achievements) 
para mantener un único tipo lógico de "fuente de progresión" en todo el modelo.
"""
from alembic import op
import sqlalchemy as sa


# identificadores de revisión, usados por Alembic.
revision = "m1_stickers_polymorphic"
down_revision = "4ee5e683fb9c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Eliminar las tablas heredadas por tipo (ambas confirmadas vacías)
    op.drop_table("user_joker_stickers")
    op.drop_table("user_deck_stickers")

    # 2. Crear tabla polimórfica unificada
    op.create_table(
        "user_sticker_applications",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("unlockable_id", sa.Integer(), nullable=False),
        sa.Column("highest_stake_order", sa.SmallInteger(), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "source",
            sa.Enum("MANUAL", "STEAM_SYNC", name="unlock_source"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "user_id", "unlockable_id",
            name="pk_user_sticker_applications",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_user_sticker_applications_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["unlockable_id"], ["unlockables.id"],
            name="fk_user_sticker_applications_unlockable",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "highest_stake_order BETWEEN 1 AND 8",
            name="ck_user_sticker_applications_order_range",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8",
    )
    op.create_index(
        "ix_user_sticker_applications_unlockable_id",
        "user_sticker_applications",
        ["unlockable_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_sticker_applications_unlockable_id",
        table_name="user_sticker_applications",
    )
    op.drop_table("user_sticker_applications")

    # Recrear las dos tablas heredadas (misma definición que antes de M1)
    op.create_table(
        "user_joker_stickers",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("joker_id", sa.Integer(), nullable=False),
        sa.Column("highest_stake_order", sa.SmallInteger(), nullable=False),
        sa.Column("earned_at", sa.DateTime(), nullable=True),
        sa.Column(
            "source",
            sa.Enum("MANUAL", "STEAM_SYNC"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id", "joker_id"),
        sa.ForeignKeyConstraint(["joker_id"], ["unlockables.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "highest_stake_order BETWEEN 1 AND 8",
            name="ck_user_joker_stickers_order_range",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8",
    )
    op.create_table(
        "user_deck_stickers",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("deck_id", sa.Integer(), nullable=False),
        sa.Column("highest_stake_order", sa.SmallInteger(), nullable=False),
        sa.Column("earned_at", sa.DateTime(), nullable=True),
        sa.Column(
            "source",
            sa.Enum("MANUAL", "STEAM_SYNC"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id", "deck_id"),
        sa.ForeignKeyConstraint(["deck_id"], ["unlockables.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "highest_stake_order BETWEEN 1 AND 8",
            name="ck_user_deck_stickers_order_range",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8",
    )