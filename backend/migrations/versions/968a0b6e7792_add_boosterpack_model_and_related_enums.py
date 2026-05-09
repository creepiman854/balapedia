"""add BoosterPack model and related enums

Revision ID: 968a0b6e7792
Revises: 66e6a8970e43
Create Date: 2026-05-09 18:04:31.735673

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = '968a0b6e7792'
down_revision = '66e6a8970e43'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Crear la nueva tabla booster_packs
    op.create_table(
        'booster_packs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column(
            'pack_type',
            sa.Enum('ARCANA', 'CELESTIAL', 'STANDARD', 'BUFFOON', 'SPECTRAL',
                    name='booster_pack_type'),
            nullable=False,
        ),
        sa.Column(
            'size',
            sa.Enum('NORMAL', 'JUMBO', 'MEGA', name='booster_pack_size'),
            nullable=False,
        ),
        sa.Column('cost', sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(['id'], ['unlockables.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('booster_packs', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_booster_packs_cost'), ['cost'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_booster_packs_pack_type'), ['pack_type'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_booster_packs_size'), ['size'], unique=False
        )

    # 2. Extiende el ENUM unlockables.type para incluir BOOSTER_PACK.
    #    Alembic no autodetecta cambios de valores en ENUMs de MySQL, por
    #    lo que esta operación se añade manualmente.
    op.alter_column(
        'unlockables', 'type',
        existing_type=mysql.ENUM(
            'JOKER', 'TAROT', 'PLANET', 'SPECTRAL', 'VOUCHER', 'DECK',
            name='unlockable_type',
        ),
        type_=mysql.ENUM(
            'JOKER', 'TAROT', 'PLANET', 'SPECTRAL', 'VOUCHER', 'DECK',
            'BOOSTER_PACK',
            name='unlockable_type',
        ),
        existing_nullable=False,
    )


def downgrade():
    # Revertir primero el ENUM (eliminando BOOSTER_PACK) ANTES de borrar la
    # tabla, para que no haya filas con type='BOOSTER_PACK' que el ENUM
    # restringido ya no acepte.
    op.alter_column(
        'unlockables', 'type',
        existing_type=mysql.ENUM(
            'JOKER', 'TAROT', 'PLANET', 'SPECTRAL', 'VOUCHER', 'DECK',
            'BOOSTER_PACK',
            name='unlockable_type',
        ),
        type_=mysql.ENUM(
            'JOKER', 'TAROT', 'PLANET', 'SPECTRAL', 'VOUCHER', 'DECK',
            name='unlockable_type',
        ),
        existing_nullable=False,
    )

    with op.batch_alter_table('booster_packs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_booster_packs_size'))
        batch_op.drop_index(batch_op.f('ix_booster_packs_pack_type'))
        batch_op.drop_index(batch_op.f('ix_booster_packs_cost'))

    op.drop_table('booster_packs')