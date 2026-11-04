from contextlib import ExitStack, nullcontext
from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock, call, patch

import pytest
from web3 import HTTPProvider, Web3

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.chain.ethereum.constants import EVM_INDEXERS_NODE_NAME
from rotkehlchen.chain.evm.constants import GENESIS_HASH, ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.chain.evm.transactions import RangeQueryOutcome
from rotkehlchen.chain.evm.types import EvmIndexer, NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.chain.mixins.rpc_nodes import EVMRPCMixin, RPCNode
from rotkehlchen.chain.optimism.constants import OP_BEDROCK_BLOCK, OP_BEDROCK_UPGRADE
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import (
    BlockchainQueryError,
    BlockscoutIncompleteResponse,
    ChainNotSupported,
    ContractReverted,
    IndexerRangeNotCovered,
    NoAvailableIndexers,
    RemoteError,
    RequestTooLargeError,
)
from rotkehlchen.externalapis.blockscout import Blockscout
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import SUPPORTED_CHAIN_IDS, ChainID, SupportedBlockchain, Timestamp

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.chain.optimism.transactions import OptimismTransactions


@dataclass
class DummyIndexer:
    name: str
    has_paid_api_key: bool = False
    missing_api_key: bool = True

    def needs_api_key_for_chain(self, chain_id: ChainID) -> bool:
        return self.missing_api_key


class DummyEvmNodeInquirer(EvmNodeInquirer):
    def __init__(self, missing_blockscout_key: bool = True) -> None:  # pylint: disable=super-init-not-called
        # Skip chain/API setup but retain real RPC health bookkeeping.
        EVMRPCMixin.__init__(self)
        self._multicall_failed_length = {}
        self.chain_id = ChainID.ETHEREUM
        self.blockchain = SupportedBlockchain.ETHEREUM
        self.chain_name = self.chain_id.to_name()
        self.database = MagicMock()
        self._notified_indexer_reasons: set[str | None] = set()
        self._etherscan_refused_chain = False
        self.etherscan = cast('Any', DummyIndexer('Etherscan'))
        self.blockscout = cast('Any', DummyIndexer('Blockscout', missing_api_key=missing_blockscout_key))  # noqa: E501
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


def test_try_indexers_notifies_blockscout_key_when_etherscan_refuses_chain() -> None:
    """A failed keyless Blockscout request offers its free key before a paid Etherscan key."""
    inquirer = DummyEvmNodeInquirer()
    inquirer.chain_id = ChainID.BASE
    inquirer.blockchain = SupportedBlockchain.BASE

    def query(indexer: Any) -> str:
        if indexer.name == 'Etherscan':
            raise ChainNotSupported('Free API access is not supported for this chain')
        if indexer.name == 'Routescan':
            raise ChainNotSupported('Routescan does not support BASE')
        raise RemoteError('Blockscout has no API key configured')

    for _ in range(3):
        with pytest.raises(RemoteError, match='Failed to query any indexer'):
            inquirer._try_indexers(func=query)

    assert EvmIndexer.ETHERSCAN not in inquirer.available_indexers
    inquirer.database.msg_aggregator.add_message.assert_called_once_with(  # type: ignore
        message_type=WSMessageType.NO_AVAILABLE_INDEXERS,
        data={
            'chain': SupportedBlockchain.BASE.value,
            'reason': 'blockscout_or_paid_etherscan_key_required',
        },
    )


