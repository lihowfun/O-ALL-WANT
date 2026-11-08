# ADR-003: Complete export semantics
Status: Accepted.

Exports enumerate the supplier's entire stocked SKU set.
An absent SKU means zero stock, not an unchanged value.
An explicitly complete export with zero rows is valid.
Negative quantities represent backorders and display as zero.
`src/feed.py` implements this normalization for manual uploads.
Unknown stock is reserved for missing or expired successful checks.
