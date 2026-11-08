# ADR 002: Reply deletion and counts

Status: Accepted

## Decision
Deleting a reply removes its body and keeps a tombstone in the timeline.
reply_count is the total number of reply rows, including tombstones.
Root comments are excluded; the UI calls this value "Total contributions".
This preserves contribution totals when authors remove text.
This release stores no body history or reply-body search index.
