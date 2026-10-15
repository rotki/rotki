import json
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.accounts import BlockchainAccountData, SingleBlockchainAccountData
from rotkehlchen.chain.evm.types import (
    EvmIndexer,
    SerializableChainIndexerOrder,
    string_to_evm_address,
)
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.settings import CachedSettings, ModifiableDBSettings
from rotkehlchen.errors.misc import ChainNotSupported, RemoteError
from rotkehlchen.externalapis.etherscan_like import HasChainActivity
from rotkehlchen.externalapis.nuthatch import Nuthatch
from rotkehlchen.tests.utils.factories import (
    make_ethereum_transaction,
    make_evm_address,
    make_evm_tx_hash,
)
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ChainID, SupportedBlockchain

if TYPE_CHECKING:
    from collections.abc import Callable

ADDRESS = string_to_evm_address('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')


@pytest.fixture(name='nuthatch')
def fixture_nuthatch(database, messages_aggregator):
    return Nuthatch(database=database, msg_aggregator=messages_aggregator)


def _answer(result: Any, status: str = '1', generation: str = '7') -> MockResponse:
    body: dict[str, Any] = {'status': status, 'message': 'OK' if status == '1' else 'NOTOK', 'result': result}  # noqa: E501
    if status == '1':
        body['generation'] = generation
    return MockResponse(status_code=HTTPStatus.OK, text=json.dumps(body))


def _ordered(*chains: ChainID) -> dict[ChainID, tuple[EvmIndexer, ...]]:
    return {
        **CachedSettings()._evm_indexers_order_per_chain,
        **dict.fromkeys(chains, (EvmIndexer.NUTHATCH,)),
    }


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
    ("NUTHATCH_UNSUPPORTED: chainid 10 is not this nest's chain 1", RemoteError),
    ('Error! Missing Or invalid Address', RemoteError),
])
def test_nuthatch_refusals_fall_through(
        nuthatch: Nuthatch,
        result: str,
        error: type[Exception],
) -> None:
    """A nest says what it cannot answer instead of returning an empty list. Each refusal must
    raise, so rotki tries the next indexer. None is ChainNotSupported, which would remove the
    nest from the chain."""
    with (
        patch.object(nuthatch.session, 'get', return_value=_answer(result, status='0')),
        pytest.raises(error) as raised,
    ):
        nuthatch._query(chain_id=ChainID.ETHEREUM, module='account', action='txlist')
    assert not isinstance(raised.value, ChainNotSupported)


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
    page = [
        {'hash': str(make_evm_tx_hash()), 'timeStamp': str(1700000000 + i), 'blockNumber': str(100 + i)}  # noqa: E501
        for i in range(1000)
    ]
    for _ in range(3):
        with patch.object(nuthatch.session, 'get', side_effect=[_answer(page), _answer([])]):
            assert sum(len(batch) for batch in nuthatch.get_token_transaction_hashes(
                chain_id=ChainID.ETHEREUM,
                account=ADDRESS,
                from_block=100,
                to_block=1100,
            )) == 1000


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
    with patch.object(nuthatch.session, 'get', return_value=_answer(rows)) as get:
        by_hash = next(nuthatch.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=None,
            action='txlistinternal',
            period_or_hash=parent_tx.tx_hash,
        ))
    assert 'page' not in get.call_args.kwargs['params'], 'a hash is answered whole, unpaged'
    with patch.object(nuthatch.session, 'get', return_value=_answer(rows)):
        by_address = next(nuthatch.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=ADDRESS,
            action='txlistinternal',
            period_or_hash=TimestampOrBlockRange(range_type='blocks', from_value=100, to_value=100),  # noqa: E501
        ))

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
        internals = next(nuthatch.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=ADDRESS,
            action='txlistinternal',
            period_or_hash=TimestampOrBlockRange(range_type='blocks', from_value=100, to_value=100),  # noqa: E501
        ))

    assert [tx.trace_id for tx in internals] == [1000]
    assert get.call_count == 2