@pytest.mark.parametrize(('custom_order', 'missing_blockscout_key'), [
    ((EvmIndexer.ETHERSCAN,), True),  # blockscout is not used, so its key would not help
    (None, False),  # blockscout already has a key, so it failed for another reason
])
def test_try_indexers_notifies_paid_key_when_blockscout_key_would_not_help(
        custom_order: tuple[EvmIndexer, ...] | None,
        missing_blockscout_key: bool,
) -> None:
    """Only offer a Blockscout key when Blockscout is in the order and has no key yet."""
    inquirer = DummyEvmNodeInquirer()
    inquirer.chain_id = ChainID.BASE
    inquirer.blockchain = SupportedBlockchain.BASE
    cast('Any', inquirer.blockscout).missing_api_key = missing_blockscout_key

    def query(indexer: Any) -> str:
        if indexer.name == 'Etherscan':
            raise ChainNotSupported('Free API access is not supported for this chain')
        raise RemoteError('Blockscout is down')

    token = CachedSettings.evm_indexers_order_override_var.set(custom_order)
    try:
        with pytest.raises(RemoteError, match='Failed to query any indexer'):
            inquirer._try_indexers(func=query)
    finally:
        CachedSettings.evm_indexers_order_override_var.reset(token)

    inquirer.database.msg_aggregator.add_message.assert_called_once_with(  # type: ignore
        message_type=WSMessageType.NO_AVAILABLE_INDEXERS,
        data={'chain': SupportedBlockchain.BASE.value, 'reason': 'etherscan_paid_key_required'},
    )


def test_try_indexers_skips_paid_key_notice_for_uncovered_range() -> None:
    """A Blockscout pre-Bedrock skip does not imply that Optimism needs a paid key."""
    inquirer = DummyEvmNodeInquirer()
    inquirer.chain_id = ChainID.OPTIMISM
    inquirer.blockchain = SupportedBlockchain.OPTIMISM

    def query(indexer: DummyIndexer) -> str:
        if indexer.name == 'Etherscan':
            raise ChainNotSupported('Free API access is not supported for this chain')
        if indexer.name == 'Blockscout':
            raise IndexerRangeNotCovered('pre-Bedrock internal transactions unavailable')
        raise RemoteError('Routescan rate limited')

    with pytest.raises(RemoteError, match='Failed to query any indexer'):
        inquirer._try_indexers(func=cast('Callable[[Any], str]', query))

    inquirer.database.msg_aggregator.add_message.assert_not_called()  # type: ignore


def test_try_indexers_notifies_paid_key_needed_when_none_remain() -> None:
    """A paid-key notice is sent when Etherscan was the last configured indexer."""
    inquirer = DummyEvmNodeInquirer()
    inquirer.chain_id = ChainID.BASE
    inquirer.blockchain = SupportedBlockchain.BASE
    inquirer.available_indexers = {EvmIndexer.ETHERSCAN: inquirer.etherscan}

    with pytest.raises(RemoteError, match='Failed to query any indexer'):
        inquirer._try_indexers(func=MagicMock(side_effect=ChainNotSupported(
            'Free API access is not supported for this chain',
        )))

    inquirer.database.msg_aggregator.add_message.assert_called_once_with(  # type: ignore
        message_type=WSMessageType.NO_AVAILABLE_INDEXERS,
        data={'chain': SupportedBlockchain.BASE.value, 'reason': 'etherscan_paid_key_required'},
    )


