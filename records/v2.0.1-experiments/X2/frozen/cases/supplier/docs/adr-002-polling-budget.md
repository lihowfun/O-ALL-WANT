# ADR-002: Polling budget
Status: Accepted; supersedes ADR-001.

Poll every 300 seconds per supplier.
The supplier permits one request per supplier every 300 seconds.
It supports complete responses within 60 seconds at the stated limits.
Reserve another 30 seconds for parsing and publication.
A healthy change is therefore visible within 390 seconds.
No immediate retries are needed; failures use the next scheduled tick.