@pytest.mark.parametrize(('field', 'value', 'match'), [
    ('nuthatchTraceIndex', None, 'without nuthatchTraceIndex'),
    ('value', 'lots', 'cannot read'),
])
def test_nuthatch_internal_that_cannot_be_read_is_refused(
        nuthatch: Nuthatch,
        field: str,
        value: str | None,
        match: str,
) -> None:
    """A row without its frame index, or one rotki cannot read, refuses the whole answer rather
    than passing the rest off as complete."""
    row = _internal(str(make_evm_tx_hash()), trace_index=1, trace_id='0_1')
    if value is None:
        del row[field]
    else:
        row[field] = value
    with (
        patch.object(nuthatch.session, 'get', return_value=_answer([row])),
        pytest.raises(RemoteError, match=match),
    ):
        next(nuthatch.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=ADDRESS,
            action='txlistinternal',
            period_or_hash=TimestampOrBlockRange(range_type='blocks', from_value=100, to_value=100),  # noqa: E501
        ))


@pytest.mark.parametrize('action', ['tokentx', 'txlistinternal'])
def test_nuthatch_endpoint_changed_between_pages_keeps_the_query_on_its_nest(
        nuthatch: Nuthatch,
        action: str,
) -> None:
    """Generations are counted per nest, so pages of two nests could look like one snapshot.
    A query that started on one nest reads every page from it."""
    first, second = 'http://127.0.0.1:8288', 'http://127.0.0.1:9999'
    parent = str(make_evm_tx_hash())
    pages = [
        [_internal(parent, trace_index=i, trace_id='0_1') | {'blockNumber': str(100 + i)} for i in range(1000)],  # noqa: E501
        [_internal(parent, trace_index=1000, trace_id='0_1') | {'blockNumber': '1100'}],
    ]
    urls: list[str] = []

    def get(url: str, **kwargs: Any) -> MockResponse:
        urls.append(url)
        CachedSettings().update_entry('nuthatch_api_endpoint', second)
        return _answer(pages[len(urls) - 1])

    queries: dict[str, Callable[[], list]] = {
        'tokentx': lambda: next(nuthatch.get_token_transaction_data(
            chain_id=ChainID.ETHEREUM,
            account=ADDRESS,
            from_block=100,
            to_block=1100,
        )),
        'txlistinternal': lambda: next(nuthatch.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=ADDRESS,
            action='txlistinternal',
            period_or_hash=TimestampOrBlockRange(range_type='blocks', from_value=100, to_value=1100),  # noqa: E501
        )),
    }
    try:
        with patch.object(nuthatch.session, 'get', side_effect=get):
            rows = queries[action]()
    finally:
        CachedSettings().update_entry('nuthatch_api_endpoint', first)

    assert urls == [f'{first}/api', f'{first}/api']
    assert len(rows) == 1001


def test_nuthatch_activity_check_stays_on_one_nest(nuthatch: Nuthatch) -> None:
    """The activity check asks several questions; a changed endpoint cannot split them."""
    first = 'http://127.0.0.1:8288'
    urls: list[str] = []

    def get(url: str, **kwargs: Any) -> MockResponse:
        urls.append(url)
        CachedSettings().update_entry('nuthatch_api_endpoint', 'http://127.0.0.1:9999')
        return _answer('0' if kwargs['params']['action'] == 'balance' else [])

    try:
        with patch.object(nuthatch.session, 'get', side_effect=get):
            assert nuthatch.has_activity(chain_id=ChainID.ETHEREUM, account=ADDRESS) == HasChainActivity.NONE  # noqa: E501
    finally:
        CachedSettings().update_entry('nuthatch_api_endpoint', first)

    assert urls == [f'{first}/api'] * 4


@pytest.mark.parametrize('action', ['txlist', 'tokentx'])
def test_nuthatch_row_that_cannot_be_read_refuses_the_answer(
        nuthatch: Nuthatch,
        action: str,
) -> None:
    """The base indexer skips a row it cannot read and hands over the rest, which for a nest
    would pass an incomplete answer off as complete. Here it refuses the answer instead."""
    row = {'hash': 'not a hash', 'timeStamp': '1700000000', 'blockNumber': '100'}
    queries: dict[str, Callable[[], object]] = {
        'txlist': lambda: next(nuthatch.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=ADDRESS,
            action='txlist',
            period_or_hash=TimestampOrBlockRange(range_type='blocks', from_value=100, to_value=100),  # noqa: E501
        )),
        'tokentx': lambda: next(nuthatch.get_token_transaction_data(
            chain_id=ChainID.ETHEREUM,
            account=ADDRESS,
            from_block=100,
            to_block=100,
        )),
    }
    with (
        patch.object(nuthatch.session, 'get', return_value=_answer([row])),
        pytest.raises(RemoteError, match='cannot read'),
    ):
        queries[action]()


