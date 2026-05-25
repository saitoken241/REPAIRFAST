"""initial

Revision ID: 5e5ebae7c746
Revises: 
Create Date: 2026-03-26 14:57:22.988467

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '5e5ebae7c746'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('departments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('manager_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['manager_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cpf', sa.String(length=11), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('password', sa.String(length=255), nullable=False),
        sa.Column('company', sa.String(length=100), nullable=False),
        sa.Column('role', sa.Enum('employee', 'analyst', 'manager', name='role_enum'), nullable=False),
        sa.Column('number', sa.String(length=20), nullable=True),
        sa.Column('status_usuario', sa.Boolean(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_cpf'), 'users', ['cpf'], unique=True)
    op.create_index(op.f('ix_users_name'), 'users', ['name'], unique=False)
    op.create_index(op.f('ix_users_number'), 'users', ['number'], unique=False)
    op.create_table('reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('attachment', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=20), nullable=False),
        sa.Column('status', sa.Enum('open', 'closed', 'in_progress', name='status_enum'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('priority', sa.Enum('low', 'medium', 'high', name='priority_enum'), nullable=False),
        sa.Column('occurrence_type', sa.Enum('failure', 'risk', 'improvement', name='occurrence_type_enum'), nullable=True),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reports_category'), 'reports', ['category'], unique=False)
    op.create_index(op.f('ix_reports_priority'), 'reports', ['priority'], unique=False)
    op.create_index(op.f('ix_reports_status'), 'reports', ['status'], unique=False)
    op.create_index(op.f('ix_reports_title'), 'reports', ['title'], unique=False)
    op.create_table('report_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=30), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_report_history_report_id', 'report_history', ['report_id'])
    op.create_table('action_plan',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('due_date', sa.String(length=10), nullable=True),
        sa.Column('done', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('done_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_action_plan_report_id', 'action_plan', ['report_id'])


def downgrade() -> None:
    op.drop_index('ix_action_plan_report_id', table_name='action_plan')
    op.drop_table('action_plan')
    op.drop_index('ix_report_history_report_id', table_name='report_history')
    op.drop_table('report_history')
    op.drop_index(op.f('ix_reports_title'), table_name='reports')
    op.drop_index(op.f('ix_reports_status'), table_name='reports')
    op.drop_index(op.f('ix_reports_priority'), table_name='reports')
    op.drop_index(op.f('ix_reports_category'), table_name='reports')
    op.drop_table('reports')
    op.drop_index(op.f('ix_users_number'), table_name='users')
    op.drop_index(op.f('ix_users_name'), table_name='users')
    op.drop_index(op.f('ix_users_cpf'), table_name='users')
    op.drop_table('users')
    op.drop_table('departments')