"""Offline admission regressions for the versioned R1 access amendment."""
from copy import deepcopy
from pathlib import Path
import sys
import os
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from memlife.r1 import access_compat as access, contract, bridge
from memlife.r1 import protocol as p


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.flavor = dict(name='m3.quad', vcpus=4, ram=15360)
        self.limits = dict(maxTotalCores=20, totalCoresUsed=4,
                           maxTotalRAMSize=60000, totalRAMUsed=15360)
        self.cloud = SimpleNamespace(project='project', grant={
            'expected_keystone_project_id': 'project', 'expected_keystone_user_id': 'owner'})
        self.cloud.request = Mock(side_effect=self.request)
        self.server = dict(id=access.INSTANCE, name='jisheng3', tenant_id='project',
                           user_id='owner', status='ACTIVE', flavor=self.flavor)

    def request(self, service, method, path):
        self.assertEqual((service, method), ('compute', 'GET'))
        if path == '/flavors/3': return {'flavor': self.flavor}
        self.assertEqual(path, '/limits')
        return {'limits': {'absolute': self.limits}}

    def test_inline_and_resolved_exact_flavor(self):
        for flavor in (self.flavor, {'id': '3'}):
            self.server['flavor'] = flavor
            result = access.verify_flavor(self.cloud, self.server)
            self.assertEqual(result['rate_SU_per_hour'], 4)
            self.assertEqual(result['VM_4h_interval_SU_ceiling_conditional_on_cleanup'], 16)
            self.assertFalse(result['cloud_billing_hard_cap'])

    def test_wrong_resources_and_ambiguous_names(self):
        for changes in ({'name': 'm3.small'}, {'vcpus': 2}, {'ram': 16384},
                        {'ram': 6144}, {'ram': 15360.0}, {'vcpus': 4.0},
                        {'original_name': 'm3.small'}):
            self.server['flavor'] = {**self.flavor, **changes}
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, 'QUAD_ACCESS'):
                access.verify_flavor(self.cloud, self.server)

    def test_wrong_instance_owner_project(self):
        for key in ('id', 'name', 'tenant_id', 'user_id'):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'SERVER_PROJECT'):
                access.verify_flavor(self.cloud, {**self.server, key: 'other'})
        self.cloud.request.assert_not_called()

    def test_allocation_and_unshelve_quota_preserved(self):
        self.limits['totalCoresUsed'] = 21
        with self.assertRaisesRegex(ValueError, 'ALLOCATION_RESOURCE'):
            access.verify_flavor(self.cloud, self.server)
        self.limits['totalCoresUsed'] = 19
        self.server['status'] = 'SHELVED_OFFLOADED'
        with self.assertRaisesRegex(ValueError, 'UNSHELVE_QUOTA'):
            access.verify_flavor(self.cloud, self.server)
        self.limits['totalCoresUsed'] = 4
        self.limits['totalRAMUsed'] = 50000
        with self.assertRaisesRegex(ValueError, 'UNSHELVE_QUOTA'):
            access.verify_flavor(self.cloud, self.server)
        self.limits['totalRAMUsed'] = 15360
        access.verify_flavor(self.cloud, self.server)

    def test_resource_and_evidence_contract_agree(self):
        import json
        amendment = json.loads((ROOT / 'manifests/r1-access-amendment-v1.json').read_bytes())
        r = contract.RESOURCE_CONTRACT
        self.assertEqual((r['access_VM_flavor'], r['access_VM_vcpus'], r['access_VM_RAM_MiB']),
                         (amendment['flavor'], amendment['vcpus'], amendment['RAM_MiB']))
        self.assertEqual((r['local_provider_cpus'], r['local_provider_container_memory'],
                          r['local_provider_network'], r['maximum_concurrent_provider_containers']),
                         (2, '6g', 'none', 1))


@unittest.skipUnless(os.environ.get('MEMLIFE_R1_TEST_ACCEPTED_ROOT'), 'Retained source closure required')
class SourceClosureTests(unittest.TestCase):
    def test_original_and_effective_drift_fail_before_module_execution(self):
        accepted = Path(os.environ['MEMLIFE_R1_TEST_ACCEPTED_ROOT']).resolve()
        pins = p.strict(p.raw(contract.QUALIFIED_PINS))['files']
        effective = bridge.effective_sources(accepted)
        access_path = 'src/memlife/tier_c_bounded/access.py'
        self.assertEqual(effective[access_path]['original_sha256'], pins[access_path])
        self.assertNotEqual(effective[access_path]['effective_sha256'], pins[access_path])
        for name in ('volume', 'policy', 'collection'):
            record = effective['src/memlife/tier_c_bounded/' + name + '.py']
            self.assertEqual(record['original_sha256'], record['effective_sha256'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            corrupt = root / access_path
            corrupt.parent.mkdir(parents=True)
            corrupt.write_bytes(p.raw(accepted / access_path) + b'\n')
            # effective_sources examines volume first; load checks the targeted
            # access file before compiling or creating a module.
            package = root / 'fixture.json'
            p.save(package, dict(accepted_sources=pins, effective_sources=effective, synthetic=True))
            with patch.object(contract, 'ROOT', root), patch.object(contract, 'PACKAGE', package):
                with self.assertRaisesRegex(ValueError, 'QUALIFIED_MODULE_DRIFT'):
                    bridge.load('never_executed_drift_fixture', 'access')
            changed = deepcopy(effective)
            changed[access_path]['effective_sha256'] = '0' * 64
            package.write_bytes(p.canonical(dict(accepted_sources=pins, effective_sources=changed, synthetic=True)))
            with patch.object(contract, 'ROOT', accepted), patch.object(contract, 'PACKAGE', package):
                with self.assertRaisesRegex(ValueError, 'EFFECTIVE_SOURCE_DRIFT'):
                    bridge.load('never_executed_drift_fixture', 'access')
            self.assertNotIn('memlife.r1.never_executed_drift_fixture', sys.modules)


if __name__ == '__main__':
    unittest.main()
