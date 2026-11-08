# ADR-002: Exclude fraud risk scores from data exports

Status: Accepted
Date: 2026-08-02

## Context
The `risk_scores` table holds per-user outputs of the fraud model.
Legal reviewed whether these scores are in scope for access requests.

## Decision
`risk_scores` is excluded from customer data exports. Legal confirmed
that the fraud-prevention exemption applies, and disclosing scores
would let fraudsters probe the model. The privacy notice tells
customers that fraud-prevention data is withheld.

## Consequences
Export coverage checks treat `risk_scores` as excluded by decision,
not as a gap.
