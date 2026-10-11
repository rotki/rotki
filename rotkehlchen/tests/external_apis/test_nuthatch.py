import json
from http import HTTPStatus
from typing import Any, cast
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.accounts import BlockchainAccountData, SingleBlockchainAccountData
from rotkehlchen.chain.ethereum.modules.eth2.structures import ValidatorDetails, ValidatorType
from rotkehlchen.chain.evm.types import (
    EvmIndexer,
    SerializableChainIndexerOrder,
    string_to_evm_address,
)
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings, ModifiableDBSettings
from rotkehlchen.errors.misc import ChainNotSupported, RemoteError
from rotkehlchen.externalapis.nuthatch import Nuthatch
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.tests.utils.factories import (
    make_ethereum_transaction,
    make_evm_address,
    make_evm_tx_hash,
)
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    ChainID,
    Eth2PubKey,
    EvmInternalTransaction,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now

ADDRESS = string_to_evm_address('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')


@pytest.fixture(name='nuthatch')
def fixture_nuthatch(database, messages_aggregator):
    return Nuthatch(database=database, msg_aggregator=messages_aggregator)


def _answer(result: Any, status: str = '1', generation: str = '7') -> MockResponse:
    body: dict[str, Any] = {'status': status, 'message': 'OK' if status == '1' else 'NOTOK', 'result': result}  # noqa: E501
    if status == '1':
        body['generation'] = generation
    return MockResponse(status_code=HTTPStatus.OK, text=json.dumps(body))


def test_nuthatch_asks_the_configured_nest(nuthatch: Nuthatch) -> None:
    assert nuthatch._get_url(chain_id=ChainID.ETHEREUM) == 'http://127.0.0.1:8288/api'
    with patch.object(nuthatch.session, 'get', return_value=_answer([])) as get:
        assert nuthatch._query(chain_id=ChainID.ETHEREUM, module='account', action='txlist', options={'address': ADDRESS}) == []  # noqa: E501

    params = get.call_args.kwargs['params']
    assert params['chainid'] == '1'
    assert 'apikey' not in params, 'a nest takes no key, and none is sent'


@pytest.mark.parametrize(('result', 'error'), [
    ('NUTHATCH_INCOMPLETE: txlist for 0xd8da is not indexed at block 0', RemoteError),
    ('NUTHATCH_UNSUPPORTED: contract/getabi is not served by this nest', RemoteError),
    ("NUTHATCH_UNSUPPORTED: chainid 10 is not this nest's chain 1", ChainNotSupported),
    ('Error! Missing Or invalid Address', RemoteError),
])
def test_nuthatch_refusals_fall_through(
        nuthatch: Nuthatch,
        result: str,
        error: type[Exception],
) -> None:
    """A nest says what it cannot answer instead of returning an empty list. Each refusal must
    raise, so rotki tries the next indexer, and a nest on another chain leaves that chain."""
    with (
        patch.object(nuthatch.session, 'get', return_value=_answer(result, status='0')),
        pytest.raises(error),
    ):
        nuthatch._query(chain_id=ChainID.ETHEREUM, module='account', action='txlist')


def test_nuthatch_pages_a_single_block_over_one_snapshot(nuthatch: Nuthatch) -> None:
    """A thousand transfers in one block fill a page. Restarting at the last block, as the other
    indexers do, would ask for the same page forever; the nest is paged by page number instead,
    with fixed bounds and the generation page 1 was cut from."""
    full = [
        {'hash': str(make_evm_tx_hash()), 'timeStamp': '1700000000', 'blockNumber': '100'}
        for _ in range(1000)
    ]
    tail = [{'hash': str(make_evm_tx_hash()), 'timeStamp': '1700000012', 'blockNumber': '101'}]
    with patch.object(nuthatch.session, 'get', side_effect=[
        _answer(full.copy()),
        _answer(full[::-1]),
        _answer(tail),
    ]) as get:
        hashes = [
            h
            for batch in nuthatch.get_token_transaction_hashes(
                chain_id=ChainID.ETHEREUM,
                account=ADDRESS,
                from_block=100,
                to_block=101,
            )
            for h in batch
        ]

    asked = [call.kwargs['params'] for call in get.call_args_list]
    assert [p['page'] for p in asked] == ['1', '2', '3']
    assert {(p['startblock'], p['endblock']) for p in asked} == {('100', '101')}
    assert 'generation' not in asked[0]
    assert [p['generation'] for p in asked[1:]] == ['7', '7']
    assert not any(k.startswith('_') for p in asked for k in p), 'paging state stays local'
    assert len(set(hashes)) == 1001


