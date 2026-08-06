# Reddit Ads control reference

Retrieved: 2026-07-11. Refresh official platform and policy sources before using
this reference after its control-plane refresh date.

## Category model

This reference does not define an executable scoring profile. Bind a versioned
profile whose categories cover the applicable controls and whose weights total 100;
otherwise produce findings without a health score.

## Runtime evaluation contract

- Treat each row as an applicability-first evidence question. Missing evidence is
  `unknown`; unavailable or ineligible surfaces are `not_applicable`.
- Verify objective, placement, geography, identity, measurement path, catalog use,
  reporting definitions, policy, and account eligibility before evaluation.
- The registered source below grounds supported conversion events only. Current
  catalog, DPA, targeting, format, policy, and API claims require additional dated
  official source IDs or account evidence.
- This reference is advisory and export-read only. It does not provide a live
  Reddit API reader or mutation adapter.

## Controls

| ID | Category | Evidence question |
| --- | --- | --- |
| RD-M01 | Measurement | Primary conversion source and ownership are identified. |
| RD-M02 | Measurement | Reddit Pixel or Conversions API events match the business conversion taxonomy. |
| RD-M03 | Measurement | Pixel and server events use deduplication when both paths send the same event. |
| RD-M04 | Measurement | Events Manager diagnostics and representative test events have been reviewed. |
| RD-S01 | Structure | Campaign objective and optimization event match the business outcome. |
| RD-S02 | Structure | Prospecting and retargeting intent are distinguishable and exclusions prevent avoidable overlap. |
| RD-A01 | Audience | Community, interest, keyword, or first-party targeting is supported by the offer and evidence. |
| RD-A02 | Audience | Audience expansion is deliberate and measured rather than assumed beneficial. |
| RD-C01 | Creative | Creative reads naturally in the selected Reddit placement and community context. |
| RD-C02 | Creative | Materially different concepts, hooks, and formats are available for testing. |
| RD-C03 | Creative | Ad promise, comment context, and landing-page experience remain consistent. |
| RD-R01 | Retail | Catalog fields, availability, prices, links, and refresh behavior are healthy when commerce formats are used. |
| RD-R02 | Retail | Dynamic product advertising maps the relevant catalog and measurement source. |
| RD-B01 | Budget | Budget and bid strategy are viable for the objective, data volume, and test design. |
| RD-P01 | Policy | Brand-safety, placement, regulated-category, and privacy controls have been reviewed. |
| RD-E01 | Experiment | Tests isolate a decision, define success criteria, and avoid overlapping changes. |

Results use `pass`, `fail`, `unknown`, or `not_applicable`. Unknown controls
reduce evidence coverage; unavailable, beta, premium, or ineligible features are
unscored opportunities.

## Registered official evidence

- `reddit-business-help`: [Reddit supported conversion events](https://business.reddithelp.com/articles/Knowledge/supported-conversion-events)

Official sources override this summary when they change. Unsupported controls stay
`unknown`; practitioner material may supplement but not replace official evidence.
