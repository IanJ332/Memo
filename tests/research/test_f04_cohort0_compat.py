"""Synthetic negative controls for the new authentic-only public admission contract.

Fixtures are never enrolled as native captures. Full original captures require
an independently accepted review supplied to the CLI after these tests pass.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('cohort0_contract_under_test', ROOT / 'scripts/research/f04_cohort0_compat.py')
f04 = importlib.util.module_from_spec(spec); spec.loader.exec_module(f04)


class ContractControls(unittest.TestCase):
    def test_duplicate_json_keys_fail(self):
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_JSON_KEY'):
            f04.strict('{"a":1,"a":2}')

    def test_nonfinite_json_fails(self):
        with self.assertRaisesRegex(ValueError, 'NONFINITE_JSON'):
            f04.strict('{"a":NaN}')

    def test_symlink_evidence_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve(); target = root / 'target'; target.write_bytes(b'{}')
            link = root / 'link'; link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, 'REGULAR_CANONICAL'):
                f04.raw(link)

    def test_identity_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder).resolve() / 'evidence'; path.write_bytes(b'{}')
            value = f04.identity(path); value['sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'EVIDENCE_IDENTITY'):
                f04.verified_identity(value)

    def test_four_field_custody_never_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / 'input-custody.json').write_bytes(f04.canonical({
                'original_manifest': {}, 'snapshot_manifest': {},
                'original_owner_grant': {}, 'snapshot_owner_grant': {}}))
            with self.assertRaisesRegex(ValueError, 'EXACT_SIX_FIELD_CUSTODY'):
                f04.verify_custody(root, {}, {}, {})

    def test_fake_review_cannot_enroll(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve(); review = root / 'review.json'; review.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'REVIEW_SCHEMA'):
                f04.review_contract(root, root, root, root / 'pins', review)

    def test_synthetic_capture_flag_has_no_admission_path(self):
        with self.assertRaisesRegex(ValueError, 'AUTHENTIC_ENROLLED_CAPTURE_REQUIRED'):
            f04._decision_only({'schema': f04.SCHEMA, 'classification': 'SYNTHETIC_VALIDATION_CAPTURE'},
                                  None, None, None)

    def mapping(self):
        units = [{'unit_id': 'source-' + str(i), 'prospective_attempt_id': 'source-attempt-' + str(i),
                  'batch_attempt_ordinal': i} for i in range(1, 61)]
        manifest = {'batch_id': 'SOURCE', 'units': units}
        binding = {'schema': 'TIER_C_FRESH_EXECUTION_BINDING_V1', 'source_batch_id': 'SOURCE',
                   'execution_id': 'FRESH', 'units': [
                       {'ordinal': i, 'source_unit_id': u['unit_id'],
                        'source_prospective_attempt_id': u['prospective_attempt_id'],
                        'execution_unit_id': f'FRESH-{i:03d}', 'prospective_attempt_id': f'EXP-QWEN-FRESH-{i:03d}'}
                       for i, u in enumerate(units, 1)]}
        return manifest, binding

    def test_fresh_mapping_preserves_scientific_identity(self):
        manifest, binding = self.mapping()
        result = f04.mapped_unit(manifest, binding, 'FRESH-034')
        self.assertEqual(result['source_unit_id'], 'source-34')
        self.assertEqual(result['batch_attempt_ordinal'], 34)
        self.assertEqual(result['unit_id'], 'FRESH-034')

    def test_other_row_tamper_rejects_whole_mapping(self):
        manifest, binding = self.mapping(); binding['units'][59]['ordinal'] = 1
        with self.assertRaisesRegex(ValueError, 'EXACT_SCIENTIFIC_EXECUTION_ROW'):
            f04.mapped_unit(manifest, binding, 'FRESH-001')

    def test_unknown_execution_unit_fails(self):
        manifest, binding = self.mapping()
        with self.assertRaisesRegex(ValueError, 'UNIT_IDENTITY'):
            f04.mapped_unit(manifest, binding, 'FRESH-061')

    def test_selected_context_must_be_literal_first_ten(self):
        scope = {'issuer': 'synthetic', 'subject': 'synthetic', 'project': 'synthetic'}
        ns = 'npq-' + f04.sha(f04.canonical(scope))
        rows = [{'id': str(i), 'memory': str(i), 'user_id': ns} for i in range(17)]
        selected = [{'native_id': str(i), 'content': str(i), 'original_position_1based': i + 1,
                     'native_user_id': ns} for i in range(10)]
        self.assertEqual(f04.verify_selection('mem0', {'results': rows}, selected, scope, {}, None), 17)
        selected[0]['content'] = 'rewritten'
        with self.assertRaisesRegex(ValueError, 'LITERAL_RAW_LIMIT10_PREFIX'):
            f04.verify_selection('mem0', {'results': rows}, selected, scope, {}, None)

    def test_arbitrary_selected_subset_fails(self):
        scope = {'issuer': 'synthetic'}; ns = 'npq-' + f04.sha(f04.canonical(scope))
        rows = [{'id': str(i), 'memory': str(i), 'user_id': ns} for i in range(17)]
        selected = [{'native_id': str(i), 'content': str(i), 'original_position_1based': i + 1,
                     'native_user_id': ns} for i in range(7, 17)]
        with self.assertRaisesRegex(ValueError, 'LITERAL_RAW_LIMIT10_PREFIX'):
            f04.verify_selection('mem0', {'results': rows}, selected, scope, {}, None)

    def test_foreign_native_scope_fails(self):
        with self.assertRaisesRegex(ValueError, 'NATIVE_USER_SCOPE'):
            f04.verify_selection('mem0', {'results': [{'id': 'x', 'memory': 'y', 'user_id': 'foreign'}]},
                                 [], {'issuer': 'synthetic'}, {}, None)

    def test_no_call_not_promoted_to_native_proposal(self):
        result = f04._decision_only({'schema': f04.SCHEMA, 'classification': 'AUTHENTIC_MODEL_NO_PROPOSAL',
                                      'unit_id': 'SYNTHETIC-UNIT', 'native_calls': []}, None, None, None)
        self.assertEqual(result['status'], 'NOT_APPLICABLE_NO_NATIVE_PROPOSAL')
        self.assertIsNone(result['decision'])
        self.assertEqual(result['protected_dispatches'], 0)
        self.assertEqual(result['OFF'], 'NOT_EVALUATED')

    def test_public_source_has_no_dispatcher_or_fallback_execution(self):
        import ast
        tree = ast.parse((ROOT / f04.SOURCE).read_text())
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        self.assertFalse(any(isinstance(n.func, ast.Attribute) and
                             n.func.attr in {'dispatch', 'dispatch_bound', '_dispatch', 'send_report'} for n in calls))
        self.assertTrue(any(isinstance(n.func, ast.Attribute) and n.func.attr == 'authorize_tool_call' for n in calls))
        self.assertNotIn('validation_fixture', (ROOT / f04.SOURCE).read_text())


if __name__ == '__main__':
    unittest.main()
