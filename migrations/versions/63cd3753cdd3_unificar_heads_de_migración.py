"""Unificar heads de migración

Revision ID: 63cd3753cdd3
Revises: add_dictamen_final_fields, 20250528_01
Create Date: 2025-05-28 14:21:47.263938

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '63cd3753cdd3'
down_revision = ('add_dictamen_final_fields', '20250528_01')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
