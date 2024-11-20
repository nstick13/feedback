"""Update User model

Revision ID: c06acff056cb
Revises: e3f9d38b524e
Create Date: 2024-11-18 16:03:09.805814

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c06acff056cb'
down_revision = 'e3f9d38b524e'
branch_labels = None
depends_on = None


def upgrade():
    # Add the column with a nullable=True to avoid errors
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('password_hash', sa.String(length=128), nullable=True))

    # Set a default value for existing rows
    op.execute("UPDATE \"user\" SET password_hash = 'default_password'")

    # Make the column non-nullable
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('password_hash', nullable=False)

def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('password_hash')
    # ### end Alembic commands ###