def test_nuthatch_chainid_refusal_falls_through_and_keeps_the_nest(
        ethereum_inquirer,
        nuthatch: Nuthatch,
) -> None:
    """A nest that refuses the chain by chainid leaves the query to the next indexer and stays
    available for the next query."""
    ethereum_inquirer.available_indexers[EvmIndexer.NUTHATCH] = nuthatch
    order = {
        **CachedSettings()._evm_indexers_order_per_chain,
        ChainID.ETHEREUM: (EvmIndexer.NUTHATCH, EvmIndexer.ETHERSCAN),
    }
    refusal = _answer("NUTHATCH_UNSUPPORTED: chainid 1 is not this nest's chain 10", status='0')
    with (
        patch.object(CachedSettings, '_evm_indexers_order_per_chain', order),
        patch.object(nuthatch.session, 'get', return_value=refusal) as nest,
        patch.object(ethereum_inquirer.etherscan, 'get_token_transaction_data', return_value=iter([['from etherscan']])) as etherscan,  # noqa: E501
    ):
        answer = ethereum_inquirer._try_indexers(func=lambda indexer: next(indexer.get_token_transaction_data(  # noqa: E501
            chain_id=ChainID.ETHEREUM,
            account=ADDRESS,
            from_block=100,
            to_block=200,
        )))

    assert answer == ['from etherscan']
    assert nest.call_count == 1 and etherscan.call_count == 1
    assert ethereum_inquirer.available_indexers.get(EvmIndexer.NUTHATCH) is nuthatch


def test_nuthatch_logs_over_too_wide_a_range_are_asked_again_narrower(
        ethereum_inquirer,
        nuthatch: Nuthatch,
) -> None:
    """A nest that cannot answer getLogs over a range in time asks for a narrower one, and
    rotki halves its block step until the nest answers."""
    ethereum_inquirer.available_indexers[EvmIndexer.NUTHATCH] = nuthatch
    order = {**CachedSettings()._evm_indexers_order_per_chain, ChainID.ETHEREUM: (EvmIndexer.NUTHATCH,)}  # noqa: E501
    log = {
        'address': str(ADDRESS), 'topics': [], 'data': '0x', 'blockNumber': hex(100),
        'logIndex': '0x0', 'timeStamp': hex(1700000000), 'gasPrice': '0x1', 'gasUsed': '0x1',
        'transactionIndex': '0x0', 'transactionHash': str(make_evm_tx_hash()),
    }
    spans: list[int] = []

    def get(url: str, **kwargs: Any) -> MockResponse:
        params = kwargs['params']
        spans.append(span := int(params['toBlock']) - int(params['fromBlock']))
        if span > 150000:
            return _answer('NUTHATCH_INCOMPLETE: not answered within the 8s deadline; ask for a narrower range', status='0')  # noqa: E501
        return _answer([log] if int(params['fromBlock']) == 0 else [])

    with (
        patch.object(CachedSettings, '_evm_indexers_order_per_chain', order),
        patch.object(nuthatch.session, 'get', side_effect=get),
    ):
        logs = ethereum_inquirer.get_logs(
            contract_address=ADDRESS,
            abi=ethereum_inquirer.contracts.abi('ERC20_TOKEN'),
            event_name='Transfer',
            argument_filters={},
            from_block=0,
            to_block=400000,
            call_order=[ethereum_inquirer.indexers_node],
        )

    assert spans[0] == 300000
    assert all(span <= 150000 for span in spans[1:]) and len(spans) > 1
    assert [x['blockNumber'] for x in logs] == [100]


