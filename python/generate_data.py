"""
Generate synthetic legacy and target payment datasets from the public PaySim dataset.

Synthetic data, adapted from PaySim (Lopez-Rojas et al.). Not real bank data.

Usage:
    python3 python/generate_data.py [--seed 42] [--n 100000]

Outputs (data/sample/):
    legacy_payments.csv       legacy schema (COBOL-style field names)
    target_payments.csv       target schema after a simulated, defective migration (trial load 1)
    target_payments_rehearsal2.csv  target schema after the corrected conversion logic (rehearsal 2)
    seed_log.json             exact count of each seeded defect (ground truth totals)
    seed_ground_truth.csv     payment_id -> defect type (used only to validate detection)
    paysim_lineage.csv        payment_id -> original PaySim row and type
"""
import argparse
import json
import os
import numpy as np
import pandas as pd
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "paysim.csv")
OUT = os.path.join(ROOT, "data", "sample")

# Seeded defect counts (fixed, so the run is reproducible and auditable)
DEFECTS = {
    "MISSING_IN_TARGET": 400,
    "DUPLICATE_ID": 300,
    "AMOUNT_ROUNDING": 800,
    "TRUNCATED_ACCOUNT": 500,
    "DATE_FORMAT_DRIFT": 600,
    "DATE_OFF_BY_ONE": 300,
    "MISSING_ROUTING": 500,
    "STATUS_MAPPING_ERROR": 400,
    "FRAUD_FLAG_DROPPED": 10,
    "ORPHAN_IN_TARGET": 200,
}

BASE_DATE = date(2026, 7, 1)  # PaySim step 1 -> 2026-07-01 (step is hours)

# PaySim type -> (legacy payment type, direction)
TYPE_MAP = {
    "TRANSFER": ("W", "C"),   # wire, credit
    "PAYMENT": ("A", "D"),    # ACH debit
    "DEBIT": ("A", "D"),      # ACH debit
    "CASH_IN": ("A", "C"),    # ACH credit
    "CASH_OUT": ("A", "D"),   # ACH debit
}


def aba_with_check(prefix8: str) -> str:
    """Append the ABA checksum digit. Prefix 99 is not a real Fed district, so numbers are clearly synthetic."""
    d = [int(c) for c in prefix8]
    # weights 3,7,1 repeating over 9 digits; the 9th digit (weight 1) makes the sum a multiple of 10
    s = 3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + (d[2] + d[5])
    check = (10 - (s % 10)) % 10
    return prefix8 + str(check)


def build_bank_pool(rng, n=25):
    pool = []
    for i in range(n):
        p = "99" + "".join(str(x) for x in rng.integers(0, 10, size=6))
        pool.append(aba_with_check(p))
    return pool


def sample_paysim(n, seed):
    df = pd.read_csv(
        RAW,
        usecols=["step", "type", "amount", "nameOrig", "nameDest", "isFraud"],
        dtype={"type": "category"},
    )
    df["paysim_row"] = df.index
    shares = df["type"].value_counts(normalize=True)
    alloc = (shares * n).round().astype(int)
    alloc.iloc[0] += n - alloc.sum()  # force exactly n
    parts = [
        df[df["type"] == t].sample(n=int(k), random_state=seed) for t, k in alloc.items()
    ]
    s = pd.concat(parts).sort_values(["step", "paysim_row"]).reset_index(drop=True)
    return s


