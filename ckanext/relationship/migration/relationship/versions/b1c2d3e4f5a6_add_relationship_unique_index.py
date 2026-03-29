"""Add relationship uniqueness index.

Revision ID: b1c2d3e4f5a6
Revises: a4b5c6d7e8f9
Create Date: 2026-03-29 17:25:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b1c2d3e4f5a6"
down_revision = "a4b5c6d7e8f9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "uq_relationship_subject_object_relation_type",
        "relationship_relationship",
        ["subject_id", "object_id", "relation_type"],
        unique=True,
    )


def downgrade():
    op.drop_index(
        "uq_relationship_subject_object_relation_type",
        table_name="relationship_relationship",
    )
