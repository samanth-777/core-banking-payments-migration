"""
Load legacy and target extracts into SQLite, run the SQL reconciliation rules,
export exceptions, and validate detection against the seeded ground truth.
Ground truth is used ONLY in the validation step, never by the SQL rules.
"""
import argparse, json, os, sqlite3
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "data", "sample")
SQL = os.path.join(ROOT, "sql")
DB = os.path.join(ROOT, "data", "payments.db")
OUT = os.path.join(ROOT, "data", "results")

RULE_TO_DEFECT = {
    "R01": "MISSING_IN_TARGET", "R02": "ORPHAN_IN_TARGET", "R03": "DUPLICATE_ID",
    "R04": "AMOUNT_ROUNDING", "R05": "TRUNCATED_ACCOUNT", "R06": "DATE_FORMAT_DRIFT",
    "R07": "DATE_OFF_BY_ONE", "R08": "MISSING_ROUTING", "R09": "STATUS_MAPPING_ERROR",
    "R10": "FRAUD_FLAG_DROPPED",
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="target_payments.csv")
    ap.add_argument("--tag", default="trial1")
    a = ap.parse_args()
    global OUT
    OUT = os.path.join(ROOT, "data", "results", a.tag)
    os.makedirs(OUT, exist_ok=True)
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    leg = pd.read_csv(os.path.join(S, "legacy_payments.csv"), dtype=str, keep_default_na=False)
    leg["PMT_AMT"] = leg["PMT_AMT"].astype(float)
    tgt = pd.read_csv(os.path.join(S, a.target), dtype=str, keep_default_na=False)
    tgt["amount_usd"] = tgt["amount_usd"].astype(float)
    tgt["fraud_indicator"] = tgt["fraud_indicator"].astype(int)
    leg.to_sql("legacy_payments", con, index=False)
    tgt.to_sql("target_payments", con, index=False)
    con.execute("CREATE INDEX ix_leg ON legacy_payments(PMT_ID)")
    con.execute("CREATE INDEX ix_tgt ON target_payments(payment_id)")

    for f in ["01_views.sql", "02_reconciliation_rules.sql", "03_control_totals.sql"]:
        con.executescript(open(os.path.join(SQL, f)).read())
    con.commit()

    exc = pd.read_sql("SELECT * FROM exceptions ORDER BY rule_id, payment_id", con)
    exc.to_csv(os.path.join(OUT, "exceptions.csv"), index=False)
    ct = pd.read_sql("SELECT * FROM control_totals", con)
    ct.to_csv(os.path.join(OUT, "control_totals.csv"), index=False)

    catalog = {
        "R01": ("MISSING_IN_TARGET", "Critical"), "R02": ("ORPHAN_IN_TARGET", "High"),
        "R03": ("DUPLICATE_ID", "High"), "R04": ("AMOUNT_MISMATCH", "High"),
        "R05": ("ORIG_ACCOUNT_MISMATCH", "Medium"), "R06": ("DATE_NOT_ISO", "Medium"),
        "R07": ("DATE_VALUE_MISMATCH", "High"), "R08": ("ROUTING_MISSING_OR_INVALID", "High"),
        "R09": ("STATUS_MISMATCH", "High"), "R10": ("FRAUD_FLAG_MISMATCH", "Critical"),
        "R11": ("PAYMENT_METHOD_MISMATCH", "High"), "R12": ("DIRECTION_MISMATCH", "High"),
        "R13": ("ORIG_ROUTING_VALUE_MISMATCH", "High"), "R14": ("BENE_ROUTING_VALUE_MISMATCH", "High"),
        "R15": ("BENE_ACCOUNT_MISMATCH", "Medium"), "R16": ("TRACE_ID_MISMATCH", "High"),
        "R17": ("ROUTING_CHECKSUM_INVALID", "High"),
    }
    counts = exc.groupby("rule_id").agg(exceptions=("payment_id", "size"), distinct_payments=("payment_id", "nunique"))
    summ = pd.DataFrame(
        [(r, nm, sv) for r, (nm, sv) in catalog.items()], columns=["rule_id", "rule_name", "severity"]
    ).merge(counts, left_on="rule_id", right_index=True, how="left").fillna({"exceptions": 0, "distinct_payments": 0})
    summ["exceptions"] = summ["exceptions"].astype(int)
    summ["distinct_payments"] = summ["distinct_payments"].astype(int)
    summ.to_csv(os.path.join(OUT, "reconciliation_summary.csv"), index=False)

    # Validation against ground truth (only meaningful for the seeded trial load)
    if a.tag != "trial1":
        print("CONTROL TOTALS"); print(ct.to_string(index=False))
        print("\nRULE SUMMARY"); print(summ.to_string(index=False))
        print("\nTotal exceptions:", len(exc)); con.close(); return
    gt = pd.read_csv(os.path.join(S, "seed_ground_truth.csv"))
    rows = []
    for rule, defect in RULE_TO_DEFECT.items():
        seeded = set(gt.loc[gt.defect_type == defect, "payment_id"])
        found = set(exc.loc[exc.rule_id == rule, "payment_id"])
        tp = len(seeded & found); fp = len(found - seeded); fn = len(seeded - found)
        rows.append(dict(rule_id=rule, defect_type=defect, seeded=len(seeded), detected=len(found),
                         true_positive=tp, false_positive=fp, false_negative=fn,
                         detection_rate=round(tp / len(seeded) * 100, 2) if seeded else None))
    val = pd.DataFrame(rows)
    val.to_csv(os.path.join(OUT, "detection_validation.csv"), index=False)

    print("CONTROL TOTALS"); print(ct.to_string(index=False))
    print("\nRULE SUMMARY"); print(summ.to_string(index=False))
    print("\nDETECTION VALIDATION"); print(val.to_string(index=False))
    print("\nTotal exceptions:", len(exc), "| unique payments with exceptions:", exc.payment_id.nunique())
    con.close()

if __name__ == "__main__":
    main()
