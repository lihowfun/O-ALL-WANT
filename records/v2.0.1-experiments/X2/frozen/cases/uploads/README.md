# upload-service

Accepts tenant file uploads into S3 and tracks them in the `uploads` table.
Clients upload straight to S3 via presigned POST. Owned by Storage Platform.