def test_nuthatch_refuses_a_repeated_page(nuthatch: Nuthatch) -> None:
    page = [
        {'hash': str(make_evm_tx_hash()), 'timeStamp': '1700000000', 'blockNumber': '100'}
        for _ in range(1000)
    ]
    with (
        patch.object(nuthatch.session, 'get', return_value=_answer(page)),
        pytest.raises(RemoteError, match='answered page 2 as an earlier one'),
    ):
        list(nuthatch.get_token_transaction_hashes(
            chain_id=ChainID.ETHEREUM,
            account=ADDRESS,
            from_block=100,
            to_block=101,
        ))


def test_nuthatch_refuses_pages_that_alternate(nuthatch: Nuthatch) -> None:
    pages = [[
        {'hash': str(make_evm_tx_hash()), 'timeStamp': '1700000000', 'blockNumber': '100'}
        for _ in range(1000)
    ] for _ in range(2)]
    with (
        patch.object(nuthatch.session, 'get', side_effect=[_answer(pages[i % 2]) for i in range(4)]),  # noqa: E501
        pytest.raises(RemoteError, match='answered page 3 as an earlier one'),
    ):
        list(nuthatch.get_token_transaction_hashes(
            chain_id=ChainID.ETHEREUM,
            account=ADDRESS,
            from_block=100,
            to_block=101,
        ))


def test_nuthatch_refusal_on_a_later_page_comes_before_any_batch(nuthatch: Nuthatch) -> None:
    """rotki settles on an indexer once it has yielded a batch, so a nest that refuses page 2
    must raise before page 1's rows are handed over, while the next indexer can still be asked."""
    page = [
        {'hash': str(make_evm_tx_hash()), 'timeStamp': str(1700000000 + i), 'blockNumber': str(100 + i)}  # noqa: E501
        for i in range(1000)
    ]
    with patch.object(nuthatch.session, 'get', side_effect=[
        _answer(page),
        _answer('NUTHATCH_INCOMPLETE: address history changed between pages', status='0'),
    ]):
        batches = nuthatch.get_token_transaction_hashes(
            chain_id=ChainID.ETHEREUM,
            account=ADDRESS,
            from_block=100,
            to_block=1100,
        )
        with pytest.raises(RemoteError, match='changed between pages'):
            next(batches)


def test_nuthatch_paging_keeps_no_state_between_queries(nuthatch: Nuthatch) -> None:
    """A query that ends on an exact full page leaves nothing behind that the same query, asked
    again, could mistake for a repeat."""
    blocks = [
        {'blockNumber': str(20000000 + i), 'timeStamp': '1717283891', 'blockReward': '1'}
        for i in range(1000)
    ]
    period = TimestampOrBlockRange(range_type='blocks', from_value=20000000, to_value=20010000)
    for _ in range(3):
        with patch.object(nuthatch.session, 'get', side_effect=[_answer(blocks), _answer([])]):
            assert len(nuthatch.get_validated_blocks(address=ADDRESS, period=period)) == 1000


def test_nuthatch_serves_produced_blocks_within_rotkis_bounds(nuthatch: Nuthatch) -> None:
    """rotki asks for produced blocks between a validator's activation and now. The nest is asked
    for that range, not from genesis, with its own action, and a relay conflict is refused."""
    block = {'blockNumber': '20000206', 'timeStamp': '1717283891', 'blockReward': '4449486205961004', 'mev': 'none'}  # noqa: E501
    period = TimestampOrBlockRange(range_type='blocks', from_value=20000000, to_value=20000299)
    with patch.object(nuthatch.session, 'get', return_value=_answer([block])) as get:
        blocks = nuthatch.get_validated_blocks(address=ADDRESS, period=period)

    assert blocks == [block]
    params = get.call_args.kwargs['params']
    assert (params['action'], params['startblock'], params['endblock']) == ('nuthatchProducedBlocks', '20000000', '20000299')  # noqa: E501
    with (
        patch.object(nuthatch.session, 'get', return_value=_answer([{**block, 'mev': 'conflict'}])),  # noqa: E501
        pytest.raises(RemoteError, match='Relays disagree about block 20000206'),
    ):
        nuthatch.get_validated_blocks(address=ADDRESS, period=period)


