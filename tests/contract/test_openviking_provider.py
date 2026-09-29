from memlife.adapters.base import CapabilitySupport, ProviderCapability
from memlife.adapters.openviking import OpenVikingMemoryAdapter
from tests.contract.provider_contract import assert_complete_capability_declaration
from tests.fakes.openviking import FakeOpenVikingTransport


def test_openviking_contract_declares_partial_lifecycle_truthfully() -> None:
    adapter = OpenVikingMemoryAdapter(FakeOpenVikingTransport())
    assert_complete_capability_declaration(adapter)
    assert adapter.support_for(ProviderCapability.WRITE) is CapabilitySupport.SUPPORTED
    assert adapter.support_for(ProviderCapability.QUERY) is CapabilitySupport.SUPPORTED
    assert adapter.support_for(ProviderCapability.UPDATE_OR_SUPERSEDE) is CapabilitySupport.UNSUPPORTED
