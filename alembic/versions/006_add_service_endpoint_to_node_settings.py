"""Add service_endpoint to node_settings

Revision ID: 006_add_service_endpoint
Revises: 5a3e7b1c8f2d
Create Date: 2026-02-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006_add_service_endpoint'
down_revision = '003_refactor_admin'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add service_endpoint column to node_settings table
    op.add_column('node_settings', 
        sa.Column('service_endpoint', sa.String(length=255), nullable=True, comment='Service endpoint URL for DIDComm')
    )


def downgrade() -> None:
    # Remove service_endpoint column from node_settings table
    op.drop_column('node_settings', 'service_endpoint')