@pytest.mark.parametrize('chain_id', [ChainID.OPTIMISM, ChainID.GNOSIS])
@pytest.mark.parametrize('etherscan_first', [False, True])
@pytest.mark.parametrize('fallback_error', [ChainNotSupported, RemoteError, None])
def test_incomplete_blockscout_response_notification(
        chain_id: SUPPORTED_CHAIN_IDS,
        etherscan_first: bool,
        fallback_error: type[RemoteError] | None,
) -> None:
    """Preserve Blockscout's incomplete response through iterator fallback, in either order."""
    fallback_succeeds = fallback_error is None
    inquirer = DummyEvmNodeInquirer(missing_blockscout_key=False)
    inquirer.chain_id = chain_id
    inquirer.blockchain = chain_id.to_blockchain()  # type: ignore[assignment]
    blockscout = Blockscout(
        database=inquirer.database,
        msg_aggregator=inquirer.database.msg_aggregator,
    )
    inquirer.available_indexers = {
        EvmIndexer.ETHERSCAN: inquirer.etherscan,
        EvmIndexer.BLOCKSCOUT: blockscout,
    }
    order = (EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN)
    token = CachedSettings.evm_indexers_order_override_var.set(order[::-1] if etherscan_first else order)  # noqa: E501
    try:
        with (
            patch.object(blockscout, '_get_api_key_for_chain', return_value=None),
            patch.object(blockscout, '_get_url', return_value='https://example.com/api'),
            patch.object(blockscout, '_query_and_process', return_value={
                'status': '2',
                'message': 'Some internal transactions within this block range have not yet been processed',  # noqa: E501
                'result': [],
            }),
            patch.object(
                inquirer.etherscan,
                'get_transactions',
                create=True,
                return_value=iter([[]]),
                side_effect=fallback_error('Etherscan query failed') if fallback_error is not None else None,  # noqa: E501
            ),
        ):
            for _ in range(1 if fallback_succeeds else 3):
                query = inquirer._try_indexers_iterable(func=lambda indexer: indexer.get_transactions(  # noqa: E501
                    chain_id=chain_id,
                    account=ZERO_ADDRESS,
                    action='txlistinternal',
                    period_or_hash=TimestampOrBlockRange(
                        range_type='blocks',
                        from_value=OP_BEDROCK_BLOCK,
                        to_value=OP_BEDROCK_BLOCK + 1,
                    ),
                ))
                if fallback_succeeds:
                    assert list(query) == [[]]
                else:
                    with pytest.raises(RemoteError, match='Failed to query any indexer'):
                        list(query)
    finally:
        CachedSettings.evm_indexers_order_override_var.reset(token)

    if fallback_error != ChainNotSupported:
        inquirer.database.msg_aggregator.add_message.assert_not_called()  # type: ignore
    else:
        assert EvmIndexer.BLOCKSCOUT in inquirer.available_indexers
        inquirer.database.msg_aggregator.add_message.assert_called_once_with(  # type: ignore
            message_type=WSMessageType.NO_AVAILABLE_INDEXERS,
            data={'chain': inquirer.blockchain.value, 'reason': 'blockscout_incomplete_response'},
        )


def test_incomplete_blockscout_context_does_not_leak_into_next_query() -> None:
    """An incomplete response followed by successful fallback does not taint later failures."""
    inquirer = DummyEvmNodeInquirer(missing_blockscout_key=False)
    token = CachedSettings.evm_indexers_order_override_var.set((
        EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN, EvmIndexer.ROUTESCAN,
    ))
    try:
        assert inquirer._try_indexers(func=MagicMock(side_effect=[
            BlockscoutIncompleteResponse('Blockscout is missing data'),
            ChainNotSupported('Free API access is not supported for this chain'),
            'ok',
        ])) == 'ok'
        inquirer.database.msg_aggregator.add_message.assert_not_called()  # type: ignore

        with pytest.raises(RemoteError, match='Failed to query any indexer'):
            inquirer._try_indexers(func=MagicMock(side_effect=RemoteError('down')))
    finally:
        CachedSettings.evm_indexers_order_override_var.reset(token)

    inquirer.database.msg_aggregator.add_message.assert_called_once_with(  # type: ignore
        message_type=WSMessageType.NO_AVAILABLE_INDEXERS,
        data={'chain': inquirer.blockchain.value, 'reason': 'etherscan_paid_key_required'},
    )


