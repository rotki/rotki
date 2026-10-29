import contextlib
import json
from http import HTTPStatus
from typing import Any, Final
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.ethereum.modules.eth2.structures import ValidatorDetails, ValidatorType
from rotkehlchen.chain.evm.types import (
    EvmIndexer,
    string_to_evm_address,
)
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.constants import ONE
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.externalapis.nuthatch import HistoryStartsLater, Nuthatch, ValidatorBlocks
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.eth2 import EthBlockEvent
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    Eth2PubKey,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_now

ADDRESS = string_to_evm_address('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')
WITHDRAWAL: Final = deserialize_evm_address('0x46d24de64abe6a7ab6afda0389074ae8c7ed5d0f')
FEE_RECIPIENT: Final = deserialize_evm_address('0xc42f80913b33ba0b6002f3b5b8ad335ed9a137e3')
PUBKEY: Final = '0xb570a57c35b4813b1bb43166f69d22a4c502360b2cf1eff8162134783a978f31b695acacc630196c7f3d0e933ecf933a'  # noqa: E501
PAID_BLOCK: Final = {
    'blockNumber': '26167074', 'timeStamp': '1767000000', 'feeRecipient': '0x4838b106fce9647bdf1e7877bf73ce8b0bad5f97',  # noqa: E501
    'blockReward': '9', 'mevRecipient': str(FEE_RECIPIENT).lower(), 'mevReward': '2275207282975303',  # noqa: E501
    'proposerPubkey': PUBKEY, 'mev': 'relay', 'relays': 'flashbots,ultrasound',
}


def _head() -> tuple[int, Timestamp]:
    """A nest's finalized head far enough on that every test block is behind it."""
    return 10 ** 9, ts_now()


@pytest.fixture(name='nuthatch')
def fixture_nuthatch(database, messages_aggregator):
    return Nuthatch(database=database, msg_aggregator=messages_aggregator)


def _answer(result: Any, status: str = '1', generation: str = '7') -> MockResponse:
    body: dict[str, Any] = {'status': status, 'message': 'OK' if status == '1' else 'NOTOK', 'result': result}  # noqa: E501
    if status == '1':
        body['generation'] = generation
    return MockResponse(status_code=HTTPStatus.OK, text=json.dumps(body))


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
        patch.object(inquirer.etherscan, 'get_withdrawals', return_value={6}) as etherscan_asked,
        patch.object(inquirer.blockscout, 'query_withdrawals', return_value={7}) as blockscout_asked,  # noqa: E501
    ):
        assert eth2._fetch_withdrawals_from_external_sources(ADDRESS, period) is None
        assert etherscan_asked.call_count == blockscout_asked.call_count == 0, (
            'with a nest ordered, the address goes to no service the order does not name'
        )

    with (
        patch.object(nuthatch, 'get_withdrawals') as nest,
        patch.object(inquirer.etherscan, 'get_withdrawals', return_value={6}),
    ):
        assert eth2._fetch_withdrawals_from_external_sources(ADDRESS, period) == {6}
    assert nest.call_count == 0, 'a nest the order does not name is never asked'


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


@pytest.mark.parametrize('multichain', [False, True])
def test_nuthatch_finalized_head(nuthatch: Nuthatch, multichain: bool) -> None:
    """The head is Ethereum's, read from a solo nest's /ready or from a multichain nest's
    entry for chain 1, never another chain's."""
    def request(method: str, url: str, **kwargs: Any) -> MockResponse:
        ethereum = {'chain_id': 1, 'head': head}
        if not multichain:
            return MockResponse(HTTPStatus.OK, json.dumps(ethereum))
        return MockResponse(HTTPStatus.OK, json.dumps({
            'chain_ids': [1, 100],
            'chains': {'1': ethereum, '100': {'chain_id': 100, 'head': 99}},
        }))

    head: int | None = 20_000_000
    with (
        patch.object(nuthatch.session, 'request', side_effect=request),
        patch.object(nuthatch, 'get_block_by_number', return_value={'timestamp': 1700000000, 'number': head}) as block,  # noqa: E501
    ):
        assert nuthatch.finalized_head() == (20_000_000, 1700000000)
        assert block.call_args.kwargs['block_number'] == 20_000_000
        head = None
        with pytest.raises(RemoteError, match='has not read its Ethereum head'):
            nuthatch.finalized_head()


def test_produced_blocks_range_that_cannot_become_blocks_falls_through(eth2) -> None:
    """A source that cannot turn the range into blocks, such as a nest asked about a time past
    its newest header, fails that address only; the query goes on. With the nest in the order
    the query ends behind now, as transaction syncs do."""
    _validator(eth2)
    with (
        patch.object(eth2.ethereum, '_get_indexers_in_order', return_value=[(EvmIndexer.NUTHATCH, None)]),  # noqa: E501
        patch.object(eth2.ethereum, 'maybe_timestamp_to_block_range', side_effect=RemoteError('timestamp is newer than the chain head')) as conversion,  # noqa: E501
    ):
        assert not eth2._get_and_store_produced_blocks_from_indexers(indices=[577475], update_cache=True)  # noqa: E501

    assert conversion.call_args.args[0].to_value <= ts_now() - 15
    assert _cursor(eth2.database) is None


def test_withdrawals_range_that_cannot_become_blocks_falls_through(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """The same for withdrawals: without a block range the indexers that need one are passed
    over and blockscout, ordered, which takes none, still answers. The end is kept behind now
    while the nest is in the order."""
    _validator(eth2)
    with (
        patch.object(eth2.ethereum, '_get_indexers_in_order', return_value=[(EvmIndexer.NUTHATCH, nuthatch), (EvmIndexer.BLOCKSCOUT, eth2.ethereum.blockscout)]),  # noqa: E501
        patch.object(eth2.ethereum, 'maybe_timestamp_to_block_range', side_effect=RemoteError('timestamp is newer than the chain head')) as conversion,  # noqa: E501
        patch.object(nuthatch, 'get_withdrawals') as nest,
        patch.object(eth2.ethereum.blockscout, 'query_withdrawals', return_value=set()) as blockscout,  # noqa: E501
    ):
        eth2.query_single_address_withdrawals(WITHDRAWAL, ts_now())

    assert conversion.call_args.args[0].to_value <= ts_now() - 15
    assert nest.call_count == 0
    assert blockscout.call_count == 1
    with eth2.database.conn.read_ctx() as cursor:
        assert eth2.database.get_dynamic_cache(cursor=cursor, name=DBCacheDynamic.WITHDRAWALS_TS, address=WITHDRAWAL) is not None  # noqa: E501


def _track(eth2, *addresses: ChecksumEvmAddress) -> None:
    with eth2.database.user_write() as write_cursor:
        eth2.database.add_blockchain_accounts(write_cursor, [
            BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=address)
            for address in addresses
        ])


def _validator(eth2, index: int = 577475, pubkey: str = PUBKEY, withdrawal: ChecksumEvmAddress = WITHDRAWAL, exited: Timestamp | None = None) -> None:  # noqa: E501
    with eth2.database.user_write() as write_cursor:
        DBEth2(eth2.database).add_or_update_validators(write_cursor, [ValidatorDetails(
            validator_index=index,
            public_key=Eth2PubKey(pubkey),
            validator_type=ValidatorType.DISTRIBUTING,
            withdrawal_address=withdrawal,
            activation_timestamp=Timestamp(1600000000),
            exited_timestamp=exited,
        )])


def _nest_pass(
        eth2,
        nuthatch: Nuthatch,
        answers: dict[ChecksumEvmAddress, list[dict[str, Any]]] | Any,
        proposer: int | None = None,
        without_mev: set[int] | None = None,
        asked: list[tuple[ChecksumEvmAddress, TimestampOrBlockRange]] | None = None,
        head: tuple[int, Timestamp] | None = None,
) -> None:
    """One nest pass. `answers` maps an address to the rows the nest gives it, or is a callable
    of address and period; a beacon node, if `proposer` is set, names that proposer."""
    def validated_blocks(address: ChecksumEvmAddress, period: TimestampOrBlockRange) -> list[dict[str, Any]]:  # noqa: E501
        if asked is not None:
            asked.append((address, period))
        return answers(address, period) if callable(answers) else answers.get(address, [])

    with (
        patch.object(eth2.ethereum, '_get_indexers_in_order', return_value=[(EvmIndexer.NUTHATCH, nuthatch)]),  # noqa: E501
        patch.object(nuthatch, 'finalized_head', return_value=head or (26_200_000, ts_now())),
        patch.object(nuthatch, 'get_validated_blocks', side_effect=validated_blocks),
        patch.object(eth2.ethereum, 'get_blocknumber_by_time', return_value=0),
        patch.object(eth2.beacon_inquirer, 'node', None if proposer is None else type('Node', (), {'query_block_proposer': lambda self, slot: proposer})()),  # noqa: E501
    ):
        eth2._get_and_store_produced_blocks_from_nest(blocks_without_mev=set() if without_mev is None else without_mev)  # noqa: E501


def _block_events(database, block: int) -> list[tuple[int, int, str]]:
    with database.conn.read_ctx() as cursor:
        return cursor.execute(
            'SELECT he.sequence_index, info.validator_index, he.amount FROM history_events he '
            'JOIN eth_staking_events_info info ON info.identifier=he.identifier '
            'WHERE he.group_identifier=? ORDER BY he.sequence_index',
            (f'BP1_{block}',),
        ).fetchall()


def _cursor(database, index: int = 577475) -> Timestamp | None:
    with database.conn.read_ctx() as cursor:
        return database.get_dynamic_cache(cursor=cursor, name=DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS, index=index)  # noqa: E501


