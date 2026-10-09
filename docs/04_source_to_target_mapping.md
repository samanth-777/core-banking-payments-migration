# Source-to-Target Mapping: Legacy Payments to Modern Platform

Synthetic data adapted from public PaySim. Profile numbers measured from the 100,000-row legacy extract. Machine-readable version: `04_source_to_target_mapping.csv`.

| Map | Legacy field | Target field | Type | Business rule | Req | Recon rule | Legacy profile |
|---|---|---|---|---|---|---|---|
| M01 | PMT_ID | payment_id | Direct | Preserve. Primary key, must be unique | 001, 002, 003 | R01, R02, R03 | length 10, 100,000 distinct |
| M02 | PMT_TYP | payment_method | Lookup | W to WIRE, A to ACH, else reject | 010 | R11 | 2 values |
| M03 | PMT_DIR | payment_direction | Lookup | C to CREDIT, D to DEBIT, else reject | 010 | R12 | 2 values |
| M04 | PMT_AMT | amount_usd | Direct | Decimal(18,2), no rounding or integer cast | 004 | R04 | total $18,180,182,908.87 |
| M05 | ORIG_ACCT | originator_account | Direct | Full value, no truncation | 005 | R05 | length 5 to 11 |
| M06 | ORIG_RTN | originator_routing | Direct + validate | 9 digits, ABA checksum, no blanks | 007 | R08, R13, R17 | length 9, 25 distinct |
| M07 | BENE_ACCT | beneficiary_account | Direct | Full value, no truncation | 005 | R15 | length 6 to 11 |
| M08 | BENE_RTN | beneficiary_routing | Direct + validate | 9 digits, ABA checksum, no blanks | 007 | R08, R14, R17 | length 9, 25 distinct |
| M09 | TRACE_NO | trace_id | Direct | Preserve unchanged | 011 | R16 | length 15 to 19 |
| M10 | STTL_DT | settlement_date | Format | YYYYMMDD to YYYY-MM-DD, value unchanged | 006 | R06, R07 | 31 distinct dates, 2026-07-01 to 2026-07-31 |
| M11 | PMT_STS | payment_status | Lookup | STL to SETTLED, PND to PENDING, RTN to RETURNED, no defaults | 008 | R09 | STL 91,943, PND 5,038, RTN 3,019 |
| M12 | FRD_FLG | fraud_indicator | Lookup | Y to 1, N to 0, must survive | 009 | R10 | 122 flagged Y, trial load lost the flag on 10 of them |

## Validation logic
Validation is run in `sql/02_reconciliation_rules.sql`. Rules R01 to R10 each map to a seeded failure type. R11 to R17 are control rules that confirm the clean fields stayed clean (all returned 0 exceptions).

## Open items
- Target column width for account numbers must be confirmed at 11 characters or more (FG-04).
- Treatment of merchant (M-prefix) beneficiary accounts needs a business decision (FG-12, RAID D-02).