def test_nuthatch_produced_blocks_become_block_and_mev_events(eth2, nuthatch: Nuthatch) -> None:
    """A block the address built itself is one event; a relay-built one is the builder's block
    event and the address's MEV event; a relay that paid the block's own fee recipient adds no
    second event for the same income, but a builder's separate transfer is MEV; a block a relay
    says another validator proposed is not this one's."""
    builder = string_to_evm_address('0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97')
    with eth2.database.user_write() as write_cursor:
        DBEth2(eth2.database).add_or_update_validators(write_cursor, [ValidatorDetails(
            validator_index=7,
            public_key=Eth2PubKey('0x' + 'ab' * 48),
            validator_type=ValidatorType.DISTRIBUTING,
            withdrawal_address=ADDRESS,
            activation_timestamp=Timestamp(1600000000),
        )])
    rows = [
        {'blockNumber': '100', 'timeStamp': '1700000000', 'feeRecipient': str(ADDRESS).lower(), 'blockReward': '5', 'mevRecipient': '', 'mevReward': '', 'proposerPubkey': '', 'mev': 'none'},  # noqa: E501
        {'blockNumber': '101', 'timeStamp': '1700000012', 'feeRecipient': str(builder).lower(), 'blockReward': '9', 'mevRecipient': str(ADDRESS).lower(), 'mevReward': '1000000000000000000', 'proposerPubkey': '0x' + 'ab' * 48, 'mev': 'relay'},  # noqa: E501
        {'blockNumber': '102', 'timeStamp': '1700000024', 'feeRecipient': str(ADDRESS).lower(), 'blockReward': '7', 'mevRecipient': str(ADDRESS).lower(), 'mevReward': '8', 'proposerPubkey': '0x' + 'ab' * 48, 'mev': 'relay', 'paymentValue': ''},  # noqa: E501
        {'blockNumber': '103', 'timeStamp': '1700000036', 'feeRecipient': str(ADDRESS).lower(), 'blockReward': '7', 'mevRecipient': str(ADDRESS).lower(), 'mevReward': '9', 'proposerPubkey': '0x' + 'ab' * 48, 'mev': 'relay', 'paymentValue': '2000000000000000000'},  # noqa: E501
        {'blockNumber': '104', 'timeStamp': '1700000048', 'feeRecipient': str(builder).lower(), 'blockReward': '9', 'mevRecipient': str(ADDRESS).lower(), 'mevReward': '5', 'proposerPubkey': '0x' + 'cd' * 48, 'mev': 'relay'},  # noqa: E501
    ]
    inquirer = eth2.ethereum
    inquirer.available_indexers[EvmIndexer.NUTHATCH] = nuthatch
    cached = CachedSettings()
    order = {**cached._evm_indexers_order_per_chain, ChainID.ETHEREUM: (EvmIndexer.NUTHATCH, EvmIndexer.ETHERSCAN)}  # noqa: E501
    added: list = []
    with (
        patch.object(type(cached), '_evm_indexers_order_per_chain', order),
        patch.object(nuthatch, 'get_validated_blocks', return_value=rows),
        patch.object(inquirer, 'maybe_timestamp_to_block_range', side_effect=lambda period: period),  # noqa: E501
        patch.object(DBHistoryEvents, 'add_history_event', side_effect=lambda write_cursor, event: added.append(event)),  # noqa: E501
        patch.object(eth2, '_get_proposer_index_for_validated_block', return_value=7),
    ):
        assert eth2._get_and_store_produced_blocks_from_indexers(indices=[7], update_cache=False, only=EvmIndexer.NUTHATCH)  # noqa: E501

    got = [(
        e.is_exit_or_blocknumber,
        e.event_subtype == HistoryEventSubType.MEV_REWARD,
        e.location_label,
        str(e.amount),
    ) for e in added]
    assert got == [
        (100, False, ADDRESS, '0.000000000000000005'),
        (101, False, builder, '0.000000000000000009'),
        (101, True, ADDRESS, '1'),
        (102, False, ADDRESS, '0.000000000000000007'),
        (103, False, ADDRESS, '0.000000000000000007'),
        (103, True, ADDRESS, '2'),
    ]


