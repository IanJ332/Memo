"""Historical analysis guards; no native calls or synthetic provider results."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("history_summary", ROOT / "scripts/research/summarize_lifecycle_history.py")
history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(history)


class HistoricalSummaryTests(unittest.TestCase):
    def setUp(self):
        import json
        self.rows = [json.loads(line) for line in (ROOT / history.COMBINED).read_text().splitlines()]

    def test_sources_and_coverage(self):
        result = history.analyze(ROOT)
        self.assertEqual(result["registered_rows"], 42)
        self.assertEqual(result["operation_status"], {"SUCCESS": 41, "ERROR": 1})
        self.assertEqual(result["new_native_observations"], 0)
        self.assertEqual(result["downstream_calls"], 0)

    def test_duplicate_is_rejected(self):
        with self.assertRaises(ValueError):
            history.summarize(self.rows + [self.rows[0]])

    def test_missing_is_rejected(self):
        with self.assertRaises(ValueError):
            history.summarize(self.rows[1:])

    def test_error_cannot_be_promoted(self):
        rows = copy.deepcopy(self.rows)
        next(r for r in rows if r["run_id"] == "freeze-v1__openviking__S0__r2")["operation_status"] = "SUCCESS"
        with self.assertRaises(ValueError):
            history.summarize(rows)

    def test_freeze_drift_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        rows[0]["freeze_sha256"] = "changed"
        with self.assertRaises(ValueError):
            history.summarize(rows)

    def test_pretransition_candidates_are_not_final_candidates(self):
        result = history.summarize(self.rows)
        group = next(g for g in result["groups"] if (g["provider"], g["scenario"]) == ("mem0", "S3"))
        for run in group["runs"]:
            self.assertEqual(run["recorded_candidate_rows_by_phase"], {"observe-before-transition": 1})
            self.assertEqual(run["selected_context"], "NOT_ESTABLISHED_BY_THIS_TABLE")


if __name__ == "__main__":
    unittest.main()
