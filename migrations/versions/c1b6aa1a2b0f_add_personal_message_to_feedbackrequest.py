"""Add personal_message to FeedbackRequest

Revision ID: c1b6aa1a2b0f
Revises: ae28a3c2b6ab
Create Date: 2024-11-20 23:04:06.801701

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1b6aa1a2b0f'
down_revision = 'ae28a3c2b6ab'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('feedback_template',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('prompt', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('feedback_request', schema=None) as batch_op:
        batch_op.add_column(sa.Column('personal_message', sa.Text(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('feedback_request', schema=None) as batch_op:
        batch_op.drop_column('personal_message')

    op.drop_table('feedback_template')
    # ### end Alembic commands ###
