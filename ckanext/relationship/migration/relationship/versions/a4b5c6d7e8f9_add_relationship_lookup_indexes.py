"""Add relationship lookup indexes.

Revision ID: a4b5c6d7e8f9
Revises: dd010e8e0680
Create Date: 2026-03-29 17:20:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "a4b5c6d7e8f9"
down_revision = "dd010e8e0680"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_relationship_subject_id_relation_type",
        "relationship_relationship",
        ["subject_id", "relation_type"],
    )
    op.create_index(
        "ix_relationship_object_id_relation_type",
        "relationship_relationship",
        ["object_id", "relation_type"],
    )


def downgrade():
    op.drop_index(
        "ix_relationship_object_id_relation_type",
        table_name="relationship_relationship",
    )
    op.drop_index(
        "ix_relationship_subject_id_relation_type",
        table_name="relationship_relationship",
    )
