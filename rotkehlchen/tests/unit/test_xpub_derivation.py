from typing import Final

import pytest

from rotkehlchen.chain.bitcoin.hdkey import HDKey
from rotkehlchen.chain.bitcoin.xpub import XpubManager
from rotkehlchen.fval import FVal
from rotkehlchen.types import SupportedBlockchain

XPUB: Final = 'xpub6CjniigyzMWgVDHvDpgvsroPkTJeqUbrHJaLHARHmAM8zuAbCjmHpp3QhKTcnnscd6iBDrqmABCJjnpwUW42cQjtvKjaEZRcShHKEVh35Y8'  # noqa: E501


class FakeChainManager:
    """Reports transactions only for the derived indices asked for by the test"""

    def __init__(self, root: HDKey, indices_with_tx: set[int]) -> None:
        self.addresses_with_tx = {
            root.derive_child(idx).address() for idx in indices_with_tx
        }

    def have_transactions(self, accounts: list) -> dict:
        return {
            address: (address in self.addresses_with_tx, FVal('1.5')) for address in accounts
        }


class FakeChainsAggregator:

    def __init__(self, root: HDKey, indices_with_tx: set[int]) -> None:
        self.database = None
        self.chain_manager = FakeChainManager(root=root, indices_with_tx=indices_with_tx)

    def get_chain_manager(self, blockchain: SupportedBlockchain) -> FakeChainManager:
        return self.chain_manager


@pytest.mark.parametrize('start_index', [0, 5])
def test_derive_addresses_loop_fills_gaps_up_to_max_derived_index(start_index):
    """Test that all addresses without transactions up to the last derived index with a
    transaction are also returned, so that later derivation can resume from that index
    """
    root = HDKey.from_xpub(xpub=XPUB, path='m')
    indices_with_tx = {start_index + 1, start_index + 3}
    manager = XpubManager(chains_aggregator=FakeChainsAggregator(root, indices_with_tx))

    derived = manager._derive_addresses_loop(
        account_index=0,
        start_index=start_index,
        root=root,
        gap_limit=5,
        blockchain=SupportedBlockchain.BITCOIN,
    )

    assert {entry.derived_index for entry in derived} == set(range(start_index, start_index + 4))
    assert {entry.address for entry in derived} == {
        root.derive_child(idx).address() for idx in range(start_index, start_index + 4)
    }
    assert {entry.balance for entry in derived} == {FVal('1.5')}
    assert all(entry.account_index == 0 for entry in derived)
