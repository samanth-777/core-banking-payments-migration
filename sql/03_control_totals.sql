-- Control totals: count and value reconciliation, legacy vs target.
DROP TABLE IF EXISTS control_totals;
CREATE TABLE control_totals AS
SELECT 'Legacy record count' AS metric, CAST(COUNT(*) AS TEXT) AS value FROM legacy_payments
UNION ALL SELECT 'Target row count (incl. duplicates)', CAST(COUNT(*) AS TEXT) FROM target_payments
UNION ALL SELECT 'Target distinct payment_id', CAST(COUNT(DISTINCT payment_id) AS TEXT) FROM target_payments
UNION ALL SELECT 'Matched records', CAST(COUNT(*) AS TEXT) FROM matched
UNION ALL SELECT 'Legacy total amount (USD)', printf('%.2f', SUM(PMT_AMT)) FROM legacy_payments
UNION ALL SELECT 'Target total amount incl. duplicates and orphans (USD)', printf('%.2f', SUM(amount_usd)) FROM target_payments
UNION ALL SELECT 'Variance, target minus legacy (USD)',
    printf('%.2f', (SELECT SUM(amount_usd) FROM target_payments) - (SELECT SUM(PMT_AMT) FROM legacy_payments));
