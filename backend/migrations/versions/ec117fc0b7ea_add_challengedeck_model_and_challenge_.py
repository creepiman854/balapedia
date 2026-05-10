"""add ChallengeDeck model and CHALLENGE_DECK enum value

Revision ID: ec117fc0b7ea
Revises: 968a0b6e7792
Create Date: 2026-05-10 13:18:40.550807

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "ec117fc0b7ea"
down_revision = "968a0b6e7792"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Crea la nueva tabla challenge_decks (auto-generado)
    op.create_table(
        "challenge_decks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("modifier", sa.Text(), nullable=False),
        sa.Column("starter", sa.Text(), nullable=True),
        sa.Column("banned", sa.Text(), nullable=True),
        sa.Column("deck_description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["id"], ["unlockables.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Extiende el ENUM unlockables.type para incluir CHALLENGE_DECK.
    #    Añadido manualmente: Alembic no autodetecta cambios de valores
    #    en ENUMs de MySQL.
    op.alter_column(
        "unlockables",
        "type",
        existing_type=mysql.ENUM(
            "JOKER",
            "TAROT",
            "PLANET",
            "SPECTRAL",
            "VOUCHER",
            "DECK",
            "BOOSTER_PACK",
            name="unlockable_type",
        ),
        type_=mysql.ENUM(
            "JOKER",
            "TAROT",
            "PLANET",
            "SPECTRAL",
            "VOUCHER",
            "DECK",
            "BOOSTER_PACK",
            "CHALLENGE_DECK",
            name="unlockable_type",
        ),
        existing_nullable=False,
    )


def downgrade():
    # Revierte el ENUM ANTES de borrar la tabla
    op.alter_column(
        "unlockables",
        "type",
        existing_type=mysql.ENUM(
            "JOKER",
            "TAROT",
            "PLANET",
            "SPECTRAL",
            "VOUCHER",
            "DECK",
            "BOOSTER_PACK",
            "CHALLENGE_DECK",
            name="unlockable_type",
        ),
        type_=mysql.ENUM(
            "JOKER",
            "TAROT",
            "PLANET",
            "SPECTRAL",
            "VOUCHER",
            "DECK",
            "BOOSTER_PACK",
            name="unlockable_type",
        ),
        existing_nullable=False,
    )

    op.drop_table("challenge_decks")
