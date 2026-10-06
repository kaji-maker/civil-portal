# Civil Portal source register

Research date: 2026-10-06. Source availability is not a claim of complete coverage.

The user confirmed that the new government website mentioned earlier belongs to
another project. It is excluded from this project's comparison and integration
scope.

| Source | Purpose | Status | Reference |
| --- | --- | --- | --- |
| PPMO e-GP Contract Records | Published contracts, status, completion dates and payments | Public field coverage and live access must be validated before enabling ingestion | https://ppmo.gov.np/content/13322/contract-records-manual/ |
| PPMO notices | Notices, amendments and cancellations | Official publication; document extraction requires field-level evidence | https://www.ppmo.gov.np/ |
| PPMO blacklist | Time-bounded official blacklist decisions | Entity identifiers and effective dates must be validated | https://blacklist.ppmo.gov.np/ |
| OCP Nepal archive | Historical OCDS context | Publisher no longer updates this dataset; coverage May 2016–August 2018 | https://data.open-contracting.org/en/publication/36 |

The nine records bundled in `core-scrapers/real_data_dump.json` have no source URLs
or OCIDs. Quarantining them is planned; this documentation update does not change
the dataset or ingestion behavior. They must not enter a
production dataset until their origins are independently established.

Do not substitute today's date, zero money, one bidder, or an estimated company
registration date for missing information. Preserve unknown values. Awarded
value, signed contract value and actual payments are separate measures.

Risk flags are screening indicators, not findings of corruption. The absence of
a calculable flag is not evidence of a clean procurement.
