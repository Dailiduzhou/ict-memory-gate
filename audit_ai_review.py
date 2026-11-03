"""Validate single-AI review provenance and labels; not a correctness evaluator."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from validate import (ROOT, load_cases, DECISIONS, OPERATIONS, REASON_CODES,
                      NON_APPROVE_PRIMARY)

FIELDS = ['decision', 'operation', 'primary_reason', 'subject_ok', 'time_ok',
          'sensitivity_action', 'secondary_reasons', 'visible_memory_ids']

def check_rows(rows, cases):
    by_id = {c['case_id']: c for c in cases}
    seen = set()
    for row in rows:
        cid = row['case_id']
        if cid not in by_id or cid in seen:
            raise ValueError(f'unknown/duplicate case: {cid}')
        seen.add(cid)
        case = by_id[cid]
        baseline = dict(case['expected'])
        baseline.setdefault('secondary_reasons', [])
        baseline.setdefault('visible_memory_ids', [])
        if row['baseline'] != baseline:
            raise ValueError(f'baseline changed: {cid}')
        label = row['label']
        if set(label) != set(FIELDS):
            raise ValueError(f'incomplete label fields: {cid}')
        choices = {'decision': DECISIONS, 'operation': OPERATIONS,
                   'primary_reason': REASON_CODES,
                   'subject_ok': {'yes', 'no', 'unclear'},
                   'time_ok': {'yes', 'no', 'unclear'},
                   'sensitivity_action': {'allow', 'private_limited', 'clarify', 'reject'}}
        for key, allowed in choices.items():
            if label[key] not in allowed:
                raise ValueError(f'invalid {key}: {cid}')
        for key in ['secondary_reasons', 'visible_memory_ids']:
            if not isinstance(label[key], list) or not all(isinstance(v, str) for v in label[key]):
                raise ValueError(f'bad list {key}: {cid}')
            if len(set(label[key])) != len(label[key]):
                raise ValueError(f'duplicate values {key}: {cid}')
        if any(r not in REASON_CODES or r == label['primary_reason'] for r in label['secondary_reasons']):
            raise ValueError(f'invalid secondary reason: {cid}')
        if label['decision'] != 'APPROVE':
            if label['operation'] != 'NOOP' or label['visible_memory_ids']:
                raise ValueError(f'rejection makes data visible: {cid}')
        elif label['primary_reason'] in NON_APPROVE_PRIMARY:
            raise ValueError(f'APPROVE rejection reason: {cid}')
        visible = set(label['visible_memory_ids'])
        if label['operation'] == 'READ':
            if case['event_type'] != 'read':
                raise ValueError(f'READ on non-read: {cid}')
            requested = set(case['read_request']['target_memory_ids'])
            memories = {m['memory_id']: m for m in case.get('existing_memories', [])}
            deleted = set((case.get('deletion_state') or {}).get('deleted_memory_ids', []))
            if not visible <= requested or any(v not in memories or v in deleted or
                memories[v]['status'] != 'ACTIVE' or
                memories[v]['owner_id'] != case['requester']['actor_id'] for v in visible):
                raise ValueError(f'invalid visible memory IDs: {cid}')
        elif visible:
            raise ValueError(f'non-READ has visible IDs: {cid}')
        if case['event_type'] == 'read' and label['operation'] not in {'READ', 'NOOP'}:
            raise ValueError(f'read case invalid operation: {cid}')
        diff = [f for f in baseline if baseline[f] != label[f]]
        if row['changed_fields'] != diff:
            raise ValueError(f'invalid diff: {cid}')
        if row.get('blind') is not False or row.get('human_verified') is not False:
            raise ValueError(f'misleading provenance: {cid}')
        if not isinstance(row.get('needs_human_review'), bool) or (diff and not row['needs_human_review']):
            raise ValueError(f'missing review flag: {cid}')
        if not row.get('note') or not row.get('evidence'):
            raise ValueError(f'missing evidence: {cid}')
        for evidence in row['evidence']:
            value = case
            for part in evidence['path'].split('.'):
                value = value[part]
            if value != evidence['value']:
                raise ValueError(f'evidence mismatch: {cid}')
    if seen != set(by_id):
        raise ValueError(f'missing {len(set(by_id) - seen)} cases')


def main():
    batch = ROOT / 'reviews/single-ai-v1'
    run = json.loads((batch / 'run.json').read_text())
    for rel, digest in run['input_sha256'].items():
        if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != digest:
            raise ValueError(f'input hash changed: {rel}')
    data = (batch / 'annotations.jsonl').read_bytes()
    if hashlib.sha256(data).hexdigest() != run['annotation_sha256']:
        raise ValueError('annotation hash mismatch')
    rows = [json.loads(line) for line in data.decode().splitlines()]
    cases, errors = load_cases()
    if errors:
        raise ValueError(errors)
    check_rows(rows, cases)
    print('Review validation PASS (structure/provenance, NOT semantic accuracy)')
    print('cases:', len(rows), 'label changes:', sum(bool(r['changed_fields']) for r in rows),
          'human-review flags:', sum(r['needs_human_review'] for r in rows))
    print('proposed decisions:', dict(Counter(r['label']['decision'] for r in rows)))

if __name__ == '__main__':
    main()