@pytest.mark.parametrize('first_etherscan_error', [ChainNotSupported, RemoteError])
def test_incomplete_blockscout_response_does_not_suppress_later_key_notice(
        first_etherscan_error: type[RemoteError],
) -> None:
    """A temporary failure cannot silence a later missing-key notice for the same chain."""
    inquirer = DummyEvmNodeInquirer(missing_blockscout_key=False)
    inquirer.chain_id = ChainID.BASE
    inquirer.blockchain = SupportedBlockchain.BASE
    expected_messages = []
    token = CachedSettings.evm_indexers_order_override_var.set((
        EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN,
    ))
    try:
        with pytest.raises(RemoteError, match='Failed to query any indexer'):
            inquirer._try_indexers(func=MagicMock(side_effect=[
                BlockscoutIncompleteResponse('Blockscout is missing data'),
                first_etherscan_error('Etherscan query failed'),
            ]))

        if first_etherscan_error == ChainNotSupported:
            expected_messages.append(call(
                message_type=WSMessageType.NO_AVAILABLE_INDEXERS,
                data={'chain': SupportedBlockchain.BASE.value, 'reason': 'blockscout_incomplete_response'},  # noqa: E501
            ))
        assert inquirer.database.msg_aggregator.add_message.call_args_list == expected_messages  # type: ignore

        with patch.object(inquirer.blockscout, 'needs_api_key_for_chain', return_value=True):
            for _ in range(3):
                with pytest.raises(RemoteError, match='Failed to query any indexer'):
                    inquirer._try_indexers(func=MagicMock(side_effect=[
                        RemoteError('Blockscout has no API key configured'),
                        ChainNotSupported('Free API access is not supported for this chain'),
                    ]))
    finally:
        CachedSettings.evm_indexers_order_override_var.reset(token)

    expected_messages.append(call(
        message_type=WSMessageType.NO_AVAILABLE_INDEXERS,
        data={'chain': SupportedBlockchain.BASE.value, 'reason': 'blockscout_or_paid_etherscan_key_required'},  # noqa: E501
    ))
    assert inquirer.database.msg_aggregator.add_message.call_args_list == expected_messages  # type: ignore


def test_incomplete_blockscout_response_preserves_uncovered_range_exemption() -> None:
    """An incomplete response must not bypass another indexer's uncovered-range exemption."""
    inquirer = DummyEvmNodeInquirer()
    token = CachedSettings.evm_indexers_order_override_var.set((
        EvmIndexer.BLOCKSCOUT, EvmIndexer.ROUTESCAN, EvmIndexer.ETHERSCAN,
    ))
    try:
        with pytest.raises(RemoteError, match='Failed to query any indexer'):
            inquirer._try_indexers(func=MagicMock(side_effect=[
                BlockscoutIncompleteResponse('Blockscout is missing data'),
                IndexerRangeNotCovered('Requested range is not covered'),
                ChainNotSupported('Free API access is not supported for this chain'),
            ]))
    finally:
        CachedSettings.evm_indexers_order_override_var.reset(token)

    inquirer.database.msg_aggregator.add_message.assert_not_called()  # type: ignore


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
    token = CachedSettings.evm_indexers_order_override_var.set((
        EvmIndexer.BLOCKSCOUT,
        EvmIndexer.ROUTESCAN,
        EvmIndexer.ETHERSCAN,
    ))
    try:
        assert [name for name, _ in inquirer._get_indexers_in_order()] == [
            EvmIndexer.BLOCKSCOUT,
            EvmIndexer.ROUTESCAN,
            EvmIndexer.ETHERSCAN,
        ]
    finally:
        CachedSettings.evm_indexers_order_override_var.reset(token)


def test_robinhood_uses_etherscan_before_blockscout() -> None:
    inquirer = DummyEvmNodeInquirer()
    inquirer.chain_id = ChainID.ROBINHOOD
    inquirer.blockchain = SupportedBlockchain.ROBINHOOD

    assert [name for name, _ in inquirer._get_indexers_in_order()] == [
        EvmIndexer.ETHERSCAN,
        EvmIndexer.BLOCKSCOUT,
    ]


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


