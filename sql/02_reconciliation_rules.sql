-- Reconciliation rules. Each rule inserts one row per exception.
-- Columns: rule_id, rule_name, severity, payment_id, legacy_value, target_value

DROP TABLE IF EXISTS exceptions;
CREATE TABLE exceptions (
    rule_id TEXT, rule_name TEXT, severity TEXT,
    payment_id TEXT, legacy_value TEXT, target_value TEXT
);

-- R01 Record completeness: in legacy, not in target
INSERT INTO exceptions
SELECT 'R01','MISSING_IN_TARGET','Critical', l.PMT_ID, 'present', 'absent'
FROM legacy_payments l
LEFT JOIN target_dedup t ON t.payment_id = l.PMT_ID
WHERE t.payment_id IS NULL;

-- R02 Record completeness: in target, not in legacy
INSERT INTO exceptions
SELECT 'R02','ORPHAN_IN_TARGET','High', t.payment_id, 'absent', 'present'
FROM target_dedup t
LEFT JOIN legacy_payments l ON l.PMT_ID = t.payment_id
WHERE l.PMT_ID IS NULL;

-- R03 Uniqueness: payment_id appears more than once in target
INSERT INTO exceptions
SELECT 'R03','DUPLICATE_ID','High', payment_id, '1', CAST(COUNT(*) AS TEXT)
FROM target_payments
GROUP BY payment_id
HAVING COUNT(*) > 1;

-- R04 Amount: differs by more than half a cent
INSERT INTO exceptions
SELECT 'R04','AMOUNT_MISMATCH','High', PMT_ID, printf('%.2f',PMT_AMT), printf('%.2f',amount_usd)
FROM matched
WHERE ABS(PMT_AMT - amount_usd) > 0.005;

-- R05 Originator account differs (truncation, padding, corruption)
INSERT INTO exceptions
SELECT 'R05','ORIG_ACCOUNT_MISMATCH','Medium', PMT_ID, ORIG_ACCT, COALESCE(originator_account,'')
FROM matched
WHERE COALESCE(originator_account,'') <> ORIG_ACCT;

-- R06 Date format: settlement_date is not ISO YYYY-MM-DD
INSERT INTO exceptions
SELECT 'R06','DATE_NOT_ISO','Medium', PMT_ID, legacy_date_iso, COALESCE(settlement_date,'')
FROM matched
WHERE settlement_date IS NULL
   OR settlement_date NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]';

-- R07 Date value: valid ISO date but different from legacy
INSERT INTO exceptions
SELECT 'R07','DATE_VALUE_MISMATCH','High', PMT_ID, legacy_date_iso, settlement_date
FROM matched
WHERE settlement_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
  AND settlement_date <> legacy_date_iso;

-- R08 Routing completeness: blank, null, or not 9 digits (either side)
INSERT INTO exceptions
SELECT 'R08','ROUTING_MISSING_OR_INVALID','High', PMT_ID, BENE_RTN, COALESCE(beneficiary_routing,'')
FROM matched
WHERE beneficiary_routing IS NULL OR length(beneficiary_routing) <> 9
   OR originator_routing IS NULL OR length(originator_routing) <> 9;

-- R09 Status mapping: STL/PND/RTN -> SETTLED/PENDING/RETURNED
INSERT INTO exceptions
SELECT 'R09','STATUS_MISMATCH','High', PMT_ID, exp_status, COALESCE(payment_status,'')
FROM matched
WHERE COALESCE(payment_status,'') <> exp_status;

-- R10 Financial crime flag must survive conversion
INSERT INTO exceptions
SELECT 'R10','FRAUD_FLAG_MISMATCH','Critical', PMT_ID, CAST(exp_fraud AS TEXT), CAST(fraud_indicator AS TEXT)
FROM matched
WHERE fraud_indicator <> exp_fraud;

-- R11 to R17: control rules. Expected to return zero rows on this data set.
INSERT INTO exceptions
SELECT 'R11','PAYMENT_METHOD_MISMATCH','High', PMT_ID, exp_method, COALESCE(payment_method,'')
FROM matched WHERE COALESCE(payment_method,'') <> exp_method;

INSERT INTO exceptions
SELECT 'R12','DIRECTION_MISMATCH','High', PMT_ID, exp_direction, COALESCE(payment_direction,'')
FROM matched WHERE COALESCE(payment_direction,'') <> exp_direction;

INSERT INTO exceptions
SELECT 'R13','ORIG_ROUTING_VALUE_MISMATCH','High', PMT_ID, ORIG_RTN, COALESCE(originator_routing,'')
FROM matched WHERE length(originator_routing) = 9 AND originator_routing <> ORIG_RTN;

INSERT INTO exceptions
SELECT 'R14','BENE_ROUTING_VALUE_MISMATCH','High', PMT_ID, BENE_RTN, COALESCE(beneficiary_routing,'')
FROM matched WHERE length(beneficiary_routing) = 9 AND beneficiary_routing <> BENE_RTN;

INSERT INTO exceptions
SELECT 'R15','BENE_ACCOUNT_MISMATCH','Medium', PMT_ID, BENE_ACCT, COALESCE(beneficiary_account,'')
FROM matched WHERE COALESCE(beneficiary_account,'') <> BENE_ACCT;

INSERT INTO exceptions
SELECT 'R16','TRACE_ID_MISMATCH','High', PMT_ID, TRACE_NO, COALESCE(trace_id,'')
FROM matched WHERE COALESCE(trace_id,'') <> TRACE_NO;

-- R17 Routing checksum: 9-digit routing numbers must pass the ABA checksum (weights 3,7,1)
INSERT INTO exceptions
SELECT 'R17','ROUTING_CHECKSUM_INVALID','High', PMT_ID, BENE_RTN, COALESCE(beneficiary_routing,'')
FROM matched
WHERE length(beneficiary_routing) = 9 AND length(originator_routing) = 9
  AND (
    ( 3*(CAST(substr(beneficiary_routing,1,1) AS INT)+CAST(substr(beneficiary_routing,4,1) AS INT)+CAST(substr(beneficiary_routing,7,1) AS INT))
    + 7*(CAST(substr(beneficiary_routing,2,1) AS INT)+CAST(substr(beneficiary_routing,5,1) AS INT)+CAST(substr(beneficiary_routing,8,1) AS INT))
    + (CAST(substr(beneficiary_routing,3,1) AS INT)+CAST(substr(beneficiary_routing,6,1) AS INT)+CAST(substr(beneficiary_routing,9,1) AS INT)) ) % 10 <> 0
  OR
    ( 3*(CAST(substr(originator_routing,1,1) AS INT)+CAST(substr(originator_routing,4,1) AS INT)+CAST(substr(originator_routing,7,1) AS INT))
    + 7*(CAST(substr(originator_routing,2,1) AS INT)+CAST(substr(originator_routing,5,1) AS INT)+CAST(substr(originator_routing,8,1) AS INT))
    + (CAST(substr(originator_routing,3,1) AS INT)+CAST(substr(originator_routing,6,1) AS INT)+CAST(substr(originator_routing,9,1) AS INT)) ) % 10 <> 0
  );
