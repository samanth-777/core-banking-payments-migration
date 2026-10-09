"""Build the source-to-target mapping CSV, with field profile numbers measured from the legacy extract."""
import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
leg = pd.read_csv(os.path.join(ROOT, "data/sample/legacy_payments.csv"), dtype=str, keep_default_na=False)

def prof(col):
    s = leg[col]
    return f"len {s.str.len().min()}-{s.str.len().max()}, distinct {s.nunique()}, blank {(s=='').sum()}"

rows = [
 ("M01","PMT_ID","payment_id","Direct move","Preserve as is. Primary key, must be unique.","REQ-001,REQ-002,REQ-003","R01,R02,R03"),
 ("M02","PMT_TYP","payment_method","Lookup","W -> WIRE, A -> ACH. Any other value rejected to exception queue.","REQ-010","R11"),
 ("M03","PMT_DIR","payment_direction","Lookup","C -> CREDIT, D -> DEBIT. Any other value rejected.","REQ-010","R12"),
 ("M04","PMT_AMT","amount_usd","Direct move","Decimal(18,2). No rounding, no integer cast. Sum of amounts must equal legacy control total.","REQ-004","R04"),
 ("M05","ORIG_ACCT","originator_account","Direct move","Move full value. Target field length must be at least the legacy max length. No truncation.","REQ-005","R05"),
 ("M06","ORIG_RTN","originator_routing","Direct move + validate","9 digits, ABA checksum valid. Reject blanks.","REQ-007","R08,R13,R17"),
 ("M07","BENE_ACCT","beneficiary_account","Direct move","Move full value. No truncation.","REQ-005","R15"),
 ("M08","BENE_RTN","beneficiary_routing","Direct move + validate","9 digits, ABA checksum valid. Reject blanks.","REQ-007","R08,R14,R17"),
 ("M09","TRACE_NO","trace_id","Direct move","Preserve. ACH: 8-digit routing prefix + 7-digit sequence. Wire: date + reference.","REQ-011","R16"),
 ("M10","STTL_DT","settlement_date","Format conversion","YYYYMMDD -> YYYY-MM-DD (ISO 8601). Value must not change.","REQ-006","R06,R07"),
 ("M11","PMT_STS","payment_status","Lookup","STL -> SETTLED, PND -> PENDING, RTN -> RETURNED. No defaulting of unmapped codes.","REQ-008","R09"),
 ("M12","FRD_FLG","fraud_indicator","Lookup","Y -> 1, N -> 0. Flag must survive conversion for financial crime review.","REQ-009","R10"),
]
out = pd.DataFrame(rows, columns=["map_id","legacy_field","target_field","transformation_type","business_rule","requirement_ids","recon_rules"])
out["legacy_profile"] = out["legacy_field"].map(prof)
out.to_csv(os.path.join(ROOT, "docs/04_source_to_target_mapping.csv"), index=False)
print(out[["map_id","legacy_field","target_field","legacy_profile"]].to_string(index=False))
print("PMT_STS values:", leg.PMT_STS.value_counts().to_dict())
print("ORIG_ACCT prefixes:", leg.ORIG_ACCT.str[0].value_counts().to_dict(), "| BENE prefixes:", leg.BENE_ACCT.str[0].value_counts().to_dict())