def test_nuthatch_comes_first_where_the_order_puts_it(eth2, nuthatch: Nuthatch) -> None:
    """Named first in Ethereum's indexer order, the nest is asked first for account history and
    for withdrawals, and etherscan only when the nest cannot answer."""
    inquirer = eth2.ethereum
    inquirer.available_indexers[EvmIndexer.NUTHATCH] = nuthatch
    cached = CachedSettings()
    order = {**cached._evm_indexers_order_per_chain, ChainID.ETHEREUM: (EvmIndexer.NUTHATCH, EvmIndexer.ETHERSCAN)}  # noqa: E501
    period = TimestampOrBlockRange(range_type='blocks', from_value=17034870, to_value=17300000)
    with patch.object(type(cached), '_evm_indexers_order_per_chain', order):
        assert [name for name, _ in inquirer._get_indexers_in_order()] == [EvmIndexer.NUTHATCH, EvmIndexer.ETHERSCAN]  # noqa: E501
        with (
            patch.object(nuthatch, 'get_withdrawals', return_value={5}) as nest,
            patch.object(inquirer.etherscan, 'get_withdrawals', return_value={6}) as etherscan,
        ):
            assert eth2._fetch_withdrawals_from_external_sources(ADDRESS, period) == {5}
            assert etherscan.call_count == 0
            nest.side_effect = RemoteError('NUTHATCH_INCOMPLETE: not indexed')
            assert eth2._fetch_withdrawals_from_external_sources(ADDRESS, period) == {6}
            assert etherscan.call_count == 1, 'etherscan is asked once, after the nest'

    reversed_order = {**order, ChainID.ETHEREUM: (EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN, EvmIndexer.NUTHATCH)}  # noqa: E501
    with (
        patch.object(type(cached), '_evm_indexers_order_per_chain', reversed_order),
        patch.object(nuthatch, 'get_withdrawals', return_value={5}) as nest,
        patch.object(inquirer.etherscan, 'get_withdrawals', return_value={6}),
    ):
        assert eth2._fetch_withdrawals_from_external_sources(ADDRESS, period) == {6}
        assert nest.call_count == 0, 'etherscan first, as ordered'

    nest_only = {**order, ChainID.ETHEREUM: (EvmIndexer.NUTHATCH,)}
    with (
        patch.object(type(cached), '_evm_indexers_order_per_chain', nest_only),
        patch.object(nuthatch, 'get_withdrawals', side_effect=RemoteError('not indexed')),
        patch.object(inquirer.etherscan, 'get_withdrawals', return_value={6}),
    ):
        assert eth2._fetch_withdrawals_from_external_sources(ADDRESS, period) == {6}, (
            'etherscan stays the fallback for withdrawals, as it was before nests'
        )

    with (
        patch.object(nuthatch, 'get_withdrawals') as nest,
        patch.object(inquirer.etherscan, 'get_withdrawals', return_value={6}),
    ):
        assert eth2._fetch_withdrawals_from_external_sources(ADDRESS, period) == {6}
    assert nest.call_count == 0, 'a nest the order does not name is never asked'


@pytest.mark.parametrize(('nest_complete', 'has_key', 'beaconchain_asked', 'indexers_asked'), [
    (True, False, False, False),
    (False, False, False, True),
    (True, True, True, False),
    (False, True, True, False),
])
def test_produced_blocks_ask_the_nest_then_beaconchain(
        eth2,
        nuthatch: Nuthatch,
        nest_complete: bool,
        has_key: bool,
        beaconchain_asked: bool,
        indexers_asked: bool,
) -> None:
    """Named in the order, the nest is asked first. beaconcha.in still runs when it has a key, so
    what the nest could not see is found; the other indexers run only when neither answered."""
    eth2.ethereum.available_indexers[EvmIndexer.NUTHATCH] = nuthatch
    cached = CachedSettings()
    order = {**cached._evm_indexers_order_per_chain, ChainID.ETHEREUM: (EvmIndexer.NUTHATCH, EvmIndexer.ETHERSCAN)}  # noqa: E501
    calls: list[EvmIndexer | None] = []

    def indexers(indices: list[int], update_cache: bool, only: EvmIndexer | None = None) -> bool:
        calls.append(only)
        return nest_complete if only is not None else True

    beaconchain = eth2.beacon_inquirer.beaconchain
    with (
        patch.object(type(cached), '_evm_indexers_order_per_chain', order),
        patch.object(eth2, '_get_and_store_produced_blocks_from_indexers', side_effect=indexers),
        patch.object(beaconchain, 'has_api_key', return_value=has_key),
        patch.object(beaconchain, '_get_and_store_produced_blocks') as beaconchain_query,
    ):
        eth2.get_and_store_produced_blocks(indices=[7])

    assert calls[0] == EvmIndexer.NUTHATCH
    assert beaconchain_query.called is beaconchain_asked
    assert (None in calls) is indexers_asked


def _nest(watched: list[str], chain_id: int = 1, down: bool = False):
    """A nest's management API: its chain, its watched set, and every call made of it."""
    calls: list[tuple[str, str, dict | None]] = []

    def request(method: str, url: str, **kwargs: Any) -> MockResponse:
        path = url.split('127.0.0.1:8288', 1)[1]
        calls.append((method, path, kwargs.get('json')))
        if down:
            raise requests.exceptions.ConnectionError('nest is down')
        if path == '/ready':
            return MockResponse(HTTPStatus.OK, f'{{"chain_id": {chain_id}}}')
        return MockResponse(HTTPStatus.OK, json.dumps({'watched': watched}))

    return request, calls


