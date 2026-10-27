"""Fresh-PostgreSQL migration-chain parity test.

Run explicitly with a disposable PostgreSQL URL:

    POSTGRES_MIGRATION_TEST_URL=postgresql+psycopg://user:pass@host:port/db \
      uv run pytest tests/integration/test_migration_schema_parity.py -q

The test creates an isolated schema, runs the full ``alembic upgrade head``
chain, and asserts that every ORM table, column, index, unique constraint and
foreign key exists. It never touches the database's public schema and drops the
isolated schema afterwards.

The normal SQLite test suite skips this test because no PostgreSQL URL is set.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

import app.infrastructure.database.models  # noqa: F401  (register ORM metadata)
from app.infrastructure.database.base import Base

PG_URL = os.environ.get("POSTGRES_MIGRATION_TEST_URL", "").strip()
REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_EXTRA_TABLES = {
    "alembic_version",
    # LangGraph owns these at runtime (PostgresSaver.setup()); they are not
    # part of the application's ORM metadata.
    "checkpoints",
    "checkpoint_blobs",
    "checkpoint_writes",
    "checkpoint_migrations",
}


def _skip_if_unavailable() -> None:
    if not PG_URL:
        pytest.skip("POSTGRES_MIGRATION_TEST_URL is not set")
    if make_url(PG_URL).get_backend_name() != "postgresql":
        pytest.skip("POSTGRES_MIGRATION_TEST_URL must be a PostgreSQL URL")


def _expected_indexes(table) -> set[tuple[tuple[str, ...], bool]]:
    return {
        (tuple(column.name for column in index.columns), bool(index.unique))
        for index in table.indexes
    }


def _expected_unique_constraints(table) -> set[tuple[str, ...]]:
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }


def _expected_fks(table) -> set[tuple[tuple[str, ...], str, tuple[str, ...], str | None]]:
    return {
        (
            (fk.parent.name,),
            fk.column.table.name,
            (fk.column.name,),
            fk.ondelete,
        )
        for fk in table.foreign_keys
    }


def test_fresh_alembic_chain_matches_orm() -> None:
    _skip_if_unavailable()
    schema = f"migration_parity_{uuid.uuid4().hex[:12]}"
    engine = create_engine(PG_URL, pool_pre_ping=True)

    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    except Exception as exc:  # noqa: BLE001 - environment availability
        pytest.skip(f"PostgreSQL is not reachable: {exc}")

    try:
        env = os.environ.copy()
        env["DATABASE_URL"] = PG_URL
        env["PGOPTIONS"] = f"-c search_path={schema}"
        completed = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=900,
        )
        assert completed.returncode == 0, (
            "alembic upgrade head failed:\n"
            f"stdout:\n{completed.stdout[-4000:]}\n"
            f"stderr:\n{completed.stderr[-4000:]}"
        )

        inspector = inspect(engine)
        actual_tables = set(inspector.get_table_names(schema=schema))
        expected_tables = set(Base.metadata.tables)
        missing_tables = sorted(expected_tables - actual_tables)
        extra_tables = sorted(
            actual_tables - expected_tables - ALLOWED_EXTRA_TABLES
        )
        assert not missing_tables, f"missing tables: {missing_tables}"
        assert not extra_tables, f"unexpected tables: {extra_tables}"

        problems: list[str] = []
        for table_name in sorted(expected_tables):
            table = Base.metadata.tables[table_name]
            actual_columns = {
                column["name"]
                for column in inspector.get_columns(table_name, schema=schema)
            }
            expected_columns = {column.name for column in table.columns}
            missing_columns = sorted(expected_columns - actual_columns)
            extra_columns = sorted(actual_columns - expected_columns)
            if missing_columns:
                problems.append(f"{table_name}: missing columns {missing_columns}")
            if extra_columns:
                problems.append(f"{table_name}: extra columns {extra_columns}")

            actual_indexes = {
                (tuple(index.get("column_names") or ()), bool(index.get("unique")))
                for index in inspector.get_indexes(table_name, schema=schema)
            }
            missing_indexes = _expected_indexes(table) - actual_indexes
            if missing_indexes:
                problems.append(
                    f"{table_name}: missing indexes {sorted(missing_indexes)}"
                )

            actual_unique = {
                tuple(constraint.get("column_names") or ())
                for constraint in inspector.get_unique_constraints(
                    table_name, schema=schema
                )
            }
            missing_unique = (
                _expected_unique_constraints(table) - actual_unique
            )
            if missing_unique:
                problems.append(
                    f"{table_name}: missing unique constraints {sorted(missing_unique)}"
                )

            actual_fks = {
                (
                    tuple(fk.get("constrained_columns") or ()),
                    fk.get("referred_table"),
                    tuple(fk.get("referred_columns") or ()),
                    (fk.get("options") or {}).get("ondelete"),
                )
                for fk in inspector.get_foreign_keys(table_name, schema=schema)
            }
            missing_fks = _expected_fks(table) - actual_fks
            if missing_fks:
                problems.append(f"{table_name}: missing FKs {sorted(missing_fks)}")

        assert not problems, "schema parity problems:\n" + "\n".join(problems)
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
