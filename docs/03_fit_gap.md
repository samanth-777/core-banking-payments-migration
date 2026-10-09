# Fit-Gap Analysis: Legacy Payments Module vs Modern Target Platform

Synthetic-data portfolio project. The target is a generic modern core banking payments platform, not a specific vendor product.

**Legend:** Fit = works as is. Partial = works with configuration or transformation. Gap = needs build, process, or decision.

| # | Capability | Legacy behavior | Target behavior | Result | Resolution |
|---|---|---|---|---|---|
| FG-01 | Date format | YYYYMMDD string | ISO 8601 date | Partial | Convert in ETL. Reconciliation rules R06, R07 verify format and value |
| FG-02 | Status codes | 3-letter codes STL, PND, RTN | Descriptive enum SETTLED, PENDING, RETURNED | Partial | Lookup table. Reject unmapped codes instead of defaulting |
| FG-03 | Fraud flag | Y/N character | Boolean 1/0 | Partial | Lookup. Add a Critical control (R10) because the flag drives financial crime review |
| FG-04 | Account number length | 5 to 11 characters, prefix C (originator), C or M (beneficiary) | Must hold at least 11 characters | Gap | Confirm target column width. Add truncation control (R05) |
| FG-05 | Routing validation | No checksum validation, blanks possible | ABA checksum enforced | Gap | Pre-load validation. Blank or invalid routing rejected to exception queue (R08, R17) |
| FG-06 | Key uniqueness | No enforced unique key on extract | Unique payment_id | Partial | Dedupe check before load (R03) |
| FG-07 | Amount precision | 2 decimals | Decimal(18,2) | Fit | Block integer casts in ETL. Control on every payment (R04) plus control total |
| FG-08 | Trace ID | 15 digits (ACH), longer reference for wires | Free text up to 35 characters | Fit | Preserve as is (R16) |
| FG-09 | Payment submission | Nightly flat file only | JSON REST API | Gap | New API spec with validation and error scenarios (see /api) |
| FG-10 | Exception handling | Manual spreadsheet review | Exception queue with severity | Gap | Run reconciliation SQL, publish exceptions.csv ranked by severity |
| FG-11 | Reporting | Static end-of-day report | Data warehouse feed | Partial | Reconciliation summary feeds a Power BI view |
| FG-12 | Merchant beneficiary accounts | Prefix M accounts mixed into beneficiary field (33,815 records) | Beneficiary type attribute expected | Gap | Open question for business owner, logged as decision D-02 in the RAID log |

**Fit-gap summary:** 12 capabilities reviewed. 2 Fit, 5 Partial, 5 Gap. Gaps FG-04, FG-05 and FG-09 are on the critical path to go-live.
