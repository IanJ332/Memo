"""Unit tests use synthetic bytes only; authentic reconciliation is a separate CLI."""
import importlib.util
import itertools
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('cohort0', Path(__file__).resolve().parents[2] / 'scripts/research/reconcile_cohort0.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReconciliationTests(unittest.TestCase):
    def test_published_untied_reference(self):
        data = [6, 8, 14, 16, 23, 24, 28, 29, 41, -48, 49, 56, 60, -67, 75]
        result = MODULE.wilcoxon(data)
        self.assertEqual(result['W_minus'], 24)
        self.assertEqual(result['p_exact_conditional_signs'], .041259765625)
        self.assertAlmostEqual(result['p_normal_no_continuity'], .04088813291185591)

    def test_tied_exact_matches_exhaustive_signs(self):
        data = [1, 1, -2, 3, 3]
        # Independently average ranks: 1.5,1.5,3,4.5,4.5.
        ranks = [1.5, 1.5, 3, 4.5, 4.5]
        observed = min(12, 3)
        sums = [sum(r for r, s in zip(ranks, signs) if s) for signs in itertools.product([0, 1], repeat=5)]
        expected = min(1, 2 * sum(s <= observed for s in sums) / len(sums))
        result = MODULE.wilcoxon(data)
        self.assertEqual(result['p_exact_conditional_signs'], expected)
        self.assertEqual(result['absolute_rank_tie_sizes'], [2, 2])

    def test_zero_removal_and_sign_symmetry(self):
        a, b = MODULE.wilcoxon([0, 1, 2, -3]), MODULE.wilcoxon([-1, -2, 3])
        self.assertEqual(a['zeros_removed'], 1)
        self.assertEqual(a['p_exact_conditional_signs'], b['p_exact_conditional_signs'])
        self.assertEqual(a['p_normal_no_continuity'], b['p_normal_no_continuity'])
        self.assertEqual(MODULE.wilcoxon([0, 0])['p_exact_conditional_signs'], 1)

    def test_all_zero_normal_not_reported_as_informative(self):
        self.assertEqual(MODULE.wilcoxon([])['n_nonzero'], 0)

    def test_integrity_and_extra_member(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'raw').write_bytes(b'synthetic')
            data = {'files': [{'path': 'raw', 'bytes': 9, 'sha256': MODULE.sha(b'synthetic')}]}
            (root / 'inventory.json').write_text(json.dumps(data))
            self.assertEqual(MODULE.verify_inventory(root)['verified_files'], 1)
            (root / 'extra').write_bytes(b'')
            with self.assertRaisesRegex(ValueError, 'membership'):
                MODULE.verify_inventory(root)
            (root / 'extra').unlink()
            (root / 'raw').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'integrity'):
                MODULE.verify_inventory(root)

    def test_inventory_rejects_escape_and_duplicate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(ValueError):
                MODULE.safe_member(root, '../secret')
            with self.assertRaises(ValueError):
                MODULE.safe_member(root, '/secret')
            (root / 'raw').write_bytes(b'x')
            row = {'path': 'raw', 'bytes': 1, 'sha256': MODULE.sha(b'x')}
            (root / 'inventory.json').write_text(json.dumps({'files': [row, row]}))
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                MODULE.verify_inventory(root)

    def test_grouping_does_not_impute_missing(self):
        def row(condition, status='COMPLETE', case='CASE'):
            return {'status': status, 'pair_id': 'P', 'provider': 'provider', 'case_id': case,
                    'condition': condition, 'unit': condition, 'reasoning_tokens': 1 if condition == 'CONTROL' else 9}
        self.assertEqual(MODULE.paired([row('CONTROL')]), [])
        self.assertEqual(MODULE.paired([row('CONTROL'), row('CONFLICT', 'UNKNOWN_RESPONSE')]), [])
        self.assertEqual(MODULE.paired([row('CONTROL'), row('CONFLICT')])[0]['reasoning_difference'], 8)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            MODULE.paired([row('CONTROL'), row('CONTROL')])
        with self.assertRaisesRegex(ValueError, 'inconsistent'):
            MODULE.paired([row('CONTROL'), row('CONFLICT', case='OTHER')])


if __name__ == '__main__':
    unittest.main()
