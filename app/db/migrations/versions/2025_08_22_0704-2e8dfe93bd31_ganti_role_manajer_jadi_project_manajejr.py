"""ganti role MANAJER jadi PROJECT_MANAJEJR

Revision ID: 2e8dfe93bd31
Revises: f33725a6ec54
Create Date: 2025-08-22 07:04:05.528192

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2e8dfe93bd31'
down_revision: Union[str, None] = 'f33725a6ec54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "postgresql":
        try:
            op.execute("ALTER TYPE role RENAME VALUE 'MANAGER' TO 'PROJECT_MANAGER'")
        except Exception:
            # Fallback jika kolom bertipe TEXT/VARCHAR
            op.execute("UPDATE user_role SET role='PROJECT_MANAGER' WHERE role='MANAGER'")
    else:
        # Fallback umum (misal SQLite / MySQL dengan kolom string)
        op.execute("UPDATE user_role SET role='PROJECT_MANAGER' WHERE role='MANAGER'")



def downgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "postgresql":
        try:
            op.execute("ALTER TYPE role RENAME VALUE 'PROJECT_MANAGER' TO 'MANAGER'")
        except Exception:
            op.execute("UPDATE user_role SET role='MANAGER' WHERE role='PROJECT_MANAGER'")
    else:
        op.execute("UPDATE user_role SET role='MANAGER' WHERE role='PROJECT_MANAGER'")
