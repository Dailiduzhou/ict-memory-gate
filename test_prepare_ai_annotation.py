import tempfile
import unittest
from pathlib import Path
from prepare_ai_annotation import prepare, anonymize

class BlindPackTests(unittest.TestCase):
    def test_references_stay_equal(self):
        result = anonymize({"case_id": "NEG-001", "target_memory_id": "M-1",
                            "existing_memories": [{"memory_id": "M-1"}]}, {})
        self.assertNotEqual(result["case_id"], "NEG-001")
        self.assertEqual(result["target_memory_id"], result["existing_memories"][0]["memory_id"])

    def test_pack_has_no_answer_fields_and_mapping_is_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "batch"
            records, reverse = prepare(dest)
            self.assertEqual(len(records), 155)
            self.assertEqual(len(reverse), 155)
            for row in records:
                self.assertFalse({"expected", "notes", "polarity", "category"} & row.keys())
                self.assertTrue(row["case_id"].startswith("id_"))
            self.assertFalse((dest / "annotator" / "PRIVATE-case-map.json").exists())
            with self.assertRaises(FileExistsError):
                prepare(dest)

if __name__ == "__main__":
    unittest.main()
