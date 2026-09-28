"""Apply the reusable provider contract to the reference adapter."""

from memlife.adapters.reference import ReferenceMemoryAdapter
from tests.contract.provider_contract import ProviderContract


class TestReferenceProviderContract(ProviderContract):
    adapter_factory = ReferenceMemoryAdapter