def test_nuthatch_watch_sync_follows_rotkis_accounts(database, nuthatch: Nuthatch) -> None:
    """The nest is told to watch every account rotki tracks on its chain, and to stop watching one
    rotki removed; a nest that is down keeps the removal for the next run; a chain whose order
    does not name the nest is left alone."""
    tracked, removed, seeded = make_evm_address(), make_evm_address(), make_evm_address()
    with database.user_write() as write_cursor:
        database.add_blockchain_accounts(
            write_cursor,
            [BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=tracked)],
        )
    cached = CachedSettings()
    order = {**cached._evm_indexers_order_per_chain, ChainID.ETHEREUM: (EvmIndexer.NUTHATCH,)}
    nuthatch.queue_unwatch([removed, tracked])  # tracked was removed, then added again

    down, calls = _nest([], down=True)
    with (
        patch.object(type(cached), '_evm_indexers_order_per_chain', order),
        patch.object(nuthatch.session, 'request', side_effect=down),
        pytest.raises(RemoteError),
    ):
        nuthatch.sync_watched()

    up, calls = _nest([str(removed).lower(), str(seeded).lower(), str(tracked).lower()])
    with (
        patch.object(type(cached), '_evm_indexers_order_per_chain', order),
        patch.object(nuthatch.session, 'request', side_effect=up),
    ):
        nuthatch.sync_watched()
    with database.conn.read_ctx() as cursor:
        everyone = {str(a).lower() for a in database.get_blockchain_accounts(cursor).eth}
    watches = {c[2]['address'] for c in calls if c[:2] == ('POST', '/api/watch')}
    assert watches == everyone - {str(removed).lower(), str(seeded).lower(), str(tracked).lower()}
    assert [c[2] for c in calls if c[1] == '/api/unwatch'] == [{'address': str(removed)}], (
        "an address rotki never tracked is not rotki's to unwatch"
    )
    posts = sum(c[0] == 'POST' for c in calls)

    with (
        patch.object(type(cached), '_evm_indexers_order_per_chain', order),
        patch.object(nuthatch.session, 'request', side_effect=up),
    ):
        nuthatch.sync_watched()
    assert sum(c[0] == 'POST' for c in calls) == 2 * posts - 1, 'the removal is not sent twice'

    other, calls = _nest([], chain_id=10)
    with patch.object(nuthatch.session, 'request', side_effect=other):
        nuthatch.sync_watched()
    assert [c[1] for c in calls] == ['/ready']


def test_adding_an_account_with_the_nest_down_still_adds_it(rotkehlchen_api_server) -> None:
    """The sync is scheduled after the account is in, and a nest that is down only logs."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    address = make_evm_address()
    with patch.object(rotki, 'schedule_nuthatch_watch_sync') as schedule:
        rotki.add_single_blockchain_accounts(
            chain=SupportedBlockchain.ETHEREUM,
            account_data=[SingleBlockchainAccountData(address=address)],
        )
        assert schedule.call_count == 1
        rotki.remove_single_blockchain_accounts(
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=[address],
        )
        assert schedule.call_count == 2

    with rotki.data.db.conn.read_ctx() as cursor:
        pending = rotki.data.db.get_static_cache(cursor, DBCacheStatic.NUTHATCH_PENDING_UNWATCH)
    assert pending == f'["{address}"]'
    with patch.object(rotki.nuthatch, 'sync_watched', side_effect=RemoteError('nest is down')):
        rotki._sync_nuthatch_watched()  # logs, never raises


def test_existing_accounts_reach_a_nest_set_up_after_them(rotkehlchen_api_server) -> None:
    """Following the guide with accounts already tracked: set the nest's address, then name it in
    Ethereum's order. Each step tells the nest what to watch, so the accounts reach it without
    waiting for the next login or account change. A setting that changes neither does not."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    address = make_evm_address()
    with patch.object(rotki, 'schedule_nuthatch_watch_sync'):
        rotki.add_single_blockchain_accounts(
            chain=SupportedBlockchain.ETHEREUM,
            account_data=[SingleBlockchainAccountData(address=address)],
        )

    request, calls = _nest([])
    with (
        patch.object(rotki, 'schedule_nuthatch_watch_sync', side_effect=rotki._sync_nuthatch_watched) as schedule,  # noqa: E501
        patch.object(rotki.nuthatch.session, 'request', side_effect=request),
    ):
        assert rotki.set_settings(ModifiableDBSettings(nuthatch_api_endpoint='http://127.0.0.1:8288'))[0]
        assert schedule.call_count == 1
        assert ('POST', '/api/watch', {'address': str(address).lower()}) not in calls, (
            'not yet in the order, so not yet told'
        )
        order = SerializableChainIndexerOrder(
            order={ChainID.ETHEREUM: [EvmIndexer.NUTHATCH, EvmIndexer.ETHERSCAN]},
        )
        assert rotki.set_settings(ModifiableDBSettings(evm_indexers_order=order))[0]
        assert schedule.call_count == 2
        assert ('POST', '/api/watch', {'address': str(address).lower()}) in calls
        assert rotki.set_settings(ModifiableDBSettings(btc_derivation_gap_limit=30))[0]
        assert schedule.call_count == 2


