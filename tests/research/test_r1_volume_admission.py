"""Offline receipt semantics using the unchanged qualified implementation.

All writable journals/receipts are synthetic temporary fixtures. No external
approval is mocked, no historical receipt is installed, and no live action runs.
"""
from copy import deepcopy
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from memlife.r1 import contract

ACCEPTED = os.environ.get('MEMLIFE_R1_TEST_ACCEPTED_ROOT')
_DENY_DISPATCH = False


def deny_dispatch(event, args):
    if _DENY_DISPATCH and (event.startswith('socket.') or event in (
            'subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.exec')):
        raise PermissionError('OFFLINE_VOLUME_RECEIPT_TEST_NO_DISPATCH')


def release_guard():
    global _DENY_DISPATCH
    _DENY_DISPATCH = False


sys.addaudithook(deny_dispatch)


@unittest.skipUnless(ACCEPTED, 'Requires retained qualified private sources')
class VolumeReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global _DENY_DISPATCH
        _DENY_DISPATCH = True
        cls.addClassCleanup(release_guard)
        accepted = Path(ACCEPTED).resolve()
        contract.connect_sources(accepted)  # Verifies the unchanged pinset first.
        from memlife.tier_c_bounded import access, volume
        from memlife.batch import evidence
        cls.access, cls.volume, cls.e = access, volume, evidence
        # Reuse the existing synthetic volume fixture, never historical capture.
        spec = importlib.util.spec_from_file_location(
            'volume_fixture', accepted / 'tests/research/test_tier_c_volume_identity.py')
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        cls.fixture = staticmethod(fixture.fixture)

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='SYNTHETIC-NO-LIVE-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.access_root = self.root / 'access'
        self.access_root.mkdir()
        self.obs, self.cloud = self.fixture()
        self.result = self.volume.verify_volume(self.obs, self.cloud)
        e = self.e
        package = e.durable(self.root / 'SYNTHETIC-package.json', {'synthetic': True})
        binding = e.durable(self.root / 'SYNTHETIC-binding.json',
                            {'package': package, 'execution_id': 'SYNTHETIC-NOT-A-CAMPAIGN'})
        grant = e.durable(self.root / 'owner-authorization.json',
                          {'synthetic': True, 'approved': False, 'volume_source_revision': binding})
        e.durable(self.root / 'input-custody.json',
                  {'original_manifest': package, 'original_owner_grant': grant})
        self.inputs = {'manifest': package, 'grant': grant, 'source_revision': binding}
        commands = {}
        for name, observation in self.obs.items():
            record = dict(exit=observation['exit'], remote_command=self.access.READ_COMMANDS[name])
            for key in ('stdout', 'stderr'):
                record[key] = e.durable(self.access_root / (name + '.' + key),
                                        observation[key].encode(), raw=True)
            commands[name] = e.durable(self.access_root / (name + '.json'), record)
        diagnosis = dict(inputs=self.inputs, observations=self.obs, result=self.result,
                         cloud=e.durable(self.access_root / 'cloud.json', self.cloud),
                         commands=commands, control_plane_evidence={})
        self.diagnosis = e.durable(self.access_root / 'volume-diagnosis.json', diagnosis)
        # Only the receipt comparison is exercised by this fixture. The outer
        # package/grant is explicitly synthetic and unapproved, never live-admitted.
        self.review = dict(classification='INDEPENDENT_ACTUAL_VOLUME_IDENTITY_REVIEW_V1',
                           accepted=True, reviewer='/root/project_binding_review',
                           diagnosis=self.diagnosis, inputs=self.inputs,
                           verified_volume=self.result)

    def install_fixture(self, review=None):
        e = self.e
        source = self.root / 'SYNTHETIC-review-original.json'
        e.durable(source, self.review if review is None else review)
        target = self.access_root / 'independent-volume-review.json'
        receipt = e.durable(target, e.regular(source), raw=True)
        self.assertEqual(e.regular(source), e.regular(target))
        e.durable(self.root / 'volume-admission.json',
                  dict(diagnosis=self.diagnosis, independent_review=receipt,
                       verified_volume=self.result))
        return target

    def test_exclusive_install_and_full_custody_revalidation(self):
        target = self.install_fixture()
        self.access.verify_volume_admission(self.root)
        with self.assertRaises(FileExistsError):
            self.e.durable(target, b'overwrite forbidden', raw=True)

    def test_missing_receipt_rejected(self):
        target = self.install_fixture()
        target.unlink()
        with self.assertRaises(ValueError):
            self.access.verify_volume_admission(self.root)

    def test_receipt_drift_rejected(self):
        target = self.install_fixture()
        target.write_bytes(target.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'CUSTODY_DRIFT'):
            self.access.verify_volume_admission(self.root)

    def test_wrong_execution_or_grant_binding_rejected(self):
        review = deepcopy(self.review)
        review['inputs']['source_revision']['sha256'] = '0' * 64
        self.install_fixture(review)
        with self.assertRaisesRegex(ValueError, 'VOLUME_REVIEW_CUSTODY_DRIFT'):
            self.access.verify_volume_admission(self.root)

    def test_unsupported_classification_rejected(self):
        self.install_fixture({**self.review, 'classification': 'UNSUPPORTED_APPROVAL'})
        with self.assertRaisesRegex(ValueError, 'VOLUME_REVIEW_CUSTODY_DRIFT'):
            self.access.verify_volume_admission(self.root)

    def test_synthetic_review_flag_rejected(self):
        self.install_fixture({**self.review, 'synthetic': True})
        with self.assertRaisesRegex(ValueError, 'VOLUME_REVIEW_CUSTODY_DRIFT'):
            self.access.verify_volume_admission(self.root)

    def test_unaccepted_review_rejected(self):
        self.install_fixture({**self.review, 'accepted': False})
        with self.assertRaisesRegex(ValueError, 'VOLUME_REVIEW_CUSTODY_DRIFT'):
            self.access.verify_volume_admission(self.root)

    def test_wrong_reviewer_rejected(self):
        self.install_fixture({**self.review, 'reviewer': 'SELF_ASSERTED_OTHER_REVIEWER'})
        with self.assertRaisesRegex(ValueError, 'VOLUME_REVIEW_CUSTODY_DRIFT'):
            self.access.verify_volume_admission(self.root)

    def test_raw_observation_drift_rejected(self):
        self.install_fixture()
        (self.access_root / 'stat_block.stdout').write_bytes(b'0\n')
        with self.assertRaisesRegex(ValueError, 'VOLUME_COMMAND_ENTITY_DRIFT'):
            self.access.verify_volume_admission(self.root)

    def test_waiting_controller_stops_at_original_deadline(self):
        # Synthetic command returns only; the audit hook forbids real dispatch.
        journal = self.access.Journal(self.root / 'SYNTHETIC-waiting-access')
        cloud = SimpleNamespace(server=lambda: self.cloud['server'],
            volume=lambda: self.cloud['volume'],
            request=lambda *a: {'volumeAttachments': self.cloud['volumeAttachments']})
        returns = [SimpleNamespace(returncode=0, stdout=self.obs[n]['stdout'].encode(),
                                  stderr=b'') for n in self.access.READ_COMMANDS]
        with patch.object(self.access, 'private_file'), \
             patch.object(self.access.subprocess, 'run', side_effect=returns), \
             patch.object(self.access.time, 'monotonic', side_effect=[0] * 20 + [101]), \
             self.assertRaisesRegex(TimeoutError, 'INDEPENDENT_VOLUME_REVIEW_DIAGNOSTIC_DEADLINE'):
            self.access.volume_diagnosis(cloud, journal, '192.0.2.1', 100, self.inputs)
        self.assertTrue((journal.root / 'volume-diagnosis.json').is_file())
        self.assertFalse((journal.root / 'independent-volume-review.json').exists())


if __name__ == '__main__':
    unittest.main()