def test_cached_incomplete_blockscout_range_still_fails_the_sync(
        optimism_transactions: OptimismTransactions,
) -> None:
    """A range skipped from blockscout's incomplete range cache fails like a real response.

    The next sync asks again from the same start block, since the range was not recorded, so
    it contains the failed range and blockscout is not asked. The other indexers must still be
    tried, the range must stay unrecorded, and the sync must still fail so it is retried.
    """
    inquirer = optimism_transactions.evm_inquirer
    location_string = f'{inquirer.blockchain.to_range_prefix("internaltxs")}_{(address := make_evm_address())}'  # noqa: E501
    other_indexers = [x for x in inquirer.available_indexers if x != EvmIndexer.BLOCKSCOUT]
    token = CachedSettings.evm_indexers_order_override_var.set((EvmIndexer.BLOCKSCOUT, *other_indexers))  # noqa: E501
    try:
        with ExitStack() as stack:
            request_mock = stack.enter_context(patch.object(
                inquirer.blockscout.session,
                'request',
                return_value=MockResponse(
                    HTTPStatus.OK,
                    '{"message": "Some internal transactions within this block range have not yet been processed","result": [],"status": "2"}',  # noqa: E501
                ),
            ))
            fallback_mocks = [stack.enter_context(patch.object(
                inquirer.available_indexers[indexer],
                'get_transactions',
                side_effect=RemoteError('fallback indexer failed'),
            )) for indexer in other_indexers]
            stack.enter_context(patch.object(inquirer, '_resolve_timestamp_range', side_effect=[
                (OP_BEDROCK_BLOCK + 100, OP_BEDROCK_BLOCK + 200, frozenset()),
                (OP_BEDROCK_BLOCK + 100, OP_BEDROCK_BLOCK + 300, frozenset()),
            ]))
            for sync_end_ts in (OP_BEDROCK_UPGRADE + 100, OP_BEDROCK_UPGRADE + 200):
                assert optimism_transactions._get_internal_transactions_for_ranges(
                    address=address,
                    start_ts=Timestamp(OP_BEDROCK_UPGRADE),
                    end_ts=Timestamp(sync_end_ts),
                ) is RangeQueryOutcome.FAILED
    finally:
        CachedSettings.evm_indexers_order_override_var.reset(token)

    assert request_mock.call_count == 1  # the second sync was skipped from the cache
    assert len(fallback_mocks) != 0
    assert all(x.call_count == 2 for x in fallback_mocks)
    with optimism_transactions.database.conn.read_ctx() as cursor:
        assert optimism_transactions.database.get_used_query_range(cursor, location_string) is None


@pytest.mark.parametrize(('node_error', 'expected'), [
    # eth_call errors as returned by real mainnet nodes (USDC/WETH calls), run through web3
    ({'code': 3, 'message': 'execution reverted', 'data': '0x'}, ContractReverted),  # publicnode
    ({'code': 3, 'message': 'execution reverted'}, ContractReverted),  # dRPC/Tenderly, no data
    ({
        'code': 3,
        'message': 'execution reverted: ERC20: transfer amount exceeds balance',
        'data': '0x08c379a00000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000002645524332303a207472616e7366657220616d6f756e7420657863656564732062616c616e63650000000000000000000000000000000000000000000000000000',  # noqa: E501
    }, ContractReverted),
    ({'code': 3, 'message': 'execution reverted', 'data': None}, ContractReverted),
    ({'code': 3, 'message': 'execution reverted', 'data': '0x82b42900'}, ContractReverted),
    ({
        'code': 3,
        'message': 'execution reverted',
        'data': '0x4e487b710000000000000000000000000000000000000000000000000000000000000011',
    }, ContractReverted),
    ({
        'code': -32005,
        'message': 'project ID request rate exceeded',
        'data': {'see': '...', 'current_rps': 13.3, 'allowed_rps': 10.0, 'backoff_seconds': 30.0},
    }, BlockchainQueryError),
    ({'code': -32000, 'message': 'header not found', 'data': {'x': 1}}, BlockchainQueryError),
    ({
        'code': -32000,
        'message': 'missing trie node abc',
        'data': 'missing trie node 0xabcdef',
    }, BlockchainQueryError),
    ({
        'code': -32000,
        'message': 'missing trie node abc',
        'data': 'execution reverted: missing trie node',
    }, BlockchainQueryError),
    ({'code': 3, 'message': 'out of gas', 'data': '0x'}, BlockchainQueryError),
    ({'code': 3, 'message': 'execution reverted: out of gas', 'data': '0x'}, BlockchainQueryError),
    ({'code': -32003, 'message': 'out of gas: gas required exceeds: 30000'}, BlockchainQueryError),
    ({'code': -32603, 'message': 'Internal error'}, BlockchainQueryError),  # cloudflare
])
def test_call_contract_only_flags_real_reverts(node_error: dict, expected: type) -> None:
    """Only a revert is a ContractReverted. Any other node error must stay generic so that
    failover still happens. The errors go through web3's own parsing, as with a real node.
    """
    def make_request(method: str, params: Any) -> dict[str, Any]:
        if method == 'eth_chainId':  # web3 asks for it before eth_call
            return {'jsonrpc': '2.0', 'id': 1, 'result': '0x1'}
        return {'jsonrpc': '2.0', 'id': 1, 'error': node_error}

    web3 = Web3(HTTPProvider('http://localhost:1'))
    with patch.object(HTTPProvider, 'make_request', side_effect=make_request), pytest.raises(expected):  # noqa: E501
        DummyEvmNodeInquirer()._call_contract(
            web3=web3,
            contract_address=make_evm_address(),
            abi=[{'inputs': [], 'name': 'totalSupply', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}],  # noqa: E501
            method_name='totalSupply',
        )


