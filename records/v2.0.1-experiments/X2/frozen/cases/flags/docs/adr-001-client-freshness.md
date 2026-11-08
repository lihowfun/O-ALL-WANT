# ADR 001: Client freshness

Status: Accepted

## Decision
The five-second visibility objective applies to evaluation API responses.
SDKs poll every 30 seconds and retain their last response between polls.
Their supported contract permits up to 35 seconds of change visibility delay.
This release does not add a push channel or change SDK polling.

## Rationale
Existing applications depend on bounded polling traffic and local reads.
The API and SDK therefore have separate freshness contracts.
