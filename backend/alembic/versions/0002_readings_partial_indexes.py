"""partial indexes for cumulative-register neighbour lookups

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-27
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

INDEXES = (("ix_readings_meter_ts_kwh_notnull", "energy_kwh_total"),
           ("ix_readings_meter_ts_kvarh_notnull", "kvarh_total"))


def upgrade() -> None:
    for name, col in INDEXES:
        where = sa.text(f"{col} IS NOT NULL")
        op.create_index(name, 'readings', ['meter_id', 'ts'], unique=False,
                        postgresql_where=where, sqlite_where=where)


def downgrade() -> None:
    for name, _ in reversed(INDEXES):
        op.drop_index(name, table_name='readings')
