# Civil Portal phased implementation plan

Updated: 2026-10-06. Proceed through one phase at a time. Draft code is not
evidence that a phase has passed verification. Later-phase drafts remain
unpublished until their dependencies and acceptance checks pass.

Implementation is paused at the user's request. This GitHub update contains
documentation only. Resume implementation only when the user explicitly asks.

There is no new government website comparison in scope. Existing official PPMO
sources remain candidates, subject to direct validation. The OCP archive is
historical and cannot establish current procurement coverage.

## Phase 1 — Audit and establish the factual baseline

- Record defects in ingestion, API, dashboard and deployment with reproducible
  examples. Prioritize data loss and invented facts before visual improvements.
- Maintain the source register with publisher, coverage, publication dates,
  supported fields, access constraints and verification status.
- Quarantine the nine legacy records whose provenance is missing. Keep unknown
  dates, amounts, bidder counts and registration dates explicitly unknown.
- Validate a sample against its official source. Distinguish award value,
  contract value and actual payments; document Gregorian versus Bikram Sambat
  handling and gaps in coverage.

Acceptance: documented audit and field mappings; traceable sample evidence for
each source to be activated. An inaccessible or unvalidated source stays
disabled and is recorded as a blocker, not represented as current data.

Status: audit and source research performed; source register exists. Direct live
feed validation and an official sample import remain outstanding. The phase
has not passed its live-source acceptance gate.

## Phase 2 — Reliable ingestion and retained evidence

- Add non-destructive migrations and retain raw source snapshots, hashes,
  collection times, release history and rejected records.
- Make repeat imports idempotent; handle corrections and older releases without
  destroying current records. Preserve multiple awards and suppliers.
- Require explicit source configuration. Add bounded fetching, retries and
  accurate success, partial failure and freshness reporting.

Acceptance: PostgreSQL tests demonstrate repeat-import safety, corrected and
older release behavior, exact monetary precision, malformed-record isolation,
retained history and preservation of existing data after fetch failures. Verify
the approved official sample end to end before activating its schedule.

## Phase 3 — Correct API and screening indicators

- Add bounded server-side filters, consistent counts and scoped source queries.
- Aggregate awards once, separate currencies and expose evidence and history.
- Calculate screening indicators only when the necessary facts are known.
  Explain their limitations and distinguish insufficient data from no detected
  indicators. Give the API a read-only database role.

Acceptance: database-backed API tests reconcile totals with source records,
exercise pagination and filters, reject invalid input and demonstrate read-only
permissions. Unknown values and historical data remain identifiable.

## Phase 4 — Dashboard usability and truthful presentation

- Show source coverage, freshness, unknown values and accurate filtered totals.
- Improve responsive layouts, navigation, accessible details and source links.
- Remove simulated progress and spending. Resolve empty, loading and failure
  states; prevent HTML injection and unsafe spreadsheet exports.

Acceptance: browser checks cover desktop and mobile, keyboard access, empty
results, unavailable API and overlapping filter requests. Reconcile displayed
values and exports with the Phase 3 API and reviewed source sample.

## Phase 5 — Deployment and recovery

- Build reproducible containers with private database networking, scoped roles,
  secret configuration, health checks and HTTPS.
- Test migrations against an existing installation and document compatibility
  with its PostgreSQL/PostGIS version.
- Add backups, restoration into a separate database and rollback instructions.

Acceptance: CI builds and starts the stack; health and API checks pass. A backup
restores successfully into a separate database and the rollback procedure is
tested. Production activation requires the actual hosting target and validated
source configuration; neither is currently supplied.

## Phase 6 — Ongoing accuracy and maintenance

- Schedule only validated sources; monitor failures, overdue imports and source
  changes. Connect monitoring to an agreed alert destination.
- Establish dependency updates, periodic source reconciliation, off-host
  backups and correction procedures.

Acceptance: demonstrate a successful scheduled import, a failed-import alert,
freshness monitoring and a repeatable reconciliation review. Assign operating
responsibilities and review intervals. Currentness is bounded by source coverage
and publication delays, which must remain visible to users.

## Current verification limits

Foundational changes for several phases have been drafted locally. Local checks
have passed 21 Python unit/API tests and four JavaScript helper tests. These do
not substitute for PostgreSQL integration, full container, browser or restore
checks. Database and Docker execution are unavailable in this workspace; those
gates remain pending. These implementation drafts are excluded from this
documentation update. No production deployment has been performed.

For each phase, report the completed changes, verification evidence, outstanding
limitations and next gate before moving on. Do not describe the system as
perfect, complete or fully current without evidence supporting those claims.
