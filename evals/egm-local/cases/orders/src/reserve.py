def reserve(db, order_id, sku, qty):
    with db.transaction():
        previous = db.reservations.find(order_id=order_id)
        if previous:
            return previous
        stock = db.inventory.lock_row(sku=sku)
        if stock.available < qty:
            return None
        stock.available -= qty
        return db.reservations.insert(order_id=order_id, sku=sku, qty=qty)
