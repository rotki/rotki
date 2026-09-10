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
from rotkehlchen.errors.misc import ChainNotSupported, NoAvailableIndexers, RemoteError
from rotkehlchen.types import SUPPORTED_CHAIN_IDS, ChainID, SupportedBlockchain

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer


@dataclass
class DummyIndexer:
    name: str
    has_paid_api_key: bool = False


class DummyEvmNodeInquirer(EvmNodeInquirer):
    def __init__(self) -> None:  # pylint: disable=super-init-not-called
        # skip parent init to avoid heavy wiring; set only attributes needed for _try_indexers
        self.chain_id = ChainID.ETHEREUM
        self.blockchain = SupportedBlockchain.ETHEREUM
        self.chain_name = self.chain_id.to_name()
        self.database = MagicMock()
        self._no_indexer_notified = False
        self._etherscan_refused_chain = False
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


def test_try_indexers_notifies_paid_key_needed_when_etherscan_refuses_chain() -> None:
    """When etherscan refuses the chain for the configured key and the remaining indexers
    fail too, the user is told once that a paid etherscan key is needed."""
    inquirer = DummyEvmNodeInquirer()
    inquirer.chain_id = ChainID.BASE
    inquirer.blockchain = SupportedBlockchain.BASE

    def query(indexer: Any) -> str:
        if indexer.name == 'Etherscan':
            raise ChainNotSupported('Free API access is not supported for this chain')
        if indexer.name == 'Routescan':
            raise ChainNotSupported('Routescan does not support BASE')
        raise RemoteError('Blockscout is missing data')

    for _ in range(3):
        with pytest.raises(RemoteError, match='Failed to query any indexer'):
            inquirer._try_indexers(func=query)

    assert set(inquirer.available_indexers) == {EvmIndexer.BLOCKSCOUT}
    inquirer.database.msg_aggregator.add_message.assert_called_once_with(  # type: ignore
        message_type=WSMessageType.NO_AVAILABLE_INDEXERS,
        data={'chain': SupportedBlockchain.BASE.value, 'reason': 'etherscan_paid_key_required'},
    )


def test_try_indexers_does_not_blame_the_key_when_etherscan_was_not_refused() -> None:
    """A plain failure of every indexer is not reported as a paid key problem."""
    inquirer = DummyEvmNodeInquirer()

    def query(indexer: Any) -> str:
        raise RemoteError('down')

    with pytest.raises(RemoteError, match='Failed to query any indexer'):
        inquirer._try_indexers(func=query)

    inquirer.database.msg_aggregator.add_message.assert_not_called()  # type: ignore


@pytest.mark.parametrize(('chain_id', 'paid', 'expected_first'), [
    (ChainID.BASE, True, EvmIndexer.ETHERSCAN),
    (ChainID.BASE, False, EvmIndexer.BLOCKSCOUT),
    (ChainID.ETHEREUM, True, EvmIndexer.ETHERSCAN),
    (ChainID.ARBITRUM_ONE, True, EvmIndexer.ETHERSCAN),
])
def test_paid_etherscan_key_goes_first_on_paid_only_chains(
        chain_id: SUPPORTED_CHAIN_IDS,
        paid: bool,
        expected_first: EvmIndexer,
) -> None:
    """On chains that etherscan serves only to paid keys the default order avoids etherscan,
    but a paid key makes it the first choice. Other chains keep their default order."""
    inquirer = DummyEvmNodeInquirer()
    inquirer.chain_id = chain_id
    inquirer.blockchain = chain_id.to_blockchain()  # type: ignore[assignment]
    cast('Any', inquirer.etherscan).has_paid_api_key = paid
    assert inquirer._get_indexers_in_order()[0][0] == expected_first


def test_paid_etherscan_key_respects_a_custom_order() -> None:
    """A user who deliberately put another indexer first on such a chain keeps that order."""
    inquirer = DummyEvmNodeInquirer()
    inquirer.chain_id = ChainID.BASE
    inquirer.blockchain = SupportedBlockchain.BASE
    cast('Any', inquirer.etherscan).has_paid_api_key = True
    token = CachedSettings.evm_indexers_order_override_var.set((EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN))  # noqa: E501
    try:
        assert [name for name, _ in inquirer._get_indexers_in_order()] == [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN]  # noqa: E501
    finally:
        CachedSettings.evm_indexers_order_override_var.reset(token)


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


@pytest.mark.parametrize('include_blockscout_key', [False])
def test_gnosis_falls_back_to_etherscan_without_a_blockscout_key(
        gnosis_inquirer: GnosisInquirer,
) -> None:
    """A paid etherscan key alone must be enough to query gnosis.

    Blockscout leads the default gnosis order but its endpoints reject keyless queries, so
    without a blockscout key it has to step aside rather than make gnosis unqueryable.
    """
    assert CachedSettings().get_evm_indexers_order_for_chain(ChainID.GNOSIS) == (
        EvmIndexer.BLOCKSCOUT,
        EvmIndexer.ETHERSCAN,
    )
    queried: list[str] = []

    def track(indexer: Any) -> str:
        queried.append(indexer.name)
        return indexer._get_url(chain_id=ChainID.GNOSIS)  # raises RemoteError for keyless blockscout  # noqa: E501

    # blockscout is attempted first, bails out keyless, and etherscan serves the query
    assert 'etherscan.io' in gnosis_inquirer._try_indexers(func=track)
    assert queried == ['Blockscout', 'Etherscan']
