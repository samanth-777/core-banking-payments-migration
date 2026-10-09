# Business Requirements Document: Payments Data Migration (Legacy to Modern Core)

**Author:** Samanth Madhesh | **Version:** 1.0 | **Date:** October 2026
**Data note:** Synthetic data adapted from the public PaySim dataset. Fictional bank, fictional stakeholders. Not real bank work.

## 1. Purpose
Define what must be true for the ACH and wire payments history to move from the legacy payments module to the modern core banking payments platform with no loss, duplication, or corruption.

## 2. Background
The bank is retiring a legacy payments module that stores records in a flat COBOL-style layout. The modern platform uses an API-first schema with ISO dates, descriptive codes, and enforced keys. A first trial conversion of 100,000 legacy payments was loaded into the target and reconciled. It produced 100,100 target rows and **4,010 exceptions (4.01% of records)**. The net dollar variance was only -$4.45M on $18.18B, but the gross error behind it was about $203.2M, because missing, duplicated and orphaned payments offset each other. A net control total alone would have passed this migration.

## 3. Scope
**In scope:** ACH (91,624 records) and wire (8,376 records) payment history, field-level mapping, reconciliation, exception management, SIT/UAT/regression testing, payment submission API, go-live readiness.
**Out of scope:** Account master conversion, customer onboarding, lending, card payments, real-time payments, decommissioning of the legacy module.

## 4. Stakeholders (fictional roles)
| Role | Interest |
|---|---|
| Head of Payments Operations (business owner) | No customer-facing payment errors, clean cutover |
| Core Platform Product Owner | Platform configuration, backlog, fit-gap decisions |
| Data Migration Lead | Conversion logic, load runs, reruns |
| QA Lead | Test strategy, SIT/UAT entry and exit |
| Financial Crime and Compliance | Fraud flag integrity, audit trail |
| Finance Controller | Control totals, sign-off on balances |
| Business Analyst (me) | Requirements, mapping, reconciliation, traceability |

## 5. Business objectives
1. 100% of in-scope payments converted, none duplicated, none invented.
2. Zero value variance at the individual payment level, not just in total.
3. Zero loss of financial crime flags.
4. Every exception logged, ranked by severity, and traceable to a requirement.

## 6. Business requirements
| ID | Requirement | Priority | Recon rule |
|---|---|---|---|
| REQ-001 | Every in-scope legacy payment shall exist in the target | Must | R01 |
| REQ-002 | No payment_id shall appear more than once in the target | Must | R03 |
| REQ-003 | No target payment shall exist without a legacy source | Must | R02 |
| REQ-004 | Payment amount shall match the legacy value to the cent, with no rounding | Must | R04 |
| REQ-005 | Originator and beneficiary account numbers shall migrate at full length | Must | R05, R15 |
| REQ-006 | Settlement date shall convert from YYYYMMDD to ISO 8601 with the same date value | Must | R06, R07 |
| REQ-007 | Routing numbers shall be present, 9 digits, ABA checksum valid, and unchanged | Must | R08, R13, R14, R17 |
| REQ-008 | Status codes shall map STL, PND, RTN to SETTLED, PENDING, RETURNED with no defaulting | Must | R09 |
| REQ-009 | The fraud flag shall be preserved for every payment | Must | R10 |
| REQ-010 | Payment method and direction shall map correctly (W/A, C/D) | Must | R11, R12 |
| REQ-011 | Trace ID shall be preserved unchanged | Must | R16 |
| REQ-012 | Every reconciliation exception shall be logged with rule, severity, legacy value, target value | Must | All |
| REQ-013 | The payment submission API shall accept JSON, validate fields, and return structured errors | Should | n/a |
| REQ-014 | Go-live shall require zero open Critical and High exceptions and signed UAT | Must | All |

## 7. Severity model
- **Critical:** loss of a payment or loss of a compliance flag (R01, R10). Currently 410 exceptions.
- **High:** wrong money, wrong status, wrong date, or duplicate/orphan record. Currently 2,500 exceptions.
- **Medium:** data quality issue with no direct money impact (account truncation, date format). Currently 1,100 exceptions.

## 8. Acceptance criteria for go-live
1. Record count, distinct key count and amount total match legacy exactly.
2. Reconciliation rules R01 to R17 return zero exceptions on the final rehearsal load.
3. SIT exit: 100% of test cases executed, zero open Critical or High defects.
4. UAT sign-off by Payments Operations and Compliance.
5. Regression pass on the last two rehearsal loads.

## 9. Assumptions
- Legacy extract is complete and frozen at extract time.
- Routing numbers follow the ABA checksum. Prefix 99 is used so synthetic numbers cannot match a real bank.
- Business rules in the mapping document are approved by the business owner.

## 10. Risks (summary, full log in the RAID log)
Offsetting errors hide in totals. Pending payments wrongly settled (400 of 5,038 pending). Dropped fraud flags (10 payments, $25.8M). Truncated account numbers break downstream posting.

## 11. Glossary
ACH: Automated Clearing House. SIT: System Integration Testing. UAT: User Acceptance Testing. RTM: Requirements Traceability Matrix. ABA: American Bankers Association routing number.
