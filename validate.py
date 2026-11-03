#!/usr/bin/env python3
"""Validate and use the AgeGuard memory-gate synthetic case set.

This is a contract/schema checker, not a model evaluator. It deliberately does
not claim that the labels are human-verified or that the set is statistically
sufficient.

Usage:
    python3 validate.py
    python3 validate.py --blind-out /tmp/memory-gate-blind.jsonl
    python3 validate.py --score annotations.csv

The blind pack drops `expected`, `notes` and `polarity` (polarity would give the
answer away) and lists cases in a hash-shuffled order, because the case files
put all positives before all negatives.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CASES_DIR = ROOT / "cases"

CATEGORIES = {
    "negation": "negation.jsonl",
    "correction": "correction.jsonl",
    "time_scope": "time-scope.jsonl",
    "wrong_person": "wrong-person.jsonl",
    "sensitive": "sensitive.jsonl",
    "post_delete": "post-delete.jsonl",
    "cross_user": "cross-user.jsonl",
    "control": "control.jsonl",
}

DECISIONS = {"APPROVE", "REJECT", "NEEDS_CLARIFICATION", "DEFER"}
OPERATIONS = {"ADD", "NOOP", "MERGE", "REVISE", "READ"}
POLARITIES = {"positive", "negative", "control"}
EVENT_TYPES = {
    "candidate", "retry", "restore", "derived_rebuild", "share_attempt",
    "read", "no_memory",
}
ASSERTION_STATUSES = {
    "self_report", "reported_other", "uncertain", "user_confirmed",
}
SENSITIVITIES = {
    "normal", "personal", "health", "financial", "family_private", "restricted",
}
SCOPES = {"private", "family_projection"}
SUBJECT_KINDS = {
    "self", "family_member", "other_person", "pet_or_object", "event",
}
MEMORY_TYPES = {
    "background", "preference", "habit", "relation", "ongoing_event",
    "health_note", "plan_context",
}

# Closed reason-code vocabulary from memory-fields-and-write-rules-v0.1.md §7.
REASON_CODES = {
    # source / identity
    "SOURCE_MISSING", "SOURCE_NOT_FINAL", "SOURCE_STALE_REVISION",
    "SESSION_OWNER_MISMATCH", "OWNER_MISMATCH", "MODEL_SET_OWNER",
    # negation / semantics
    "NEGATION_PRESERVED", "NEGATION_LOST", "NEGATION_INVERTED",
    "NEGATION_STRENGTHENED", "NEGATION_SCOPE_SHIFT", "QUANTIFIER_EXPANDED",
    "EXCEPTION_DROPPED", "RELATION_MISREAD",
    # subject
    "SUBJECT_BOUND", "SUBJECT_MISMATCH", "QUOTED_OTHER_AS_SELF",
    "THIRD_PARTY_AS_SELF", "REPORTED_ABOUT_SELF_NEEDS_CONFIRMATION",
    # time
    "TIME_SCOPE_BOUNDED", "TIME_SCOPE_PRESERVED", "TIME_SCOPE_EXPANDED",
    "TIME_ANCHOR_WRONG", "TIME_ANCHOR_AMBIGUOUS", "PAST_AS_CURRENT",
    "RECURRENCE_PRESERVED",
    "ONE_OFF_AS_HABIT", "ONE_OFF_AS_RECURRING", "RECENT_AS_PERMANENT",
    "TRANSIENT_AS_PERMANENT",
    # duplicate / correction / conflict
    "DUPLICATE_NOOP", "EXPLICIT_CORRECTION", "EXPLICIT_CHANGE",
    "CHANGE_OVER_TIME", "NOT_EXPLICIT_CORRECTION", "UNCERTAIN_CORRECTION",
    "REPORTED_CHANGE_NEEDS_CONFIRMATION", "UNCERTAIN_RESCHEDULE",
    "CONFLICT_UNRESOLVED", "CONTEXT_AS_CORRECTION",
    # sensitive / retention
    "PRIVATE_ONLY", "SENSITIVE_PRIVATE_ALLOWED",
    "SENSITIVE_LIMITED_RETENTION", "SENSITIVE_REQUIRES_CONFIRMATION",
    "DIAGNOSIS_INFERENCE", "MEDICATION_INFERENCE", "RISK_INFERENCE",
    "ASSISTANT_FACT_NOT_SOURCE", "REPORTED_MEDICAL_CLAIM",
    "SHARE_WITHOUT_GRANT",
    # deletion / derived
    "NEW_SOURCE_AFTER_DELETE", "EXPLICIT_REAUTHORIZATION",
    "DELETED_SOURCE_REPLAY", "DELETED_SOURCE_REVISION", "DELETED_TARGET",
    "DELETED_MEMORY_RECALL", "RESTORE_RESURRECTION",
    "DERIVED_CONTENT_RECOVERY", "DELETED_MEMORY_SHARE", "SUPPRESSION_HIT",
    # isolation / permission
    "OWNER_MATCH", "CROSS_TENANT_WRITE", "CROSS_TENANT_READ",
    "TARGET_OWNER_MISMATCH", "FAMILY_WRITE_DENIED",
    "FAMILY_PRIVATE_READ_DENIED", "PRIVATE_MEMORY_NOT_GRANTABLE",
    "GRANT_REVOKED", "FORGED_OWNER",
    # side effects / other
    "SIDE_EFFECT_BLOCKED", "MEMORY_AS_REMINDER", "RECURRENCE_AS_PLAN",
    "NO_MEMORY_INTENT", "LOW_VALUE_TRANSIENT", "UNCERTAINTY_NOT_RESOLVED",
    "SCHEMA_INVALID", "REVIEW_FAILED",
}

# Codes that are not acceptable as a primary reason for an APPROVE decision.
NON_APPROVE_PRIMARY = {
    "SOURCE_MISSING", "SOURCE_NOT_FINAL", "SOURCE_STALE_REVISION",
    "SESSION_OWNER_MISMATCH", "OWNER_MISMATCH", "MODEL_SET_OWNER",
    "NEGATION_LOST", "NEGATION_INVERTED", "NEGATION_STRENGTHENED",
    "NEGATION_SCOPE_SHIFT", "QUANTIFIER_EXPANDED", "EXCEPTION_DROPPED",
    "RELATION_MISREAD", "SUBJECT_MISMATCH", "QUOTED_OTHER_AS_SELF",
    "THIRD_PARTY_AS_SELF", "TIME_SCOPE_EXPANDED", "TIME_ANCHOR_WRONG",
    "PAST_AS_CURRENT", "ONE_OFF_AS_HABIT", "ONE_OFF_AS_RECURRING",
    "RECENT_AS_PERMANENT", "TRANSIENT_AS_PERMANENT",
    "NOT_EXPLICIT_CORRECTION", "CONTEXT_AS_CORRECTION",
    "UNCERTAIN_CORRECTION", "REPORTED_CHANGE_NEEDS_CONFIRMATION",
    "UNCERTAIN_RESCHEDULE", "CONFLICT_UNRESOLVED",
    "TIME_ANCHOR_AMBIGUOUS", "SENSITIVE_REQUIRES_CONFIRMATION",
    "REPORTED_MEDICAL_CLAIM", "UNCERTAINTY_NOT_RESOLVED",
    "DIAGNOSIS_INFERENCE", "MEDICATION_INFERENCE", "RISK_INFERENCE",
    "ASSISTANT_FACT_NOT_SOURCE", "SHARE_WITHOUT_GRANT",
    "DELETED_SOURCE_REPLAY", "DELETED_SOURCE_REVISION", "DELETED_TARGET",
    "DELETED_MEMORY_RECALL", "RESTORE_RESURRECTION",
    "DERIVED_CONTENT_RECOVERY", "DELETED_MEMORY_SHARE", "SUPPRESSION_HIT",
    "CROSS_TENANT_WRITE", "CROSS_TENANT_READ", "TARGET_OWNER_MISMATCH",
    "FAMILY_WRITE_DENIED", "FAMILY_PRIVATE_READ_DENIED",
    "PRIVATE_MEMORY_NOT_GRANTABLE", "GRANT_REVOKED", "FORGED_OWNER",
    "SCHEMA_INVALID", "REVIEW_FAILED",
}

HARD_CATEGORIES = {"wrong_person", "post_delete", "cross_user"}


def load_cases() -> tuple[list[dict[str, Any]], list[str]]:
    cases: list[dict[str, Any]] = []
    errors: list[str] = []
    for category, filename in CATEGORIES.items():
        path = CASES_DIR / filename
        if not path.exists():
            errors.append(f"{path}: missing file")
            continue
        for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError as exc:
                errors.append(f"{path}:{lineno}: invalid JSON: {exc}")
                continue
            item["_file"] = path.name
            item["_line"] = lineno
            cases.append(item)
    return cases, errors


def require(condition: bool, errors: list[str], where: str, message: str) -> None:
    if not condition:
        errors.append(f"{where}: {message}")


def parse_dt(value: Any, errors: list[str], where: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        errors.append(f"{where}: timestamp must be an ISO string or null")
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{where}: invalid ISO timestamp {value!r}")
        return None


def validate_case(case: dict[str, Any], errors: list[str]) -> None:
    where = f"{case.get('_file', '?')}:{case.get('_line', '?')} {case.get('case_id', '?')}"
    required = ["case_id", "category", "polarity", "event_type", "requester", "expected"]
    for key in required:
        require(key in case, errors, where, f"missing top-level field {key}")

    category = case.get("category")
    require(category in CATEGORIES, errors, where, f"unknown category {category!r}")
    if category in CATEGORIES:
        require(CATEGORIES[category] == case.get("_file"), errors, where,
                f"category {category!r} is in wrong file {case.get('_file')!r}")

    polarity = case.get("polarity")
    require(polarity in POLARITIES, errors, where, f"bad polarity {polarity!r}")
    event_type = case.get("event_type")
    require(event_type in EVENT_TYPES, errors, where, f"bad event_type {event_type!r}")

    requester = case.get("requester")
    require(isinstance(requester, dict), errors, where, "requester must be an object")
    if isinstance(requester, dict):
        require(bool(requester.get("actor_id")), errors, where, "requester.actor_id missing")
        require(bool(requester.get("purpose")), errors, where, "requester.purpose missing")

    source = case.get("source")
    if source is not None:
        require(isinstance(source, dict), errors, where, "source must be an object or null")
        if isinstance(source, dict):
            for key in ["owner_id", "speaker_id", "session_id", "turn_id",
                        "source_revision", "final", "expressed_at", "timezone", "text"]:
                require(key in source, errors, where, f"source missing {key}")
            require(isinstance(source.get("final"), bool), errors, where,
                    "source.final must be boolean")
            require(isinstance(source.get("source_revision"), int),
                    errors, where, "source.source_revision must be int")
            parse_dt(source.get("expressed_at"), errors, where=f"{where}.source.expressed_at")
            require(isinstance(source.get("text"), str) and bool(source.get("text")),
                    errors, where, "source.text must be non-empty")

    candidate = case.get("candidate")
    if event_type in {"candidate", "retry", "restore", "derived_rebuild", "share_attempt"}:
        require(isinstance(candidate, dict), errors, where,
                f"{event_type} case must have a candidate")
    if candidate is not None:
        require(isinstance(candidate, dict), errors, where, "candidate must be an object or null")
        if isinstance(candidate, dict):
            require(candidate.get("subject_kind") in SUBJECT_KINDS, errors, where,
                    f"bad subject_kind {candidate.get('subject_kind')!r}")
            require(bool(candidate.get("subject_id")), errors, where, "candidate.subject_id missing")
            require(candidate.get("memory_type") in MEMORY_TYPES, errors, where,
                    f"bad memory_type {candidate.get('memory_type')!r}")
            require(isinstance(candidate.get("claim"), str) and bool(candidate.get("claim")),
                    errors, where, "candidate.claim must be non-empty")
            require(candidate.get("assertion_status") in ASSERTION_STATUSES, errors, where,
                    f"bad assertion_status {candidate.get('assertion_status')!r}")
            require(candidate.get("sensitivity") in SENSITIVITIES, errors, where,
                    f"bad sensitivity {candidate.get('sensitivity')!r}")
            require(candidate.get("scope") in SCOPES, errors, where,
                    f"bad scope {candidate.get('scope')!r}")
            require(bool(candidate.get("retention_policy_id")), errors, where,
                    "candidate.retention_policy_id missing")
            operation = candidate.get("operation")
            require(operation in {"ADD", "NOOP", "MERGE", "REVISE"}, errors, where,
                    f"bad candidate.operation {operation!r}")
            if operation in {"REVISE", "MERGE"}:
                require(bool(candidate.get("target_memory_id")), errors, where,
                        f"{operation} needs target_memory_id")
                require(isinstance(candidate.get("expected_version"), int), errors, where,
                        f"{operation} needs expected_version")
            parse_dt(candidate.get("valid_from"), errors, where=f"{where}.candidate.valid_from")
            parse_dt(candidate.get("valid_to"), errors, where=f"{where}.candidate.valid_to")
            vf = candidate.get("valid_from")
            vt = candidate.get("valid_to")
            if isinstance(vf, str) and isinstance(vt, str):
                a = parse_dt(vf, [], where)
                b = parse_dt(vt, [], where)
                if a and b:
                    require(a <= b, errors, where,
                            "candidate.valid_to must not precede valid_from")

    existing = case.get("existing_memories", [])
    require(isinstance(existing, list), errors, where, "existing_memories must be a list")
    if isinstance(existing, list):
        for i, memory in enumerate(existing):
            require(isinstance(memory, dict), errors, where,
                    f"existing_memories[{i}] must be an object")
            if isinstance(memory, dict):
                for key in ["memory_id", "owner_id", "version", "status",
                            "subject_kind", "subject_id", "claim", "visibility"]:
                    require(key in memory, errors, where,
                            f"existing_memories[{i}] missing {key}")
                require(isinstance(memory.get("version"), int), errors, where,
                        f"existing_memories[{i}].version must be int")
                require(memory.get("subject_kind") in SUBJECT_KINDS, errors, where,
                        f"existing_memories[{i}] bad subject_kind")
                require(memory.get("visibility") in {"private", "family_projection"},
                        errors, where, f"existing_memories[{i}] bad visibility")

    deletion = case.get("deletion_state")
    if deletion is not None:
        require(isinstance(deletion, dict), errors, where,
                "deletion_state must be an object or null")
        if isinstance(deletion, dict):
            for key in ["deleted_memory_ids", "suppressed_source_turn_ids"]:
                require(isinstance(deletion.get(key, []), list), errors, where,
                        f"deletion_state.{key} must be a list")

    read_request = case.get("read_request")
    if event_type == "read":
        require(isinstance(read_request, dict), errors, where,
                "read case must have read_request")
    if read_request is not None:
        require(isinstance(read_request, dict), errors, where,
                "read_request must be an object or null")
        if isinstance(read_request, dict):
            require(isinstance(read_request.get("target_memory_ids"), list),
                    errors, where, "read_request.target_memory_ids must be a list")
            require(bool(read_request.get("scope")), errors, where,
                    "read_request.scope missing")
            targets = read_request.get("target_memory_ids", [])
            known = {m.get("memory_id") for m in existing if isinstance(m, dict)}
            for target in targets:
                require(target in known, errors, where,
                        f"read target {target!r} not present in existing_memories")

    if source is not None and isinstance(source, dict):
        session_owner = source.get("session_owner_id")
        if session_owner is not None and session_owner != source.get("owner_id"):
            exp = case.get("expected", {}) if isinstance(case.get("expected"), dict) else {}
            require(exp.get("primary_reason") == "SESSION_OWNER_MISMATCH",
                    errors, where,
                    "source.session_owner_id differs from owner_id; expected SESSION_OWNER_MISMATCH")
    if candidate is not None and isinstance(candidate, dict):
        claimed_owner = candidate.get("owner_id")
        source_owner = source.get("owner_id") if isinstance(source, dict) else None
        if claimed_owner is not None and claimed_owner != source_owner:
            exp = case.get("expected", {}) if isinstance(case.get("expected"), dict) else {}
            require(exp.get("primary_reason") == "MODEL_SET_OWNER",
                    errors, where,
                    "candidate.owner_id differs from source owner; expected MODEL_SET_OWNER")

    expected = case.get("expected")
    require(isinstance(expected, dict), errors, where, "expected must be an object")
    if not isinstance(expected, dict):
        return
    decision = expected.get("decision")
    operation = expected.get("operation")
    primary = expected.get("primary_reason")
    secondary = expected.get("secondary_reasons", [])
    require(decision in DECISIONS, errors, where, f"bad expected.decision {decision!r}")
    require(operation in OPERATIONS, errors, where, f"bad expected.operation {operation!r}")
    require(primary in REASON_CODES, errors, where,
            f"bad expected.primary_reason {primary!r}")
    require(isinstance(secondary, list), errors, where,
            "expected.secondary_reasons must be a list")
    if isinstance(secondary, list):
        for code in secondary:
            require(code in REASON_CODES, errors, where,
                    f"bad secondary reason {code!r}")
            require(code != primary, errors, where,
                    "secondary reason duplicates primary")
    for key in ["subject_ok", "time_ok"]:
        require(expected.get(key) in {"yes", "no", "unclear"}, errors, where,
                f"expected.{key} must be yes/no/unclear")
    require(expected.get("sensitivity_action") in {"allow", "private_limited", "clarify", "reject"},
            errors, where,
            "expected.sensitivity_action must be allow/private_limited/clarify/reject")

    if decision == "APPROVE":
        require(operation in {"ADD", "NOOP", "MERGE", "REVISE", "READ"},
                errors, where, "APPROVE operation must be ADD/NOOP/MERGE/REVISE/READ")
        require(primary not in NON_APPROVE_PRIMARY, errors, where,
                f"APPROVE uses a non-approve primary reason {primary!r}")
    else:
        require(operation == "NOOP", errors, where,
                f"{decision} must use expected.operation=NOOP")
        require(expected.get("visible_memory_ids", []) == [],
                errors, where, f"{decision} must not make memories visible")
    if operation == "READ":
        require(event_type == "read", errors, where, "operation READ requires event_type=read")
        require(isinstance(expected.get("visible_memory_ids"), list),
                errors, where, "READ requires visible_memory_ids list")
    if event_type == "read":
        require(operation in {"READ", "NOOP"}, errors, where,
                "read case operation must be READ or NOOP")

    if polarity == "positive":
        require(decision == "APPROVE", errors, where,
                "positive case must expect APPROVE")
    elif polarity == "negative":
        require(decision != "APPROVE", errors, where,
                "negative case must expect REJECT/NEEDS_CLARIFICATION/DEFER")
        if category in HARD_CATEGORIES:
            require(decision in {"REJECT", "NEEDS_CLARIFICATION"}, errors, where,
                    "hard-safety negative case must block or clarify")

    if candidate and isinstance(candidate, dict) and candidate.get("operation") in {"REVISE", "MERGE"}:
        target = candidate.get("target_memory_id")
        match = [m for m in existing if isinstance(m, dict) and m.get("memory_id") == target]
        require(bool(match), errors, where,
                f"candidate target {target!r} not in existing_memories")
        if match:
            if match[0].get("owner_id") != (source.get("owner_id") if source else None):
                require(expected.get("primary_reason") == "TARGET_OWNER_MISMATCH",
                        errors, where, "target memory owner differs from source owner")
            if decision == "APPROVE":
                require(candidate.get("expected_version") == match[0].get("version"),
                        errors, where,
                        "candidate.expected_version does not match target memory version")


def validate_set(cases: list[dict[str, Any]], errors: list[str]) -> None:
    seen: set[str] = set()
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        cid = case.get("case_id")
        if not isinstance(cid, str) or not cid:
            errors.append(f"{case.get('_file')}:{case.get('_line')}: missing case_id")
            continue
        if cid in seen:
            errors.append(f"{case.get('_file')}:{case.get('_line')}: duplicate case_id {cid}")
        seen.add(cid)
        by_category[case.get("category")].append(case)
        validate_case(case, errors)

    for category, filename in CATEGORIES.items():
        items = by_category.get(category, [])
        require(bool(items), errors, filename, "category has no cases")
        if category == "control":
            continue
        pos = sum(1 for c in items if c.get("polarity") == "positive")
        neg = sum(1 for c in items if c.get("polarity") == "negative")
        require(len(items) == 20, errors, filename,
                f"expected 20 cases, got {len(items)}")
        require(pos == 10, errors, filename, f"expected 10 positive, got {pos}")
        require(neg == 10, errors, filename, f"expected 10 negative, got {neg}")

    controls = by_category.get("control", [])
    require(len(controls) >= 14, errors, "control.jsonl",
            f"expected at least 14 controls, got {len(controls)}")


def validate_manifest(cases: list[dict[str, Any]], errors: list[str]) -> None:
    path = ROOT / "manifest.json"
    if not path.exists():
        errors.append("manifest.json: missing file")
        return
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"manifest.json: invalid JSON: {exc}")
        return
    require(manifest.get("case_count") == len(cases), errors, "manifest.json",
            f"case_count {manifest.get('case_count')} != actual {len(cases)}")
    counts = Counter((c["category"], c["polarity"]) for c in cases)
    for category, info in manifest.get("categories", {}).items():
        if category not in CATEGORIES:
            errors.append(f"manifest.json: unknown category {category!r}")
            continue
        total = sum(counts[(category, p)] for p in POLARITIES)
        require(info.get("total") == total, errors, "manifest.json",
                f"{category} total {info.get('total')} != actual {total}")
        for polarity in ("positive", "negative"):
            if polarity in info:
                require(info[polarity] == counts[(category, polarity)], errors,
                        "manifest.json",
                        f"{category} {polarity} {info[polarity]} != actual {counts[(category, polarity)]}")
    if manifest.get("human_annotation") != "not_started":
        print("NOTE: manifest says human_annotation is no longer 'not_started'; "
              "update annotation-status.md and README before claiming agreement.")


def print_stats(cases: list[dict[str, Any]]) -> None:
    print(f"cases: {len(cases)}")
    by_category: dict[str, Counter[str]] = defaultdict(Counter)
    for case in cases:
        by_category[case["category"]][case["polarity"]] += 1
    for category in CATEGORIES:
        counts = by_category.get(category, Counter())
        total = sum(counts.values())
        print(f"  {category:14s} total={total:3d} positive={counts['positive']:3d} "
              f"negative={counts['negative']:3d} control={counts['control']:3d}")
    decisions = Counter(c["expected"]["decision"] for c in cases)
    print("expected decisions:", dict(sorted(decisions.items())))
    reasons = Counter(c["expected"]["primary_reason"] for c in cases)
    print(f"distinct primary reasons: {len(reasons)}")
    print("label status: draft_assistant (not human-verified)")


# Blind packs must not leak anything that reveals the intended label.
# `polarity` says positive/negative/control outright; `expected`/`notes` are the
# answer key. Anything added here needs the same test: could an annotator infer
# the draft label from it without doing the judgment work?
BLIND_FORBIDDEN_KEYS = {"expected", "notes", "polarity", "label_status"}


def blind_order(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stable pseudo-random order for blind packs.

    Case files list positives before negatives (001-010 positive, 011-020
    negative), so emitting them in file order leaks the label through the
    case_id. Ordering by a hash of case_id is deterministic across runs and
    Python versions, and breaks that correlation.
    """
    return sorted(cases, key=lambda c: hashlib.sha256(c["case_id"].encode()).hexdigest())


