# Design: Asynchronous click pipeline

Status: In review, Platform team

## Context

Every redirect in `src/redirect.py` writes to `daily_clicks` before it
answers (`handle_redirect` calls `record_click`). During campaigns the row
of a popular code is contended and redirect p99 reaches 900 ms. Owners also
want referrer and country breakdowns. Invoices for paid workspaces are
computed from `daily_clicks`.

## Goals and requirements

- R1: Redirect p99 under 50 ms at a peak of 12,000 redirects/s.
- R2: Campaign peaks of 12,000 clicks/s last up to 1 hour; analytics lag
  stays under 60 s throughout.
- R3: Click counts in `daily_clicks` are exact; they are invoiced.
- R4: A link's stats are visible only to its owner.
- R5: Raw click events are kept 400 days.

Non-goals: real-time dashboards, bot filtering.

## Proposed design

The redirect handler resolves the code, publishes a click event to the
`clicks` topic (ADR-001) and returns 302 (ADR-002). It no longer writes to
the database. Each redirect process caches code-to-target lookups for 5
minutes.

A new `click-aggregator` service consumes `clicks` in batches of up to 500
events. Per batch it opens one transaction, inserts the events into
`click_events` and adds the batch's per-(code, day) counts to
`daily_clicks`. The consumer offset is committed after the transaction
commits, so a worker crash never loses a click.

The topic has 4 partitions with one aggregator worker each. Load tests show
a worker sustains 2,000 events/s, so the pipeline handles 8,000 events/s,
well above the 2,300 clicks/s average.

Storage: 2,300 clicks/s is about 200 M clicks/day. A `click_events` row is
about 120 bytes with indexes: 24 GB/day, 9.6 TB for 400 days. The analytics
cluster has 12 TB.

Stats move to the read API, which reads a replica and joins `daily_clicks`
with breakdowns from `click_events`.

## Data model and interfaces

Click event (JSON on `clicks`, keyed by `event_id`): `event_id` (UUID from the
producer), `code`, `ts` (UTC), `referrer` (Referer host or null), `country`
(ISO code from the edge GeoIP header or null).

Table `click_events` (new): the event fields, partitioned by month on `ts`,
indexed on (code, ts). A monthly partition is dropped once its newest row is
older than 400 days.

Table `daily_clicks` (existing): primary key (code, day), `clicks` bigint.

`GET /api/links/{code}/stats?from=YYYY-MM-DD&to=YYYY-MM-DD` returns daily
totals and the top 10 referrers and countries. It skips the session lookup;
the code in the path identifies the link, so the CDN caches responses for 60 s.

## Rollout

1. Create `click_events` and the 4-partition `clicks` topic; deploy
   `click-aggregator` with no producers attached.
2. Add flag `async_clicks`, evaluated per code. Codes with it on publish
   events; codes with it off keep calling `record_click`, so no click is
   counted on both paths.
3. Enable for 5%, 50%, then 100% of codes, two days per step, checking
   redirect p99 and aggregator lag at each step.
4. Remove `record_click` and the flag one week after reaching 100%.

Done when redirect p99 is under 50 ms and aggregator lag under 60 s for 7
consecutive days at 100%.

Rollback: turn the flag off; redirects return to `record_click` and the
aggregator drains the events already on the topic.
