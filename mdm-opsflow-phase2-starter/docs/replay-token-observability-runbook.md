# Replay Token Observability Runbook

This runbook covers the replay export token observability endpoints and how to tune stale-token alert thresholds.

## Endpoints

- `GET /api/intake/events/replay-history/export-token-states`
  - Legacy list contract.
  - Returns token state items and pagination headers.
  - Keeps compatibility for existing clients.

- `GET /api/intake/events/replay-history/export-token-states/list`
  - Envelope list contract.
  - Returns `items`, cursor fields, `has_more`, `sort`, and UTC window metadata.

- `GET /api/intake/events/replay-history/export-token-states/summary`
  - Aggregated totals and actor breakdown.
  - Includes UTC window metadata.

- `GET /api/intake/events/replay-history/export-token-states/alerts`
  - Operational thresholds and ratios.
  - Main fields for dashboards:
    - `active_tokens_older_than_threshold`
    - `active_tokens_older_than_threshold_exceeded`
    - `consumed_to_revoked_ratio`

- `GET /api/intake/events/replay-history/export-token-history/summary`
  - Aggregate counts for token-audit lifecycle actions.
  - Returns:
    - `total_entries`
    - `issued_count`
    - `consumed_count`
    - `revoked_count`
    - `consume_rate_percent`
    - `revoke_rate_percent`
    - `unique_actor_count`
    - `latest_created_at`

- `GET /api/intake/events/replay-history/export-token-history/trends`
  - Bucketed audit trend counts for the current filter scope.
  - Supports `granularity=day` or `granularity=hour`.
  - Returns:
    - `items` with `bucket_start_created_at`, `issued_count`, `consumed_count`, `revoked_count`, and `total_count`
    - `window_start_created_at`
    - `window_end_created_at`
    - `window_effective_timezone`

  ## Intake UI Trend Controls

  In the Intake Hub audit panel, operators can now set `Trend granularity`:

  - `Day` (default): useful for longer operational windows.
  - `Hour`: useful for incident response and short-horizon burst analysis.

  Changing this selector and clicking `Refresh audit` applies the selected
  granularity to the trends endpoint request.

  Operators can also set `Audit window preset` to quickly bound filter timestamps:

  - `All time`: clears `start_created_at` and `end_created_at`.
  - `Last 1 hour`: sets an auto-generated UTC window ending now.
  - `Last 6 hours`: sets an auto-generated UTC window ending now.
  - `Last 12 hours`: sets an auto-generated UTC window ending now.
  - `Last 24 hours`: sets an auto-generated UTC window ending now.
  - `Last 48 hours`: sets an auto-generated UTC window ending now.
  - `Last 72 hours`: sets an auto-generated UTC window ending now.
  - `Last 96 hours`: sets an auto-generated UTC window ending now.
  - `Last 120 hours`: sets an auto-generated UTC window ending now.
  - `Last 144 hours`: sets an auto-generated UTC window ending now.
  - `Last 168 hours`: sets an auto-generated UTC window ending now.
  - `Last 7 days`: sets an auto-generated UTC window ending now.
  - `Last 14 days`: sets an auto-generated UTC window ending now.
  - `Last 21 days`: sets an auto-generated UTC window ending now.
  - `Last 28 days`: sets an auto-generated UTC window ending now.
  - `Last 60 days`: sets an auto-generated UTC window ending now.
  - `Last 90 days`: sets an auto-generated UTC window ending now.
  - `Last 30 days`: sets an auto-generated UTC window ending now.
  - `Custom`: preserves manual timestamp values.

  Selecting a preset updates the audit filter fields; clicking `Refresh audit`
  then propagates those timestamps to history, summary, and trends requests.

## Alert Tuning

Use these query parameters on alerts endpoint:

- `stale_threshold_minutes`
  - Age threshold for active issued tokens.
  - Suggested defaults:
    - Normal operations: `60`
    - Incident mode: `15`

- `stale_active_threshold_count`
  - Count threshold that flips `active_tokens_older_than_threshold_exceeded` to `true`.
  - Suggested defaults:
    - Small tenant: `5`
    - Medium tenant: `10`
    - Large tenant: `25`

## Pager Guidance

Treat alert conditions as severity by combining age and count:

- Low: exceeded for one polling cycle only.
- Medium: exceeded for three consecutive cycles.
- High: exceeded and ratio `consumed_to_revoked_ratio < 1` for at least 30 minutes.

## Cursor And Sort Contract

For deterministic paging in state lists:

- Use `sort=-issued_at` for newest-first feed.
- Pass both cursor fields from response for next page:
  - `next_cursor_issued_at`
  - `next_cursor_token_id`
- Request next page with:
  - `cursor_issued_at`
  - `cursor_token_id`

## Governance Notes

- `POST /api/intake/events/replay-history/export-token/revoke-active`
  - `dry_run=true`: available with `intake_read`.
  - `dry_run=false`: requires `intake_review` permission or platform wildcard.
  - `dry_run=false`: also requires a non-empty `reason` for audit governance.

## Audit History Filters

Use these query parameters on `GET /api/intake/events/replay-history/export-token-history`:

- `action`
  - Filter to one lifecycle action:
    - `issue_replay_history_export_token`
    - `consume_replay_history_export_token`
    - `revoke_replay_history_export_token`
- `actor_user_id`
  - Filter by operator user ID.
- `token_id`
  - Filter to one token lifecycle.
- `start_created_at` and `end_created_at`
  - Filter by UTC timestamp window.

These same filters also apply to `GET /api/intake/events/replay-history/export-token-history/summary`.
They also apply to `GET /api/intake/events/replay-history/export-token-history/trends`.

## Audit Pagination Contract

For deterministic paging on `GET /api/intake/events/replay-history/export-token-history/list`:

- Response body includes envelope fields:
  - `items`
  - `limit`
  - `has_more`
  - `next_cursor_created_at`
  - `next_cursor_id`
  - `sort`
- `limit` is server-capped to `100` even if a larger value is requested.

- Supported sort values:
  - `-created_at` (default, newest first)
  - `+created_at` (oldest first)

- Request the next page with both query parameters:
  - `cursor_created_at`
  - `cursor_id`
- If `cursor_id` is provided without `cursor_created_at`, the API returns `400`.

## Suggested Polling Strategy

- Alerts endpoint: poll every 60 seconds.
- Envelope list endpoint: refresh every 2 to 5 minutes, or on operator demand.
- Summary endpoint: refresh every 5 minutes for management dashboards.
