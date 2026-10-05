# ADR-001: Database Strategy

**Date**: 2026-10-04  
**Status**: Accepted  
**Deciders**: Lead Architect

---

## Context

The system requires a persistent relational store for 22 domain entities with referential integrity, JSON columns (for value objects like EvidenceManifest), and migration support.

Development must work with zero external infrastructure. Production must support concurrent load and production-grade reliability.

## Decision

Use **SQLite** (via SQLAlchemy 2.x + aiosqlite) for development.  
Use **PostgreSQL** (via asyncpg) for production.

Database is selected entirely by the `DATABASE_URL` environment variable. Alembic manages migrations on both engines.

## Rationale

- SQLite: zero setup, no server process, works in OneDrive-synced folders (with WAL mode caveat documented)
- PostgreSQL: battle-tested for production; supports concurrent writes; native JSON type
- SQLAlchemy 2.x: same ORM code works on both; async-native
- Alembic: autogenerate migrations from model changes; tested on both engines

## Consequences

- Developers run with SQLite by default (no configuration needed)
- CI can use SQLite; production uses PostgreSQL
- JSON columns stored as TEXT in SQLite, native JSON in PostgreSQL (SQLAlchemy handles transparently)
- OneDrive SQLite WAL conflict is documented in OPERATIONS.md

## Rejected Alternatives

- **MongoDB**: Document model doesn't fit relational integrity needed for evidence chains
- **PostgreSQL-only**: Requires running a server for dev setup
- **TinyDB**: No migration support, no SQLAlchemy compatibility
