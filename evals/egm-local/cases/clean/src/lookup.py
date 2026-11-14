class CacheUnavailable(Exception):
    pass


def lookup(customer_id, cache, database):
    # Cache adapter contract: returns None for an expired/missing entry; raises
    # CacheUnavailable for every connectivity/service failure.
    try:
        cached = cache.get(customer_id)
    except CacheUnavailable:
        cached = None
    if cached is not None:
        return cached
    return database.lookup_public_display_name(customer_id)
