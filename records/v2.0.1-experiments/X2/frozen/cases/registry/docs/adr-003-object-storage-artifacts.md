# ADR-003: Store model artifacts in object storage

Status: Accepted (supersedes ADR-001)

## Context
Artifacts grew past 20 GB and NFS reads slowed node startup.

## Decision
Artifacts live in the `models-prod` bucket under `<model>/<version>/`. The
registry records the object prefix and a SHA-256 checksum at registration.

## Consequences
Nodes download artifacts at load time. The NFS volume is read-only until it
is decommissioned.
