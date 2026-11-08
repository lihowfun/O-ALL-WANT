# Design: Staged rollout for the model registry

## Context

The registry stores model versions and tells the inference fleet which
version to serve. Changing a version today switches all traffic at once;
two Q3 incidents came from versions that regressed only on live traffic.
Serving nodes already support a canary split (`resolve_version()` in
`src/rollout.py`), but nothing in the registry sets the canary fields.

## Goals and requirements

- R1: Versions move `canary` -> `stable` only by explicit operator action.
- R2: Canary share configurable from 1% to 50%.
- R3: A rollback takes effect on every serving node within 60 s.
- R4: A request key maps to the same version on every node while the
  assignment is unchanged.
- R5: Tenant pins take precedence over any rollout.
- Non-goal: automated promotion from live metrics.

## Proposed design

### Stages

A version moves `registered -> canary -> stable`, or `canary -> rolled_back`.
A model has at most one canary. Each transition is one row update on
`assignments` guarded by `expected_generation`; it increments `generation`.
On mismatch the call returns 409 and the operator re-reads state.

### Traffic split

Nodes keep using `resolve_version()`. `bucket_for()` hashes
`model:request_key` with CRC32, so the bucket is the same on every node and
across restarts (R4). The pin is checked before the split (R5).

### Propagation and rollback

Nodes poll every `POLL_INTERVAL_S` (20 s) and `refresh()` accepts an
assignment only if its `generation` is newer than the cached one. Rollback
is an ordinary transition: it clears `canary_version`, sets `canary_percent`
to 0 and increments `generation`. Both versions stay loaded on every node
during a canary, so rollback needs no model load.

Worst case for R3: a node sees the change within one poll (20 s), and a
request already routed to the canary completes within the 30 s fleet
request deadline. Total 50 s.

### Registry outage

Nodes keep their cached assignment and retry on the next poll (ADR-002).
Transitions are unavailable during an outage; serving is unaffected.

### Artifacts

Artifacts are read from the `models-prod` bucket under
`<model>/<version>/` (ADR-003). A version enters `canary` only if the
SHA-256 recorded at registration matches the stored object.

## Data model and interfaces

Table `assignments` (existing, one row per model):

| column | type | notes |
|---|---|---|
| model | text | primary key |
| stable_version | text | not null |
| canary_version | text | null when no canary |
| canary_percent | int | 0 to 50; 0 when no canary |
| generation | bigint | +1 on every transition |
| updated_by | text | new: operator of last transition |

New table `rollout_events(model, from_stage, to_stage, percent, generation,
operator, created_at)` records every transition for audit.

Endpoints, all requiring the `registry:rollout` role:

- `POST /models/{model}/canary` `{version, percent, expected_generation}`,
  percent 1 to 50.
- `POST /models/{model}/promote` `{expected_generation}`: canary becomes
  `stable_version`; `canary_version` cleared, `canary_percent` 0.
- `POST /models/{model}/rollback` `{expected_generation}`.
- `GET /models/{model}/assignment` returns the `Assignment` fields.

## Rollout plan

1. Migration adds `rollout_events` and `assignments.updated_by`. Done when
   applied in staging and production.
2. Ship the three transition endpoints behind the `staged_rollout` flag.
   Done when integration tests cover each transition and the 409 path.
3. Enable for two internal models; run one canary and one rollback each.
   Done when measured fleet convergence is under 60 s (R3).
4. Enable for all models. To back out, turn the flag off; existing
   assignment rows stay valid for serving nodes.