@pytest.mark.parametrize(('refusal', 'serves_the_range'), [
    ("NUTHATCH_UNSUPPORTED: chain 42161's blocks can share a timestamp", True),
    ('NUTHATCH_INCOMPLETE: no verified headers bracket timestamp 1700000000', False),
])
def test_nuthatch_timestamp_refusal_is_not_stale_history(
        ethereum_inquirer,
        nuthatch: Nuthatch,
        refusal: str,
        serves_the_range: bool,
) -> None:
    """A nest that never resolves timestamps on a chain still serves that chain's transactions
    once another indexer turns the range into blocks. One whose headers do not reach the range is
    stale for it, and is skipped as any other indexer would be."""
    ethereum_inquirer.available_indexers[EvmIndexer.NUTHATCH] = nuthatch
    order = {
        **CachedSettings()._evm_indexers_order_per_chain,
        ChainID.ETHEREUM: (EvmIndexer.NUTHATCH, EvmIndexer.ETHERSCAN),
    }
    period = TimestampOrBlockRange(range_type='timestamps', from_value=1700000000, to_value=1700000100)  # noqa: E501
    with (
        patch.object(CachedSettings, '_evm_indexers_order_per_chain', order),
        patch.object(nuthatch.session, 'get', return_value=_answer(refusal, status='0')),
        patch.object(
            ethereum_inquirer.etherscan,
            'get_blocknumber_by_time',
            side_effect=lambda chain_id, ts, closest='before': ts // 10,
        ),
        ethereum_inquirer.block_range_skipping_stale_indexers(period) as blocks,
    ):
        assert blocks.to_value == 170000010
        asked = [name for name, _ in ethereum_inquirer._get_indexers_in_order()]

    assert (EvmIndexer.NUTHATCH in asked) is serves_the_range
    assert EvmIndexer.ETHERSCAN in asked


def _nest(
        watched: list[str],
        ready: dict[str, Any] | None = None,
        down: bool = False,
        chains: dict[str, list[str]] | None = None,
):
    """A nest's management API: its chains, a watched set the POSTs change, and every call made
    of it. chains is a multichain nest's per-chain watched lists."""
    calls: list[tuple[str, str, dict | None]] = []
    watched = [str(address).lower() for address in watched]

    def request(method: str, url: str, **kwargs: Any) -> MockResponse:
        path, body = url.split('127.0.0.1:8288', 1)[1], kwargs.get('json') or {}
        calls.append((method, path, kwargs.get('json')))
        if down:
            raise requests.exceptions.ConnectionError('nest is down')
        if path == '/ready':
            return MockResponse(HTTPStatus.OK, json.dumps(ready or {'chain_id': 1}))
        if method == 'POST' and path == '/api/watch' and body['address'] not in watched:
            watched.append(body['address'])
        listed: dict[str, Any] = {'watched': watched}
        if chains is not None:
            listed['chains'] = chains
        return MockResponse(HTTPStatus.OK, json.dumps(listed))

    return request, calls


def _sync(nuthatch: Nuthatch, request: Callable, *chains: ChainID) -> None:
    with (
        patch.object(CachedSettings, '_evm_indexers_order_per_chain', _ordered(*chains)),
        patch.object(nuthatch.session, 'request', side_effect=request),
    ):
        nuthatch.sync_watched()


def _posts(calls: list[tuple[str, str, dict | None]], path: str) -> list[str]:
    return [c[2]['address'] for c in calls if c[:2] == ('POST', path) and c[2] is not None]


