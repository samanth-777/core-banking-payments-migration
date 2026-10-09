# Payments Data Migration: Legacy to Modern Core Banking

Synthetic-data portfolio project. A fictional bank moves 100,000 ACH and wire payments from a legacy payments module to a modern core platform. The work covers requirements, source-to-target mapping, SQL reconciliation, API documentation, SIT/UAT/regression testing, traceability and go-live readiness.

**Data:** adapted from the public PaySim dataset (Kaggle, `ealaxi/paysim1`). Bank, platform, roles and routing numbers are fictional (routing prefix 99 is not a real Fed district). This is not real bank work.

## Result in one table
| Measure | Trial load 1 | Rehearsal 2 |
|---|---|---|
| Target rows | 100,100 | 100,000 |
| Reconciliation exceptions (17 rules) | 4,010 (4.01%) | 0 |
| Net amount variance | -$4,452,155.93 | $0.00 |
| Gross error behind the net variance | about $203.2M | $0 |
| Failed test cases (of 30) | 11 | 0 |
| Open defects | 10 | 0 |

Key finding: the net variance was 0.02% of total value and would pass a net-only tolerance check. Missing, duplicated and orphaned payments offset each other. Payment-level reconciliation exposed the gross error.

Status: all technical tests pass. 3 UAT cases are written but not run (need business users), so the recommendation is **conditional go**.

## Deliverables
| Folder | Contents |
|---|---|
| `docs/` | BRD, user stories, fit-gap, source-to-target mapping (md + csv) |
| `sql/` | Staging views, 17 reconciliation rules, control totals |
| `python/` | Data generation, reconciliation runner, mapping, API and QA builders |
| `api/` | OpenAPI 3 spec, 7 sample payloads, XML batch sample, API test results |
| `tests/` | `QA_Workbook.xlsx`: 30 test cases, RTM, defect log, change log, RAID log, results |
| `data/sample/` | Legacy and target extracts, seed log, ground truth, lineage |
| `data/results/` | Exceptions, summaries, control totals, detection validation for each load |

## Reproduce
```bash
# 1. Put paysim.csv in data/raw/ (Kaggle: ealaxi/paysim1). It is gitignored.
python3 python/generate_data.py                 # seed 42, 100K sample
python3 python/run_reconciliation.py --target target_payments.csv --tag trial1
python3 python/run_reconciliation.py --target target_payments_rehearsal2.csv --tag rehearsal2
python3 python/build_mapping.py
python3 python/build_api_artifacts.py
python3 python/build_test_artifacts.py
```

## How the checks stay honest
- Ten defect types are seeded into the trial load with exact counts (`data/sample/seed_log.json`).
- The SQL rules never read the ground truth. A separate step compares detections to it: 100% detected, 0 false positives (`data/results/trial1/detection_validation.csv`).
- Seven control rules (R11 to R17) on fields that should not change returned 0 exceptions, so the rules do not over-report.
- The API tests run against a reference validator in `python/build_api_artifacts.py`, not a deployed API.
- Defect root causes are simulated hypotheses, because the defects were seeded.

## Not in this repo
Current-state and future-state process flows (Lucidchart) and the Power BI reconciliation dashboard.