def _through(database, address: ChecksumEvmAddress) -> int | None:
    with database.conn.read_ctx() as cursor:
        return database.get_dynamic_cache(cursor=cursor, name=DBCacheDynamic.NEST_PRODUCED_BLOCKS_THROUGH, address=address)  # noqa: E501


def test_nest_books_a_validator_block_paid_to_an_address_it_does_not_withdraw_to(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """Validator 577475's block 26167074 was paid to a tracked address it does not withdraw to.
    Every tracked address is asked, the relay's proposer key books the block to the validator,
    and the validator's produced-block query time does not move: the nest covers addresses, not
    validators. Each address's progress moves on to the nest's finalized head."""
    _track(eth2, WITHDRAWAL, FEE_RECIPIENT)
    _validator(eth2)
    asked: list[tuple[ChecksumEvmAddress, TimestampOrBlockRange]] = []
    _nest_pass(eth2, nuthatch, {FEE_RECIPIENT: [PAID_BLOCK]}, asked=asked)

    assert {address for address, _ in asked} >= {WITHDRAWAL, FEE_RECIPIENT}
    assert _block_events(eth2.database, 26167074) == [(0, 577475, '0.000000000000000009'), (1, 577475, '0.002275207282975303')]  # noqa: E501
    assert _cursor(eth2.database) is None
    assert _through(eth2.database, FEE_RECIPIENT) == _through(eth2.database, WITHDRAWAL) == 26_200_000  # noqa: E501


def test_nest_asks_each_address_from_its_progress_to_the_finalized_head(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """The nest serves produced blocks through its finalized head only, so it is asked to there,
    each address from where it was last asked through."""
    _track(eth2, FEE_RECIPIENT)
    _validator(eth2)
    with eth2.database.user_write() as write_cursor:
        eth2.database.set_dynamic_cache(write_cursor=write_cursor, name=DBCacheDynamic.NEST_PRODUCED_BLOCKS_THROUGH, value=26_000_000, address=FEE_RECIPIENT)  # noqa: E501
        eth2.database.set_static_cache(write_cursor=write_cursor, name=DBCacheStatic.NUTHATCH_PRODUCED_VALIDATORS, value='[577475]')  # noqa: E501
    asked: list[tuple[ChecksumEvmAddress, TimestampOrBlockRange]] = []
    _nest_pass(eth2, nuthatch, {}, asked=asked, head=(26_100_000, Timestamp(ts_now() - 600)))

    periods = [(p.from_value, p.to_value) for address, p in asked if address == FEE_RECIPIENT]
    assert periods == [(26_000_001, 26_100_000)]
    assert _through(eth2.database, FEE_RECIPIENT) == 26_100_000


def test_nest_block_paid_to_untracked_addresses_is_not_found_and_claims_nothing(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    _track(eth2, WITHDRAWAL)
    _validator(eth2)
    _nest_pass(eth2, nuthatch, {})
    assert _block_events(eth2.database, 26167074) == []
    assert _cursor(eth2.database) is None


def test_nest_books_a_shared_recipients_block_to_the_validator_the_relay_names(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    other_pubkey = '0x' + 'cd' * 48
    _track(eth2, FEE_RECIPIENT)
    _validator(eth2)
    _validator(eth2, index=7, pubkey=other_pubkey, withdrawal=FEE_RECIPIENT)
    _nest_pass(eth2, nuthatch, {FEE_RECIPIENT: [{**PAID_BLOCK, 'proposerPubkey': other_pubkey}]})
    assert [validator for _, validator, _ in _block_events(eth2.database, 26167074)] == [7, 7]


def test_nest_block_without_a_proposer_is_booked_only_by_a_beacon_node(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """A block the address built itself carries no relay proposer key. A tracked address
    receiving it says nothing about who proposed it, so it is booked only if a configured beacon
    node names a tracked validator, never to the one active validator that withdraws there."""
    self_built = {'blockNumber': '26167080', 'timeStamp': '1767000072', 'feeRecipient': str(WITHDRAWAL).lower(), 'blockReward': '5', 'mevRecipient': '', 'mevReward': '', 'proposerPubkey': '', 'mev': 'unrecorded'}  # noqa: E501
    _track(eth2, WITHDRAWAL)
    _validator(eth2)
    _nest_pass(eth2, nuthatch, {WITHDRAWAL: [self_built]})
    assert _block_events(eth2.database, 26167080) == []

    with eth2.database.user_write() as write_cursor:
        write_cursor.execute("DELETE FROM key_value_cache WHERE name LIKE 'nest_produced_blocks_through_%'")  # noqa: E501
    _nest_pass(eth2, nuthatch, {WITHDRAWAL: [self_built]}, proposer=577475)
    assert _block_events(eth2.database, 26167080) == [(0, 577475, '0.000000000000000005')]


def test_nest_rows_that_do_not_read_book_nothing_and_claim_nothing(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    _track(eth2, WITHDRAWAL)
    _validator(eth2)
    _nest_pass(eth2, nuthatch, {WITHDRAWAL: [{'blockNumber': 'not a number'}]})
    assert _cursor(eth2.database) is None


def test_nest_block_without_a_relay_record_gets_its_mev_when_the_range_is_asked_again(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """No relay record is not "no MEV": the reward is stored, no MEV event is invented, and the
    block waits for beaconcha.in. The served range is asked about again, so a record published
    late adds the MEV to the stored block, its reward not twice, and a builder's payment the nest
    attributes only later is found too. After the nest's window, one last ask, then no more."""
    _track(eth2, FEE_RECIPIENT)
    _validator(eth2)
    unrecorded = {**PAID_BLOCK, 'feeRecipient': str(FEE_RECIPIENT).lower(), 'mev': 'unrecorded', 'mevRecipient': '', 'mevReward': '', 'relays': ''}  # noqa: E501
    without_mev: set[int] = set()
    _nest_pass(eth2, nuthatch, {FEE_RECIPIENT: [unrecorded]}, without_mev=without_mev)
    assert _block_events(eth2.database, 26167074) == [(0, 577475, '0.000000000000000009')]
    assert without_mev == {26167074}

    recorded = {**PAID_BLOCK, 'feeRecipient': str(FEE_RECIPIENT).lower(), 'paymentValue': '3000000000000000000'}  # noqa: E501
    later = {**PAID_BLOCK, 'blockNumber': '26167090', 'timeStamp': '1767000192'}
    asked: list[tuple[ChecksumEvmAddress, TimestampOrBlockRange]] = []

    def nest_now(address: ChecksumEvmAddress, period: TimestampOrBlockRange) -> list[dict[str, Any]]:  # noqa: E501
        return [recorded, later] if period.from_value <= 26167074 <= period.to_value else []

    _nest_pass(eth2, nuthatch, nest_now, asked=asked)
    assert [a for a, _ in asked].count(FEE_RECIPIENT) == 1, 'nothing new, but the served range again'  # noqa: E501
    assert _block_events(eth2.database, 26167074) == [(0, 577475, '0.000000000000000009'), (1, 577475, '3')]  # noqa: E501
    assert [seq for seq, _, _ in _block_events(eth2.database, 26167090)] == [0, 1]

    with eth2.database.user_write() as write_cursor:  # the nest has stopped asking the relays
        eth2.database.set_static_cache(write_cursor=write_cursor, name=DBCacheStatic.NUTHATCH_PRODUCED_RANGES, value=json.dumps([[str(FEE_RECIPIENT), 0, 26_200_000, ts_now() - 40 * 86400]]))  # noqa: E501
    asked.clear()
    _nest_pass(eth2, nuthatch, nest_now, asked=asked)
    assert [a for a, _ in asked] == [FEE_RECIPIENT], 'once more, for what it learnt before it stopped'  # noqa: E501
    asked.clear()
    _nest_pass(eth2, nuthatch, nest_now, asked=asked)
    assert asked == [], 'nothing left to ask'


def test_nest_cursors_written_before_are_repaired(eth2, nuthatch: Nuthatch) -> None:
    """A validator's produced-block query times that an earlier version moved on from the nest's
    answers are dropped, so the validator is asked about again."""
    _track(eth2, WITHDRAWAL)
    _validator(eth2)
    with eth2.database.user_write() as write_cursor:
        for key in (DBCacheDynamic.NEST_PRODUCED_BLOCKS_QUERY_TS, DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS):  # noqa: E501
            eth2.database.set_dynamic_cache(write_cursor=write_cursor, name=key, value=ts_now(), index=577475)  # noqa: E501
    _nest_pass(eth2, nuthatch, {})
    assert _cursor(eth2.database) is None
    with eth2.database.conn.read_ctx() as cursor:
        assert eth2.database.get_dynamic_cache(cursor=cursor, name=DBCacheDynamic.NEST_PRODUCED_BLOCKS_QUERY_TS, index=577475) is None  # noqa: E501


def test_produced_blocks_fallback_never_asks_the_nest(eth2, nuthatch: Nuthatch) -> None:
    """The fallback asks by withdrawal address and moves validators on from the answer, which a
    nest's answer cannot support, so it never asks the nest."""
    with (
        patch.object(eth2.ethereum, '_get_indexers_in_order', return_value=[(EvmIndexer.NUTHATCH, nuthatch)]),  # noqa: E501
        patch.object(nuthatch, 'get_validated_blocks') as nest,
    ):
        assert eth2._fetch_validated_blocks_from_external_sources(address=WITHDRAWAL, period=TimestampOrBlockRange('blocks', 0, 1)) is None  # noqa: E501
    assert nest.call_count == 0


@pytest.mark.parametrize(('order', 'has_key', 'uncovered', 'beaconchain_asked', 'indexers_asked', 'warned'), [  # noqa: E501
    ((EvmIndexer.NUTHATCH,), False, {577475}, False, False, True),
    ((EvmIndexer.NUTHATCH,), False, set(), False, False, False),
    ((EvmIndexer.NUTHATCH,), True, {577475}, True, False, False),
    ((EvmIndexer.NUTHATCH, EvmIndexer.ETHERSCAN), False, {577475}, False, False, True),
    ((EvmIndexer.ETHERSCAN,), False, set(), False, True, False),
])
def test_produced_blocks_ask_the_nest_then_beaconchain_then_the_indexers(
        eth2,
        nuthatch: Nuthatch,
        order: tuple[EvmIndexer, ...],
        has_key: bool,
        uncovered: set[int],
        beaconchain_asked: bool,
        indexers_asked: bool,
        warned: bool,
) -> None:
    """The nest, when ordered, is asked first: for each validator's proven blocks, then for its
    addresses' relay records. beaconcha.in runs when it has a key. The other indexers, which find
    blocks by withdrawal address, run only when no nest is ordered: they cannot fill a validator's
    gap. A validator the nest did not cover, and beaconcha.in cannot, is told to the user."""
    beaconchain = eth2.beacon_inquirer.beaconchain
    with (
        patch.object(eth2.ethereum, '_get_indexers_in_order', return_value=[(name, nuthatch if name == EvmIndexer.NUTHATCH else None) for name in order]),  # noqa: E501
        patch.object(eth2, '_get_and_store_proven_blocks_from_nest', return_value=(set(), uncovered)) as proven,  # noqa: E501
        patch.object(eth2, '_get_and_store_produced_blocks_from_nest') as nest,
        patch.object(eth2, '_get_and_store_produced_blocks_from_indexers') as indexers,
        patch.object(beaconchain, 'has_api_key', return_value=has_key),
        patch.object(beaconchain, '_get_and_store_produced_blocks', return_value=set()) as beaconchain_query,  # noqa: E501
        patch.object(eth2.msg_aggregator, 'add_warning') as warning,
    ):
        eth2.get_and_store_produced_blocks(indices=[577475])

    assert proven.called is nest.called is (EvmIndexer.NUTHATCH in order)
    assert beaconchain_query.called is beaconchain_asked
    assert indexers.called is indexers_asked
    assert warning.called is warned


def test_beaconchain_rechecks_blocks_the_nest_stored_without_mev(eth2, nuthatch: Nuthatch) -> None:
    """beaconcha.in runs after the nest. A block the nest stored without its MEV reward, however
    old, is asked about there, also in a later run if it failed, and beaconcha.in adds the MEV it
    knows without the reward twice, also for a validator no longer picked."""
    _track(eth2, FEE_RECIPIENT)
    _validator(eth2)
    old = ts_now() - 40 * 86400
    unrecorded = {**PAID_BLOCK, 'timeStamp': str(old), 'feeRecipient': str(FEE_RECIPIENT).lower(), 'mev': 'unrecorded', 'mevRecipient': '', 'mevReward': '', 'relays': ''}  # noqa: E501
    beaconchain = eth2.beacon_inquirer.beaconchain
    builder = '0x4838b106fce9647bdf1e7877bf73ce8b0bad5f97'

    def run(rows: list[dict[str, Any]], beaconchain_up: bool, indices: list[int]) -> Any:
        with (
            patch.object(eth2.ethereum, '_get_indexers_in_order', return_value=[(EvmIndexer.NUTHATCH, nuthatch)]),  # noqa: E501
            patch.object(nuthatch, 'finalized_head', return_value=(26_200_000, ts_now())),
            patch.object(nuthatch, 'get_validated_blocks', return_value=rows),
            patch.object(eth2.ethereum, 'get_blocknumber_by_time', return_value=0),
            patch.object(beaconchain, 'has_api_key', return_value=True),
            patch.object(beaconchain, '_query_chunked_endpoint_with_cursor_pagination', return_value=[{'block': 26167074, 'validator': {'index': 577475}}]) as listed,  # noqa: E501
            patch.object(beaconchain, '_query_block_data', return_value={'timestamp': old, 'fee_recipient': builder}),  # noqa: E501
            patch.object(beaconchain, '_query_block_rewards', return_value={'priority_fees': {'amount': '9', 'recipient': {'address': builder}}, 'mev': {'amount': '2000000000000000000', 'recipient': {'address': str(FEE_RECIPIENT)}}, 'relay': {'producer_fee_recipient': str(FEE_RECIPIENT)}}) if beaconchain_up else patch.object(beaconchain, '_query_block_rewards', side_effect=RemoteError('beaconcha.in is down')),  # noqa: E501
        ):
            eth2.get_and_store_produced_blocks(indices=indices)
        return listed

    run([unrecorded], beaconchain_up=False, indices=[577475])
    assert _block_events(eth2.database, 26167074) == [(0, 577475, '0.000000000000000009')]
    assert eth2._mev_recheck() == {26167074}
    listed = run([], beaconchain_up=True, indices=[])
    assert listed.call_args.kwargs['indices'] == [577475], "asked about the block's validator"
    assert _block_events(eth2.database, 26167074) == [(0, 577475, '0.000000000000000009'), (1, 577475, '2')]  # noqa: E501
    assert eth2._mev_recheck() == set()


def test_validators_are_picked_while_the_nest_is_ordered(eth2, nuthatch: Nuthatch) -> None:
    """A validator whose last query is past its exit is not picked any more, unless a block of
    its waits for beaconcha.in, or Ethereum's order names a nest: the nest is asked by address,
    and no answer says it has nothing more to tell, so every validator is picked, by the
    periodic query once a day after the nest was last asked."""
    long_exited = Timestamp(ts_now() - 40 * 86400)
    _validator(eth2, exited=long_exited)
    with eth2.database.user_write() as write_cursor:
        eth2.database.set_dynamic_cache(write_cursor=write_cursor, name=DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS, value=ts_now(), index=577475)  # noqa: E501
        DBHistoryEvents(eth2.database).add_history_event(write_cursor, event=EthBlockEvent(
            validator_index=577475,
            timestamp=TimestampMS(1700000000000),
            amount=ONE,
            fee_recipient=WITHDRAWAL,
            fee_recipient_tracked=True,
            block_number=304,
            is_mev_reward=False,
        ))
    beaconchain = eth2.beacon_inquirer.beaconchain
    manual, periodic = beaconchain.get_validators_to_query_for_blocks, beaconchain.get_outdated_validators_to_query_for_blocks  # noqa: E501
    assert 577475 not in manual() and 577475 not in periodic()

    eth2._set_mev_recheck({304})
    assert 577475 in manual() and 577475 in periodic(), 'a block waiting for beaconcha.in'
    eth2._set_mev_recheck(set())

    cached = CachedSettings()
    order = {**cached._evm_indexers_order_per_chain, ChainID.ETHEREUM: (EvmIndexer.NUTHATCH,)}
    with patch.object(type(cached), '_evm_indexers_order_per_chain', order):
        assert 577475 in manual() and 577475 in periodic(), 'the nest was never asked'
        with eth2.database.user_write() as write_cursor:
            eth2.database.set_static_cache(write_cursor=write_cursor, name=DBCacheStatic.NUTHATCH_PRODUCED_LAST_RUN, value=ts_now())  # noqa: E501
        assert 577475 in manual(), 'a refresh always asks the nest'
        assert 577475 in periodic(), 'the nest has not proven anything of it yet'
        with eth2.database.user_write() as write_cursor:
            eth2.database.set_static_cache(write_cursor=write_cursor, name=DBCacheStatic.NUTHATCH_VALIDATOR_COVERAGE, value=json.dumps({'577475': [19_426_587, 26_199_999, 1800000000, 1700000000]}))  # noqa: E501
        assert 577475 not in periodic(), 'the periodic query waits a day'


def test_nest_range_with_a_block_nobody_could_be_named_for_is_kept(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """A served range is forgotten once the nest stopped asking the relays about it, but not
    while a block in it has nobody to book it to: a beacon node configured later can still name
    the proposer."""
    self_built = {'blockNumber': '26167080', 'timeStamp': '1767000072', 'feeRecipient': str(WITHDRAWAL).lower(), 'blockReward': '5', 'mevRecipient': '', 'mevReward': '', 'proposerPubkey': '', 'mev': 'unrecorded'}  # noqa: E501
    _track(eth2, WITHDRAWAL)
    _validator(eth2)
    with eth2.database.user_write() as write_cursor:
        eth2.database.set_static_cache(write_cursor=write_cursor, name=DBCacheStatic.NUTHATCH_PRODUCED_RANGES, value=json.dumps([[str(WITHDRAWAL), 0, 26_200_000, ts_now() - 40 * 86400]]))  # noqa: E501
        eth2.database.set_static_cache(write_cursor=write_cursor, name=DBCacheStatic.NUTHATCH_PRODUCED_VALIDATORS, value='[577475]')  # noqa: E501
        eth2.database.set_dynamic_cache(write_cursor=write_cursor, name=DBCacheDynamic.NEST_PRODUCED_BLOCKS_THROUGH, value=26_200_000, address=WITHDRAWAL)  # noqa: E501
    _nest_pass(eth2, nuthatch, {WITHDRAWAL: [self_built]})
    with eth2.database.conn.read_ctx() as cursor:
        kept = json.loads(eth2.database.get_static_cache(cursor=cursor, name=DBCacheStatic.NUTHATCH_PRODUCED_RANGES) or '[]')  # noqa: E501
    assert [str(WITHDRAWAL), 0, 26_200_000] in [entry[:3] for entry in kept]

    _nest_pass(eth2, nuthatch, {WITHDRAWAL: [self_built]}, proposer=577475)
    assert _block_events(eth2.database, 26167080) == [(0, 577475, '0.000000000000000005')]
    with eth2.database.conn.read_ctx() as cursor:
        kept = json.loads(eth2.database.get_static_cache(cursor=cursor, name=DBCacheStatic.NUTHATCH_PRODUCED_RANGES) or '[]')  # noqa: E501
    assert [str(WITHDRAWAL), 0, 26_200_000] not in [entry[:3] for entry in kept]


def test_nest_history_is_asked_again_once_a_validator_is_added(eth2, nuthatch: Nuthatch) -> None:
    """A block of a validator not tracked then was passed over, so adding one asks the
    addresses' history again, and its old block is booked."""
    other_pubkey = '0x' + 'cd' * 48
    _track(eth2, FEE_RECIPIENT)
    _validator(eth2)
    shared = {FEE_RECIPIENT: [{**PAID_BLOCK, 'proposerPubkey': other_pubkey}]}
    _nest_pass(eth2, nuthatch, shared)
    assert _block_events(eth2.database, 26167074) == []
    with eth2.database.user_write() as write_cursor:
        eth2.database.set_static_cache(write_cursor=write_cursor, name=DBCacheStatic.NUTHATCH_PRODUCED_RANGES, value='[]')  # noqa: E501

    _validator(eth2, index=7, pubkey=other_pubkey, withdrawal=FEE_RECIPIENT)
    asked: list[tuple[ChecksumEvmAddress, TimestampOrBlockRange]] = []
    _nest_pass(eth2, nuthatch, shared, asked=asked)
    assert any(address == FEE_RECIPIENT and period.from_value == 0 for address, period in asked)
    assert [validator for _, validator, _ in _block_events(eth2.database, 26167074)] == [7, 7]


def test_nest_produced_blocks_are_asked_from_where_its_history_starts(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """A nest keeping history from a later block than a validator's activation refuses the
    earlier part; it is asked again from its first block, and what it holds is booked."""
    _track(eth2, FEE_RECIPIENT)
    _validator(eth2)
    asked: list[tuple[ChecksumEvmAddress, TimestampOrBlockRange]] = []

    def nest(address: ChecksumEvmAddress, period: TimestampOrBlockRange) -> list[dict[str, Any]]:
        if period.from_value < 18_000_000:
            raise HistoryStartsLater('history starts at block 18000000', first_block=18_000_000)
        return [PAID_BLOCK] if address == FEE_RECIPIENT else []

    _nest_pass(eth2, nuthatch, nest, asked=asked)
    assert [(p.from_value, p.to_value) for a, p in asked if a == FEE_RECIPIENT][:2] == [(0, 26_200_000), (18_000_000, 26_200_000)]  # noqa: E501
    assert [validator for _, validator, _ in _block_events(eth2.database, 26167074)] == [577475, 577475]  # noqa: E501


@pytest.mark.parametrize('pass_between', [False, True])
def test_nest_history_is_asked_again_for_a_validator_removed_and_added_again(eth2, nuthatch: Nuthatch, pass_between: bool) -> None:  # noqa: E501
    """Removing a validator deletes its rewards, so adding it back, with or without a pass
    between, asks the addresses' history again; also when it was the only one."""
    _track(eth2, FEE_RECIPIENT)
    _validator(eth2)
    _nest_pass(eth2, nuthatch, {})
    with eth2.database.user_write() as write_cursor:
        eth2.database.set_static_cache(write_cursor=write_cursor, name=DBCacheStatic.NUTHATCH_PRODUCED_RANGES, value='[]')  # noqa: E501
    DBEth2(eth2.database).delete_validators([577475])
    if pass_between:
        _nest_pass(eth2, nuthatch, {})
    _validator(eth2)
    asked: list[tuple[ChecksumEvmAddress, TimestampOrBlockRange]] = []
    _nest_pass(eth2, nuthatch, {FEE_RECIPIENT: [PAID_BLOCK]}, asked=asked)
    assert any(address == FEE_RECIPIENT and period.from_value == 0 for address, period in asked)
    assert [validator for _, validator, _ in _block_events(eth2.database, 26167074)] == [577475, 577475]  # noqa: E501


def test_nest_range_with_a_block_that_did_not_read_is_kept(eth2, nuthatch: Nuthatch) -> None:
    _track(eth2, WITHDRAWAL)
    _validator(eth2)
    with eth2.database.user_write() as write_cursor:
        eth2.database.set_static_cache(write_cursor=write_cursor, name=DBCacheStatic.NUTHATCH_PRODUCED_RANGES, value=json.dumps([[str(WITHDRAWAL), 0, 26_200_000, ts_now() - 40 * 86400]]))  # noqa: E501
        eth2.database.set_static_cache(write_cursor=write_cursor, name=DBCacheStatic.NUTHATCH_PRODUCED_VALIDATORS, value='[577475]')  # noqa: E501
        eth2.database.set_dynamic_cache(write_cursor=write_cursor, name=DBCacheDynamic.NEST_PRODUCED_BLOCKS_THROUGH, value=26_200_000, address=WITHDRAWAL)  # noqa: E501
    _nest_pass(eth2, nuthatch, {WITHDRAWAL: [{**PAID_BLOCK, 'timeStamp': 'not a time'}]})
    with eth2.database.conn.read_ctx() as cursor:
        kept = json.loads(eth2.database.get_static_cache(cursor=cursor, name=DBCacheStatic.NUTHATCH_PRODUCED_RANGES) or '[]')  # noqa: E501
    assert [str(WITHDRAWAL), 0, 26_200_000] in [entry[:3] for entry in kept]


def _proven(index: int = 577475, block: int = 26167074, **fields: Any) -> dict[str, Any]:
    """A row of the nest's nuthatchValidatorBlocks: a block it proved `index` proposed."""
    return {
        'proposerIndex': str(index), 'blockNumber': str(block), 'timeStamp': '1767000000',
        'blockHash': '0x' + '11' * 32, 'feeRecipient': '0x4838b106fce9647bdf1e7877bf73ce8b0bad5f97',  # noqa: E501
        'blockReward': '9', 'mev': 'relay', 'mevRecipient': str(FEE_RECIPIENT).lower(),
        'mevReward': '2275207282975303', 'relays': 'flashbots,ultrasound', **fields,
    }


def _validator_page(rows: list[dict[str, Any]], through: Any = 26_199_998, **meta: Any) -> MockResponse:  # noqa: E501
    body = {'status': '1', 'message': 'OK', 'result': rows, 'generation': '7', 'supportedFrom': 19426587, 'verifiedThrough': through, **meta}  # noqa: E501
    return MockResponse(status_code=HTTPStatus.OK, text=json.dumps(body))


def test_nuthatch_validator_blocks_read_every_page_of_one_proof(nuthatch: Nuthatch) -> None:
    """Every page is read, through the snapshot page 1 was cut from, and the answer covers the
    validator through what the nest proved."""
    nuthatch.pagination_limit = 2
    pages = [
        _validator_page([_proven(block=19_500_000), _proven(block=19_500_001)]),
        _validator_page([_proven(block=19_600_000)]),
    ]
    with patch.object(nuthatch.session, 'get', side_effect=pages) as get:
        answer = nuthatch.get_validator_blocks(validator_index=577475, from_block=19_426_587)
    assert (answer.from_block, answer.through) == (19_426_587, 26_199_998)
    assert [row['blockNumber'] for row in answer.rows] == ['19500000', '19500001', '19600000']
    second = get.call_args_list[1].kwargs['params']
    assert (second['action'], second['validator'], second['page'], second['generation']) == ('nuthatchValidatorBlocks', '577475', '2', '7')  # noqa: E501
    assert 'endblock' not in second, 'without an end, the nest answers through what it proved'


@pytest.mark.parametrize('pages', [
    [_validator_page([_proven(index=1)])],  # another validator's block
    [_validator_page([{**_proven(), 'proposerIndex': None}])],  # no proposer
    [_validator_page([_proven()], through=None)],  # no proven bound
    [_validator_page([_proven(block=1), _proven(block=2)]), _validator_page([], through=5)],  # bounds that move  # noqa: E501
])
def test_nuthatch_validator_blocks_that_do_not_prove_the_validator_are_refused(nuthatch: Nuthatch, pages: list[MockResponse]) -> None:  # noqa: E501
    nuthatch.pagination_limit = 2
    with patch.object(nuthatch.session, 'get', side_effect=pages), pytest.raises(RemoteError):
        nuthatch.get_validator_blocks(validator_index=577475, from_block=19_426_587)


def test_nuthatch_validator_blocks_past_the_proof_are_refused(nuthatch: Nuthatch) -> None:
    """An answer through an end the nest says it has not proven yet is not taken."""
    with patch.object(nuthatch.session, 'get', return_value=_validator_page([], through=100)), pytest.raises(RemoteError):  # noqa: E501
        nuthatch.get_validator_blocks(validator_index=577475, from_block=50, to_block=200)


def test_nuthatch_watch_sync_follows_rotkis_validators(database, nuthatch: Nuthatch) -> None:
    """Every validator rotki tracks is watched, also one whose activation and withdrawal address
    are not known; a removed one is unwatched only if rotki removed it and no longer tracks it."""
    with database.user_write() as write_cursor:
        DBEth2(database).add_or_update_validators(write_cursor, [
            ValidatorDetails(validator_index=7, public_key=Eth2PubKey('0x' + '07' * 48), validator_type=ValidatorType.DISTRIBUTING),  # noqa: E501
            ValidatorDetails(validator_index=8, public_key=Eth2PubKey('0x' + '08' * 48), validator_type=ValidatorType.DISTRIBUTING, withdrawal_address=WITHDRAWAL, activation_timestamp=Timestamp(1600000000)),  # noqa: E501
        ])
    nuthatch.queue_unwatch_validators([9, 8])  # 8 was removed, then added again
    calls: list[tuple[str, str, dict | None]] = []

    def request(method: str, url: str, **kwargs: Any) -> MockResponse:
        path = url.split('127.0.0.1:8288', 1)[1]
        calls.append((method, path, kwargs.get('json')))
        if path == '/ready':
            return MockResponse(HTTPStatus.OK, '{"chain_id": 1}')
        return MockResponse(HTTPStatus.OK, json.dumps({'watched': [], 'validators': [8, 9, 10]}))

    cached = CachedSettings()
    order = {**cached._evm_indexers_order_per_chain, ChainID.ETHEREUM: (EvmIndexer.NUTHATCH,)}
    with (
        patch.object(type(cached), '_evm_indexers_order_per_chain', order),
        patch.object(nuthatch.session, 'request', side_effect=request),
    ):
        nuthatch.sync_watched()

    changes = [(path, body) for method, path, body in calls if method == 'POST' and 'validator' in (body or {})]  # noqa: E501
    assert changes == [('/api/watch', {'validator': 7}), ('/api/unwatch', {'validator': 9})]
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(cursor=cursor, name=DBCacheStatic.NUTHATCH_PENDING_UNWATCH_VALIDATORS) == '[]'  # noqa: E501


def _proven_pass(
        eth2,
        nuthatch: Nuthatch,
        answers: Any,
        head: int = 26_200_000,
        without_mev: set[int] | None = None,
        asked: list[tuple[int, int, int | None]] | None = None,
) -> tuple[set[int], set[int]]:
    """One pass of the nest's proven path. `answers` maps a validator to its rows, or is a
    callable of validator, first block and last block returning a ValidatorBlocks or raising."""
    def validator_blocks(validator_index: int, from_block: int, to_block: int | None = None) -> ValidatorBlocks:  # noqa: E501
        if asked is not None:
            asked.append((validator_index, from_block, to_block))
        if callable(answers):
            return answers(validator_index, from_block, to_block)
        return ValidatorBlocks(from_block, head - 1 if to_block is None else to_block, answers.get(validator_index, []))  # noqa: E501

    with (
        patch.object(eth2.ethereum, '_get_indexers_in_order', return_value=[(EvmIndexer.NUTHATCH, nuthatch)]),  # noqa: E501
        patch.object(nuthatch, 'finalized_head', return_value=(head, ts_now())),
        patch.object(nuthatch, 'sync_watched'),
        patch.object(nuthatch, 'get_validator_blocks', side_effect=validator_blocks),
        patch.object(nuthatch, 'block_timestamp', side_effect=lambda block: Timestamp(1700000000 + block - 19_426_587)),  # noqa: E501
    ):
        return eth2._get_and_store_proven_blocks_from_nest(blocks_without_mev=set() if without_mev is None else without_mev)  # noqa: E501


def _coverage(database) -> dict[str, list]:
    with database.conn.read_ctx() as cursor:
        return json.loads(database.get_static_cache(cursor=cursor, name=DBCacheStatic.NUTHATCH_VALIDATOR_COVERAGE) or '{}')  # noqa: E501


@pytest.mark.parametrize('recipient_tracked', [False, True])
def test_proven_block_is_booked_to_its_validator_wherever_its_rewards_went(eth2, nuthatch: Nuthatch, recipient_tracked: bool) -> None:  # noqa: E501
    """Validator 577475's block 26167074: the nest proves who proposed it, so it is booked to the
    validator whether or not its fee recipient is tracked, as income when it is and as
    information when it is not, and the validator is covered from Dencun through what the nest
    proved. Its produced-block query time is beaconcha.in's and does not move."""
    _validator(eth2)
    if recipient_tracked:
        _track(eth2, deserialize_evm_address(_proven()['feeRecipient']))
    unanswered, before = _proven_pass(eth2, nuthatch, {577475: [_proven()]})
    assert _block_events(eth2.database, 26167074) == [(0, 577475, '0.000000000000000009'), (1, 577475, '0.002275207282975303')]  # noqa: E501
    with eth2.database.conn.read_ctx() as cursor:
        kind = cursor.execute('SELECT type FROM history_events WHERE group_identifier=? AND sequence_index=0', ('BP1_26167074',)).fetchone()[0]  # noqa: E501
    expected = HistoryEventType.STAKING if recipient_tracked else HistoryEventType.INFORMATIONAL
    assert kind == expected.serialize()
    assert _coverage(eth2.database)['577475'][:2] == [19_426_587, 26_199_999]
    assert _cursor(eth2.database) is None
    assert unanswered == set()
    assert before == {577475}, 'active before Dencun, its earlier blocks are not covered'


def test_proven_path_asks_a_validator_nothing_is_known_about(eth2, nuthatch: Nuthatch) -> None:
    """A validator with no known activation or withdrawal address is asked about all the same,
    and, its activation unknown, its blocks before the proven interval are not claimed covered."""
    with eth2.database.user_write() as write_cursor:
        DBEth2(eth2.database).add_or_update_validators(write_cursor, [ValidatorDetails(
            validator_index=577475,
            public_key=Eth2PubKey(PUBKEY),
            validator_type=ValidatorType.DISTRIBUTING,
        )])
    _, before = _proven_pass(eth2, nuthatch, {577475: [_proven()]})
    assert [validator for _, validator, _ in _block_events(eth2.database, 26167074)] == [577475, 577475]  # noqa: E501
    assert before == {577475}


def test_proven_progress_moves_only_through_what_the_nest_proved(eth2, nuthatch: Nuthatch) -> None:
    """The next pass asks from the block after the proven interval; a validator proven to the
    nest's head is not asked; one that exited is not asked once proven through its exit; a
    validator activated after the proven interval began is fully covered."""
    _validator(eth2, index=1, pubkey='0x' + '01' * 48)
    _validator(eth2, index=2, pubkey='0x' + '02' * 48, exited=Timestamp(1700000000 + 100))
    with eth2.database.user_write() as write_cursor:
        write_cursor.execute('UPDATE eth2_validators SET activation_timestamp=? WHERE validator_index=2', (1800000000,))  # noqa: E501
    asked: list[tuple[int, int, int | None]] = []
    _proven_pass(eth2, nuthatch, {}, head=19_426_700, asked=asked)
    assert sorted(a for a in asked if a[2] is None) == [(1, 19_426_587, None), (2, 19_426_587, None)]  # noqa: E501

    asked.clear()
    _, before = _proven_pass(eth2, nuthatch, {}, head=19_426_800, asked=asked)
    assert [a for a in asked if a[2] is None] == [(1, 19_426_700, None)], 'proven through its exit, validator 2 is done'  # noqa: E501
    assert (2, 19_426_587, 19_426_699) in asked, 'its proven range is asked again for late relay records'  # noqa: E501
    assert _coverage(eth2.database)['1'][:2] == [19_426_587, 19_426_799]
    assert before == {1}

    asked.clear()
    _proven_pass(eth2, nuthatch, {}, head=19_426_800, asked=asked)
    assert [a for a in asked if a[2] is None] == [], 'proven to head - 1, nothing new to ask'


def test_proven_rows_that_name_another_validator_or_do_not_read_book_nothing(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """A row that does not read refuses the whole answer: nothing is stored, the validator is
    left uncovered and its progress does not move."""
    _validator(eth2)
    unanswered, _ = _proven_pass(eth2, nuthatch, {577475: [_proven(block=26167073), {**_proven(), 'timeStamp': 'not a time'}]})  # noqa: E501
    assert unanswered == {577475}
    assert _block_events(eth2.database, 26167073) == []
    assert _coverage(eth2.database) == {}


def test_proven_block_without_its_reward_is_kept_and_booked_later(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """A block whose reward the nest could not read is not booked at zero: its range is kept,
    and booked once the nest has the reward."""
    _validator(eth2)
    without_reward = {k: v for k, v in _proven().items() if k != 'blockReward'}
    _proven_pass(eth2, nuthatch, {577475: [{**without_reward, 'rewardStatus': 'unavailable'}]})
    assert _block_events(eth2.database, 26167074) == []
    _proven_pass(eth2, nuthatch, {577475: [_proven()]})
    assert _block_events(eth2.database, 26167074) == [(0, 577475, '0.000000000000000009'), (1, 577475, '0.002275207282975303')]  # noqa: E501


def test_proven_block_without_a_relay_record_gets_its_mev_later_once(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """No relay record is not no MEV: the block goes to the recheck, and when the nest later has
    the record, the MEV is added without the reward twice."""
    _validator(eth2)
    without_mev: set[int] = set()
    _proven_pass(eth2, nuthatch, {577475: [_proven(mev='unrecorded', mevRecipient='', mevReward='')]}, without_mev=without_mev)  # noqa: E501
    assert without_mev == {26167074}
    assert _block_events(eth2.database, 26167074) == [(0, 577475, '0.000000000000000009')]
    _proven_pass(eth2, nuthatch, {577475: [_proven()]})
    assert _block_events(eth2.database, 26167074) == [(0, 577475, '0.000000000000000009'), (1, 577475, '0.002275207282975303')]  # noqa: E501


def test_proof_replaces_an_earlier_guess_but_not_an_edit(eth2, nuthatch: Nuthatch) -> None:
    """Events an earlier source booked to another validator are replaced by the proven ones;
    events the user edited are kept as they are."""
    _validator(eth2)
    _validator(eth2, index=2, pubkey='0x' + '02' * 48)
    dbevents = DBHistoryEvents(eth2.database)
    guess = EthBlockEvent(validator_index=2, timestamp=TimestampMS(1767000000000), amount=ONE, fee_recipient=WITHDRAWAL, fee_recipient_tracked=False, block_number=26167074, is_mev_reward=False)  # noqa: E501
    edited = EthBlockEvent(validator_index=2, timestamp=TimestampMS(1767000000000), amount=ONE, fee_recipient=WITHDRAWAL, fee_recipient_tracked=False, block_number=26167075, is_mev_reward=False)  # noqa: E501
    with eth2.database.user_write() as write_cursor:
        dbevents.add_history_event(write_cursor=write_cursor, event=guess)
        dbevents.add_history_event(write_cursor=write_cursor, event=edited, mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED})  # noqa: E501
    _proven_pass(eth2, nuthatch, {577475: [_proven(), _proven(block=26167075)]})
    assert _block_events(eth2.database, 26167074) == [(0, 577475, '0.000000000000000009'), (1, 577475, '0.002275207282975303')]  # noqa: E501
    assert _block_events(eth2.database, 26167075)[0] == (0, 2, '1'), "the edit is the user's"


def test_address_answers_never_rebook_a_proven_block(eth2, nuthatch: Nuthatch) -> None:
    """Once the nest proved a block's proposer, a relay key naming another tracked validator in
    an address answer does not move it."""
    _track(eth2, FEE_RECIPIENT)
    _validator(eth2)
    other = '0x' + '02' * 48
    _validator(eth2, index=2, pubkey=other)
    _proven_pass(eth2, nuthatch, {577475: [_proven(mev='unrecorded', mevRecipient='', mevReward='')]})  # noqa: E501
    _nest_pass(eth2, nuthatch, {FEE_RECIPIENT: [{**PAID_BLOCK, 'proposerPubkey': other}]})
    assert [validator for _, validator, _ in _block_events(eth2.database, 26167074)] == [577475, 577475]  # noqa: E501


def test_proven_history_starting_later_leaves_the_earlier_blocks_uncovered(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """A nest whose proposer history starts after Dencun is asked from there, and the blocks
    before are left uncovered."""
    _validator(eth2)

    def later(validator_index: int, from_block: int, to_block: int | None) -> ValidatorBlocks:
        if from_block < 20_000_000:
            raise HistoryStartsLater('history starts at block 20000000', first_block=20_000_000)
        return ValidatorBlocks(from_block, 26_199_999, [])

    with patch.object(nuthatch, 'get_validator_blocks', side_effect=later):
        answer = eth2._ask_nest_for_validator(nuthatch, 577475, 19_426_587)
    assert (answer.from_block, answer.through) == (20_000_000, 26_199_999)


def _refusal(text: str) -> MockResponse:
    return MockResponse(status_code=HTTPStatus.OK, text=json.dumps({'status': '0', 'message': 'NOTOK', 'result': text}))  # noqa: E501


def test_nuthatch_validator_blocks_read_the_nests_refusals(nuthatch: Nuthatch) -> None:
    """In the nest's own words: before its first provable block the answer says where that is;
    with nothing proven past the stored interval yet, nothing new is answered and nothing fails;
    anything else is refused."""
    later = _refusal('NUTHATCH_UNSUPPORTED: proposals are proven from block 19500000; ask from there and use another source before it')  # noqa: E501
    with patch.object(nuthatch.session, 'get', return_value=later), pytest.raises(HistoryStartsLater) as starts:  # noqa: E501
        nuthatch.get_validator_blocks(validator_index=577475, from_block=19_426_587)
    assert starts.value.first_block == 19_500_000

    not_yet = _refusal("NUTHATCH_INCOMPLETE: validator 577475's proposals are not proven from block 26200000 yet")  # noqa: E501
    with patch.object(nuthatch.session, 'get', return_value=not_yet):
        answer = nuthatch.get_validator_blocks(validator_index=577475, from_block=26_200_000)
    assert (answer.through, answer.rows) == (26_199_999, [])

    unwatched = _refusal('NUTHATCH_INCOMPLETE: validator 577475 is not watched')
    with patch.object(nuthatch.session, 'get', return_value=unwatched), pytest.raises(RemoteError):
        nuthatch.get_validator_blocks(validator_index=577475, from_block=26_200_000)


def test_validator_removed_and_added_back_is_asked_from_the_start(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """Removing a validator deletes its blocks and what the nest proved for it, so adding it back
    asks for its blocks again, even an exited one proven through its exit."""
    _validator(eth2, exited=Timestamp(1700000000))
    _proven_pass(eth2, nuthatch, {577475: [_proven()]})
    DBEth2(eth2.database).delete_validators([577475])
    assert _block_events(eth2.database, 26167074) == []
    _validator(eth2, exited=Timestamp(1700000000))
    asked: list[tuple[int, int, int | None]] = []
    _proven_pass(eth2, nuthatch, {577475: [_proven()]}, asked=asked)
    assert (577475, 19_426_587, None) in asked
    assert [validator for _, validator, _ in _block_events(eth2.database, 26167074)] == [577475, 577475]  # noqa: E501


def test_answer_starting_later_than_asked_never_bridges_the_gap(eth2, nuthatch: Nuthatch) -> None:
    """Proven through block A, then a nest that proves only from B > A + 1: the interval kept
    restarts at B, and the blocks between stay uncovered."""
    _validator(eth2)
    _proven_pass(eth2, nuthatch, {}, head=19_426_700)  # proven 19,426,587 to 19,426,699

    def later(validator_index: int, from_block: int, to_block: int | None) -> ValidatorBlocks:
        if to_block is not None:
            return ValidatorBlocks(from_block, to_block, [])
        return ValidatorBlocks(20_000_000, 26_199_999, [])  # as the nest asked again from 20M

    _, before = _proven_pass(eth2, nuthatch, later, head=26_200_000)
    assert _coverage(eth2.database)['577475'][:2] == [20_000_000, 26_199_999]
    assert 577475 in before


def test_proof_without_its_reward_still_settles_who_proposed(eth2, nuthatch: Nuthatch) -> None:
    """A proven block whose reward the nest cannot read yet still takes effect: an earlier guess
    booking it to another validator goes, and an address answer naming another proposer books it
    to the proven one."""
    _track(eth2, FEE_RECIPIENT)
    _validator(eth2)
    other = '0x' + '02' * 48
    _validator(eth2, index=2, pubkey=other)
    guess = EthBlockEvent(validator_index=2, timestamp=TimestampMS(1767000000000), amount=ONE, fee_recipient=WITHDRAWAL, fee_recipient_tracked=False, block_number=26167074, is_mev_reward=False)  # noqa: E501
    with eth2.database.user_write() as write_cursor:
        DBHistoryEvents(eth2.database).add_history_event(write_cursor=write_cursor, event=guess)
    without_reward = {k: v for k, v in _proven().items() if k != 'blockReward'}
    _proven_pass(eth2, nuthatch, {577475: [{**without_reward, 'rewardStatus': 'unavailable'}]})
    assert _block_events(eth2.database, 26167074) == []
    _nest_pass(eth2, nuthatch, {FEE_RECIPIENT: [{**PAID_BLOCK, 'proposerPubkey': other}]})
    assert [validator for _, validator, _ in _block_events(eth2.database, 26167074)] == [577475, 577475]  # noqa: E501


@pytest.mark.parametrize(('guessed_recipient', 'guessed_as_income'), [
    (WITHDRAWAL, False),  # the wrong recipient, the right kind
    (deserialize_evm_address('0x4838b106fce9647bdf1e7877bf73ce8b0bad5f97'), True),  # the right recipient, booked as income  # noqa: E501
])
def test_proof_replaces_a_guess_with_the_wrong_recipient(eth2, nuthatch: Nuthatch, guessed_recipient: ChecksumEvmAddress, guessed_as_income: bool) -> None:  # noqa: E501
    """An earlier event with the right validator and amount but another fee recipient, or booked
    as income where the proven recipient is not tracked, is replaced by the proven information."""
    _validator(eth2)
    guess = EthBlockEvent(validator_index=577475, timestamp=TimestampMS(1767000000000), amount=FVal('0.000000000000000009'), fee_recipient=guessed_recipient, fee_recipient_tracked=guessed_as_income, block_number=26167074, is_mev_reward=False)  # noqa: E501
    with eth2.database.user_write() as write_cursor:
        DBHistoryEvents(eth2.database).add_history_event(write_cursor=write_cursor, event=guess)
    _proven_pass(eth2, nuthatch, {577475: [_proven()]})
    with eth2.database.conn.read_ctx() as cursor:
        label, kind = cursor.execute('SELECT location_label, type FROM history_events WHERE group_identifier=? AND sequence_index=0', ('BP1_26167074',)).fetchone()  # noqa: E501
    assert (label.lower(), kind) == (_proven()['feeRecipient'], HistoryEventType.INFORMATIONAL.serialize())  # noqa: E501


def test_a_later_source_cannot_book_a_proven_block_to_another_validator(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """beaconcha.in, asked after the nest, books by its own proposer; whatever it adds to a proven
    block for another validator is removed."""
    _validator(eth2)
    _validator(eth2, index=2, pubkey='0x' + '02' * 48)
    _proven_pass(eth2, nuthatch, {577475: [_proven(mev='unrecorded', mevRecipient='', mevReward='')]})  # noqa: E501
    mev = EthBlockEvent(validator_index=2, timestamp=TimestampMS(1767000000000), amount=ONE, fee_recipient=WITHDRAWAL, fee_recipient_tracked=False, block_number=26167074, is_mev_reward=True)  # noqa: E501
    with eth2.database.user_write() as write_cursor:
        DBHistoryEvents(eth2.database).add_history_event(write_cursor=write_cursor, event=mev)
    beaconchain = eth2.beacon_inquirer.beaconchain
    with (
        patch.object(eth2.ethereum, '_get_indexers_in_order', return_value=[(EvmIndexer.NUTHATCH, nuthatch)]),  # noqa: E501
        patch.object(eth2, '_get_and_store_proven_blocks_from_nest', return_value=(set(), set())),
        patch.object(eth2, '_get_and_store_produced_blocks_from_nest'),
        patch.object(beaconchain, 'has_api_key', return_value=True),
        patch.object(beaconchain, '_get_and_store_produced_blocks', return_value=set()),
    ):
        eth2.get_and_store_produced_blocks(indices=[577475])
    assert _block_events(eth2.database, 26167074) == [(0, 577475, '0.000000000000000009')]


@pytest.mark.parametrize('second', [
    {'generation': '8'},  # another snapshot
    {'supportedFrom': 19500000},  # another catalogue start
])
def test_nuthatch_validator_pages_from_different_proofs_are_refused(nuthatch: Nuthatch, second: dict[str, Any]) -> None:  # noqa: E501
    nuthatch.pagination_limit = 2
    pages = [
        _validator_page([_proven(block=19_500_000), _proven(block=19_500_001)]),
        _validator_page([_proven(block=19_600_000)], **second),
    ]
    with patch.object(nuthatch.session, 'get', side_effect=pages), pytest.raises(RemoteError):
        nuthatch.get_validator_blocks(validator_index=577475, from_block=19_426_587)


def test_nuthatch_range_asked_again_that_is_no_longer_proven_is_refused(nuthatch: Nuthatch) -> None:  # noqa: E501
    """Nothing new proven is an answer only to an open question: a remembered range the nest no
    longer proves is a refusal, so it stays to be asked again."""
    not_yet = _refusal("NUTHATCH_INCOMPLETE: validator 577475's proposals are not proven from block 26100000 yet")  # noqa: E501
    with patch.object(nuthatch.session, 'get', return_value=not_yet), pytest.raises(RemoteError):
        nuthatch.get_validator_blocks(validator_index=577475, from_block=26_100_000, to_block=26_150_000)  # noqa: E501


def test_beaconchain_failing_part_way_cannot_book_a_proven_block_to_another_validator(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """beaconcha.in stores what it read before failing; what it booked to a proven block for
    another validator is removed all the same."""
    _validator(eth2)
    _validator(eth2, index=2, pubkey='0x' + '02' * 48)
    _proven_pass(eth2, nuthatch, {577475: [_proven(mev='unrecorded', mevRecipient='', mevReward='')]})  # noqa: E501

    def store_then_fail(**kwargs: Any) -> set[int]:
        mev = EthBlockEvent(validator_index=2, timestamp=TimestampMS(1767000000000), amount=ONE, fee_recipient=WITHDRAWAL, fee_recipient_tracked=False, block_number=26167074, is_mev_reward=True)  # noqa: E501
        with eth2.database.user_write() as write_cursor:
            DBHistoryEvents(eth2.database).add_history_event(write_cursor=write_cursor, event=mev)
        raise RemoteError('beaconcha.in failed on the next block')

    beaconchain = eth2.beacon_inquirer.beaconchain
    with (
        patch.object(eth2.ethereum, '_get_indexers_in_order', return_value=[(EvmIndexer.NUTHATCH, nuthatch)]),  # noqa: E501
        patch.object(eth2, '_get_and_store_proven_blocks_from_nest', return_value=(set(), set())),
        patch.object(eth2, '_get_and_store_produced_blocks_from_nest'),
        patch.object(beaconchain, 'has_api_key', return_value=True),
        patch.object(beaconchain, '_get_and_store_produced_blocks', side_effect=store_then_fail),
    ):
        eth2.get_and_store_produced_blocks(indices=[577475])
    assert _block_events(eth2.database, 26167074) == [(0, 577475, '0.000000000000000009')]


def test_range_asked_again_whose_start_is_no_longer_proven_is_kept(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """A remembered range whose start a newer nest no longer proves is kept whole, and its
    validator reported not covered, so a reward owed before the new start is not forgotten."""
    _validator(eth2)
    with eth2.database.user_write() as write_cursor:
        eth2.database.set_static_cache(write_cursor=write_cursor, name=DBCacheStatic.NUTHATCH_VALIDATOR_RANGES, value=json.dumps([[577475, 19_500_000, 19_600_000, ts_now() - 40 * 86400]]))  # noqa: E501
        eth2.database.set_static_cache(write_cursor=write_cursor, name=DBCacheStatic.NUTHATCH_VALIDATOR_COVERAGE, value=json.dumps({'577475': [19_426_587, 26_199_999, 1800000000, 1700000000]}))  # noqa: E501

    def later(validator_index: int, from_block: int, to_block: int | None) -> ValidatorBlocks:
        if to_block is not None and from_block < 19_550_000:
            raise HistoryStartsLater('proposals are proven from block 19550000', first_block=19_550_000)  # noqa: E501
        return ValidatorBlocks(from_block, 26_199_999 if to_block is None else to_block, [])

    unanswered, _ = _proven_pass(eth2, nuthatch, later)
    with eth2.database.conn.read_ctx() as cursor:
        kept = json.loads(eth2.database.get_static_cache(cursor=cursor, name=DBCacheStatic.NUTHATCH_VALIDATOR_RANGES) or '[]')  # noqa: E501
    assert [577475, 19_500_000, 19_600_000] in [entry[:3] for entry in kept]
    assert 577475 in unanswered


def test_validator_without_activation_or_past_its_last_query_is_picked_for_the_nest(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """With the nest ordered, a registered validator is picked whatever its activation or its
    legacy query time says, so its proven blocks are asked for."""
    with eth2.database.user_write() as write_cursor:
        DBEth2(eth2.database).add_or_update_validators(write_cursor, [ValidatorDetails(
            validator_index=577475,
            public_key=Eth2PubKey(PUBKEY),
            validator_type=ValidatorType.DISTRIBUTING,
            exited_timestamp=Timestamp(ts_now() - 40 * 86400),
        )])
        eth2.database.set_dynamic_cache(write_cursor=write_cursor, name=DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS, value=ts_now(), index=577475)  # noqa: E501
        eth2.database.set_static_cache(write_cursor=write_cursor, name=DBCacheStatic.NUTHATCH_PRODUCED_LAST_RUN, value=ts_now())  # noqa: E501
    beaconchain = eth2.beacon_inquirer.beaconchain
    cached = CachedSettings()
    order = {**cached._evm_indexers_order_per_chain, ChainID.ETHEREUM: (EvmIndexer.NUTHATCH,)}
    with patch.object(type(cached), '_evm_indexers_order_per_chain', order):
        assert 577475 in beaconchain.get_validators_to_query_for_blocks()
        assert 577475 in beaconchain.get_outdated_validators_to_query_for_blocks()


def test_proven_range_still_waiting_for_a_relay_record_is_kept(eth2, nuthatch: Nuthatch) -> None:
    """A range past rotki's own settling time is kept while the nest still answers a block in it
    without a relay record, as the nest may still learn one."""
    _validator(eth2)
    with eth2.database.user_write() as write_cursor:
        eth2.database.set_static_cache(write_cursor=write_cursor, name=DBCacheStatic.NUTHATCH_VALIDATOR_RANGES, value=json.dumps([[577475, 26_100_000, 26_199_999, ts_now() - 40 * 86400]]))  # noqa: E501
        eth2.database.set_static_cache(write_cursor=write_cursor, name=DBCacheStatic.NUTHATCH_VALIDATOR_COVERAGE, value=json.dumps({'577475': [19_426_587, 26_199_999, 1800000000, 1700000000]}))  # noqa: E501
    _proven_pass(eth2, nuthatch, {577475: [_proven(mev='unrecorded', mevRecipient='', mevReward='')]})  # noqa: E501
    with eth2.database.conn.read_ctx() as cursor:
        kept = json.loads(eth2.database.get_static_cache(cursor=cursor, name=DBCacheStatic.NUTHATCH_VALIDATOR_RANGES) or '[]')  # noqa: E501
    assert [577475, 26_100_000, 26_199_999] in [entry[:3] for entry in kept]


def test_withdrawals_before_the_nests_history_are_asked_from_its_start_and_told(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """With only the nest ordered, a withdrawals range starting before its history is asked again
    from its first block, no other service is asked, the query time is not moved past the period
    nothing covered, and the user is told once per session, not on every refresh."""
    _validator(eth2)
    asked: list[TimestampOrBlockRange] = []

    def withdrawals(address: ChecksumEvmAddress, period: TimestampOrBlockRange) -> set[int]:
        asked.append(period)
        if period.from_value < 25_870_000:
            raise HistoryStartsLater('history starts at block 25870000', first_block=25_870_000)
        with eth2.database.user_write() as write_cursor:  # as the source does, page by page
            eth2.database.set_dynamic_cache(write_cursor=write_cursor, name=DBCacheDynamic.WITHDRAWALS_TS, value=ts_now(), address=address)  # noqa: E501
        return {1}

    cached = CachedSettings()
    nest_only = {**cached._evm_indexers_order_per_chain, ChainID.ETHEREUM: (EvmIndexer.NUTHATCH,)}
    with (
        patch.object(type(cached), '_evm_indexers_order_per_chain', nest_only),
        patch.object(eth2.ethereum, '_get_indexers_in_order', return_value=[(EvmIndexer.NUTHATCH, nuthatch)]),  # noqa: E501
        patch.object(eth2.ethereum, 'maybe_timestamp_to_block_range', side_effect=lambda period: TimestampOrBlockRange('blocks', 0, 26_200_000)),  # noqa: E501
        patch.object(nuthatch, 'get_withdrawals', side_effect=withdrawals),
        patch.object(eth2.ethereum.etherscan, 'get_withdrawals', return_value={6}) as etherscan,
        patch.object(eth2.ethereum.blockscout, 'query_withdrawals', return_value={7}) as blockscout,  # noqa: E501
        patch.object(eth2.beacon_inquirer, 'get_validator_data', return_value=[]),
        patch.object(eth2.msg_aggregator, 'add_warning') as warning,
    ):
        eth2.query_single_address_withdrawals(WITHDRAWAL, ts_now())
        eth2.query_single_address_withdrawals(WITHDRAWAL, ts_now())

    assert [(p.from_value, p.to_value) for p in asked[:2]] == [(0, 26_200_000), (25_870_000, 26_200_000)]  # noqa: E501
    assert etherscan.call_count == blockscout.call_count == 0
    with eth2.database.conn.read_ctx() as cursor:
        assert eth2.database.get_dynamic_cache(cursor=cursor, name=DBCacheDynamic.WITHDRAWALS_TS, address=WITHDRAWAL) is None  # noqa: E501
    assert warning.call_count == 1
    assert '25870000' in warning.call_args.args[0]


def test_withdrawals_are_asked_of_the_nest_through_its_head(nuthatch: Nuthatch) -> None:
    """A range ending past the blocks the nest has read, as one resolved against its RPC's newest
    block does, is asked only through the nest's head, which it would otherwise refuse whole. A
    range starting past the head asks nothing."""
    with (
        patch.object(nuthatch, 'finalized_head', return_value=(26_205_915, Timestamp(1792165000))),
        patch.object(Etherscan, 'get_withdrawals', return_value={5}) as etherscan,
    ):
        assert nuthatch.get_withdrawals(ADDRESS, TimestampOrBlockRange('blocks', 17_030_000, 26_205_964)) == {5}  # noqa: E501
        assert nuthatch.get_withdrawals(ADDRESS, TimestampOrBlockRange('blocks', 26_205_920, 26_205_964)) == set()  # noqa: E501
        assert nuthatch.get_withdrawals(ADDRESS, TimestampOrBlockRange('timestamps', 1700000000, 1792165600)) == {5}  # noqa: E501

    periods = [call.kwargs['period'] for call in etherscan.call_args_list]
    assert [(p.range_type, p.from_value, p.to_value) for p in periods] == [
        ('blocks', 17_030_000, 26_205_915),
        ('timestamps', 1700000000, 1792165000),
    ]


def test_withdrawals_of_a_nest_starting_before_shapella_are_not_told_as_uncovered(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """A nest whose history starts before Shapella misses no withdrawal: it is asked from its
    first block, nobody is warned, and the query time is not put back."""
    _validator(eth2)
    asked: list[TimestampOrBlockRange] = []
    now = ts_now()

    def withdrawals(address: ChecksumEvmAddress, period: TimestampOrBlockRange) -> set[int]:
        asked.append(period)
        if period.from_value < 17_030_000:
            raise HistoryStartsLater('history starts at block 17030000', first_block=17_030_000)
        with eth2.database.user_write() as write_cursor:
            eth2.database.set_dynamic_cache(write_cursor=write_cursor, name=DBCacheDynamic.WITHDRAWALS_TS, value=now, address=address)  # noqa: E501
        return set()

    cached = CachedSettings()
    nest_only = {**cached._evm_indexers_order_per_chain, ChainID.ETHEREUM: (EvmIndexer.NUTHATCH,)}
    with (
        patch.object(type(cached), '_evm_indexers_order_per_chain', nest_only),
        patch.object(eth2.ethereum, '_get_indexers_in_order', return_value=[(EvmIndexer.NUTHATCH, nuthatch)]),  # noqa: E501
        patch.object(eth2.ethereum, 'maybe_timestamp_to_block_range', side_effect=lambda period: TimestampOrBlockRange('blocks', 0, 26_200_000)),  # noqa: E501
        patch.object(nuthatch, 'get_withdrawals', side_effect=withdrawals),
        patch.object(eth2.beacon_inquirer, 'get_validator_data', return_value=[]),
        patch.object(eth2.msg_aggregator, 'add_warning') as warning,
    ):
        eth2.query_single_address_withdrawals(WITHDRAWAL, now)

    assert [(p.from_value, p.to_value) for p in asked] == [(0, 26_200_000), (17_030_000, 26_200_000)]  # noqa: E501
    assert warning.call_count == 0
    with eth2.database.conn.read_ctx() as cursor:
        assert eth2.database.get_dynamic_cache(cursor=cursor, name=DBCacheDynamic.WITHDRAWALS_TS, address=WITHDRAWAL) is not None  # noqa: E501


def test_withdrawals_go_nowhere_unchosen_when_the_ordered_nest_is_dropped(eth2, nuthatch: Nuthatch) -> None:  # noqa: E501
    """A nest ordered alone but dropped for the session leaves no indexer to ask: the address
    does not go to etherscan or blockscout, which the user did not choose."""
    cached = CachedSettings()
    nest_only = {**cached._evm_indexers_order_per_chain, ChainID.ETHEREUM: (EvmIndexer.NUTHATCH,)}
    period = TimestampOrBlockRange(range_type='blocks', from_value=17034870, to_value=17300000)
    with (
        patch.object(type(cached), '_evm_indexers_order_per_chain', nest_only),
        patch.object(eth2.ethereum, '_get_indexers_in_order', return_value=[]),
        patch.object(eth2.ethereum.etherscan, 'get_withdrawals', return_value={6}) as etherscan,
        patch.object(eth2.ethereum.blockscout, 'query_withdrawals', return_value={7}) as blockscout,  # noqa: E501
    ):
        assert eth2._fetch_withdrawals_from_external_sources(ADDRESS, period) is None
    assert etherscan.call_count == blockscout.call_count == 0


@pytest.mark.parametrize('fails', ['shortened query', 'validator lookup'])
def test_withdrawals_query_time_is_put_back_whatever_fails_after_a_refusal(eth2, nuthatch: Nuthatch, fails: str) -> None:  # noqa: E501
    """The source records its progress page by page. If the query asked again from the nest's
    first block fails after a page, or the validator lookup after it fails, the query time is
    still put back, so the period nothing covered is asked for again."""
    _validator(eth2)

    def withdrawals(address: ChecksumEvmAddress, period: TimestampOrBlockRange) -> set[int]:
        if period.from_value < 25_870_000:
            raise HistoryStartsLater('history starts at block 25870000', first_block=25_870_000)
        with eth2.database.user_write() as write_cursor:
            eth2.database.set_dynamic_cache(write_cursor=write_cursor, name=DBCacheDynamic.WITHDRAWALS_TS, value=ts_now(), address=address)  # noqa: E501
            eth2.database.set_dynamic_cache(write_cursor=write_cursor, name=DBCacheDynamic.WITHDRAWALS_IDX, value=123456, address=address)  # noqa: E501
        if fails == 'shortened query':
            raise RemoteError('the second page failed')
        return {1}

    cached = CachedSettings()
    nest_only = {**cached._evm_indexers_order_per_chain, ChainID.ETHEREUM: (EvmIndexer.NUTHATCH,)}
    with (
        patch.object(type(cached), '_evm_indexers_order_per_chain', nest_only),
        patch.object(eth2.ethereum, '_get_indexers_in_order', return_value=[(EvmIndexer.NUTHATCH, nuthatch)]),  # noqa: E501
        patch.object(eth2.ethereum, 'maybe_timestamp_to_block_range', side_effect=lambda period: TimestampOrBlockRange('blocks', 0, 26_200_000)),  # noqa: E501
        patch.object(nuthatch, 'get_withdrawals', side_effect=withdrawals),
        patch.object(eth2.beacon_inquirer, 'get_validator_data', side_effect=RemoteError('beacon down')),  # noqa: E501
        patch.object(eth2.msg_aggregator, 'add_warning'),
        contextlib.suppress(RemoteError),
    ):
        eth2.query_single_address_withdrawals(WITHDRAWAL, ts_now())
    with eth2.database.conn.read_ctx() as cursor:
        assert eth2.database.get_dynamic_cache(cursor=cursor, name=DBCacheDynamic.WITHDRAWALS_TS, address=WITHDRAWAL) is None  # noqa: E501
        assert eth2.database.get_dynamic_cache(cursor=cursor, name=DBCacheDynamic.WITHDRAWALS_IDX, address=WITHDRAWAL) is None, 'blockscout must not stop short of the gap'  # noqa: E501
