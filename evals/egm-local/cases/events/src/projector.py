def apply_event(db, event):
    with db.transaction():
        row = db.shipments.lock_row(event.shipment_id)
        if event.version <= row.version:
            return
        row.status = event.status
        row.version = event.version
