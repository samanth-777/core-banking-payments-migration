# User Stories and Acceptance Criteria

Synthetic-data portfolio project. Each story links to a requirement in the BRD.

| # | Story | Req |
|---|---|---|
| US-01 | As a Payments Operations manager, I want every legacy payment present in the target so that no customer payment is lost. | REQ-001 |
| US-02 | As a Payments Operations manager, I want each payment to appear once so that customers are not paid or charged twice. | REQ-002 |
| US-03 | As a Finance Controller, I want no target payment without a legacy source so that balances are not overstated. | REQ-003 |
| US-04 | As a Finance Controller, I want amounts to match to the cent so that control totals tie out. | REQ-004 |
| US-05 | As a Payments Operations analyst, I want full-length account numbers so that payments post to the right account. | REQ-005 |
| US-06 | As a Settlement analyst, I want settlement dates converted without changing the date so that cut-off reporting stays correct. | REQ-006 |
| US-07 | As a Payments Operations analyst, I want valid 9-digit routing numbers so that payments can be routed. | REQ-007 |
| US-08 | As a Payments Operations manager, I want status codes mapped exactly so that pending items are not reported as settled. | REQ-008 |
| US-09 | As a Compliance officer, I want the fraud flag preserved so that flagged payments stay under review. | REQ-009 |
| US-10 | As a Data Migration Lead, I want a ranked exception report so that I fix Critical items first. | REQ-012 |
| US-11 | As an integration developer, I want a documented payment API with error responses so that channels can submit payments. | REQ-013 |
| US-12 | As a Program Manager, I want objective go-live criteria so that the cutover decision is evidence based. | REQ-014 |

## Acceptance criteria (Given / When / Then)

**US-01** Given 100,000 legacy payments, when the load completes, then rule R01 returns 0 exceptions and target distinct payment_id count equals 100,000.
**US-02** Given the target table, when rule R03 runs, then no payment_id has a count above 1.
**US-03** Given the target table, when rule R02 runs, then 0 payment_ids exist that are absent from legacy.
**US-04** Given matched records, when rule R04 runs, then the absolute difference per payment is under $0.005 and total target amount equals legacy total amount.
**US-05** Given any legacy account number, when it is loaded, then the target value equals it exactly and rule R05 returns 0 exceptions.
**US-06** Given a legacy date 20260715, when converted, then the target holds 2026-07-15. Rules R06 and R07 return 0 exceptions.
**US-07** Given any payment, when loaded, then both routing numbers are 9 digits with a valid ABA checksum. Rules R08 and R17 return 0 exceptions.
**US-08** Given status PND, when converted, then the target status is PENDING. Rule R09 returns 0 exceptions.
**US-09** Given FRD_FLG = Y, when converted, then fraud_indicator = 1. Rule R10 returns 0 exceptions.
**US-10** Given a reconciliation run, when it finishes, then exceptions.csv lists rule, severity, payment_id, legacy value and target value, and the summary groups counts by severity.
**US-11** Given a valid JSON payload, when POSTed, then the API returns 201 with a payment_id. Given an invalid payload, then it returns the documented 4xx error with a machine-readable code.
**US-12** Given the final rehearsal, when all 14 requirements show Pass in the RTM and no Critical or High defects are open, then the readiness deck recommends Go.
