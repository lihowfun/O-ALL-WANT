"""Static settings for the notify service."""

REGION = "us-east"
DELIVERY_DSN = "postgresql://notify@db.internal:5432/notify"
DELIVERY_RECORD_RETENTION_DAYS = 7
CHANNELS = ("email", "push")
