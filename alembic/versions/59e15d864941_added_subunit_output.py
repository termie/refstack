"""added subunit output field

Revision ID: 59e15d864941
Revises: 4f6f77184d45
Create Date: 2013-11-02 04:41:58.431516

"""

# revision identifiers, used by Alembic.
revision = '59e15d864941'
down_revision = '4f6f77184d45'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('test_results', sa.Column('subunit', sa.String(length=8192), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('test_results', 'subunit')
    ### end Alembic commands ###
