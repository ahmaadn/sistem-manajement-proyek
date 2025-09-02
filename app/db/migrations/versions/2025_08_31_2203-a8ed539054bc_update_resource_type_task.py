"""update resource type task

Revision ID: a8ed539054bc
Revises: 7048481edddf
Create Date: 2025-08-31 22:03:46.301820

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a8ed539054bc'
down_revision: Union[str, None] = '7048481edddf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Pastikan tidak ada nilai 'SECTION' yang tersisa pada kolom
    op.execute("UPDATE task SET resource_type = 'TASK' WHERE resource_type = 'SECTION'")

    # Buat tipe enum baru tanpa 'SECTION'
    op.execute("CREATE TYPE resource_type_new AS ENUM ('TASK', 'MILESTONE')")

    # Ubah tipe kolom ke enum baru
    op.execute(
        "ALTER TABLE task "
        "ALTER COLUMN resource_type TYPE resource_type_new "
        "USING resource_type::text::resource_type_new"
    )

    # Hapus tipe lama dan rename tipe baru ke nama asli
    op.execute("DROP TYPE resource_type")
    op.execute("ALTER TYPE resource_type_new RENAME TO resource_type")


def downgrade() -> None:
    # Kembalikan enum dengan menambahkan kembali 'SECTION'
    op.execute("CREATE TYPE resource_type_old AS ENUM ('TASK', 'MILESTONE', 'SECTION')")

    op.execute(
        "ALTER TABLE task "
        "ALTER COLUMN resource_type TYPE resource_type_old "
        "USING resource_type::text::resource_type_old"
    )

    op.execute("DROP TYPE resource_type")
    op.execute("ALTER TYPE resource_type_old RENAME TO resource_type")
