#!/usr/bin/env python3
"""Build the adjudication pack for the v0.1 A/B double-annotation round.

Outputs (in this directory):
  adjudication-material.jsonl  blind inputs for the 54 disputed cases, grouped
                                P0 -> P3, no expected/notes/polarity
  pass1-sheet-*.csv            per-adjudicator pass-1 sheets: NO A/B labels,
                                NO draft labels; independent judgment only
  adjudication-sheet.csv       pass-2 reconciliation: A/B raw labels + blank
                                consensus columns (fill after both pass-1 files)
  draft-reference.csv          draft `expected` labels; open only in pass 3

Run:  python3 adjudication/build-pack.py
"""
from __future__ import annotations

import csv
import glob
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
FIELDS = ["decision", "operation", "primary_reason",
          "subject_ok", "time_ok", "sensitivity_action"]

# --- load cases + both annotation CSVs -------------------------------------
cases: dict[str, dict] = {}
for path in sorted(glob.glob(str(ROOT / "cases" / "*.jsonl"))):
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            cases[item["case_id"]] = item


def load(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return {r["case_id"]: r for r in csv.DictReader(fh)}


A = load(ROOT / "annotations" / "A-v0.1.csv")
B = load(ROOT / "annotations" / "b-v0.1.csv")
assert set(A) == set(B) == set(cases), "case_id sets must match"

# --- dispute classification ------------------------------------------------
HARD = ["TEN-015", "TEN-016", "TIME-016"]           # hard-constraint gate
CLAR = ["COR-012", "CTRL-011", "TIME-020"]          # clarify vs reject
FIELD = {"subject_ok", "time_ok", "sensitivity_action"}
REASON = {"primary_reason", "operation"}

GROUP_LABEL = {
    "P0": "硬约束（decision 级，先裁）",
    "P1": "澄清 vs 拒绝（decision 级）",
    "P2": "字段口径 subject_ok/time_ok/sensitivity_action",
    "P3": "取码 primary_reason/operation",
}

CLUE = {
    "P0": "G1 逐字段清单 1–2 / G8 副作用落点",
    "P1": "§四『澄清还是拒绝』情形 3–4 + G5 不通过条",
    "P2": "§3.2 字段判据（正交性、读取类 subject_ok、unclear 条件）",
    "P3": "主理由选择规则 1–6（含 G7 内部顺序）",
}
CLUE_OVERRIDE = {
    "TEN-015": "G1 清单第 2 项（候选自带 owner_id → MODEL_SET_OWNER）",
    "TEN-016": "G1 清单第 1 项（source.session_owner_id → SESSION_OWNER_MISMATCH）",
    "TIME-016": "G8：claim 文本已内嵌提醒 → 不能部分放行",
    "COR-012": "情形 4（来源给了一次性，候选改写为周期）+ 取码规则 1/2",
    "CTRL-011": "情形 4（“最近”被放大为“长期”）",
    "TIME-020": "情形 4（同 CTRL-011 同型）",
}

# 裁决人：规则作者 + 非作者（rubric §二.6）。杨冰冰同时是标注者 A，
# 因此 pass 1 必须两人各自独立、不看 A/B 判定与草案标签。
ADJUDICATORS = [
    ("qiu-zhenhao", "邱振豪（规则作者，非 A/B 标注者）"),
    ("yang-bingbing", "杨冰冰（标注者 A，非规则作者）"),
]
PASS1_COLS = (["seq", "group", "group_label", "case_id", "category",
               "rubric_v0.1.1_clause"]
              + [f"adj_{f}" for f in FIELDS]
              + ["adjudicator", "basis", "pass1_done"])


def group_of(cid: str) -> str:
    if cid in HARD:
        return "P0"
    if cid in CLAR:
        return "P1"
    fields = set()
    for f in FIELDS:
        if A[cid][f] != B[cid][f]:
            fields.add(f)
        elif A[cid][f] != cases[cid]["expected"][f]:
            fields.add(f)
    if fields & FIELD:
        return "P2"
    if fields & REASON:
        return "P3"
    raise SystemExit(f"{cid}: no dispute classification")


disputed = [c for c in cases
            if any(A[c][f] != B[c][f] for f in FIELDS)
            or any(A[c][f] == B[c][f] and A[c][f] != cases[c]["expected"][f]
                   for f in FIELDS)]
groups: dict[str, list[str]] = {"P0": [], "P1": [], "P2": [], "P3": []}
for cid in disputed:
    groups[group_of(cid)].append(cid)
for key in groups:
    groups[key].sort(key=lambda c: hashlib.sha256(c.encode()).hexdigest())
print({k: len(v) for k, v in groups.items()}, "total", len(disputed))

# --- 1. blind material ------------------------------------------------------
FORBIDDEN = {"expected", "notes", "polarity", "label_status"}
with (OUT / "adjudication-material.jsonl").open("w", encoding="utf-8") as fh:
    for key in ("P0", "P1", "P2", "P3"):
        for cid in groups[key]:
            src = cases[cid]
            rec = {"group": key,
                   "case_id": cid,
                   "category": src["category"],
                   "event_type": src.get("event_type"),
                   "source": src.get("source"),
                   "candidate": src.get("candidate"),
                   "existing_memories": src.get("existing_memories", []),
                   "deletion_state": src.get("deletion_state"),
                   "requester": src.get("requester"),
                   "read_request": src.get("read_request")}
            leaked = FORBIDDEN & set(rec)
            if leaked:
                raise SystemExit(f"material would leak {sorted(leaked)}")
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
print("adjudication-material.jsonl:", len(disputed), "cases, blind")

# --- 2. adjudication sheet (no draft labels) --------------------------------
COLS = (["seq", "group", "group_label", "case_id", "category",
         "gate_A", "gate_B", "dispute_kind", "rubric_v0.1.1_clause"]
        + [f"A_{f}" for f in FIELDS] + ["A_note"]
        + [f"B_{f}" for f in FIELDS] + ["B_note"]
        + [f"adj_{f}" for f in FIELDS]
        + ["adjudicator", "basis", "change_expected", "change_case",
           "change_rubric", "pass2_done", "pass3_done"])


def gate(code: str) -> str:
    code = code or ""
    table = [
        ("G0", {"SOURCE_MISSING", "SOURCE_NOT_FINAL", "SOURCE_STALE_REVISION",
                "SCHEMA_INVALID", "REVIEW_FAILED"}),
        ("G1", {"SESSION_OWNER_MISMATCH", "MODEL_SET_OWNER", "OWNER_MISMATCH",
                "OWNER_MATCH", "CROSS_TENANT_WRITE", "CROSS_TENANT_READ",
                "TARGET_OWNER_MISMATCH", "FAMILY_WRITE_DENIED",
                "FAMILY_PRIVATE_READ_DENIED", "GRANT_REVOKED", "FORGED_OWNER"}),
        ("G2", {"NEW_SOURCE_AFTER_DELETE", "EXPLICIT_REAUTHORIZATION",
                "DELETED_SOURCE_REPLAY", "DELETED_SOURCE_REVISION",
                "DELETED_TARGET", "DELETED_MEMORY_RECALL",
                "DELETED_MEMORY_SHARE", "RESTORE_RESURRECTION",
                "DERIVED_CONTENT_RECOVERY", "SUPPRESSION_HIT"}),
        ("G3", {"SUBJECT_BOUND", "SUBJECT_MISMATCH", "QUOTED_OTHER_AS_SELF",
                "THIRD_PARTY_AS_SELF",
                "REPORTED_ABOUT_SELF_NEEDS_CONFIRMATION"}),
        ("G5", {"TIME_SCOPE_BOUNDED", "TIME_SCOPE_PRESERVED",
                "TIME_SCOPE_EXPANDED", "TIME_ANCHOR_WRONG",
                "TIME_ANCHOR_AMBIGUOUS", "PAST_AS_CURRENT",
                "ONE_OFF_AS_HABIT", "ONE_OFF_AS_RECURRING",
                "RECENT_AS_PERMANENT", "TRANSIENT_AS_PERMANENT",
                "RECURRENCE_PRESERVED", "RECURRENCE_AS_PLAN",
                "UNCERTAIN_RESCHEDULE", "CONFLICT_UNRESOLVED"}),
        ("G7", {"PRIVATE_ONLY", "SENSITIVE_PRIVATE_ALLOWED",
                "SENSITIVE_LIMITED_RETENTION",
                "SENSITIVE_REQUIRES_CONFIRMATION", "REPORTED_MEDICAL_CLAIM",
                "SHARE_WITHOUT_GRANT"}),
        ("G8", {"SIDE_EFFECT_BLOCKED", "MEMORY_AS_REMINDER"}),
        ("G6", {"DUPLICATE_NOOP", "EXPLICIT_CORRECTION", "EXPLICIT_CHANGE",
                "CHANGE_OVER_TIME", "NOT_EXPLICIT_CORRECTION",
                "CONTEXT_AS_CORRECTION", "UNCERTAIN_CORRECTION",
                "REPORTED_CHANGE_NEEDS_CONFIRMATION", "LOW_VALUE_TRANSIENT",
                "NO_MEMORY_INTENT", "UNCERTAINTY_NOT_RESOLVED"}),
        ("G4", set()),  # fallback bucket filled below
    ]
    g4 = {"NEGATION_PRESERVED", "NEGATION_LOST", "NEGATION_INVERTED",
          "NEGATION_STRENGTHENED", "NEGATION_SCOPE_SHIFT", "QUANTIFIER_EXPANDED",
          "EXCEPTION_DROPPED", "RELATION_MISREAD", "DIAGNOSIS_INFERENCE",
          "MEDICATION_INFERENCE", "RISK_INFERENCE", "ASSISTANT_FACT_NOT_SOURCE"}
    for name, codes in table:
        if code in codes:
            return name
    if code in g4:
        return "G4"
    return "?"


rows = []
seq = 0
for key in ("P0", "P1", "P2", "P3"):
    for cid in groups[key]:
        seq += 1
        g = gate(A[cid]["primary_reason"])
        gb = gate(B[cid]["primary_reason"])
        if A[cid]["decision"] != B[cid]["decision"]:
            kind = "decision 级（A/B 分歧）"
        elif any(A[cid][f] != B[cid][f] for f in FIELD):
            kind = "字段口径（A/B 分歧）"
        elif A[cid]["primary_reason"] != B[cid]["primary_reason"] or \
                A[cid]["operation"] != B[cid]["operation"]:
            kind = "取码（A/B 分歧）"
        else:
            diff = [f for f in FIELDS
                    if A[cid][f] != cases[cid]["expected"][f]]
            kind = "双标一致但偏离草案：" + "/".join(diff)
        pair = "同门" if g == gb else f"{g} vs {gb}"
        row = {"seq": seq, "group": key, "group_label": GROUP_LABEL[key],
               "case_id": cid, "category": cases[cid]["category"],
               "gate_A": g, "gate_B": gb,
               "dispute_kind": f"{kind}（{pair}）",
               "rubric_v0.1.1_clause": CLUE_OVERRIDE.get(cid, CLUE[key])}
        for f in FIELDS:
            row[f"A_{f}"] = A[cid][f]
            row[f"B_{f}"] = B[cid][f]
        row["A_note"] = A[cid]["note"]
        row["B_note"] = B[cid]["note"]
        row["adjudicator"] = "邱振豪＋杨冰冰（独立 pass 1 后对齐）"
        rows.append(row)

# --- 2a. pass-1 sheets: independent, no A/B labels, no draft ----------------
for slug, display in ADJUDICATORS:
    path = OUT / f"pass1-sheet-{slug}.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=PASS1_COLS)
        w.writeheader()
        for row in rows:
            rec = {c: row.get(c, "") for c in PASS1_COLS}
            rec["adjudicator"] = display
            w.writerow(rec)
    print(f"pass1-sheet-{slug}.csv:", len(rows), "rows (no A/B, no draft)")

with (OUT / "adjudication-sheet.csv").open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=COLS)
    w.writeheader()
    for row in rows:
        w.writerow(row)
print("adjudication-sheet.csv:", len(rows), "rows,", len(COLS), "cols")

# --- 4. draft reference (pass 3 only) ---------------------------------------
with (OUT / "draft-reference.csv").open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["case_id", "group"] + FIELDS
                       + ["draft_notes"])
    w.writeheader()
    for row in rows:
        cid, exp = row["case_id"], cases[row["case_id"]]["expected"]
        rec = {"case_id": cid, "group": row["group"],
               "draft_notes": cases[cid].get("notes", "")}
        for f in FIELDS:
            rec[f] = exp.get(f, "")
        w.writerow(rec)
print("draft-reference.csv:", len(rows), "rows (open in pass 3 only)")
