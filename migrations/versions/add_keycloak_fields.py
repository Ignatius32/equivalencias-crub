"""Add Keycloak integration fields

Revision ID: add_keycloak_fields
Revises: add_dictamen_final_fields
Create Date: 2025-06-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_keycloak_fields'
down_revision = 'add_dictamen_final_fields'
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns for Keycloak integration
    op.add_column('usuarios', sa.Column('keycloak_id', sa.String(length=100), nullable=True))
    op.add_column('usuarios', sa.Column('is_keycloak_user', sa.Boolean(), nullable=True, default=False))
    op.add_column('usuarios', sa.Column('last_login', sa.DateTime(), nullable=True))
    
    # Create unique constraint for keycloak_id
    op.create_unique_constraint('uq_usuarios_keycloak_id', 'usuarios', ['keycloak_id'])
    
    # Make password_hash nullable for Keycloak users
    op.alter_column('usuarios', 'password_hash', nullable=True)

def downgrade():
    # Remove the constraints and columns
    op.drop_constraint('uq_usuarios_keycloak_id', 'usuarios', type_='unique')
    op.drop_column('usuarios', 'last_login')
    op.drop_column('usuarios', 'is_keycloak_user')
    op.drop_column('usuarios', 'keycloak_id')
    
    # Make password_hash not nullable again
    op.alter_column('usuarios', 'password_hash', nullable=False)