@pytest.mark.parametrize(('outcomes', 'expectation', 'failures', 'hits', 'alias'), [
    # Two distinct endpoints confirm a revert without penalizing the nodes.
    ([ContractReverted('r')] * 5, pytest.raises(ContractReverted), 0, 2, False),
    # A single revert is not trusted, so a later node can still answer.
    ([ContractReverted('r'), 42, 43], nullcontext(), 0, 2, False),
    # Preserve an unconfirmed revert instead of raising the generic error.
    ([ContractReverted('r'), RemoteError('down')], pytest.raises(ContractReverted), 1, 2, False),
    # Two URL aliases of one endpoint do not independently confirm a revert.
    ([ContractReverted('r')] * 2 + [42], nullcontext(), 0, 3, True),
    # Known gas-limit errors retain priority and allow a later node to answer.
    ([RemoteError('out of gas')] + [ContractReverted('r')] * 2,
     pytest.raises(RequestTooLargeError), 0, 3, False),
    ([RequestTooLargeError('large')] + [ContractReverted('r')] * 2,
     pytest.raises(RequestTooLargeError), 0, 3, False),
    ([RemoteError('out of gas')] + [ContractReverted('r')] * 2 + [42],
     nullcontext(), 0, 4, False),
])
def test_query_reverts(
        outcomes: list[Any],
        expectation: Any,
        failures: int,
        hits: int,
        alias: bool,
) -> None:
    """A revert is deterministic, so _query stops after the second node confirms it instead of
    walking every node and the indexers. Each fake node raises or returns its outcome in turn.
    """
    inquirer = DummyEvmNodeInquirer()
    nodes = [
        NodeName(
            name=f'node-{idx}',
            endpoint=f'http://node-{idx}.invalid',
            owned=False,
            blockchain=SupportedBlockchain.ETHEREUM,
        ) for idx in range(len(outcomes))
    ]
    if alias:
        nodes[1] = nodes[1]._replace(endpoint=f'{nodes[0].endpoint}/')
    inquirer.rpc_mapping = {
        node: RPCNode(MagicMock(), is_pruned=False, is_archive=True) for node in nodes
    }
    hit: list[int] = []

    def method(web3: Any) -> Any:
        outcome = outcomes[len(hit)]
        hit.append(len(hit))
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    with expectation:
        assert inquirer._query(
            method=method,
            call_order=[WeightedNode(node, True, ONE) for node in nodes],
        ) == 42

    assert hit == list(range(hits))
    assert sum(
        state.consecutive_failures
        for node in nodes
        if (state := inquirer.get_runtime_state(node)) is not None
    ) == failures