def _internal(parent: str, trace_index: int, trace_id: str, is_error: str = '0', value: str = '7') -> dict[str, Any]:  # noqa: E501
    return {
        'hash': parent, 'blockNumber': '100', 'timeStamp': '1700000000', 'from': str(ADDRESS),
        'to': '0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97', 'value': value, 'gas': '2300',
        'gasUsed': '0', 'isError': is_error, 'traceId': trace_id, 'nuthatchTraceIndex': str(trace_index),  # noqa: E501
        'type': 'call',
    }


def test_nuthatch_internals_drop_reverted_frames_and_keep_same_depth_siblings(
        database,
        nuthatch: Nuthatch,
) -> None:
    """A successful transaction whose subtree reverted: the reverted frames' transfers never
    happened, and rotki keeps neither the flag nor the frame's failure, so they are dropped. Two
    transfers at one depth, identical in every other stored field, share Etherscan's depth-only
    traceId; both are kept, by the frame index, and the address and hash paths agree on them."""
    parent_tx = make_ethereum_transaction()
    parent = str(parent_tx.tx_hash)
    rows = [
        _internal(parent, trace_index=1, trace_id='0_1'),
        _internal(parent, trace_index=2, trace_id='0_1'),
        _internal(parent, trace_index=3, trace_id='0_1', is_error='1'),
        _internal(parent, trace_index=4, trace_id='0_1_1', is_error='1'),
    ]
    with patch.object(nuthatch.session, 'get', return_value=_answer(rows)):
        by_hash = cast('list[EvmInternalTransaction]', next(nuthatch.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=None,
            action='txlistinternal',
            period_or_hash=parent_tx.tx_hash,
        )))
    with patch.object(nuthatch.session, 'get', return_value=_answer(rows)):
        by_address = cast('list[EvmInternalTransaction]', next(nuthatch.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=ADDRESS,
            action='txlistinternal',
            period_or_hash=TimestampOrBlockRange(range_type='blocks', from_value=100, to_value=100),  # noqa: E501
        )))

    assert [tx.trace_id for tx in by_hash] == [1, 2]
    assert [tx.trace_id for tx in by_address] == [1, 2]
    dbevmtx = DBEvmTx(database)
    with database.user_write() as write_cursor:
        dbevmtx.add_transactions(write_cursor=write_cursor, evm_transactions=[parent_tx], relevant_address=None)  # noqa: E501
        for txs in (by_address, by_hash):
            dbevmtx.add_evm_internal_transactions(write_cursor=write_cursor, transactions=txs, relevant_address=None)  # noqa: E501
    with database.conn.read_ctx() as cursor:
        stored = cursor.execute('SELECT trace_id FROM evm_internal_transactions ORDER BY trace_id').fetchall()  # noqa: E501
    assert stored == [(1,), (2,)]


def test_nuthatch_internals_page_on_what_the_nest_answered(nuthatch: Nuthatch) -> None:
    """A full page of reverted frames leaves nothing to keep, but it is still a full page: the
    next page is asked for, not taken as the end."""
    parent = str(make_evm_tx_hash())
    reverted = [_internal(parent, trace_index=i, trace_id='0_1', is_error='1') for i in range(1000)]  # noqa: E501
    tail = [_internal(parent, trace_index=1000, trace_id='0_1')]
    with patch.object(nuthatch.session, 'get', side_effect=[_answer(reverted), _answer(tail)]) as get:  # noqa: E501
        internals = cast('list[EvmInternalTransaction]', next(nuthatch.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=ADDRESS,
            action='txlistinternal',
            period_or_hash=TimestampOrBlockRange(range_type='blocks', from_value=100, to_value=100),  # noqa: E501
        )))

    assert [tx.trace_id for tx in internals] == [1000]
    assert get.call_count == 2


def test_nuthatch_internal_without_its_frame_index_is_refused(nuthatch: Nuthatch) -> None:
    row = _internal(str(make_evm_tx_hash()), trace_index=1, trace_id='0_1')
    del row['nuthatchTraceIndex']
    with (
        patch.object(nuthatch.session, 'get', return_value=_answer([row])),
        pytest.raises(RemoteError, match='nuthatchTraceIndex'),
    ):
        next(nuthatch.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=ADDRESS,
            action='txlistinternal',
            period_or_hash=TimestampOrBlockRange(range_type='blocks', from_value=100, to_value=100),  # noqa: E501
        ))


