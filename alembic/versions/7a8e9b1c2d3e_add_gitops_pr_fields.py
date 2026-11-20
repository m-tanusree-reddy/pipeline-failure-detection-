"""add_gitops_pr_fields

Revision ID: 7a8e9b1c2d3e
Revises: 45f5112cb868
Create Date: 2026-11-20 22:22:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a8e9b1c2d3e'
down_revision: Union[str, Sequence[str], None] = '45f5112cb868'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: adds pr_url and pr_number to code_remediations table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'code_remediations' in existing_tables:
        cols = [c['name'] for c in inspector.get_columns('code_remediations')]
        if 'pr_url' not in cols:
            op.add_column('code_remediations', sa.Column('pr_url', sa.String(length=512), nullable=True))
        if 'pr_number' not in cols:
            op.add_column('code_remediations', sa.Column('pr_number', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema: removes pr_url and pr_number."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'code_remediations' in existing_tables:
        cols = [c['name'] for c in inspector.get_columns('code_remediations')]
        if 'pr_number' in cols:
            op.drop_column('code_remediations', 'pr_number')
        if 'pr_url' in cols:
            op.drop_column('code_remediations', 'pr_url')
