"""extend BlindType enum with SHOWDOWN value

Revision ID: 83afae5a0073
Revises: 8792a1949c18
Create Date: 2026-05-12 21:07:22.970225

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "83afae5a0073"
down_revision = "8792a1949c18"
branch_labels = None
depends_on = None


def upgrade():
    # Añadido manualmente: Alembic no autodetecta cambios de valores
    # en ENUMs de MySQL.
    op.alter_column(
        "blinds",
        "blind_type",
        existing_type=mysql.ENUM("SMALL", "BIG", "BOSS", name="blind_type"),
        type_=mysql.ENUM("SMALL", "BIG", "BOSS", "SHOWDOWN", name="blind_type"),
        existing_nullable=False,
    )


def downgrade():
    op.alter_column(
        "blinds",
        "blind_type",
        existing_type=mysql.ENUM("SMALL", "BIG", "BOSS", "SHOWDOWN", name="blind_type"),
        type_=mysql.ENUM("SMALL", "BIG", "BOSS", name="blind_type"),
        existing_nullable=False,
    )