def test_nuthatch_watch_sync_reads_the_chain_of_an_unready_nest(database, nuthatch: Nuthatch) -> None:  # noqa: E501
    """A nest that has not reached its chain head answers /ready with 503 and its chain. The watch
    sync still tells it what to watch, or it could never be given the accounts it lacks."""
    with database.user_write() as write_cursor:
        database.add_blockchain_accounts(
            write_cursor,
            [BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=make_evm_address())],  # noqa: E501
        )
    cached = CachedSettings()
    order = {**cached._evm_indexers_order_per_chain, ChainID.ETHEREUM: (EvmIndexer.NUTHATCH,)}
    calls: list[tuple[str, str, dict | None]] = []

    def request(method: str, url: str, **kwargs: Any) -> MockResponse:
        path = url.split('127.0.0.1:8288', 1)[1]
        calls.append((method, path, kwargs.get('json')))
        if path == '/ready':
            return MockResponse(HTTPStatus.SERVICE_UNAVAILABLE, '{"ready": false, "chain_id": 1, "head": null}')  # noqa: E501
        if path == '/api/watch' and method == 'POST':
            return MockResponse(HTTPStatus.SERVICE_UNAVAILABLE, '{"error": "busy"}')
        return MockResponse(HTTPStatus.OK, '{"watched": []}')

    with (
        patch.object(type(cached), '_evm_indexers_order_per_chain', order),
        patch.object(nuthatch.session, 'request', side_effect=request),
        pytest.raises(RemoteError, match='/api/watch answered 503'),
    ):
        nuthatch.sync_watched()

    assert any(c[:2] == ('POST', '/api/watch') for c in calls), (
        'past an unready /ready to the watch, where a 503 still fails the sync'
    )


def _validator(eth2, index: int = 7) -> None:
    with eth2.database.user_write() as write_cursor:
        DBEth2(eth2.database).add_or_update_validators(write_cursor, [ValidatorDetails(
            validator_index=index,
            public_key=Eth2PubKey('0x' + 'ab' * 48),
            validator_type=ValidatorType.DISTRIBUTING,
            withdrawal_address=ADDRESS,
            activation_timestamp=Timestamp(1600000000),
        )])


def _produced(eth2, nuthatch: Nuthatch, rows: list[dict[str, Any]], proposer: int | None = 7) -> bool:  # noqa: E501
    inquirer = eth2.ethereum
    inquirer.available_indexers[EvmIndexer.NUTHATCH] = nuthatch
    cached = CachedSettings()
    order = {**cached._evm_indexers_order_per_chain, ChainID.ETHEREUM: (EvmIndexer.NUTHATCH, EvmIndexer.ETHERSCAN)}  # noqa: E501
    with (
        patch.object(type(cached), '_evm_indexers_order_per_chain', order),
        patch.object(nuthatch, 'get_validated_blocks', return_value=rows),
        patch.object(inquirer, 'maybe_timestamp_to_block_range', side_effect=lambda period: period),  # noqa: E501
        patch.object(eth2, '_get_proposer_index_for_validated_block', return_value=proposer),
    ):
        return eth2._get_and_store_produced_blocks_from_indexers(indices=[7], update_cache=True, only=EvmIndexer.NUTHATCH)  # noqa: E501


def _block_events(database, block: int) -> list[tuple[int, str]]:
    with database.conn.read_ctx() as cursor:
        return cursor.execute(
            'SELECT sequence_index, amount FROM history_events WHERE group_identifier=? ORDER BY sequence_index',  # noqa: E501
            (f'BP1_{block}',),
        ).fetchall()


def _cursor(database, index: int = 7) -> Timestamp | None:
    with database.conn.read_ctx() as cursor:
        return database.get_dynamic_cache(cursor=cursor, name=DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS, index=index)  # noqa: E501


