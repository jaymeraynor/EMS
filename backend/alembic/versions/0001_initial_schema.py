"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-11-27
"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('organizations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_organizations')),
    sa.UniqueConstraint('name', name=op.f('uq_organizations_name'))
    )
    op.create_table('sites',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('address', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], name=op.f('fk_sites_org_id_organizations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sites'))
    )
    op.create_index(op.f('ix_sites_org_id'), 'sites', ['org_id'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=320), nullable=False),
    sa.Column('password_hash', sa.String(length=100), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("role = 'admin' OR org_id IS NOT NULL", name=op.f('ck_users_org_required_unless_admin')),
    sa.CheckConstraint("role IN ('admin','org_admin','viewer')", name=op.f('ck_users_role_valid')),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], name=op.f('fk_users_org_id_organizations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email'))
    )
    op.create_index(op.f('ix_users_org_id'), 'users', ['org_id'], unique=False)
    op.create_table('meters',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('site_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('taipower_account_no', sa.String(length=20), nullable=True),
    sa.Column('api_key_hash', sa.String(length=64), nullable=False),
    sa.Column('api_key_prefix', sa.String(length=16), nullable=False),
    sa.Column('is_demo', sa.Boolean(), nullable=False),
    sa.Column('voltage', sa.String(length=20), nullable=False),
    sa.Column('scheme', sa.String(length=20), nullable=False),
    sa.Column('contract_regular_kw', sa.Float(precision=53), nullable=False),
    sa.Column('contract_non_summer_kw', sa.Float(precision=53), nullable=False),
    sa.Column('contract_semi_peak_kw', sa.Float(precision=53), nullable=False),
    sa.Column('contract_sat_semi_peak_kw', sa.Float(precision=53), nullable=False),
    sa.Column('contract_off_peak_kw', sa.Float(precision=53), nullable=False),
    sa.Column('customer_category', sa.String(length=20), nullable=False),
    sa.Column('industry_adjustment_coef', sa.Float(precision=53), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['sites.id'], name=op.f('fk_meters_site_id_sites')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_meters')),
    sa.UniqueConstraint('api_key_hash', name=op.f('uq_meters_api_key_hash'))
    )
    op.create_index(op.f('ix_meters_site_id'), 'meters', ['site_id'], unique=False)
    op.create_table('ingest_batches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('meter_id', sa.Integer(), nullable=False),
    sa.Column('source', sa.String(length=10), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('received', sa.Integer(), nullable=False),
    sa.Column('inserted', sa.Integer(), nullable=False),
    sa.Column('duplicates', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['meter_id'], ['meters.id'], name=op.f('fk_ingest_batches_meter_id_meters')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_ingest_batches_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ingest_batches'))
    )
    op.create_index(op.f('ix_ingest_batches_meter_id'), 'ingest_batches', ['meter_id'], unique=False)
    op.create_table('readings',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('meter_id', sa.Integer(), nullable=False),
    sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
    sa.Column('power_kw', sa.Float(precision=53), nullable=False),
    sa.Column('energy_kwh_total', sa.Float(precision=53), nullable=True),
    sa.Column('kvarh_total', sa.Float(precision=53), nullable=True),
    sa.Column('source', sa.String(length=10), nullable=False),
    sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("source IN ('api','csv')", name=op.f('ck_readings_source_valid')),
    sa.ForeignKeyConstraint(['meter_id'], ['meters.id'], name=op.f('fk_readings_meter_id_meters')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_readings')),
    sa.UniqueConstraint('meter_id', 'ts', name='uq_readings_meter_ts')
    )
    op.create_index('ix_readings_meter_id_ts', 'readings', ['meter_id', 'ts'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_readings_meter_id_ts', table_name='readings')
    op.drop_table('readings')
    op.drop_index(op.f('ix_ingest_batches_meter_id'), table_name='ingest_batches')
    op.drop_table('ingest_batches')
    op.drop_index(op.f('ix_meters_site_id'), table_name='meters')
    op.drop_table('meters')
    op.drop_index(op.f('ix_users_org_id'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_sites_org_id'), table_name='sites')
    op.drop_table('sites')
    op.drop_table('organizations')
