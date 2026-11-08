# ADR-001: Dashboards query the orders primary

Status: Superseded by ADR-003

## Context
The first dashboard prototype had four charts and few users.

## Decision
Dashboard queries run directly against the orders Postgres primary
using a read-only role.

## Consequences
Simple to build; heavy queries compete with checkout traffic.