@pytest.mark.parametrize(('node_error', 'error_kind'), [
    ({
        'code': -32005,
        'message': 'project ID request rate exceeded',
        'data': {'current_rps': 13.3, 'allowed_rps': 10.0, 'backoff_seconds': 30.0},
    }, 'rate_limited'),
    ({'code': -32000, 'message': 'header not found', 'data': {'x': 1}}, 'failure'),
    ({
        'code': -32000,
        'message': 'missing trie node abc',
        'data': 'missing trie node 0xabcdef',
    }, 'failure'),
])
@pytest.mark.parametrize('use_indexer', [False, True])
def test_call_contract_node_errors_fail_over(
        node_error: dict[str, Any],
        error_kind: str,
        use_indexer: bool,
) -> None:
    """Provider errors must not confirm a revert, and must update node health before failover."""
    inquirer = DummyEvmNodeInquirer()
    nodes = [
        NodeName(
            name=f'node-{idx}',
            endpoint=f'http://node-{idx}.invalid',
            owned=False,
            blockchain=SupportedBlockchain.ETHEREUM,
        ) for idx in range(3)
    ]
    if use_indexer:
        nodes[-1] = NodeName(
            name=EVM_INDEXERS_NODE_NAME,
            endpoint='',
            owned=False,
            blockchain=SupportedBlockchain.ETHEREUM,
        )
    inquirer.rpc_mapping = {
        node: RPCNode(Web3(HTTPProvider(node.endpoint)), is_pruned=False, is_archive=True)
        for node in nodes if node.name != EVM_INDEXERS_NODE_NAME
    }
    queried: list[str] = []

    def make_request(provider: HTTPProvider, method: str, params: Any) -> dict[str, Any]:
        if method == 'eth_chainId':
            return {'jsonrpc': '2.0', 'id': 1, 'result': '0x1'}
        assert method == 'eth_call'
        queried.append(str(provider.endpoint_uri))
        if provider.endpoint_uri in (nodes[0].endpoint, nodes[1].endpoint):
            return {'jsonrpc': '2.0', 'id': 1, 'error': node_error}
        return {'jsonrpc': '2.0', 'id': 1, 'result': f'0x{42:064x}'}

    with (
        patch.object(HTTPProvider, 'make_request', make_request),
        patch.object(inquirer, '_call_contract_indexers', return_value=42) as indexer_call,
    ):
        assert inquirer.call_contract(
            # A random address containing '429' would be misread as a rate-limit error.
            contract_address=string_to_evm_address('0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'),
            abi=[{'inputs': [], 'name': 'totalSupply', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}],  # noqa: E501
            method_name='totalSupply',
            call_order=[WeightedNode(node, True, ONE) for node in nodes],
        ) == 42

    assert queried == [node.endpoint for node in nodes if node.name != EVM_INDEXERS_NODE_NAME]
    assert indexer_call.call_count == int(use_indexer)
    for node in nodes[:2]:
        assert (state := inquirer.get_runtime_state(node)) is not None
        assert state.last_error_kind == error_kind
        assert state.consecutive_failures == 1
        assert inquirer.is_node_in_cooldown(node) is (error_kind == 'rate_limited')


