"""Emit the full PostgreSQL DDL from the SQLAlchemy metadata.

    cd backend && python ../database/schema/generate_schema.py

`schema.sql` is a *derived* artefact. Alembic remains the source of truth for
schema changes; this exists so the whole schema can be read in one file, and
so a database can be created without replaying the migration chain.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "backend"))

from sqlalchemy import create_mock_engine  # noqa: E402

import app.models  # noqa: E402,F401  - registers every mapper
from app.core.database import Base  # noqa: E402

OUTPUT = pathlib.Path(__file__).with_name("schema.sql")


def main() -> None:
    statements: list[str] = []

    def collect(sql, *_args, **_kwargs) -> None:
        text = str(sql.compile(dialect=engine.dialect)).strip()
        if text:
            statements.append(text + ";\n")

    engine = create_mock_engine("postgresql+psycopg2://", collect)
    Base.metadata.create_all(engine, checkfirst=False)

    header = f"""-- SkillBridge — PostgreSQL schema
-- ---------------------------------------------------------------------------
-- GENERATED FILE. Do not edit by hand.
--
-- Regenerate with:
--     cd backend && python ../database/schema/generate_schema.py
--
-- Alembic is the source of truth for schema *changes*; this file is a
-- flattened snapshot for reading, review and bootstrapping a database without
-- replaying the migration chain.
--
-- Tables: {len(Base.metadata.tables)}
-- ---------------------------------------------------------------------------

"""
    OUTPUT.write_text(header + "\n".join(statements))
    print(f"wrote {OUTPUT} — {len(Base.metadata.tables)} tables, {len(statements)} statements")


if __name__ == "__main__":
    main()
