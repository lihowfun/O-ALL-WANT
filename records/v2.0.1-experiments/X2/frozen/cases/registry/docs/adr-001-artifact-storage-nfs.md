# ADR-001: Store model artifacts on the shared NFS volume

Status: Superseded by ADR-003

## Context
Training jobs and serving nodes both mount `/mnt/models`.

## Decision
Artifacts are written to `/mnt/models/<model>/<version>/` and the registry
stores the path.

## Consequences
Simple to adopt; read throughput is bounded by the NFS server.