def test_nuthatch_watch_sync_follows_rotkis_accounts(database, nuthatch: Nuthatch) -> None:
    """The nest is told to watch every account rotki tracks on its chain and is not yet watching.
    A removed account is not unwatched. A nest on a chain whose order does not name it is left
    alone, and one no order names is not contacted."""
    kept, removed, seeded = make_evm_address(), make_evm_address(), make_evm_address()
    with database.user_write() as write_cursor:
        database.add_blockchain_accounts(write_cursor, [
            BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=address)
            for address in (kept, removed)
        ])
    with database.conn.read_ctx() as cursor:
        everyone = {str(a).lower() for a in database.get_blockchain_accounts(cursor).eth}

    request, calls = _nest([seeded])
    _sync(nuthatch, request, ChainID.ETHEREUM)
    assert set(_posts(calls, '/api/watch')) == everyone

    with database.user_write() as write_cursor:
        database.remove_single_blockchain_accounts(write_cursor, SupportedBlockchain.ETHEREUM, [removed])  # noqa: E501
    calls.clear()
    _sync(nuthatch, request, ChainID.ETHEREUM)
    assert [c[:2] for c in calls] == [('GET', '/ready'), ('GET', '/api/watch')], 'nothing to send'

    down, _ = _nest([], down=True)
    with pytest.raises(RemoteError):
        _sync(nuthatch, down, ChainID.ETHEREUM)

    other, calls = _nest([], ready={'chain_id': 10})
    _sync(nuthatch, other, ChainID.ETHEREUM)
    assert [c[1] for c in calls] == ['/ready']

    unordered, calls = _nest([])
    _sync(nuthatch, unordered)
    assert calls == [], 'a nest no order names is never contacted'


def test_nuthatch_endpoint_changed_during_a_sync_leaves_the_sync_on_its_nest(
        database,
        nuthatch: Nuthatch,
) -> None:
    """A sync that started on one nest finishes there: an endpoint changed while it waits for the
    watched list sends nothing to the new nest."""
    first, second = 'http://127.0.0.1:8288', 'http://127.0.0.1:9999'
    with database.user_write() as write_cursor:
        database.add_blockchain_accounts(
            write_cursor,
            [BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=make_evm_address())],  # noqa: E501
        )
    urls: list[str] = []

    def request(method: str, url: str, **kwargs: Any) -> MockResponse:
        urls.append(url)
        if url.endswith('/ready'):
            return MockResponse(HTTPStatus.OK, '{"chain_id": 1}')
        if method == 'GET':
            CachedSettings().update_entry('nuthatch_api_endpoint', second)
        return MockResponse(HTTPStatus.OK, '{"watched": []}')

    try:
        _sync(nuthatch, request, ChainID.ETHEREUM)
    finally:
        CachedSettings().update_entry('nuthatch_api_endpoint', first)

    with database.conn.read_ctx() as cursor:
        everyone = database.get_blockchain_accounts(cursor).eth
    assert len(urls) == 2 + len(everyone), 'ready, the list and each watch'
    assert all(url.startswith(first) for url in urls)


def test_nuthatch_watch_sync_covers_every_chain_a_multichain_nest_serves(
        database,
        nuthatch: Nuthatch,
) -> None:
    """A nest serving several chains lists them as chain_ids. It is told about the accounts of
    each of those chains whose order names it, and of no other."""
    on_optimism, on_base, on_gnosis = make_evm_address(), make_evm_address(), make_evm_address()
    with database.user_write() as write_cursor:
        database.add_blockchain_accounts(write_cursor, [
            BlockchainAccountData(chain=SupportedBlockchain.OPTIMISM, address=on_optimism),
            BlockchainAccountData(chain=SupportedBlockchain.BASE, address=on_base),
            BlockchainAccountData(chain=SupportedBlockchain.GNOSIS, address=on_gnosis),
        ])

    request, calls = _nest([], ready={'chain_ids': [1, 10, 8453]})
    with (
        patch.object(CachedSettings, '_evm_indexers_order_per_chain', _ordered(ChainID.OPTIMISM, ChainID.GNOSIS)),  # noqa: E501
        patch.object(nuthatch.session, 'request', side_effect=request),
    ):
        nuthatch.sync_watched()

    assert [c[2] for c in calls if c[:2] == ('POST', '/api/watch')] == [
        {'address': str(on_optimism).lower()},
    ], 'base is served but not ordered, gnosis is ordered but not served'


