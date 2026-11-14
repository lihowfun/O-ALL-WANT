# Design draft: regional notification fan-out

Status: draft for review. Owner: notify team. Revision: d3.

## 1. Context

The notify service sends account notifications (password resets, order updates)
to email and mobile push. Today one process in a single region sends every
message (see `src/notify/dispatcher.py`). Sends queue up during regional
maintenance windows.

## 2. Goals

- Send notifications from three regions (us-east, eu-west, ap-south) at the same time.
- Keep sending when one region is down.
- Let support staff see what was sent to a customer.

## 3. Terms

- **Fan-out worker**: the process that expands one notification into one send
  per device or email address of the recipient.
- **Delivery record**: one row describing a single send attempt and its outcome.

## 4. Architecture

Each region runs a pool of fan-out workers behind a regional queue. Producers
write a notification once; the Kestrel shim copies it into every regional queue,
and each region runs a BRV pass on it before fan-out.

The delivery log moves to a new MongoDB cluster: a three-node replica set per
region with cross-region replication, so that every region can read every
delivery record.

## 5. Data retention

Delivery records are kept for 7 days and then deleted by a nightly job.

## 6. Operations

Support staff can look up any delivery record from the last 30 days in the
admin console when a customer reports a message that never arrived.

## 7. Implementation plan

1. Build the fan-out workers.
2. Make the dispatcher production ready.
3. Handle failures properly.
4. Run verification.