def write_blind(cases: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for case in blind_order(cases):
            blind = {
                "case_id": case["case_id"],
                "category": case["category"],
                "event_type": case["event_type"],
                "source": case.get("source"),
                "candidate": case.get("candidate"),
                "existing_memories": case.get("existing_memories", []),
                "deletion_state": case.get("deletion_state"),
                "requester": case.get("requester"),
                "read_request": case.get("read_request"),
            }
            leaked = BLIND_FORBIDDEN_KEYS & set(blind)
            if leaked:
                raise SystemExit(f"blind pack would leak {sorted(leaked)}; refusing to write")
            handle.write(json.dumps(blind, ensure_ascii=False) + "\n")
    print(f"blind pack written: {path} ({len(cases)} cases, polarity removed, order shuffled)")


def write_sheet(cases: list[dict[str, Any]], path: Path) -> None:
    columns = ["case_id", "annotator", "decision", "operation",
               "primary_reason", "subject_ok", "time_ok",
               "sensitivity_action", "note"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for case in blind_order(cases):
            writer.writerow({"case_id": case["case_id"]})
    print(f"blank annotation sheet written: {path} ({len(cases)} rows, same order as blind pack)")


def cohen_kappa(a: list[str], b: list[str]) -> tuple[float, float]:
    n = len(a)
    if n == 0:
        return 0.0, 0.0
    agree = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum((ca[k] / n) * (cb[k] / n) for k in set(ca) | set(cb))
    if pe >= 1.0:
        return agree, 1.0 if agree == 1.0 else 0.0
    return agree, (agree - pe) / (1.0 - pe)


FIELDS = ["decision", "operation", "primary_reason",
          "subject_ok", "time_ok", "sensitivity_action"]


def score(path: Path, cases: list[dict[str, Any]]) -> None:
    expected = {c["case_id"]: c["expected"] for c in cases}
    categories = {c["case_id"]: c["category"] for c in cases}
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [f for f in ["case_id", "annotator", *FIELDS] if f not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"annotation CSV missing columns: {missing}")
        for row in reader:
            if row.get("case_id") not in expected:
                raise SystemExit(f"annotation CSV has unknown case_id {row.get('case_id')!r}")
            rows.append(row)

    annotators = sorted({r["annotator"] for r in rows})
    if len(annotators) < 2:
        raise SystemExit("need at least two annotators for agreement scoring")
    print("annotators:", annotators)
    print("cases annotated:", len({r["case_id"] for r in rows}))

    # pairwise agreement
    for i in range(len(annotators)):
        for j in range(i + 1, len(annotators)):
            a_name, b_name = annotators[i], annotators[j]
            a = {r["case_id"]: r for r in rows if r["annotator"] == a_name}
            b = {r["case_id"]: r for r in rows if r["annotator"] == b_name}
            common = sorted(set(a) & set(b))
            print(f"\npair {a_name} vs {b_name}: {len(common)} common cases")
            for field in FIELDS:
                av = [a[c][field] for c in common]
                bv = [b[c][field] for c in common]
                agree, kappa = cohen_kappa(av, bv)
                flag = "OK" if agree >= 0.85 else "LOW"
                if field in {"subject_ok", "time_ok", "sensitivity_action"}:
                    flag = "OK" if agree >= 0.90 else "LOW"
                print(f"  {field:20s} agree={agree:.3f} kappa={kappa:.3f} {flag}")
            for category in CATEGORIES:
                subset = [c for c in common if categories[c] == category]
                if not subset:
                    continue
                av = [a[c]["decision"] for c in subset]
                bv = [b[c]["decision"] for c in subset]
                agree, _ = cohen_kappa(av, bv)
                hard = " HARD" if category in HARD_CATEGORIES else ""
                print(f"  decision/{category}: n={len(subset)} agree={agree:.3f}{hard}")

    # annotator vs draft labels
    print("\nannotator vs draft labels (draft labels are not gold):")
    for name in annotators:
        subset = [r for r in rows if r["annotator"] == name]
        print(f"  {name}: n={len(subset)}")
        for field in FIELDS:
            correct = sum(1 for r in subset if r[field] == expected[r["case_id"]][field])
            print(f"    {field:20s} {correct}/{len(subset)} = {correct / len(subset):.3f}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blind-out", type=Path, help="write a blind annotation pack")
    parser.add_argument("--sheet-out", type=Path, help="write a blank annotation CSV")
    parser.add_argument("--score", type=Path, help="score a two-annotator CSV")
    args = parser.parse_args()

    cases, errors = load_cases()
    if errors:
        for error in errors:
            print("ERROR", error, file=sys.stderr)
        print(f"\n{len(errors)} validation error(s)", file=sys.stderr)
        return 1

    validate_set(cases, errors)
    validate_manifest(cases, errors)
    if errors:
        for error in errors:
            print("ERROR", error, file=sys.stderr)
        print(f"\n{len(errors)} validation error(s)", file=sys.stderr)
        return 1

    print_stats(cases)
    if args.blind_out:
        write_blind(cases, args.blind_out)
    if args.sheet_out:
        write_sheet(cases, args.sheet_out)
    if args.score:
        score(args.score, cases)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
