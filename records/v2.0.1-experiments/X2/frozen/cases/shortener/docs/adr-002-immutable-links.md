# ADR-002: Immutable links and 302 redirects

Status: Accepted (2025-05-02)

## Context
Editable targets let vetted links be redirected elsewhere after sharing, and
301 responses are cached by browsers, hiding repeat clicks from analytics.

## Decision
- A link's `target_url` cannot change after creation.
- Deleting a link stops its redirects within 5 minutes; the terms of
  service state this window.
- Redirects return 302 so every click reaches the service.

## Consequences
Redirect nodes may cache code-to-target lookups for up to 5 minutes.
