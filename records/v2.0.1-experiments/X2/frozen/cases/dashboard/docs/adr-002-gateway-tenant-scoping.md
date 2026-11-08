# ADR-002: Tenant scoping comes from the gateway

Status: Accepted

## Context
All dashboard traffic passes the shared API gateway. It verifies the
session token, strips any client X-Tenant-Id and sets it from claims.

## Decision
Services behind the gateway do not verify tokens. They take tenant_id
only from X-Tenant-Id and include it in every query and cache key.

## Consequences
Services must be reachable only through the gateway.
