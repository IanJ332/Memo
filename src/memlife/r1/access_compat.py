"""R1 m3.quad access amendment v1; original Tier C source stays immutable.

Only flavor admission and its conditional compute estimate change. Cloud
identity, allocation, lifecycle, volume, forwarding and custody checks remain
in the hash-pinned Tier C module. This function additionally binds the server
identity so direct callers cannot admit another instance.
"""
from .protocol import need

INSTANCE = '5baeeae7-4c29-4903-89fe-2e9df0a8eced'


def verify_flavor(cloud, server):
    need(server['id'] == INSTANCE and server['name'] == 'jisheng3'
         and server['tenant_id'] == cloud.project == cloud.grant['expected_keystone_project_id']
         and server['user_id'] == cloud.grant['expected_keystone_user_id'],
         'EXACT_SERVER_PROJECT_IDENTITY')
    f = server['flavor']
    if 'id' in f:
        f = cloud.request('compute', 'GET', '/flavors/' + f['id'])['flavor']
    names = [f[k] for k in ('name', 'original_name') if k in f]
    need(names and all(n == 'm3.quad' for n in names)
         and type(f['vcpus']) is int and f['vcpus'] == 4
         and type(f['ram']) is int and f['ram'] == 15360,
         'EXACT_APPROVED_R1_QUAD_ACCESS_VM_ONLY')
    limits = cloud.request('compute', 'GET', '/limits')['limits']['absolute']
    need(limits['maxTotalCores'] >= limits['totalCoresUsed']
         and limits['maxTotalRAMSize'] >= limits['totalRAMUsed'],
         'CURRENT_ALLOCATION_RESOURCE_LIMITS')
    if server['status'] == 'SHELVED_OFFLOADED':
        need(limits['maxTotalCores'] - limits['totalCoresUsed'] >= f['vcpus']
             and limits['maxTotalRAMSize'] - limits['totalRAMUsed'] >= f['ram'],
             'INSUFFICIENT_UNSHELVE_QUOTA_NO_MUTATION')
    return {'flavor': f, 'limits': limits, 'rate_SU_per_hour': 4,
            'VM_4h_interval_SU_ceiling_conditional_on_cleanup': 16,
            'cloud_billing_hard_cap': False}
