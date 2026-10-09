"""
Build API sample payloads, a simplified XML batch file, and run a reference validator.
The validator is NOT a deployed API. It implements the validation rules in api/openapi.yaml
so the 6 error scenarios and the valid case can be tested for real.
"""
import copy, csv, json, os
import pandas as pd
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = os.path.join(ROOT, "api")
os.makedirs(os.path.join(API, "payloads"), exist_ok=True)

def aba_ok(r: str) -> bool:
    if not (isinstance(r, str) and len(r) == 9 and r.isdigit()):
        return False
    d = [int(c) for c in r]
    return (3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + (d[2] + d[5] + d[8])) % 10 == 0

REQUIRED = ["payment_method", "payment_direction", "amount", "currency", "originator", "beneficiary", "settlement_date"]
SEEN_KEYS = set()

def validate(payload, idem_key):
    """Returns (http_status, error_code or None). Order mirrors the spec."""
    for f in REQUIRED:
        if f not in payload or payload[f] in (None, ""):
            return 400, "ERR_MISSING_FIELD"
    for party in ("originator", "beneficiary"):
        p = payload[party]
        if not isinstance(p, dict) or "account" not in p or "routing" not in p:
            return 400, "ERR_MISSING_FIELD"
    if payload["payment_method"] not in ("ACH", "WIRE"):
        return 400, "ERR_METHOD_UNSUPPORTED"
    d = str(payload["settlement_date"])
    ok_date = len(d) == 10 and d[4] == "-" and d[7] == "-" and d.replace("-", "").isdigit()
    if not ok_date:
        return 400, "ERR_DATE_FORMAT"
    amt = payload["amount"]
    if not isinstance(amt, (int, float)) or amt <= 0 or round(amt * 100) != amt * 100 and abs(round(amt, 2) - amt) > 1e-9:
        return 422, "ERR_AMOUNT_INVALID"
    for party in ("originator", "beneficiary"):
        if not aba_ok(payload[party]["routing"]):
            return 422, "ERR_ROUTING_INVALID"
    if idem_key in SEEN_KEYS:
        return 409, "ERR_DUPLICATE_PAYMENT"
    SEEN_KEYS.add(idem_key)
    return 201, None

def main():
    leg = pd.read_csv(os.path.join(ROOT, "data/sample/legacy_payments.csv"), dtype=str)
    ach = leg[leg.PMT_TYP == "A"].head(3)
    first = ach.iloc[0]
    valid = {
        "payment_method": "ACH", "payment_direction": "CREDIT", "amount": 1250.75, "currency": "USD",
        "originator": {"account": first.ORIG_ACCT, "routing": first.ORIG_RTN},
        "beneficiary": {"account": first.BENE_ACCT, "routing": first.BENE_RTN},
        "settlement_date": "2026-10-15",
    }
    cases = []
    cases.append(("TC-18", "valid_payment", valid, "key-0001", 201, None))
    c = copy.deepcopy(valid); c["beneficiary"]["routing"] = c["beneficiary"]["routing"][:-1] + str((int(c["beneficiary"]["routing"][-1]) + 1) % 10)
    cases.append(("TC-19", "invalid_routing_checksum", c, "key-0002", 422, "ERR_ROUTING_INVALID"))
    c = copy.deepcopy(valid); del c["amount"]
    cases.append(("TC-20", "missing_amount", c, "key-0003", 400, "ERR_MISSING_FIELD"))
    c = copy.deepcopy(valid); c["amount"] = -50.00
    cases.append(("TC-21", "negative_amount", c, "key-0004", 422, "ERR_AMOUNT_INVALID"))
    cases.append(("TC-22", "duplicate_idempotency_key", copy.deepcopy(valid), "key-0001", 409, "ERR_DUPLICATE_PAYMENT"))
    c = copy.deepcopy(valid); c["settlement_date"] = "10/15/2026"
    cases.append(("TC-23", "date_wrong_format", c, "key-0005", 400, "ERR_DATE_FORMAT"))
    c = copy.deepcopy(valid); c["payment_method"] = "CHECK"
    cases.append(("TC-24", "unsupported_method", c, "key-0006", 400, "ERR_METHOD_UNSUPPORTED"))

    rows = []
    for tc, name, payload, key, exp_status, exp_code in cases:
        with open(os.path.join(API, "payloads", f"{tc}_{name}.json"), "w") as f:
            json.dump(payload, f, indent=2)
        status, code = validate(payload, key)
        rows.append(dict(test_case=tc, scenario=name, idempotency_key=key, expected_http=exp_status,
                         expected_code=exp_code or "", actual_http=status, actual_code=code or "",
                         result="Pass" if (status, code) == (exp_status, exp_code) else "Fail"))
    res = pd.DataFrame(rows)
    res.to_csv(os.path.join(API, "api_test_results.csv"), index=False)
    print(res.to_string(index=False))

    # Simplified XML batch file built from three real legacy ACH records
    root = ET.Element("PaymentBatch", attrib={"batchId": "BATCH-SAMPLE-001", "currency": "USD", "note": "synthetic sample"})
    for _, r in ach.iterrows():
        p = ET.SubElement(root, "Payment", attrib={"id": r.PMT_ID, "method": "ACH"})
        ET.SubElement(p, "Amount").text = f"{float(r.PMT_AMT):.2f}"
        o = ET.SubElement(p, "Originator"); ET.SubElement(o, "Account").text = r.ORIG_ACCT; ET.SubElement(o, "Routing").text = r.ORIG_RTN
        b = ET.SubElement(p, "Beneficiary"); ET.SubElement(b, "Account").text = r.BENE_ACCT; ET.SubElement(b, "Routing").text = r.BENE_RTN
        ET.SubElement(p, "SettlementDate").text = f"{r.STTL_DT[:4]}-{r.STTL_DT[4:6]}-{r.STTL_DT[6:]}"
        ET.SubElement(p, "TraceId").text = r.TRACE_NO
    ET.indent(root)
    ET.ElementTree(root).write(os.path.join(API, "sample_payment_batch.xml"), encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    main()
