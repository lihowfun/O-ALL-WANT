import uuid

import boto3

from db import get_conn

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
INCOMING_BUCKET = "incoming"
PRESIGN_TTL_SECONDS = 900

s3 = boto3.client("s3")


def create_upload(tenant_id: str, filename: str, size_bytes: int) -> dict:
    """Register an upload and return a presigned POST for the client."""
    if size_bytes <= 0 or size_bytes > MAX_UPLOAD_BYTES:
        raise ValueError("size_bytes out of range")

    upload_id = str(uuid.uuid4())
    key = f"{tenant_id}/{upload_id}"

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO uploads"
            " (id, tenant_id, filename, size_bytes, source, status, key)"
            " VALUES (%s, %s, %s, %s, 'upload', 'pending', %s)",
            (upload_id, tenant_id, filename, size_bytes, key),
        )

    post = s3.generate_presigned_post(
        Bucket=INCOMING_BUCKET,
        Key=key,
        Conditions=[["content-length-range", 1, MAX_UPLOAD_BYTES]],
        ExpiresIn=PRESIGN_TTL_SECONDS,
    )
    return {"upload_id": upload_id, "url": post["url"], "fields": post["fields"]}
