# Civil Portal audit

Audit date: 2026-10-06. Baseline: commit
`c9b3702f7728ff694a60e12c03773984b5639d6c`.

This is a source-code review with limited local execution. It does not certify
the deployed system or validate a current live government feed. Implementation
is paused until the user gives the instruction to start.

## Findings and priorities

| Priority | Evidence in the baseline | Consequence | Planned action |
| --- | --- | --- | --- |
| Critical | `core-scrapers/scraper_procure.py:20–21` drops both application tables; `core-scrapers/scraper_real.py:23–24` truncates them | Existing records can be lost during ingestion | Non-destructive migrations, retained snapshots and idempotent imports |
| Critical | `scraper_procure.py:12` defaults to the application's mock stream; lines 222–229 generate registration-date offsets randomly | Screening indicators can depend on invented inputs | Explicit approved sources; unknown facts remain unknown |
| High | `client-dashboard/app.js:355` onwards uses a seeded generator; lines 432–436 derive budget consumption from estimated progress | The interface can present simulated progress and spending as procurement facts | Remove simulations; display only documented implementation and payment facts |
| High | `core-scrapers/real_data_dump.json` contains nine records without source URLs or OCIDs | Their provenance and correctness cannot be established from the bundle | Quarantine until independently verified |
| High | Database credentials are embedded in application defaults and Compose configuration; Compose publishes port 5432 | Credentials are exposed in repository history and the database can be reachable outside its container network | Rotate credentials in the actual installation, require secrets and private networking |
| High | `client-dashboard/app.js:471` and other paths interpolate content through `innerHTML` | External record content can become executable markup | Safe DOM rendering, URL validation and browser regression tests |
| Medium | `backend-api/main.py:41–42` accepts pagination without declared bounds; dashboard requests 10,000 records at once | Large requests and browser-side processing can produce poor performance and inconsistent filtered totals | Bounded server-side pagination, filters and aggregates |
| Medium | Dashboard API URL is fixed to localhost at `app.js:7` | A hosted dashboard can call the visitor's own machine instead of its server | Same-origin routing and tested deployment configuration |
| Medium | Deployment lacks a demonstrated migration, health, backup and restore workflow | Releases and recovery have unverified failure modes | Container startup checks and a restore drill into a separate database |

Line references describe the audited baseline, not future implementation.
Source review identified these defects; impact on a particular live installation
must be checked against its configuration and dataset.

## Research and accuracy boundaries

The [source register](source-register.md) records official PPMO references and
the historical OCP dataset. Public documentation describes Contract Records
features, but a usable live endpoint and its exact field coverage remain
unvalidated. Do not infer an API URL from the manual or claim complete national
coverage. The unrelated new government website mentioned earlier is out of
scope, as clarified by the user.

Award value, signed contract value and actual payments need separate fields.
Bidder counts cannot be inferred from the number of winning suppliers. Company
registration dates require evidence. Dates must identify their calendar; missing
dates must not become today's date. Currency-specific totals must avoid counting
an award once per joint-venture supplier.

Risk indicators are screening heuristics, not findings of corruption. Missing
inputs must remain visible and cannot justify a "clean" label. Collection time,
source publication time and covered period are distinct freshness measures.

## Next step

Follow the [phased implementation plan](implementation-plan.md). Finish the
source-validation gate before activating live ingestion. PostgreSQL integration,
full container execution, browser checks and recovery validation remain required;
limited local checks on unpublished drafts do not satisfy these gates.
