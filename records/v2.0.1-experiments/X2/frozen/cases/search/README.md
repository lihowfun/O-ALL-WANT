# customer-search

Keeps an OpenSearch index of customers for the support console, fed by
change events that `src/change_publisher.py` relays from `change_log` to Kafka.
