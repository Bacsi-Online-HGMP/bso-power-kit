# GAQL compatibility and accuracy notes

GAQL fields, compatibility rules, date constants, and API versions change. Treat
this file as query-design guidance, not a current field catalog. Before executing
a query, record the customer ID, API version, query resource, selected fields,
date window, and the current Google Ads API field/reference source ID. A runtime
`INVALID_ARGUMENT` or `UNRECOGNIZED_FIELD` is `needs_input` for query repair; it
must not be silently converted into an empty dataset.

## Compatibility discovery

Use the current official Google Ads API documentation and field metadata for the
selected version to validate:

- whether each selected and filtered field is selectable with the primary resource;
- whether segments change row grain or conflict with metrics;
- whether the chosen date constant exists, otherwise use explicit dates;
- whether resource status is available in-query or must be joined or filtered
  after retrieval;
- pagination, partial-failure, quota, currency-unit, timezone, and manager-account
  behavior.

Do not carry a query forward solely because it worked with a prior API version.

## Keyword Deduplication

**Problem:** `keyword_view + segments.date DURING LAST_30_DAYS` returns one row per keyword per day. A keyword active 5 days = 5 rows. Same keyword with BROAD + PHRASE = 2 rows per day = 10 total.

**Fix:** Deduplicate by `(ad_group_id + keyword_text + match_type)` at fetch time. Aggregate metrics (impressions, clicks, cost, conversions) across duplicate rows.

**Alternative:** Remove `segments.date` from GAQL queries entirely to eliminate date-level duplication at source.

Record the resulting row grain in the run manifest. Downstream checks may consume
the normalized keyword grain only after fixture or account-level reconciliation.

## Filter Scope Best Practices

Scope status to the question being answered. A current-serving health view normally
separates enabled, paused, and removed entities. A historical change, overlap, or
rollback investigation may require paused entities. Never describe the account as
complete when the query intentionally excludes a status, and never assume a fixed
lookback is suitable for every conversion lag or business cycle.

## Error Handling

Track which data fetches failed and why. Report as a G-SYS1 diagnostic:
- List all failed data sources with error messages
- Provide per-check context on which checks were skipped due to missing data
- Never silently skip checks; always explain why data is unavailable

## Historical match-type interpretation

Do not infer legacy Broad Match Modified behavior or advertiser intent from the
current `BROAD` enum, bidding strategy, or absence of a `+` prefix. Inspect dated
change history, search terms, current matching behavior, campaign controls, and
owner intent. If that evidence is unavailable, report the historical classification
as `unknown`; do not turn it into a failure or an automated negative-keyword action.
