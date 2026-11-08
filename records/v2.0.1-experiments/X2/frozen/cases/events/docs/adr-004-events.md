# ADR-004: event consumption
Status: accepted; revision r1; date 2026-08-12.
The broker may redeliver and reorder shipment events. Consumer projections must not move a shipment back to an older version. A shipment_id and version identify a logical event. Authentication tokens must never be written to logs.
