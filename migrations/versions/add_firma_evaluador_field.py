"""
Revision ID: 20250528_01
Revises: 
Create Date: 2025-05-28
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250528_01'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('solicitudes_equivalencia', sa.Column('firma_evaluador', sa.String(length=255), nullable=True))

def downgrade():
    op.drop_column('solicitudes_equivalencia', 'firma_evaluador')
