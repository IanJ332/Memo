from memlife.adapters.hindsight import HindsightMemoryAdapter
from tests.contract.provider_contract import ProviderContract
from tests.fakes.hindsight import FakeHindsightTransport


class TestHindsightProviderContract(ProviderContract):
    adapter_factory = staticmethod(
        lambda: HindsightMemoryAdapter(
            FakeHindsightTransport(),
            restart_callback=lambda: None,
            poll_interval_seconds=0.001,
        )
    )
