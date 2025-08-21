"""ganti status project dari finish ke completed

Revision ID: f137cd8be077
Revises: 5b920484af7d
Create Date: 2025-08-21 11:51:51.377306

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f137cd8be077'
down_revision: Union[str, None] = '5b920484af7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "postgresql":
        try:
            op.execute("ALTER TYPE status_project RENAME VALUE 'FINISH' TO 'COMPLETED'")
        except Exception:
            # Fallback jika kolom bertipe TEXT/VARCHAR
            op.execute("UPDATE project SET status='COMPLETED' WHERE status='FINISH'")
    else:
        # Fallback umum (misal SQLite / MySQL dengan kolom string)
        op.execute("UPDATE project SET status='COMPLETED' WHERE status='FINISH'")



def downgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "postgresql":
        try:
            op.execute("ALTER TYPE status_project RENAME VALUE 'COMPLETED' TO 'FINISH'")
        except Exception:
            op.execute("UPDATE project SET status='FINISH' WHERE status='COMPLETED'")
    else:
        op.execute("UPDATE project SET status='FINISH' WHERE status='COMPLETED'")
