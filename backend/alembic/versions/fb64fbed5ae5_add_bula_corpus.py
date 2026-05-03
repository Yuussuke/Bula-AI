"""add bula corpus

Revision ID: fb64fbed5ae5
Revises: b4e6c8d9a0f1
Create Date: 2026-05-02 22:02:08.360887

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fb64fbed5ae5"
down_revision: Union[str, Sequence[str], None] = "b4e6c8d9a0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bula_corpus = sa.Enum("private", "system", "shared", name="bulacorpus")
    bula_corpus.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "bulas",
        sa.Column(
            "corpus",
            bula_corpus,
            server_default="private",
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("bulas", "corpus")

    bula_corpus = sa.Enum("private", "system", "shared", name="bulacorpus")
    bula_corpus.drop(op.get_bind(), checkfirst=True)
