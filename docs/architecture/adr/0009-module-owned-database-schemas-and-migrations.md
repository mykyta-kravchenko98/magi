# ADR 0009: Module-owned database schemas and migration histories

- Status: Accepted
- Date: 2026-08-13

## Context

The modular monolith uses one PostgreSQL instance and is deployed as one application, but
its bounded contexts must own their relational data independently. Tables in one context
must not become an integration surface for another context. The design should also keep a
future extraction of a module into a separately deployed service practical.

A single SQLAlchemy declarative registry and a single Alembic history would create a
shared persistence model. Even if migration filenames mention their owning modules, a
single revision chain would make one module's database history depend on revisions owned
by other modules. That dependency would have to be untangled during extraction.

## Decision

Each bounded context owns an independent relational persistence boundary:

- a dedicated PostgreSQL schema;
- a dedicated SQLAlchemy `DeclarativeBase`, registry, and `MetaData`;
- a dedicated Alembic environment and revision history;
- a dedicated Alembic version table;
- ORM mappings, repositories, units of work, and migrations located in that module's
  `infrastructure.persistence` package.

The initial schemas are `documents`, `ingestion`, and `retrieval`. All three contexts have
independent migration histories even when a context does not yet own product tables.

The first revision in each history creates only the database infrastructure owned by that
context, beginning with its PostgreSQL schema. Product tables are introduced by later
revisions. Initial table creation should normally use one revision per table; a later
product change may alter multiple database objects in one revision when those changes
form one atomic model evolution.

Each context's complete migration history must apply successfully to an empty PostgreSQL
database without running migrations from any other context. Revisions must not import
another context's metadata, depend on another context's revision identifiers, or create
objects owned by another context.

Cross-context references are stored as scalar identifiers. There are no cross-context
foreign keys, SQLAlchemy relationships, or database joins. A context validates and uses
such references through the owning module's public application contract rather than by
reading its tables.

The modules may share persistence mechanisms that have no product knowledge. The shared
persistence package may provide engine and session factories, connection settings, and a
constraint naming convention. It must not define a shared declarative base, product
tables, repositories, or a global unit of work.

Database creation, credentials, PostgreSQL roles, global extensions, backup policy, and
other server-level concerns remain deployment or platform responsibilities. A module's
migrations own its schema-local objects and product model.

The application bootstrap runs every module's migrations during deployment, but this
orchestration does not merge their histories. Each history remains directly transferable
with its owning module.

## Consequences

- Database ownership is visible in Python packages, PostgreSQL object names, metadata,
  and migration histories.
- A module can be extracted with its persistence code and full revision history without
  carrying unrelated revisions from the monolith.
- Alembic configuration and deployment orchestration are more verbose than a single
  global migration environment.
- PostgreSQL schemas provide namespace and ownership boundaries, but not access control
  while all modules connect with the same database role. Separate roles and connection
  pools may be introduced if database-enforced isolation becomes necessary.
- Cross-context referential integrity is not enforced with foreign keys. Consistency is
  maintained at application boundaries and by the workflows that coordinate contexts.
- Moving a table to another context is an explicit ownership transfer and requires a
  coordinated migration rather than a simple Python package move.
- CI should prove that each context can independently migrate an empty database to its
  head revision.

## Rejected alternatives

- One shared `DeclarativeBase` and Alembic history: rejected because it merges persistence
  ownership and couples every module to one revision graph.
- Separate PostgreSQL schemas with one Alembic history: rejected because schema separation
  alone does not make a module's migration history independently transferable.
- One initial migration containing all product tables: rejected because it mixes database
  namespace bootstrap with product-model evolution and creates an oversized baseline.
- Cross-context foreign keys and ORM relationships: rejected because they expose another
  context's storage model as an integration contract.
- A separate PostgreSQL database per context immediately: rejected because independent
  deployment and database-level operational isolation are not yet required for this
  modular monolith.
