"""add performance indexes

Revision ID: e7b2c1a4d890
Revises: f371d797a2e9
Create Date: 2026-11-23 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7b2c1a4d890'
down_revision = 'f371d797a2e9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_tasks_board_id'), ['board_id'], unique=False)

    with op.batch_alter_table('boards', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_boards_project_id'), ['project_id'], unique=False)

    with op.batch_alter_table('project_members', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_project_members_user_id'), ['user_id'], unique=False)

    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_notifications_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_notifications_is_read'), ['is_read'], unique=False)


def downgrade():
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_notifications_is_read'))
        batch_op.drop_index(batch_op.f('ix_notifications_user_id'))

    with op.batch_alter_table('project_members', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_project_members_user_id'))

    with op.batch_alter_table('boards', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_boards_project_id'))

    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_tasks_board_id'))
