-- Staging views for reconciliation (SQLite).
-- legacy_payments: legacy extract (COBOL-style field names)
-- target_payments: post-migration extract (may contain duplicates)

DROP VIEW IF EXISTS target_dedup;
CREATE VIEW target_dedup AS
SELECT DISTINCT * FROM target_payments;           -- exact duplicate rows collapse to one

DROP VIEW IF EXISTS matched;
CREATE VIEW matched AS
SELECT
    l.PMT_ID,
    l.PMT_TYP, l.PMT_DIR, l.PMT_AMT, l.ORIG_ACCT, l.ORIG_RTN, l.BENE_ACCT, l.BENE_RTN,
    l.TRACE_NO, l.STTL_DT, l.PMT_STS, l.FRD_FLG,
    substr(l.STTL_DT,1,4) || '-' || substr(l.STTL_DT,5,2) || '-' || substr(l.STTL_DT,7,2) AS legacy_date_iso,
    CASE l.PMT_TYP WHEN 'W' THEN 'WIRE' WHEN 'A' THEN 'ACH' END                    AS exp_method,
    CASE l.PMT_DIR WHEN 'C' THEN 'CREDIT' WHEN 'D' THEN 'DEBIT' END                AS exp_direction,
    CASE l.PMT_STS WHEN 'STL' THEN 'SETTLED' WHEN 'PND' THEN 'PENDING'
                   WHEN 'RTN' THEN 'RETURNED' END                                  AS exp_status,
    CASE l.FRD_FLG WHEN 'Y' THEN 1 ELSE 0 END                                      AS exp_fraud,
    t.payment_method, t.payment_direction, t.amount_usd, t.originator_account,
    t.originator_routing, t.beneficiary_account, t.beneficiary_routing, t.trace_id,
    t.settlement_date, t.payment_status, t.fraud_indicator
FROM legacy_payments l
JOIN target_dedup t ON t.payment_id = l.PMT_ID;
