import copy
import unittest
from pathlib import Path
import json
from validate import load_cases, validate_annotation_rows, ROOT, score
from audit_ai_review import check_rows
from prepare_ai_annotation import anonymize
import csv
import tempfile

class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.cases, _ = load_cases()
        self.rows = [dict(c['expected'], case_id=c['case_id'], annotator='reviewer-a') for c in self.cases]

    def test_complete_rows(self):
        validate_annotation_rows(self.rows, self.cases)

    def test_duplicate_rejected(self):
        with self.assertRaises(SystemExit):
            validate_annotation_rows(self.rows + [self.rows[0]], self.cases)

    def test_missing_rejected(self):
        with self.assertRaises(SystemExit):
            validate_annotation_rows(self.rows[:-1], self.cases)

    def test_partial_explicit(self):
        validate_annotation_rows(self.rows[:2], self.cases, True)

    def test_invalid_and_blank(self):
        for key, value in [('decision',''), ('annotator',' '), ('time_ok','maybe')]:
            rows = copy.deepcopy(self.rows)
            rows[0][key] = value
            with self.assertRaises(SystemExit):
                validate_annotation_rows(rows, self.cases)

    def test_rejection_cannot_write(self):
        rows = copy.deepcopy(self.rows)
        rows[0].update(decision='REJECT', operation='ADD')
        with self.assertRaises(SystemExit):
            validate_annotation_rows(rows, self.cases)

    def test_role_semantics_preserved(self):
        out = anonymize({'speaker_id':'assistant','actor_id':'family_lin',
                         'turn_id':'T-SENS-012'}, {})
        self.assertEqual(out['speaker_id'], 'assistant')
        self.assertEqual(out['actor_id'], 'family_lin')
        self.assertNotEqual(out['turn_id'], 'T-SENS-012')

    def test_review_all_and_missing_duplicate(self):
        rows = [json.loads(l) for l in (ROOT/'reviews/single-ai-v1/annotations.jsonl').read_text().splitlines()]
        check_rows(rows, self.cases)
        for invalid in [rows[:-1], rows + [rows[0]]]:
            with self.assertRaises(ValueError):
                check_rows(invalid, self.cases)

    def test_review_evidence_tampering(self):
        rows = [json.loads(l) for l in (ROOT/'reviews/single-ai-v1/annotations.jsonl').read_text().splitlines()]
        rows[0]['evidence'][0]['value'] = 'invented'
        with self.assertRaises(ValueError):
            check_rows(rows, self.cases)

    def test_review_cannot_expose_memory_on_reject(self):
        rows = [json.loads(l) for l in (ROOT/'reviews/single-ai-v1/annotations.jsonl').read_text().splitlines()]
        target = next(r for r in rows if r['label']['decision']=='REJECT')
        target['label']['visible_memory_ids']=['invented']
        with self.assertRaises(ValueError):
            check_rows(rows, self.cases)

if __name__ == '__main__':
    unittest.main()