@pytest.mark.parametrize('multichain', [False, True])
def test_nuthatch_watch_sync_compares_each_chain_it_serves(
        database,
        nuthatch: Nuthatch,
        multichain: bool,
) -> None:
    """A multichain nest's watched list is the union of its chains. An address it watches on
    Ethereum only is still registered when rotki also tracks it on Base. A solo nest has no
    per-chain lists and its watched list is the answer."""
    address = make_evm_address()
    with database.user_write() as write_cursor:
        database.add_blockchain_accounts(write_cursor, [
            BlockchainAccountData(chain=chain, address=address)
            for chain in (SupportedBlockchain.ETHEREUM, SupportedBlockchain.BASE)
        ])
    if multichain:
        request, calls = _nest(
            [address],
            ready={'chain_ids': [1, 8453]},
            chains={'1': [str(address).lower()], '8453': []},
        )
    else:
        request, calls = _nest([address])
    _sync(nuthatch, request, ChainID.ETHEREUM, ChainID.BASE)

    assert (str(address).lower() in _posts(calls, '/api/watch')) is multichain


def test_nuthatch_watch_sync_reads_the_chain_of_an_unready_nest(database, nuthatch: Nuthatch) -> None:  # noqa: E501
    """A nest that has not reached its chain head answers /ready with 503 and its chain. The watch
    sync still tells it what to watch, or it could never be given the accounts it lacks."""
    with database.user_write() as write_cursor:
        database.add_blockchain_accounts(
            write_cursor,
            [BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=make_evm_address())],  # noqa: E501
        )
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
        patch.object(CachedSettings, '_evm_indexers_order_per_chain', _ordered(ChainID.ETHEREUM)),
        patch.object(nuthatch.session, 'request', side_effect=request),
        pytest.raises(RemoteError, match='/api/watch answered 503'),
    ):
        nuthatch.sync_watched()

    assert any(c[:2] == ('POST', '/api/watch') for c in calls), (
        'past an unready /ready to the watch, where a 503 still fails the sync'
    )


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

    with patch.object(rotki.nuthatch, 'sync_watched', side_effect=RemoteError('nest is down')):
        rotki._sync_nuthatch_watched()  # logs, never raises


@pytest.mark.parametrize('detected', [True, False])
def test_detected_accounts_reach_the_nest(rotkehlchen_api_server, detected: bool) -> None:
    """Accounts detection adds are registered with the nest like added ones, and detection that
    adds nothing schedules nothing."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    address = make_evm_address()
    with patch.object(rotki, 'schedule_nuthatch_watch_sync'):
        rotki.add_single_blockchain_accounts(
            chain=SupportedBlockchain.ETHEREUM,
            account_data=[SingleBlockchainAccountData(address=address)],
        )
    assert rotki.chains_aggregator.schedule_nuthatch_watch_sync == rotki.schedule_nuthatch_watch_sync  # noqa: E501
    found = [(SupportedBlockchain.BASE, address)] if detected else []

    def check_chains_and_add_accounts(account: str, **_kwargs: Any) -> tuple[list, list, bool]:
        if account != address:
            return [], [], False
        for chain, added in found:  # detection keeps only accounts that are tracked
            rotki.chains_aggregator.accounts.add(blockchain=chain, address=added)
        return found, [], detected

    with (
        patch.object(
            rotki.chains_aggregator,
            'check_chains_and_add_accounts',
            side_effect=check_chains_and_add_accounts,
        ),
        patch.object(rotki.chains_aggregator, 'schedule_nuthatch_watch_sync') as schedule,
    ):
        assert rotki.chains_aggregator.detect_evm_accounts() == found

    assert schedule.call_count == int(detected)


def test_existing_accounts_reach_a_nest_set_up_after_them(rotkehlchen_api_server) -> None:
    """With accounts already tracked: set the nest's address, then name it in a chain's order.
    Each step tells the nest what to watch, so the accounts reach it without waiting for the next
    login or account change. A setting that changes neither does not."""
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
        assert calls == [], 'not yet in any order, so not yet contacted'
        order = SerializableChainIndexerOrder(
            order={ChainID.ETHEREUM: [EvmIndexer.NUTHATCH, EvmIndexer.ETHERSCAN]},
        )
        assert rotki.set_settings(ModifiableDBSettings(evm_indexers_order=order))[0]
        assert schedule.call_count == 2
        assert ('POST', '/api/watch', {'address': str(address).lower()}) in calls
        assert rotki.set_settings(ModifiableDBSettings(btc_derivation_gap_limit=30))[0]
        assert schedule.call_count == 2
