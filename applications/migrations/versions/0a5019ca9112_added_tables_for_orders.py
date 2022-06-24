"""Added tables for orders

Revision ID: 0a5019ca9112
Revises: 45fb24ea370e
Create Date: 2022-06-24 10:15:16.305273

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0a5019ca9112'
down_revision = '45fb24ea370e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('price', sa.Float(), nullable=False),
    sa.Column('status', sa.String(length=8), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('email', sa.String(length=256), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('productorder',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('productId', sa.Integer(), nullable=False),
    sa.Column('orderId', sa.Integer(), nullable=False),
    sa.Column('requested', sa.Integer(), nullable=False),
    sa.Column('received', sa.Integer(), nullable=False),
    sa.Column('price', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['orderId'], ['orders.id'], ),
    sa.ForeignKeyConstraint(['productId'], ['products.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('productorder')
    op.drop_table('orders')
    # ### end Alembic commands ###
