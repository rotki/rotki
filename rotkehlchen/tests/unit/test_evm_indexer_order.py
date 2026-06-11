from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock

import pytest

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.chain.evm.constants import GENESIS_HASH, ZERO_ADDRESS
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.chain.evm.types import EvmIndexer, string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import NoAvailableIndexers, RemoteError
from rotkehlchen.types import ChainID, SupportedBlockchain

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class DummyIndexer:
    name: str


class DummyEvmNodeInquirer(EvmNodeInquirer):
    def __init__(self) -> None:  # pylint: disable=super-init-not-called
        # skip parent init to avoid heavy wiring; set only attributes needed for _try_indexers
        self.chain_id = ChainID.ETHEREUM
        self.blockchain = SupportedBlockchain.ETHEREUM
        self.chain_name = self.chain_id.to_name()
        self.database = MagicMock()
        self._no_indexer_notified = False
        self.etherscan = cast('Any', DummyIndexer('Etherscan'))
        self.blockscout = cast('Any', DummyIndexer('Blockscout'))
        self.routescan = cast('Any', DummyIndexer('Routescan'))
        self.available_indexers = {
            EvmIndexer.ETHERSCAN: self.etherscan,
            EvmIndexer.BLOCKSCOUT: self.blockscout,
            EvmIndexer.ROUTESCAN: self.routescan,
        }

    def _get_archive_check_data(self):
        return (ZERO_ADDRESS, 0, ZERO)

    def _get_pruned_check_tx_hash(self):
        return GENESIS_HASH

    def _is_pruned(self, web3: Any):
        return False


def test_try_indexers_respects_settings_order() -> None:
    cached_settings = CachedSettings()
    previous_order = cached_settings.get_entry('evm_indexers_order')
    inquirer = DummyEvmNodeInquirer()

    calls: list[str] = []

    def query(indexer: DummyIndexer) -> str:
        calls.append(indexer.name)
        if indexer.name != 'Blockscout':
            raise RemoteError('boom')
        return 'ok'

    cached_settings.update_entry(
        'evm_indexers_order',
        {ChainID.ETHEREUM: (EvmIndexer.ROUTESCAN, EvmIndexer.ETHERSCAN, EvmIndexer.BLOCKSCOUT)},
    )
    try:
        result = inquirer._try_indexers(func=cast('Callable[[Any], str]', query))
    finally:
        cached_settings.update_entry('evm_indexers_order', previous_order)

    assert result == 'ok'
    assert calls == ['Routescan', 'Etherscan', 'Blockscout']


def test_try_indexers_custom_override() -> None:
    cached_settings = CachedSettings()
    previous_order = cached_settings.get_entry('evm_indexers_order')
    inquirer = DummyEvmNodeInquirer()
    cached_settings.update_entry(
        'evm_indexers_order',
        {ChainID.ETHEREUM: (EvmIndexer.ROUTESCAN, EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN)},
    )
    calls: list[str] = []

    def query(indexer: DummyIndexer) -> str:
        calls.append(indexer.name)
        if indexer.name != 'Blockscout':
            raise RemoteError('boom')
        return 'ok'

    indexer_setting = CachedSettings().evm_indexers_order_override_var.set((
        EvmIndexer.ETHERSCAN,
        EvmIndexer.ROUTESCAN,
        EvmIndexer.BLOCKSCOUT,
    ))

    try:
        result = inquirer._try_indexers(func=cast('Callable[[Any], str]', query))
    finally:
        cached_settings.update_entry('evm_indexers_order', previous_order)

    CachedSettings().evm_indexers_order_override_var.reset(indexer_setting)
    assert result == 'ok'
    assert calls == ['Etherscan', 'Routescan', 'Blockscout']


def test_try_indexers_custom_override_subset() -> None:
    cached_settings = CachedSettings()
    previous_order = cached_settings.get_entry('evm_indexers_order')
    inquirer = DummyEvmNodeInquirer()
    cached_settings.update_entry(
        'evm_indexers_order',
        {ChainID.ETHEREUM: (EvmIndexer.ROUTESCAN, EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN)},
    )
    calls: list[str] = []

    def query(indexer: DummyIndexer) -> str:
        calls.append(indexer.name)
        if indexer.name != 'Routescan':
            raise RemoteError('boom')
        return 'ok'

    indexer_setting = CachedSettings().evm_indexers_order_override_var.set((
        EvmIndexer.ETHERSCAN,
        EvmIndexer.ROUTESCAN,
    ))

    try:
        result = inquirer._try_indexers(func=cast('Callable[[Any], str]', query))
    finally:
        cached_settings.update_entry('evm_indexers_order', previous_order)

    CachedSettings().evm_indexers_order_override_var.reset(indexer_setting)
    assert result == 'ok'
    assert calls == ['Etherscan', 'Routescan']


def test_try_indexers_sends_ws_notification_when_no_indexers() -> None:
    """Test that _try_indexers sends a WS notification only once when no indexers are available."""
    inquirer = DummyEvmNodeInquirer()
    inquirer.available_indexers = {}

    for _ in range(3):
        with pytest.raises(NoAvailableIndexers):
            inquirer._try_indexers(func=lambda _: 'ok')

    inquirer.database.msg_aggregator.add_message.assert_called_once_with(  # type: ignore
        message_type=WSMessageType.NO_AVAILABLE_INDEXERS,
        data={'chain': SupportedBlockchain.ETHEREUM.value},
    )


def test_call_contract_indexers_forwards_block_identifier() -> None:
    """Regression test for historical eth_call via indexers executing at the latest block.

    _call_contract used to drop block_identifier when falling back to the indexers, so
    historical contract queries silently returned state from the latest block instead.
    """
    inquirer = DummyEvmNodeInquirer()
    seen_kwargs: dict[str, Any] = {}

    def eth_call(**kwargs: Any) -> str:
        seen_kwargs.update(kwargs)
        return '0x' + '1'.zfill(64)

    for indexer in (inquirer.etherscan, inquirer.blockscout, inquirer.routescan):
        indexer.eth_call = eth_call  # type: ignore[assignment,method-assign]

    assert inquirer._call_contract(
        web3=None,
        contract_address=string_to_evm_address('0x6B175474E89094C44Da98b954EedeAC495271d0F'),
        abi=[{'inputs': [], 'name': 'totalSupply', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}],  # noqa: E501
        method_name='totalSupply',
        block_identifier=10000000,
    ) == 1
    assert seen_kwargs['block_identifier'] == 10000000