def build_legacy(s, rng, pool):
    n = len(s)
    ptype = s["type"].astype(str).map(lambda t: TYPE_MAP[t][0])
    pdir = s["type"].astype(str).map(lambda t: TYPE_MAP[t][1])
    orig_rtn = rng.choice(pool, size=n)
    bene_rtn = rng.choice(pool, size=n)
    day = BASE_DATE
    sttl = [(BASE_DATE + timedelta(days=int(st) // 24)) for st in s["step"]]
    seq = np.arange(1, n + 1)

    trace = []
    for i in range(n):
        if ptype.iat[i] == "A":
            trace.append(orig_rtn[i][:8] + f"{seq[i]:07d}")
        else:
            trace.append(sttl[i].strftime("%Y%m%d") + "SYN" + f"{seq[i]:08d}")

    status = rng.choice(["STL", "PND", "RTN"], size=n, p=[0.92, 0.05, 0.03])

    legacy = pd.DataFrame(
        {
            "PMT_ID": [f"PMT{i:07d}" for i in seq],
            "PMT_TYP": ptype.values,
            "PMT_DIR": pdir.values,
            "PMT_AMT": s["amount"].round(2).values,
            "ORIG_ACCT": s["nameOrig"].values,
            "ORIG_RTN": orig_rtn,
            "BENE_ACCT": s["nameDest"].values,
            "BENE_RTN": bene_rtn,
            "TRACE_NO": trace,
            "STTL_DT": [d.strftime("%Y%m%d") for d in sttl],
            "PMT_STS": status,
            "FRD_FLG": np.where(s["isFraud"].values == 1, "Y", "N"),
        }
    )
    lineage = pd.DataFrame(
        {
            "payment_id": legacy["PMT_ID"],
            "paysim_row": s["paysim_row"].values,
            "paysim_type": s["type"].astype(str).values,
        }
    )
    return legacy, lineage


def transform_clean(legacy):
    """The correct conversion logic (the mapping document describes exactly this)."""
    t = pd.DataFrame(
        {
            "payment_id": legacy["PMT_ID"],
            "payment_method": legacy["PMT_TYP"].map({"W": "WIRE", "A": "ACH"}),
            "payment_direction": legacy["PMT_DIR"].map({"C": "CREDIT", "D": "DEBIT"}),
            "amount_usd": legacy["PMT_AMT"],
            "originator_account": legacy["ORIG_ACCT"],
            "originator_routing": legacy["ORIG_RTN"],
            "beneficiary_account": legacy["BENE_ACCT"],
            "beneficiary_routing": legacy["BENE_RTN"],
            "trace_id": legacy["TRACE_NO"],
            "settlement_date": pd.to_datetime(legacy["STTL_DT"], format="%Y%m%d").dt.strftime("%Y-%m-%d"),
            "payment_status": legacy["PMT_STS"].map(
                {"STL": "SETTLED", "PND": "PENDING", "RTN": "RETURNED"}
            ),
            "fraud_indicator": (legacy["FRD_FLG"] == "Y").astype(int),
        }
    )
    return t


def inject_defects(legacy, target, rng):
    n = len(target)
    gt = []  # (payment_id, defect_type)
    used = set()

    def pick(k, eligible=None):
        idx = np.array(sorted(set(range(n)) - used)) if eligible is None else np.array(
            sorted(set(eligible) - used)
        )
        chosen = rng.choice(idx, size=k, replace=False)
        used.update(int(i) for i in chosen)
        return sorted(int(i) for i in chosen)

    t = target.copy()

    # Eligibility so each seeded defect really changes the data
    pending = list(np.where(t["payment_status"] == "PENDING")[0])
    fraud = list(np.where(t["fraud_indicator"] == 1)[0])
    has_cents = list(np.where((t["amount_usd"] * 100).round() % 100 != 0)[0])
    long_acct = list(np.where(t["originator_account"].str.len() > 8)[0])  # truncation must change the value

    idx_fraud = pick(DEFECTS["FRAUD_FLAG_DROPPED"], fraud)
    idx_status = pick(DEFECTS["STATUS_MAPPING_ERROR"], pending)
    idx_amt = pick(DEFECTS["AMOUNT_ROUNDING"], has_cents)
    idx_acct = pick(DEFECTS["TRUNCATED_ACCOUNT"], long_acct)
    idx_dfmt = pick(DEFECTS["DATE_FORMAT_DRIFT"])
    idx_doff = pick(DEFECTS["DATE_OFF_BY_ONE"])
    idx_rtn = pick(DEFECTS["MISSING_ROUTING"])
    idx_dup = pick(DEFECTS["DUPLICATE_ID"])
    idx_miss = pick(DEFECTS["MISSING_IN_TARGET"])

    t.loc[idx_fraud, "fraud_indicator"] = 0
    t.loc[idx_status, "payment_status"] = "SETTLED"
    t.loc[idx_amt, "amount_usd"] = t.loc[idx_amt, "amount_usd"].round(0)
    t.loc[idx_acct, "originator_account"] = t.loc[idx_acct, "originator_account"].str[:8]
    d = pd.to_datetime(t.loc[idx_dfmt, "settlement_date"])
    t.loc[idx_dfmt, "settlement_date"] = d.dt.strftime("%m/%d/%Y")
    d2 = pd.to_datetime(t.loc[idx_doff, "settlement_date"]) + pd.Timedelta(days=1)
    t.loc[idx_doff, "settlement_date"] = d2.dt.strftime("%Y-%m-%d")
    t.loc[idx_rtn, "beneficiary_routing"] = ""

    for name, idx in [
        ("FRAUD_FLAG_DROPPED", idx_fraud),
        ("STATUS_MAPPING_ERROR", idx_status),
        ("AMOUNT_ROUNDING", idx_amt),
        ("TRUNCATED_ACCOUNT", idx_acct),
        ("DATE_FORMAT_DRIFT", idx_dfmt),
        ("DATE_OFF_BY_ONE", idx_doff),
        ("MISSING_ROUTING", idx_rtn),
        ("DUPLICATE_ID", idx_dup),
        ("MISSING_IN_TARGET", idx_miss),
    ]:
        for i in idx:
            gt.append((target["payment_id"].iat[i], name))

    # Duplicates: append an exact second copy
    dups = t.iloc[idx_dup].copy()
    # Dropped records: remove from target
    t = t.drop(index=t.index[idx_miss])
    t = pd.concat([t, dups], ignore_index=True)

    # Orphans: records in target that never existed in legacy
    k = DEFECTS["ORPHAN_IN_TARGET"]
    donors = t.sample(n=k, random_state=int(rng.integers(0, 10**6))).copy()
    donors["payment_id"] = [f"PMT9{i:06d}" for i in range(1, k + 1)]
    donors["trace_id"] = [f"ORPHAN{i:09d}" for i in range(1, k + 1)]
    t = pd.concat([t, donors], ignore_index=True)
    for pid in donors["payment_id"]:
        gt.append((pid, "ORPHAN_IN_TARGET"))

    t = t.sample(frac=1, random_state=int(rng.integers(0, 10**6))).reset_index(drop=True)
    gt_df = pd.DataFrame(gt, columns=["payment_id", "defect_type"]).sort_values(
        ["defect_type", "payment_id"]
    )
    return t, gt_df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n", type=int, default=100_000)
    a = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(a.seed)

    s = sample_paysim(a.n, a.seed)
    pool = build_bank_pool(rng)
    legacy, lineage = build_legacy(s, rng, pool)
    clean = transform_clean(legacy)
    target, gt = inject_defects(legacy, clean, rng)

    legacy.to_csv(os.path.join(OUT, "legacy_payments.csv"), index=False)
    target.to_csv(os.path.join(OUT, "target_payments.csv"), index=False)
    # Rehearsal 2 simulates the corrected conversion logic (no seeded defects)
    clean.to_csv(os.path.join(OUT, "target_payments_rehearsal2.csv"), index=False)
    gt.to_csv(os.path.join(OUT, "seed_ground_truth.csv"), index=False)
    lineage.to_csv(os.path.join(OUT, "paysim_lineage.csv"), index=False)

    log = {
        "seed": a.seed,
        "sample_size": int(len(legacy)),
        "legacy_rows": int(len(legacy)),
        "target_rows": int(len(target)),
        "seeded_defects": {k: int(v) for k, v in gt["defect_type"].value_counts().sort_index().items()},
        "total_seeded_defects": int(len(gt)),
        "paysim_type_mix": lineage["paysim_type"].value_counts().to_dict(),
        "method_mix": legacy["PMT_TYP"].map({"W": "WIRE", "A": "ACH"}).value_counts().to_dict(),
        "date_range": [legacy["STTL_DT"].min(), legacy["STTL_DT"].max()],
        "note": "Synthetic data adapted from public PaySim. Routing numbers use prefix 99 (not a real Fed district).",
    }
    with open(os.path.join(OUT, "seed_log.json"), "w") as f:
        json.dump(log, f, indent=2)
    print(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
