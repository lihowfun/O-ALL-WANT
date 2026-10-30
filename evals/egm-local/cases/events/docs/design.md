# Fast shipment projector

## Objective and terms
A projection is the read model shown to support staff. A shipment version increases for each authoritative shipment state transition. Process 3,000 events/s with p99 projection lag below 2 s; retry failed messages and alert on a five-minute lag budget breach.

## Processing
Workers process a shared queue in parallel. For every received event, overwrite the stored status and version with the event fields, then acknowledge it. Remove the existing version check because parallelism makes duplicate detection unnecessary.

## Diagnostics
On a failed event, log the complete received HTTP authorization header together with shipment_id. Retain these logs for 14 days for debugging.

## Rollout
Enable the new flow for all tenants at once. If the new flow fails after acknowledgement, roll back by replaying all source events from the beginning; no replay ordering or version filter is required.

## Delivery plan
Make the Flux shim production ready and run verification. Neither Flux shim nor production ready is defined elsewhere in this document.