@pytest.mark.parametrize(('node_errors', 'queried_sizes', 'indexer_calls'), [
    # Gas limit errors that web3 reports as reverts must still shrink the multicall chunks.
    ([{'code': 3, 'message': 'execution reverted: out of gas', 'data': '0x'}] * 3, [5, 5, 5, 3, 2], 0),  # noqa: E501
    ([{'code': 3, 'message': 'execution reverted: exceeds block gas limit', 'data': '0x'}] * 3, [5, 5, 5, 3, 2], 0),  # noqa: E501
    ([{'code': -32000, 'message': 'out of gas', 'data': {'x': 1}}] * 3, [5, 5, 5, 3, 2], 0),
    # One node reporting the gas limit outranks the others agreeing on a revert.
    ([
        {'code': 3, 'message': 'out of gas', 'data': '0x'},
        {'code': 3, 'message': 'execution reverted', 'data': '0x'},
        {'code': 3, 'message': 'execution reverted', 'data': '0x'},
    ], [5, 5, 5, 3, 2], 0),
    ([
        {'code': 3, 'message': 'execution reverted', 'data': '0x'},
        {'code': 3, 'message': 'out of gas', 'data': '0x'},
        {'code': 3, 'message': 'execution reverted', 'data': '0x'},
    ], [5, 5, 5, 3, 2], 0),
    # A confirmed revert stops at the second node. Smaller chunks would revert just the same,
    # so only the indexers are left to try, since nodes also report out of gas sub-calls this way.
    ([{'code': 3, 'message': 'execution reverted', 'data': '0x'}] * 3, [5, 5], 1),
])
def test_multicall_chunks_on_gas_limit_but_not_on_revert(
        node_errors: list[dict[str, Any]],
        queried_sizes: list[int],
        indexer_calls: int,
) -> None:
    """Each node fails multicalls of more than 3 calls with its error and answers smaller ones.
    Runs the whole path from multicall() down to web3 parsing the node's response.
    """
    inquirer = DummyEvmNodeInquirer()
    nodes = [
        NodeName(
            name=f'node-{idx}',
            endpoint=f'http://node-{idx}.invalid',
            owned=False,
            blockchain=SupportedBlockchain.ETHEREUM,
        ) for idx in range(len(node_errors))
    ]
    inquirer.rpc_mapping = {
        node: RPCNode(Web3(HTTPProvider(node.endpoint)), is_pruned=False, is_archive=True)
        for node in nodes
    }
    inquirer.contract_multicall = EvmContract(
        address=(multicall_address := string_to_evm_address('0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696')),  # noqa: E501
        abi=[{
            'inputs': [{
                'components': [
                    {'name': 'target', 'type': 'address'},
                    {'name': 'callData', 'type': 'bytes'},
                ],
                'name': 'calls',
                'type': 'tuple[]',
            }],
            'name': 'aggregate',
            'outputs': [
                {'name': 'blockNumber', 'type': 'uint256'},
                {'name': 'returnData', 'type': 'bytes[]'},
            ],
            'stateMutability': 'nonpayable',
            'type': 'function',
        }],
    )
    errors = {node.endpoint: error for node, error in zip(nodes, node_errors, strict=True)}
    queried: list[int] = []

    def make_request(provider: HTTPProvider, method: str, params: Any) -> dict[str, Any]:
        if method == 'eth_chainId':
            return {'jsonrpc': '2.0', 'id': 1, 'result': '0x1'}
        assert method == 'eth_call'
        calls = (codec := Web3().codec).decode(
            ['(address,bytes)[]'],
            bytes.fromhex(params[0]['data'][10:]),  # skip the method selector
        )[0]
        queried.append(len(calls))
        if len(calls) > 3:
            return {'jsonrpc': '2.0', 'id': 1, 'error': errors[str(provider.endpoint_uri)]}
        # echo each call's data so that the order of the merged chunks can be checked
        encoded = codec.encode(['uint256', 'bytes[]'], [1, [call[1] for call in calls]])
        return {'jsonrpc': '2.0', 'id': 1, 'result': f'0x{encoded.hex()}'}

    expected_output = [idx.to_bytes(4) for idx in range(5)]
    with (
        patch.object(HTTPProvider, 'make_request', make_request),
        patch.object(
            inquirer,
            '_call_contract_indexers',
            return_value=(1, expected_output),
        ) as indexer_call,
    ):
        assert inquirer.multicall(
            calls=[(multicall_address, f'0x{data.hex()}') for data in expected_output],
            call_order=[WeightedNode(node, True, ONE) for node in nodes],
        ) == expected_output

    assert queried == queried_sizes
    assert indexer_call.call_count == indexer_calls
    # the failed length is what makes later big multicalls start from the smaller chunks
    assert ('nodes' in inquirer._multicall_failed_length) is (indexer_calls == 0)
