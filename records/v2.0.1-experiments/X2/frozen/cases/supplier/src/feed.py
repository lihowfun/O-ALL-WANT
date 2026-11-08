"""Parse supplier inventory exports."""

MAX_ROWS = 120_000


def parse_snapshot(doc, supplier):
    if doc["supplier"] != supplier or doc["complete"] is not True:
        raise ValueError("incomplete supplier snapshot")
    revision = doc["revision"]
    if type(revision) is not int or revision < 0:
        raise ValueError("invalid revision")
    rows = doc["rows"]
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise ValueError("invalid rows")
    count = doc["row_count"]
    if type(count) is not int or count != len(rows):
        raise ValueError("row count mismatch")
    quantities = {}
    for row in rows:
        sku = row["sku"]
        qty = row["quantity"]
        if not isinstance(sku, str) or not 1 <= len(sku) <= 64:
            raise ValueError("invalid SKU")
        if sku in quantities:
            raise ValueError("duplicate SKU")
        if type(qty) is not int or not -(2**31) <= qty < 2**31:
            raise ValueError("invalid quantity")
        quantities[sku] = max(0, qty)
    return revision, quantities


def quantity_for(quantities, sku):
    return quantities.get(sku, 0)