def test_produced_block_without_a_relay_record_is_asked_about_again(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """No relay record is not "no MEV": the block's reward is stored, no MEV event is invented,
    and the validator's next query starts at the block, so a record published late adds the MEV
    reward to the block already stored, without its reward twice."""
    _validator(eth2)
    recent = ts_now() - 3600
    block = {'blockNumber': '200', 'timeStamp': str(recent), 'feeRecipient': str(ADDRESS).lower(), 'blockReward': '5', 'mevRecipient': '', 'mevReward': '', 'proposerPubkey': '', 'mev': 'unrecorded'}  # noqa: E501
    assert _produced(eth2, nuthatch, [block])
    assert _block_events(eth2.database, 200) == [(0, '0.000000000000000005')]
    assert _cursor(eth2.database) == recent, 'asked about again from the block'

    recorded = {**block, 'mev': 'relay', 'mevRecipient': str(ADDRESS).lower(), 'mevReward': '4', 'paymentValue': '3000000000000000000', 'proposerPubkey': '0x' + 'ab' * 48}  # noqa: E501
    assert _produced(eth2, nuthatch, [recorded])
    assert _block_events(eth2.database, 200) == [(0, '0.000000000000000005'), (1, '3')]
    assert (cursor := _cursor(eth2.database)) is not None and cursor > recent, 'nothing left to wait for'  # noqa: E501

    assert _produced(eth2, nuthatch, [recorded])
    assert _block_events(eth2.database, 200) == [(0, '0.000000000000000005'), (1, '3')]


def test_produced_block_without_a_relay_record_stops_being_asked_about(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """Past the retry window a block without a record no longer holds its validator back."""
    _validator(eth2)
    old = ts_now() - 40 * 86400
    block = {'blockNumber': '201', 'timeStamp': str(old), 'feeRecipient': str(ADDRESS).lower(), 'blockReward': '5', 'mevRecipient': '', 'mevReward': '', 'proposerPubkey': '', 'mev': 'unrecorded'}  # noqa: E501
    assert _produced(eth2, nuthatch, [block])
    assert (cursor := _cursor(eth2.database)) is not None and cursor > old


def test_produced_block_not_attributed_leaves_the_validator_retryable(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """A block whose proposer cannot be named is not stored, and the validator's range is not
    recorded as queried, so the next query asks again and stores it once it can be named."""
    _validator(eth2)
    block = {'blockNumber': '202', 'timeStamp': '1700000000', 'feeRecipient': str(ADDRESS).lower(), 'blockReward': '5', 'mevRecipient': '', 'mevReward': '', 'proposerPubkey': '', 'mev': 'none'}  # noqa: E501
    assert not _produced(eth2, nuthatch, [block], proposer=None)
    assert _block_events(eth2.database, 202) == []
    assert _cursor(eth2.database) is None

    assert _produced(eth2, nuthatch, [block])
    assert _block_events(eth2.database, 202) == [(0, '0.000000000000000005')]
    assert _cursor(eth2.database) is not None


def test_produced_block_rows_that_do_not_read_leave_the_validator_retryable(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    _validator(eth2)
    assert _produced(eth2, nuthatch, [{'blockNumber': 'not a number'}])
    assert _cursor(eth2.database) is None


def test_nuthatch_internal_that_does_not_read_refuses_the_answer(nuthatch: Nuthatch) -> None:
    """Skipping an unreadable row would pass the rest off as the whole answer, and an empty nest
    answer replaces the stored internals, so the answer is refused instead."""
    row = _internal(str(make_evm_tx_hash()), trace_index=1, trace_id='0_1')
    row['from'] = 'not an address'
    with (
        patch.object(nuthatch.session, 'get', return_value=_answer([row])),
        pytest.raises(RemoteError, match='cannot read'),
    ):
        next(nuthatch.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=None,
            action='txlistinternal',
            period_or_hash=make_evm_tx_hash(),
        ))


def test_beaconchain_does_not_move_on_a_validator_the_nest_is_waiting_on(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """The nest leaves a validator's next query at a block awaiting its relay record. beaconcha.in
    then covers everything and moves every validator on to now, but only the nest can bring that
    block's record, so the nest's place is kept."""
    _validator(eth2)
    pinned = Timestamp(ts_now() - 3600)
    eth2.ethereum.available_indexers[EvmIndexer.NUTHATCH] = nuthatch
    cached = CachedSettings()
    order = {**cached._evm_indexers_order_per_chain, ChainID.ETHEREUM: (EvmIndexer.NUTHATCH, EvmIndexer.ETHERSCAN)}  # noqa: E501

    def nest(indices: list[int], update_cache: bool, only: EvmIndexer | None = None) -> bool:
        with eth2.database.user_write() as write_cursor:
            eth2.database.set_dynamic_cache(write_cursor=write_cursor, name=DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS, value=pinned, index=7)  # noqa: E501
        return True

    def beaconchain(indices: list[int], update_cache: bool) -> None:
        with eth2.database.user_write() as write_cursor:
            eth2.database.set_dynamic_cache(write_cursor=write_cursor, name=DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS, value=ts_now(), index=7)  # noqa: E501

    with (
        patch.object(type(cached), '_evm_indexers_order_per_chain', order),
        # an indexer an earlier test in the process left degraded is not this test's concern
        patch.object(eth2.ethereum, '_get_indexers_in_order', return_value=[(EvmIndexer.NUTHATCH, nuthatch)]),  # noqa: E501
        patch.object(eth2, '_get_and_store_produced_blocks_from_indexers', side_effect=nest),
        patch.object(eth2.beacon_inquirer.beaconchain, 'has_api_key', return_value=True),
        patch.object(eth2.beacon_inquirer.beaconchain, '_get_and_store_produced_blocks', side_effect=beaconchain),  # noqa: E501
    ):
        eth2.get_and_store_produced_blocks(indices=[7])

    assert (got := _cursor(eth2.database)) == pinned, f'{got=} {pinned=} now={ts_now()}'
