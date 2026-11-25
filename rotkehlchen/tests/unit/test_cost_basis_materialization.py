import json
import threading
from typing import TYPE_CHECKING, Any, Final
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.accounting.cost_basis.lots import BucketLots
from rotkehlchen.accounting.cost_basis.pnl import get_unprocessed_from_ts
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.ethereum.constants import SHAPPELA_TIMESTAMP
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.constants.assets import A_BTC, A_DAI, A_ETH, A_ETH2, A_USD
from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.db.cache import DBCacheStatic, mark_stale_from_ts
from rotkehlchen.db.constants import HistoryMappingState, UpdateType
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.db.updates import RotkiDataUpdater
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import RemoteError, remote_error_for_status
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import MANUAL_PRICE_CHANGES_RETENTION_MS, GlobalDBHandler
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.types import DataIssueFilters
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.price import HistoricalOracleState, PriceHistorian
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.locations.constants import (
    LOCATION_BITCOIN,
    LOCATION_ETHEREUM,
    LOCATION_KRAKEN,
    LOCATION_OPTIMISM,
)
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tasks.cost_basis import (
    _CostBasisPass,
    _Rules,
    get_cost_basis_stalled_info,
    process_balances_and_cost_basis,
    process_cost_basis,
)
from rotkehlchen.tasks.historical_balances import Bucket, process_historical_balances
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import (
    CacheType,
    CostBasisMethod,
    Price,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash

pytestmark = pytest.mark.accounting_update

# Base timestamp well above 86400 so Windows datetime.fromtimestamp(ts).astimezone()
# does not fail with EINVAL (python/cpython#107078).
BASE_TS: Final = 1_700_000_000
# The price of ETH at each second offset from BASE_TS the tests place an event at.
ETH_PRICES: Final = {
    BASE_TS + second: price
    for second, price in {
        1: 1000, 2: 3000, 3: 2000, 4: 4000, 5: 5000, 6: 1200, 7: 1500, 8: 1700,
    }.items()
}
ROW_COLUMNS: Final = (
    'event_identifier, location_label, asset, direction, lot_created_id, basis_per_unit, '
    'basis_source, lots_consumed_json, realized_pnl, basis_removed, post_spend_basis_remaining, '
    'method'
)


def _ts(at: int) -> Timestamp:
    return Timestamp(BASE_TS + at)


def _ts_ms(at: int) -> TimestampMS:
    return TimestampMS((BASE_TS + at) * 1000)


@pytest.fixture(name='queried_prices')
def fixture_queried_prices() -> Iterator[list[tuple[str, Timestamp]]]:
    """Price ETH by ETH_PRICES, DAI and USD at 1, nothing else. Yields the queries made."""
    queried: list[tuple[str, Timestamp]] = []

    def query_historical_price(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        queried.append((from_asset.identifier, timestamp))
        if from_asset == A_ETH:
            return Price(FVal(ETH_PRICES[timestamp]))
        if from_asset in (A_DAI, A_USD):
            return Price(FVal(1))
        raise NoPriceForGivenTimestamp(from_asset=from_asset, to_asset=to_asset, time=timestamp)

    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price = query_historical_price
        yield queried


def _event(
        at: int,
        amount: str,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType = HistoryEventSubType.NONE,
        location_label: ChecksumEvmAddress = TEST_ADDR1,
        asset: Asset = A_ETH,
        tx_ref: EVMTxHash | None = None,
        sequence_index: int = 0,
        address: ChecksumEvmAddress | None = None,
) -> EvmEvent:
    return EvmEvent(
        tx_ref=make_evm_tx_hash() if tx_ref is None else tx_ref,
        sequence_index=sequence_index,
        timestamp=_ts_ms(at),
        location=LOCATION_ETHEREUM,
        event_type=event_type,
        event_subtype=event_subtype,
        asset=asset,
        amount=FVal(amount),
        location_label=location_label,
        address=address,
    )


def _add_rule(
        database: DBHandler,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType = HistoryEventSubType.NONE,
        taxable: bool = True,
        count_entire_amount_spend: bool = False,
        count_cost_basis_pnl: bool = True,
        accounting_treatment: TxAccountingTreatment | None = None,
        event_ids: list[int] | None = None,
) -> None:
    DBAccountingRules(database).add_accounting_rule(
        event_type=event_type,
        event_subtype=event_subtype,
        counterparty=None,
        rule=BaseEventSettings(
            taxable=taxable,
            count_entire_amount_spend=count_entire_amount_spend,
            count_cost_basis_pnl=count_cost_basis_pnl,
            accounting_treatment=accounting_treatment,
        ),
        links={},
        event_ids=event_ids,
    )


def _process(
        database: DBHandler,
        events: list[EvmEvent | HistoryEvent],
        method: CostBasisMethod,
        **settings: Any,
) -> list[str]:
    """Add the events and process the cost basis.

    Plain spends realize the difference to their basis and trades are swaps, as by the rules
    that rotki ships. Returns the identifiers of the events, as the lots they create are named.
    """
    _add_rule(database, HistoryEventType.SPEND)
    _add_rule(
        database=database,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        accounting_treatment=TxAccountingTreatment.SWAP,
    )
    with database.user_write() as write_cursor:
        database.set_settings(
            write_cursor,
            ModifiableDBSettings(cost_basis_method=method, **settings),
        )
        identifiers = [
            str(DBHistoryEvents(database).add_history_event(write_cursor=write_cursor, event=event))  # noqa: E501
            for event in events
        ]

    assert process_cost_basis(database, database.msg_aggregator) is True
    return identifiers


def _rows(database: DBHandler, columns: str = ROW_COLUMNS) -> list[tuple[Any, ...]]:
    with database.conn.read_ctx() as cursor:
        return cursor.execute(
            f'SELECT {columns} FROM event_cost_basis ORDER BY timestamp, sequence_index, id',
        ).fetchall()


def _spend_row(
        database: DBHandler,
        identifier: str,
) -> tuple[list[tuple[str, FVal]], FVal, FVal, FVal]:
    """The (lot, amount) pairs a spend consumed, its PnL, and the basis removed and remaining."""
    with database.conn.read_ctx() as cursor:
        lots, pnl, removed, remaining = cursor.execute(
            'SELECT lots_consumed_json, realized_pnl, basis_removed, post_spend_basis_remaining '
            'FROM event_cost_basis WHERE event_identifier=? AND direction=?',
            (identifier, 'spend'),
        ).fetchone()

    return (
        [(lot['lot_id'], FVal(lot['amount_consumed'])) for lot in json.loads(lots)],
        FVal(pnl),
        FVal(removed),
        FVal(remaining),
    )


def _three_lots_and_a_spend() -> list[EvmEvent | HistoryEvent]:
    """Lots of 1 ETH bought at 1000, 3000 and 2000, and then 1.5 ETH spent at 4000."""
    return [
        _event(at=1, amount='1', event_type=HistoryEventType.RECEIVE),
        _event(at=2, amount='1', event_type=HistoryEventType.RECEIVE),
        _event(at=3, amount='1', event_type=HistoryEventType.RECEIVE),
        _event(at=4, amount='1.5', event_type=HistoryEventType.SPEND),
    ]


@pytest.mark.parametrize(('method', 'consumed', 'pnl', 'removed', 'remaining'), [
    (CostBasisMethod.FIFO, [(0, '1'), (1, '0.5')], 3500, 2500, 3500),
    (CostBasisMethod.LIFO, [(2, '1'), (1, '0.5')], 2500, 3500, 2500),
    (CostBasisMethod.HIFO, [(1, '1'), (2, '0.5')], 2000, 4000, 2000),
    (CostBasisMethod.ACB, [(0, '1'), (1, '0.5')], 3000, 3000, 3000),
])
@pytest.mark.usefixtures('queried_prices')
def test_spend_consumes_lots_in_method_order(
        database: DBHandler,
        method: CostBasisMethod,
        consumed: list[tuple[int, str]],
        pnl: int,
        removed: int,
        remaining: int,
) -> None:
    identifiers = _process(database=database, method=method, events=_three_lots_and_a_spend())
    assert _rows(database)[:3] == [(
        int(identifier), TEST_ADDR1, 'ETH', 'receive', identifier, price, 'price_oracle',
        None, None, None, None, method.serialize(),
    ) for identifier, price in zip(identifiers[:3], ('1000', '3000', '2000'), strict=True)]
    assert _spend_row(database, identifiers[3]) == (
        [(identifiers[idx], FVal(amount)) for idx, amount in consumed],
        FVal(pnl),
        FVal(removed),
        FVal(remaining),
    )


@pytest.mark.parametrize('method', list(CostBasisMethod))
@pytest.mark.usefixtures('queried_prices')
def test_transfer_between_owned_accounts_keeps_the_lot(
        database: DBHandler,
        method: CostBasisMethod,
) -> None:
    received, transferred, spent = _process(database=database, method=method, events=[
        _event(at=1, amount='2', event_type=HistoryEventType.RECEIVE),
        _event(at=6, amount='2', event_type=HistoryEventType.TRANSFER, address=TEST_ADDR2),
        _event(at=7, amount='1', event_type=HistoryEventType.SPEND, location_label=TEST_ADDR2),
    ])
    assert _spend_row(database, transferred) == (
        [(received, FVal(2))],
        FVal(0),  # moving the asset realizes nothing
        FVal(2000),
        FVal(0),
    )
    assert _rows(
        database=database,
        columns='location_label, direction, lot_created_id, basis_per_unit, basis_source',
    )[2] == (TEST_ADDR2, 'receive', received, '1000', 'transfer_in')
    assert _spend_row(database, spent) == ([(received, FVal(1))], FVal(500), FVal(1000), FVal(1000))  # noqa: E501


@pytest.mark.parametrize(('method', 'consumed_lot', 'pnl'), [
    (CostBasisMethod.FIFO, 0, 3000),  # the lot received at 1 is the first one acquired
    (CostBasisMethod.LIFO, 1, 1000),
])
@pytest.mark.usefixtures('queried_prices')
def test_transferred_lot_keeps_its_acquisition_order(
        database: DBHandler,
        method: CostBasisMethod,
        consumed_lot: int,
        pnl: int,
) -> None:
    """A lot moved into a bucket that already holds lots is consumed by when it was acquired,
    not by when it arrived, and a spend lists only the lots it took something from."""
    identifiers = _process(database=database, method=method, events=[
        _event(at=1, amount='1', event_type=HistoryEventType.RECEIVE),
        _event(at=2, amount='1', event_type=HistoryEventType.RECEIVE, location_label=TEST_ADDR2),
        _event(at=3, amount='1', event_type=HistoryEventType.TRANSFER, address=TEST_ADDR2),
        _event(at=4, amount='1', event_type=HistoryEventType.SPEND, location_label=TEST_ADDR2),
    ])
    assert _spend_row(database, identifiers[3])[:2] == (
        [(identifiers[consumed_lot], FVal(1))],
        FVal(pnl),
    )


@pytest.mark.parametrize('method', list(CostBasisMethod))
@pytest.mark.parametrize(('include_crypto2crypto', 'pnl'), [(True, 500), (False, 0)])
@pytest.mark.usefixtures('queried_prices')
def test_swap_writes_both_directions(
        database: DBHandler,
        method: CostBasisMethod,
        include_crypto2crypto: bool,
        pnl: int,
) -> None:
    acquired, spent, received, _, bought = _process(
        database=database,
        method=method,
        include_crypto2crypto=include_crypto2crypto,
        events=[
            _event(at=1, amount='1', event_type=HistoryEventType.RECEIVE),
            _event(
                at=7,
                amount='1',
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                tx_ref=(tx_ref := make_evm_tx_hash()),
            ), _event(
                at=7,
                amount='2000',
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_DAI,
                tx_ref=tx_ref,
                sequence_index=1,
            ), HistoryEvent(
                group_identifier='fiat_buy',
                sequence_index=0,
                timestamp=_ts_ms(7),
                location=LOCATION_KRAKEN,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                asset=A_USD,
                amount=FVal('3200'),
                location_label='kraken',
            ), HistoryEvent(
                group_identifier='fiat_buy',
                sequence_index=1,
                timestamp=_ts_ms(7),
                location=LOCATION_KRAKEN,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_ETH,
                amount=FVal('2'),
                location_label='kraken',
            ),
        ],
    )
    assert _spend_row(database, spent) == ([(acquired, FVal(1))], FVal(pnl), FVal(1000), FVal(0))
    receives = _rows(database, 'event_identifier, direction, basis_per_unit, basis_source')[2:]
    assert set(receives) == {
        (int(received), 'receive', '0.75', 'price_oracle'),
        (int(bought), 'receive', '1600', 'event_amount'),
    }


@pytest.mark.usefixtures('queried_prices')
def test_swap_does_not_pair_a_spend_with_a_fee_when_the_receive_is_ignored(
        database: DBHandler,
) -> None:
    with database.user_write() as write_cursor:
        database.add_to_ignored_assets(write_cursor, A_DAI)

    acquired, spent, _, fee = _process(
        database=database,
        method=CostBasisMethod.FIFO,
        include_crypto2crypto=False,
        events=[
            _event(at=1, amount='2', event_type=HistoryEventType.RECEIVE),
            _event(
                at=7,
                amount='1',
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                tx_ref=(tx_ref := make_evm_tx_hash()),
            ), _event(
                at=7,
                amount='1500',
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_DAI,
                tx_ref=tx_ref,
                sequence_index=1,
            ), _event(
                at=7,
                amount='0.1',
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.FEE,
                tx_ref=tx_ref,
                sequence_index=2,
            ),
        ],
    )
    assert _spend_row(database, spent) == (
        [(acquired, FVal(1))], FVal(500), FVal(1000), FVal(1000),
    )
    assert _spend_row(database, fee) == ([(acquired, FVal('0.1'))], FVal(0), FVal(100), FVal(900))


@pytest.mark.parametrize('method', list(CostBasisMethod))
@pytest.mark.usefixtures('queried_prices')
def test_receive_without_price_has_zero_cost(database: DBHandler, method: CostBasisMethod) -> None:
    _process(database=database, method=method, events=[_event(
        at=1,
        amount='1',
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.AIRDROP,
        asset=asset,
        sequence_index=sequence_index,
    ) for sequence_index, asset in enumerate((A_ETH, A_BTC))])
    assert _rows(database, 'asset, basis_per_unit, basis_source') == [
        ('ETH', '1000', 'price_oracle'),
        ('BTC', '0', 'zero_cost'),
    ]


@pytest.mark.parametrize('method', list(CostBasisMethod))
@pytest.mark.parametrize('from_ts', [0, _ts_ms(3), _ts_ms(5)])
@pytest.mark.usefixtures('queried_prices')
def test_reprocessing_is_idempotent(
        database: DBHandler,
        method: CostBasisMethod,
        from_ts: int,
) -> None:
    _process(database=database, method=method, events=[
        _event(at=1, amount='1', event_type=HistoryEventType.RECEIVE),
        _event(at=2, amount='1', event_type=HistoryEventType.RECEIVE),
        _event(at=3, amount='1.5', event_type=HistoryEventType.TRANSFER, address=TEST_ADDR2),
        _event(at=4, amount='1', event_type=HistoryEventType.RECEIVE, location_label=TEST_ADDR2),
        _event(at=5, amount='2', event_type=HistoryEventType.SPEND, location_label=TEST_ADDR2),
        _event(at=6, amount='0.5', event_type=HistoryEventType.SPEND),
    ])
    assert len(rows := _rows(database)) == 7

    with database.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO key_value_cache(name, value) VALUES (?, ?)',
            [
                (DBCacheStatic.STALE_COST_BASIS_FROM_TS.value, str(from_ts)),
                (DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS.value, '1'),
            ],
        )

    assert process_cost_basis(database, database.msg_aggregator) is True
    assert _rows(database) == rows


@pytest.mark.parametrize(('method', 'consumed', 'pnl'), [
    (CostBasisMethod.FIFO, [(1, '0.5'), (2, '1')], 4000),
    (CostBasisMethod.LIFO, [(1, '0.5'), (0, '1')], 5000),
    (CostBasisMethod.HIFO, [(2, '0.5'), (0, '1')], 5500),
    (CostBasisMethod.ACB, [(1, '0.5'), (2, '1')], 4500),
])
def test_resume_from_stale_marker(
        database: DBHandler,
        queried_prices: list[tuple[str, Timestamp]],
        method: CostBasisMethod,
        consumed: list[tuple[int, str]],
        pnl: int,
) -> None:
    identifiers = _process(database=database, method=method, events=_three_lots_and_a_spend())
    rows_before = _rows(database, f'id, {ROW_COLUMNS}')
    with database.conn.read_ctx() as cursor:
        assert database.get_static_caches(cursor=cursor, names=(
            DBCacheStatic.STALE_COST_BASIS_FROM_TS,
            DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS,
        )) == (None, None)
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.LAST_COST_BASIS_PROCESSING_TS,
        ) is not None

    queried_prices.clear()
    with database.user_write() as write_cursor:
        spent = str(DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=_event(at=5, amount='1.5', event_type=HistoryEventType.SPEND),
        ))

    # Adding an event marks both pipelines. The balances were not processed here, so their
    # marker is still at the first event, while the cost basis one starts at the new event.
    with database.conn.read_ctx() as cursor:
        assert database.get_static_caches(cursor=cursor, names=(
            DBCacheStatic.STALE_BALANCES_FROM_TS,
            DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        )) == (str(_ts_ms(1)), str(_ts_ms(5)))

    assert process_cost_basis(database, database.msg_aggregator) is True
    assert queried_prices == [('ETH', _ts(5))]  # the basis of the earlier lots comes from their rows  # noqa: E501
    assert _rows(database, f'id, {ROW_COLUMNS}')[:-1] == rows_before
    assert _spend_row(database, spent)[:2] == (
        [(identifiers[idx], FVal(amount)) for idx, amount in consumed],
        FVal(pnl),
    )
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        ) is None


@pytest.mark.usefixtures('queried_prices')
def test_rate_limited_prices_keep_the_pass_stale(database: DBHandler) -> None:
    def rate_limited_at_two(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        if timestamp == _ts(2):
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
                rate_limited=True,
            )
        return Price(FVal(1000))

    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(write_cursor=write_cursor, history=[
            _event(at=1, amount='1', event_type=HistoryEventType.RECEIVE),
            _event(at=2, amount='1', event_type=HistoryEventType.RECEIVE),
        ])
        # as on a first pass over events that were there before the markers existed
        write_cursor.execute('DELETE FROM key_value_cache WHERE name LIKE ?', ('stale_cost_%',))

    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price = rate_limited_at_two
        assert process_cost_basis(database, database.msg_aggregator) is False

    assert len(_rows(database)) == 1
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        ) == str(_ts_ms(2))
    assert process_cost_basis(database, database.msg_aggregator) is True  # prices are back
    assert len(_rows(database)) == 2


@pytest.mark.usefixtures('queried_prices')
def test_unfinished_pass_keeps_progress_until_events_change(database: DBHandler) -> None:
    def unprocessed_from_ts() -> TimestampMS | None:
        with database.conn.read_ctx() as cursor:
            return get_unprocessed_from_ts(cursor=cursor, database=database)

    with database.user_write() as write_cursor:
        identifiers = [identifier for at in (1, 2, 3, 4) if (identifier := DBHistoryEvents(
            database,
        ).add_history_event(
            write_cursor=write_cursor,
            event=_event(at=at, amount='1', event_type=HistoryEventType.RECEIVE),
        )) is not None]

    apply = _CostBasisPass.apply

    def apply_until_three(
            self: _CostBasisPass,
            event: HistoryBaseEntry,
            next_event: HistoryBaseEntry | None,
            treat_eth2_as_eth: bool,
            swap_fee_events: Sequence[HistoryBaseEntry] = (),
    ) -> None:
        if event.timestamp == _ts_ms(3):
            raise AssertionError('the pass dies at the third event')
        apply(
            self,
            event=event,
            next_event=next_event,
            treat_eth2_as_eth=treat_eth2_as_eth,
            swap_fee_events=swap_fee_events,
        )

    with (
        patch('rotkehlchen.tasks.cost_basis.COST_BASIS_BATCH_SIZE', 1),
        patch.object(_CostBasisPass, 'apply', apply_until_three),
        pytest.raises(AssertionError),
    ):
        process_cost_basis(database, database.msg_aggregator)

    assert unprocessed_from_ts() == _ts_ms(3)
    assert _rows(database, 'event_identifier') == [(identifier,) for identifier in identifiers[:2]]

    with database.user_write() as write_cursor:  # a change may make what the pass wrote outdated
        DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=_event(at=5, amount='1', event_type=HistoryEventType.RECEIVE),
        )
    assert unprocessed_from_ts() == 0

    _set_method(database, CostBasisMethod.LIFO)  # also before any pass finished
    assert _rows(database) == []

    assert process_cost_basis(database, database.msg_aggregator) is True
    assert unprocessed_from_ts() is None
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM key_value_cache WHERE name LIKE ?',
            ('cost_basis_pass_%',),
        ).fetchone()[0] == 0


@pytest.mark.parametrize(('rule', 'pnl'), [
    (None, 0),  # an event without a rule only moves lots
    ({'taxable': False}, 0),
    ({}, 3000),  # worth 4000 with a basis of 1000
    ({'count_cost_basis_pnl': False, 'count_entire_amount_spend': True}, -4000),
    ({'count_entire_amount_spend': True}, -1000),
])
@pytest.mark.usefixtures('queried_prices')
def test_spend_realizes_what_its_rule_says(
        database: DBHandler,
        rule: dict[str, bool] | None,
        pnl: int,
) -> None:
    if rule is not None:
        _add_rule(
            database=database,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            taxable=rule.get('taxable', True),
            count_entire_amount_spend=rule.get('count_entire_amount_spend', False),
            count_cost_basis_pnl=rule.get('count_cost_basis_pnl', True),
        )

    acquired, spent = _process(database=database, method=CostBasisMethod.FIFO, events=[
        _event(at=1, amount='1', event_type=HistoryEventType.RECEIVE),
        _event(at=4, amount='1', event_type=HistoryEventType.SPEND, event_subtype=HistoryEventSubType.FEE),  # noqa: E501
    ])
    assert _spend_row(database, spent) == ([(acquired, FVal(1))], FVal(pnl), FVal(1000), FVal(0))


@pytest.mark.usefixtures('queried_prices')
def test_rule_of_an_event_overrides_and_reprocesses(database: DBHandler) -> None:
    _add_rule(database, HistoryEventType.SPEND, HistoryEventSubType.FEE, taxable=False)
    _, spent = _process(database=database, method=CostBasisMethod.FIFO, events=[
        _event(at=1, amount='1', event_type=HistoryEventType.RECEIVE),
        _event(at=4, amount='1', event_type=HistoryEventType.SPEND, event_subtype=HistoryEventSubType.FEE),  # noqa: E501
    ])
    assert _spend_row(database, spent)[1] == FVal(0)

    _add_rule(database, HistoryEventType.SPEND, HistoryEventSubType.FEE, event_ids=[int(spent)])
    assert process_cost_basis(database, database.msg_aggregator) is True
    assert _spend_row(database, spent)[1] == FVal(3000)
    assert len(_rows(database)) == 2


@pytest.mark.usefixtures('queried_prices')
def test_reassigned_event_rule_does_not_become_generic(database: DBHandler) -> None:
    _, first_fee, second_fee = _process(database=database, method=CostBasisMethod.FIFO, events=[
        _event(at=1, amount='2', event_type=HistoryEventType.RECEIVE),
        _event(at=4, amount='1', event_type=HistoryEventType.SPEND, event_subtype=HistoryEventSubType.FEE),  # noqa: E501
        _event(at=5, amount='1', event_type=HistoryEventType.SPEND, event_subtype=HistoryEventSubType.FEE),  # noqa: E501
    ])
    _add_rule(
        database=database,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        event_ids=[int(first_fee)],
    )
    assert process_cost_basis(database, database.msg_aggregator) is True
    assert _spend_row(database, first_fee)[1] == FVal(3000)

    _add_rule(
        database=database,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        taxable=False,
        event_ids=[int(first_fee)],
    )
    assert process_cost_basis(database, database.msg_aggregator) is True
    assert _spend_row(database, first_fee)[1] == FVal(0)
    assert _spend_row(database, second_fee)[1] == FVal(0)


@pytest.mark.parametrize('method', list(CostBasisMethod))
@pytest.mark.parametrize('received_asset', [A_DAI, A_ETH2])
@pytest.mark.usefixtures('queried_prices')
def test_basis_transfer_carries_the_lots_across_asset_conversion(
        database: DBHandler,
        method: CostBasisMethod,
        received_asset: Asset,
) -> None:
    _add_rule(
        database=database,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        accounting_treatment=TxAccountingTreatment.BASIS_TRANSFER,
    )
    spend_asset = A_DAI if received_asset == A_DAI else A_ETH
    acquired, wrapped, received, spent = _process(
        database=database,
        method=method,
        treat_eth2_as_eth=True,
        events=[
            _event(at=1, amount='2', event_type=HistoryEventType.RECEIVE),
            _event(
                at=6,
                amount='2',
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
                tx_ref=(tx_ref := make_evm_tx_hash()),
            ), _event(
                at=6,
                amount='4',
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                asset=received_asset,
                tx_ref=tx_ref,
                sequence_index=1,
            ),
            _event(at=7, amount='1', event_type=HistoryEventType.SPEND, asset=spend_asset),
        ],
    )
    assert _spend_row(database, wrapped) == ([(acquired, FVal(2))], FVal(0), FVal(2000), FVal(0))
    assert _rows(
        database=database,
        columns='event_identifier, asset, direction, lot_created_id, basis_per_unit, basis_source',
    )[2] == (int(received), spend_asset.identifier, 'receive', acquired, '500', 'transfer_in')
    assert _spend_row(database, spent) == (
        [(acquired, FVal(1))],
        FVal(-499 if spend_asset == A_DAI else 1000),
        FVal(500),
        FVal(1500),
    )


def _set_method(database: DBHandler, method: CostBasisMethod) -> None:
    with database.user_write() as write_cursor:
        database.set_settings(write_cursor, ModifiableDBSettings(cost_basis_method=method))


@pytest.mark.usefixtures('queried_prices')
def test_method_switch_wipes_and_reprocesses_only_the_cost_basis(database: DBHandler) -> None:
    def balance_state() -> list[tuple[Any, ...]]:
        with database.conn.read_ctx() as cursor:
            return cursor.execute(
                'SELECT name, value FROM key_value_cache WHERE name LIKE ? '
                'UNION ALL SELECT metric_key, metric_value FROM event_metrics',
                ('stale_balances_%',),
            ).fetchall()

    _process(database=database, method=CostBasisMethod.FIFO, events=_three_lots_and_a_spend())
    process_historical_balances(database, database.msg_aggregator)
    fifo_rows, balances = _rows(database), balance_state()
    assert len(balances) == 4  # one balance per event, and no stale marker

    _set_method(database, CostBasisMethod.FIFO)  # setting the same method changes nothing
    assert _rows(database) == fifo_rows

    _set_method(database, CostBasisMethod.LIFO)
    assert _rows(database) == []
    with database.conn.read_ctx() as cursor:
        stale_from_ts, modification_ts = database.get_static_caches(cursor=cursor, names=(
            DBCacheStatic.STALE_COST_BASIS_FROM_TS,
            DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS,
        ))
    assert stale_from_ts == '0'
    assert modification_ts is not None

    assert process_cost_basis(database, database.msg_aggregator) is True
    lifo_rows = _rows(database)
    assert {row[-1] for row in lifo_rows} == {'lifo'}
    assert len(lifo_rows) == len(fifo_rows)

    # back and forth before the next pass ends up at the method that is set last
    _set_method(database, CostBasisMethod.HIFO)
    _set_method(database, CostBasisMethod.FIFO)
    assert process_cost_basis(database, database.msg_aggregator) is True
    assert _rows(database) == fifo_rows
    assert balance_state() == balances


@pytest.mark.usefixtures('queried_prices')
def test_spend_separates_the_gain_on_lots_held_past_the_taxfree_period(
        database: DBHandler,
) -> None:
    acquired = _process(database=database, method=CostBasisMethod.FIFO, taxfree_after_period=2, events=[  # noqa: E501
        _event(at=1, amount='1', event_type=HistoryEventType.RECEIVE),
        _event(at=2, amount='1', event_type=HistoryEventType.RECEIVE),
        _event(at=3, amount='1', event_type=HistoryEventType.RECEIVE),
        _event(at=5, amount='2.5', event_type=HistoryEventType.SPEND),
    ])[:3]
    lots, proceeds, realized_pnl, taxfree_pnl = _rows(
        database=database,
        columns='lots_consumed_json, proceeds, realized_pnl, taxfree_pnl',
    )[-1]
    # at 5 the lots of 1 and 2 were held for more than 2 seconds, the one of 3 was not
    assert [(lot['lot_id'], lot['acquired_at'], lot['taxable']) for lot in json.loads(lots)] == [
        (acquired[0], _ts(1), False),
        (acquired[1], _ts(2), False),
        (acquired[2], _ts(3), True),
    ]
    assert proceeds == '12500'
    assert realized_pnl == '1500'  # half a unit worth 2500 that was bought for 1000
    assert taxfree_pnl == '6000'  # two units worth 10000 that were bought for 4000


def _mixed_history() -> list[EvmEvent | HistoryEvent]:
    """A receive, a swap, a transfer to TEST_ADDR2 and spends from both accounts."""
    tx_ref = make_evm_tx_hash()
    return [
        _event(at=1, amount='2', event_type=HistoryEventType.RECEIVE),
        _event(
            at=2,
            amount='0.5',
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            tx_ref=tx_ref,
        ),
        _event(
            at=2,
            amount='1500',
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_DAI,
            tx_ref=tx_ref,
            sequence_index=1,
        ),
        _event(at=3, amount='1', event_type=HistoryEventType.TRANSFER, address=TEST_ADDR2),
        _event(at=4, amount='1', event_type=HistoryEventType.RECEIVE, location_label=TEST_ADDR2),
        _event(at=5, amount='1.5', event_type=HistoryEventType.SPEND, location_label=TEST_ADDR2),
        _event(at=6, amount='0.25', event_type=HistoryEventType.SPEND),
    ]


@pytest.mark.parametrize('method', list(CostBasisMethod))
def test_crashed_pass_resumes_from_committed_progress(
        database: DBHandler,
        queried_prices: list[tuple[str, Timestamp]],
        method: CostBasisMethod,
) -> None:
    events = _mixed_history()
    _add_rule(database, HistoryEventType.SPEND)
    _add_rule(
        database=database,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        accounting_treatment=TxAccountingTreatment.SWAP,
    )
    with database.user_write() as write_cursor:
        database.set_settings(write_cursor, ModifiableDBSettings(cost_basis_method=method))
        DBHistoryEvents(database).add_history_events(write_cursor=write_cursor, history=events)

    apply = _CostBasisPass.apply

    def crash_at_five(
            self: _CostBasisPass,
            event: HistoryBaseEntry,
            next_event: HistoryBaseEntry | None,
            treat_eth2_as_eth: bool,
            swap_fee_events: Sequence[HistoryBaseEntry] = (),
    ) -> None:
        if event.timestamp == _ts_ms(5):
            raise RuntimeError('deterministic crash after committed batches')
        apply(
            self,
            event=event,
            next_event=next_event,
            treat_eth2_as_eth=treat_eth2_as_eth,
            swap_fee_events=swap_fee_events,
        )

    with (
        patch('rotkehlchen.tasks.cost_basis.COST_BASIS_BATCH_SIZE', 2),
        patch.object(_CostBasisPass, 'apply', crash_at_five),
        pytest.raises(RuntimeError, match='deterministic crash after committed batches'),
    ):
        process_cost_basis(database, database.msg_aggregator)

    committed_rows = _rows(database, f'id, {ROW_COLUMNS}')
    assert len(committed_rows) == 5
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.LAST_COST_BASIS_PROCESSING_TS,
        ) is None
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.LAST_COST_BASIS_FAILURE_TS,
        ) is not None
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS,
        ) == '0'

    queried_prices.clear()
    assert process_cost_basis(database, database.msg_aggregator) is True
    assert queried_prices == [('ETH', _ts(4)), ('ETH', _ts(5)), ('ETH', _ts(6))]
    resumed_rows_with_ids = _rows(database, f'id, {ROW_COLUMNS}')
    assert resumed_rows_with_ids[:len(committed_rows)] == committed_rows
    resumed_rows = _rows(database)

    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.LAST_COST_BASIS_FAILURE_TS,
        ) is None
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.LAST_COST_BASIS_PROCESSING_TS,
        ) is not None

    # Compare against an uninterrupted pass from scratch.
    with database.user_write() as write_cursor:
        write_cursor.execute('DELETE FROM event_cost_basis')
        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name IN (?, ?)',
            (
                DBCacheStatic.LAST_COST_BASIS_PROCESSING_TS.value,
                DBCacheStatic.STALE_COST_BASIS_FROM_TS.value,
            ),
        )
    assert process_cost_basis(database, database.msg_aggregator) is True
    assert _rows(database) == resumed_rows


def _checkpoint_timestamps(database: DBHandler) -> list[int]:
    with database.conn.read_ctx() as cursor:
        return [row[0] for row in cursor.execute(
            'SELECT timestamp FROM cost_basis_checkpoints ORDER BY timestamp',
        )]


def _process_counting_applied(database: DBHandler) -> list[int]:
    """Process the cost basis and return the timestamps of the events the pass applied."""
    applied: list[int] = []
    apply = _CostBasisPass.apply

    def counting_apply(
            self: _CostBasisPass,
            event: HistoryBaseEntry,
            next_event: HistoryBaseEntry | None,
            treat_eth2_as_eth: bool,
            swap_fee_events: Sequence[HistoryBaseEntry] = (),
    ) -> None:
        applied.append(event.timestamp)
        apply(
            self,
            event=event,
            next_event=next_event,
            treat_eth2_as_eth=treat_eth2_as_eth,
            swap_fee_events=swap_fee_events,
        )

    with patch.object(_CostBasisPass, 'apply', counting_apply):
        assert process_cost_basis(database, database.msg_aggregator) is True

    return applied


@pytest.mark.parametrize('method', list(CostBasisMethod))
@pytest.mark.usefixtures('queried_prices')
def test_pass_resumes_from_the_last_checkpoint_before_the_stale_events(
        database: DBHandler,
        method: CostBasisMethod,
) -> None:
    with patch('rotkehlchen.tasks.cost_basis.COST_BASIS_CHECKPOINT_INTERVAL', 1):
        identifiers = _process(database=database, method=method, events=_mixed_history())
        # none between the two sides of the swap at 2, and the last one after the last event
        assert _checkpoint_timestamps(database) == [
            _ts_ms(2), _ts_ms(3), _ts_ms(4), _ts_ms(5), _ts_ms(6), _ts_ms(6) + 1,
        ]

        with database.user_write() as write_cursor:
            DBHistoryEvents(database).add_history_event(
                write_cursor=write_cursor,
                event=_event(at=7, amount='0.25', event_type=HistoryEventType.SPEND),
            )
        assert _process_counting_applied(database) == [_ts_ms(7)]

        with database.user_write() as write_cursor:
            write_cursor.execute(
                'UPDATE history_events SET amount = ? WHERE identifier = ?',
                ('2', int(identifiers[4])),
            )
            write_cursor.executemany(
                'INSERT OR REPLACE INTO key_value_cache(name, value) VALUES (?, ?)',
                [
                    (DBCacheStatic.STALE_COST_BASIS_FROM_TS.value, str(_ts_ms(4))),
                    (DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS.value, '1'),
                ],
            )
        assert _process_counting_applied(database) == [
            _ts_ms(4), _ts_ms(5), _ts_ms(6), _ts_ms(7),
        ]
        assert _checkpoint_timestamps(database) == [
            _ts_ms(2), _ts_ms(3), _ts_ms(4), _ts_ms(5), _ts_ms(6), _ts_ms(7), _ts_ms(7) + 1,
        ]
        resumed_rows = _rows(database)

        with database.user_write() as write_cursor:  # compare against a pass from scratch
            write_cursor.execute('DELETE FROM event_cost_basis')
            write_cursor.execute('DELETE FROM cost_basis_checkpoints')
            write_cursor.execute(
                'DELETE FROM key_value_cache WHERE name = ?',
                (DBCacheStatic.LAST_COST_BASIS_PROCESSING_TS.value,),
            )
        assert _process_counting_applied(database) == [
            _ts_ms(1), _ts_ms(2), _ts_ms(2), _ts_ms(3),
            _ts_ms(4), _ts_ms(5), _ts_ms(6), _ts_ms(7),
        ]
        assert _rows(database) == resumed_rows


@pytest.mark.usefixtures('queried_prices')
def test_rule_change_marks_the_cost_basis_stale_from_the_first_event_it_affects(
        database: DBHandler,
) -> None:
    def stale_from_ts() -> str | None:
        with database.conn.read_ctx() as cursor:
            return database.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
            )

    _, first_fee, second_fee = _process(database=database, method=CostBasisMethod.FIFO, events=[
        _event(at=1, amount='2', event_type=HistoryEventType.RECEIVE),
        _event(at=4, amount='1', event_type=HistoryEventType.SPEND, event_subtype=HistoryEventSubType.FEE),  # noqa: E501
        _event(at=5, amount='1', event_type=HistoryEventType.SPEND, event_subtype=HistoryEventSubType.FEE),  # noqa: E501
    ])
    assert stale_from_ts() is None
    _add_rule(database, HistoryEventType.SPEND, HistoryEventSubType.FEE, event_ids=[int(second_fee)])  # noqa: E501
    assert stale_from_ts() == str(_ts_ms(5))
    _add_rule(database, HistoryEventType.SPEND, HistoryEventSubType.FEE)
    assert stale_from_ts() == str(_ts_ms(4))

    assert process_cost_basis(database, database.msg_aggregator) is True
    _add_rule(database, HistoryEventType.DEPOSIT)  # no event of the type, so nothing is stale
    assert stale_from_ts() is None
    assert _spend_row(database, first_fee)[1] == FVal(3000)


def test_spend_with_invalid_amount_includes_event_details_in_error(
        database: DBHandler,
) -> None:
    with database.conn.read_ctx() as cursor:
        settings = database.get_settings(cursor)
    lots = BucketLots[Bucket](settings)
    bucket = Bucket(
        location=str(LOCATION_ETHEREUM),
        location_label=TEST_ADDR1,
        protocol=None,
        asset=A_ETH.identifier,
    )
    lots.obtain(
        bucket=bucket,
        lot_id='1',
        amount=FVal('1'),
        basis_per_unit=FVal('1000'),
        timestamp=_ts(1),
    )
    spend_event = _event(at=2, amount='-0.5', event_type=HistoryEventType.SPEND)
    with pytest.raises(
        AssertionError,
        match=f'Used amount must be in the interval \\[0, 1\\] but it was -0\\.5 for {spend_event!s}',  # noqa: E501
    ):
        lots.spend(
            bucket=bucket,
            asset=A_ETH,
            amount=spend_event.amount,
            timestamp=_ts(2),
            event=spend_event,
        )


@pytest.mark.usefixtures('queried_prices')
def test_negative_amount_event_records_data_issue_and_blocks_only_its_bucket(
        database: DBHandler,
) -> None:
    identifiers = _process(
        database=database,
        method=CostBasisMethod.FIFO,
        events=[
            _event(at=1, amount='1', event_type=HistoryEventType.RECEIVE, location_label=TEST_ADDR1),  # noqa: E501
            _event(at=1, amount='2', event_type=HistoryEventType.RECEIVE, location_label=TEST_ADDR2),  # noqa: E501
            _event(at=2, amount='-0.5', event_type=HistoryEventType.SPEND, location_label=TEST_ADDR1),  # noqa: E501
            _event(at=3, amount='1', event_type=HistoryEventType.SPEND, location_label=TEST_ADDR2),
            _event(at=4, amount='0.5', event_type=HistoryEventType.SPEND, location_label=TEST_ADDR1),  # noqa: E501
        ],
    )
    assert sorted(_rows(database, 'event_identifier, location_label, direction')) == [
        (int(identifiers[0]), TEST_ADDR1, 'receive'),
        (int(identifiers[1]), TEST_ADDR2, 'receive'),
        (int(identifiers[3]), TEST_ADDR2, 'spend'),
    ]
    issues = DataIssuesManager(database).list_issues(
        DataIssueFilters(kind=IssueKind.INVALID_EVENT_AMOUNT),
    )
    assert len(issues) == 1
    assert issues[0].state == IssueState.OPEN
    assert issues[0].location == str(LOCATION_ETHEREUM)
    assert issues[0].location_label == TEST_ADDR1
    assert issues[0].asset == A_ETH.identifier
    assert issues[0].payload == {
        'event_identifier': int(identifiers[2]),
        'amount': '-0.5',
    }
    with database.conn.read_ctx() as cursor:
        assert database.get_static_caches(cursor=cursor, names=(
            DBCacheStatic.STALE_COST_BASIS_FROM_TS,
            DBCacheStatic.LAST_COST_BASIS_FAILURE_TS,
        )) == (None, None)
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.LAST_COST_BASIS_PROCESSING_TS,
        ) is not None

    with database.user_write() as write_cursor:
        write_cursor.execute(
            'UPDATE history_events SET amount = ? WHERE identifier = ?',
            ('0.5', int(identifiers[2])),
        )
        write_cursor.executemany(
            'INSERT OR REPLACE INTO key_value_cache(name, value) VALUES (?, ?)',
            [
                (DBCacheStatic.STALE_COST_BASIS_FROM_TS.value, str(_ts_ms(2))),
                (DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS.value, '1'),
            ],
        )

    assert process_cost_basis(database, database.msg_aggregator) is True
    assert sorted(_rows(database, 'event_identifier, location_label, direction')) == [
        (int(identifiers[0]), TEST_ADDR1, 'receive'),
        (int(identifiers[1]), TEST_ADDR2, 'receive'),
        (int(identifiers[2]), TEST_ADDR1, 'spend'),
        (int(identifiers[3]), TEST_ADDR2, 'spend'),
        (int(identifiers[4]), TEST_ADDR1, 'spend'),
    ]
    issues = DataIssuesManager(database).list_issues(
        DataIssueFilters(kind=IssueKind.INVALID_EVENT_AMOUNT),
    )
    assert len(issues) == 1
    assert issues[0].state == IssueState.RESOLVED


@pytest.mark.usefixtures('queried_prices')
def test_setting_and_rule_changes_during_startup_keep_stale_marker(
        database: DBHandler,
) -> None:
    """A setting or rule change after startup reads inputs must not be cleared on completion."""
    _add_rule(database, HistoryEventType.SPEND)
    with database.user_write() as write_cursor:
        database.set_settings(
            write_cursor,
            ModifiableDBSettings(cost_basis_method=CostBasisMethod.FIFO),
        )
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=_three_lots_and_a_spend(),
        )

    # Synchronized method change between get_settings() (which already read FIFO) and _Rules().
    entered_rules = threading.Event()
    method_changed = threading.Event()
    original_rules_init = _Rules.__init__

    def paused_rules_init(
            self: _Rules,
            database: DBHandler,
            cursor: DBCursor | None = None,
    ) -> None:
        entered_rules.set()
        assert method_changed.wait(timeout=5)
        original_rules_init(self, database, cursor=cursor)

    def switch_method_concurrently() -> None:
        assert entered_rules.wait(timeout=5)
        _set_method(database, CostBasisMethod.LIFO)
        method_changed.set()

    worker = threading.Thread(target=switch_method_concurrently)
    worker.start()
    try:
        with patch.object(_Rules, '__init__', paused_rules_init):
            assert process_cost_basis(database, database.msg_aggregator) is True
    finally:
        worker.join(timeout=5)
    assert not worker.is_alive()

    with database.conn.read_ctx() as cursor:
        assert get_unprocessed_from_ts(cursor=cursor, database=database) == 0

    assert process_cost_basis(database, database.msg_aggregator) is True
    assert {row[-1] for row in _rows(database)} == {'lifo'}
    with database.conn.read_ctx() as cursor:
        assert get_unprocessed_from_ts(cursor=cursor, database=database) is None

    # Synchronized rule change between _Rules() (which already read old rules) and reading events.
    with database.user_write() as write_cursor:
        fee_id = DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=_event(
                at=5,
                amount='0.5',
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
            ),
        )
    assert fee_id is not None

    entered_events = threading.Event()
    rule_changed = threading.Event()
    original_get_events = DBHistoryEvents.get_history_events_internal

    def paused_get_events(
            self: DBHistoryEvents,
            cursor: DBCursor,
            filter_query: Any,
    ) -> list[HistoryBaseEntry]:
        entered_events.set()
        assert rule_changed.wait(timeout=5)
        return original_get_events(self, cursor=cursor, filter_query=filter_query)

    def add_rule_concurrently() -> None:
        assert entered_events.wait(timeout=5)
        _add_rule(
            database=database,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            event_ids=[fee_id],
        )
        rule_changed.set()

    worker = threading.Thread(target=add_rule_concurrently)
    worker.start()
    try:
        with patch.object(DBHistoryEvents, 'get_history_events_internal', paused_get_events):
            assert process_cost_basis(database, database.msg_aggregator) is True
    finally:
        worker.join(timeout=5)
    assert not worker.is_alive()

    with database.conn.read_ctx() as cursor:
        assert get_unprocessed_from_ts(cursor=cursor, database=database) == _ts_ms(5)

    assert process_cost_basis(database, database.msg_aggregator) is True
    # LIFO consumed 1 ETH @ 2000 and 0.5 ETH @ 3000 at t=4, leaving 0.5 ETH @ 3000 for t=5 @ 5000.
    assert _spend_row(database, str(fee_id))[1] == FVal(1000)


@pytest.mark.usefixtures('queried_prices')
def test_edit_history_event_invalidates_cost_basis_on_all_consumed_fields(
        database: DBHandler,
) -> None:
    events_db = DBHistoryEvents(database)
    evm_event = _event(
        at=3,
        amount='1',
        event_type=HistoryEventType.TRANSFER,
        address=TEST_ADDR2,
    )
    btc_event = HistoryEvent(
        group_identifier='btc_tx',
        sequence_index=0,
        timestamp=_ts_ms(4),
        location=LOCATION_BITCOIN,
        location_label='bc1q000000000000000000000000000000000000000',
        asset=A_BTC,
        amount=FVal('1'),
        notes='Transfer 1 BTC to 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
        event_type=HistoryEventType.TRANSFER,
        event_subtype=HistoryEventSubType.NONE,
    )
    evm_id_str, btc_id_str = _process(
        database=database,
        method=CostBasisMethod.FIFO,
        events=[evm_event, btc_event],
    )
    evm_event.identifier = int(evm_id_str)
    btc_event.identifier = int(btc_id_str)

    def stale_from_ts() -> str | None:
        with database.conn.read_ctx() as cursor:
            return database.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
            )

    def edit_and_assert_stale(
            event: EvmEvent | HistoryEvent,
            expected_from_ts: str | None,
    ) -> None:
        with database.user_write() as write_cursor:
            events_db.edit_history_event(
                write_cursor=write_cursor,
                event=event,
                mapping_state=HistoryMappingState.CUSTOMIZED,
            )
        assert stale_from_ts() == expected_from_ts
        if expected_from_ts is not None:
            assert process_cost_basis(database, database.msg_aggregator) is True
            assert stale_from_ts() is None

    # Non-Bitcoin notes-only edit does not invalidate.
    evm_event.notes = 'plain memo'
    edit_and_assert_stale(evm_event, None)

    # Counterparty-only edit invalidates.
    evm_event.counterparty = 'uniswap-v3'
    edit_and_assert_stale(evm_event, str(_ts_ms(3)))

    # Address-only edit invalidates.
    evm_event.address = TEST_ADDR1
    edit_and_assert_stale(evm_event, str(_ts_ms(3)))

    # Location-only edit invalidates.
    evm_event.location = LOCATION_OPTIMISM
    edit_and_assert_stale(evm_event, str(_ts_ms(3)))

    # Group identifier-only edit invalidates.
    evm_event.group_identifier = 'edited_group'
    edit_and_assert_stale(evm_event, str(_ts_ms(3)))

    # Sequence index-only edit invalidates.
    evm_event.sequence_index = 2
    edit_and_assert_stale(evm_event, str(_ts_ms(3)))

    # Moving timestamp forward still marks stale from the minimum of old and new timestamps.
    evm_event.timestamp = _ts_ms(6)
    edit_and_assert_stale(evm_event, str(_ts_ms(3)))

    # Moving timestamp backward marks stale from the new earlier timestamp.
    evm_event.timestamp = _ts_ms(2)
    edit_and_assert_stale(evm_event, str(_ts_ms(2)))

    # Bitcoin notes edit can change counterparty address extraction and invalidates.
    btc_event.notes = 'Transfer 1 BTC to 1BoatSLRHtKNngkdXEeobR76b53LETtpyT'
    edit_and_assert_stale(btc_event, str(_ts_ms(4)))


@pytest.mark.usefixtures('queried_prices')
def test_swap_fees_follow_include_fees_in_cost_basis(database: DBHandler) -> None:
    """Swap fee legs fold into acquired basis when include_fees_in_cost_basis is enabled, and
    are realized as standalone fee spends when disabled."""
    tx_crypto = make_evm_tx_hash()
    tx_fiat = make_evm_tx_hash()
    acquired, spent, received, fee, fiat_spent, _, fiat_fee = _process(
        database=database,
        method=CostBasisMethod.FIFO,
        include_crypto2crypto=True,
        include_fees_in_cost_basis=True,
        events=[
            _event(at=1, amount='3', event_type=HistoryEventType.RECEIVE),
            _event(
                at=3,
                amount='1',
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                tx_ref=tx_crypto,
            ),
            _event(
                at=3,
                amount='2000',
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_DAI,
                tx_ref=tx_crypto,
                sequence_index=1,
            ),
            _event(
                at=3,
                amount='0.1',
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.FEE,
                tx_ref=tx_crypto,
                sequence_index=2,
            ),
            _event(
                at=4,
                amount='1',
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                tx_ref=tx_fiat,
            ),
            _event(
                at=4,
                amount='4000',
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_USD,
                tx_ref=tx_fiat,
                sequence_index=1,
            ),
            _event(
                at=4,
                amount='0.1',
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.FEE,
                tx_ref=tx_fiat,
                sequence_index=2,
            ),
        ],
    )
    # 1 ETH ($2000) -> 2000 DAI with 0.1 ETH ($200) fee => $2200 DAI lot (1.1/DAI).
    assert _spend_row(database, spent) == ([(acquired, FVal(1))], FVal(1000), FVal(1000), FVal(2000))  # noqa: E501
    assert _rows(database, 'event_identifier, basis_per_unit, basis_source')[2] == (
        int(received), '1.1', 'price_oracle',
    )
    assert _spend_row(database, fee) == (
        [(acquired, FVal('0.1'))], FVal(0), FVal(100), FVal(1900),
    )
    # Selling 1 ETH for $4000 USD with 0.1 ETH ($400) fee => $3600 proceeds, $2600 realized PnL.
    assert _spend_row(database, fiat_spent) == (
        [(acquired, FVal(1))], FVal(2600), FVal(1000), FVal(900),
    )
    assert _spend_row(database, fiat_fee) == (
        [(acquired, FVal('0.1'))], FVal(0), FVal(100), FVal(800),
    )

    # Toggling include_fees_in_cost_basis wipes and invalidates the materialized rows.
    with database.user_write() as write_cursor:
        database.set_settings(
            write_cursor,
            ModifiableDBSettings(include_fees_in_cost_basis=False),
        )
    assert _rows(database) == []
    assert process_cost_basis(database, database.msg_aggregator) is True

    # DAI lot is now $2000 (1/DAI), and fees realize expense (-value) + gain (value - basis).
    assert _rows(database, 'event_identifier, basis_per_unit, basis_source')[2] == (
        int(received), '1', 'price_oracle',
    )
    assert _spend_row(database, fee) == (
        [(acquired, FVal('0.1'))], FVal(-100), FVal(100), FVal(1900),
    )
    assert _spend_row(database, fiat_spent) == (
        [(acquired, FVal(1))], FVal(3000), FVal(1000), FVal(900),
    )
    assert _spend_row(database, fiat_fee) == (
        [(acquired, FVal('0.1'))], FVal(-100), FVal(100), FVal(800),
    )


def test_eth2_pre_shapella_staking_reward_follows_withdrawal_setting(
        database: DBHandler,
) -> None:
    """Pre-Shapella Kraken ETH2 staking rewards are skipped when withdrawal-time taxation is
    enabled (matching legacy HistoryEvent.process), while non-Kraken rewards, post-Shapella
    rewards, and ETH withdrawals still create lots."""
    t_pre = Timestamp(SHAPPELA_TIMESTAMP - 1000)
    t_post_reward = Timestamp(SHAPPELA_TIMESTAMP + 500)
    t_withdrawal = Timestamp(SHAPPELA_TIMESTAMP + 1000)
    t_spend = Timestamp(SHAPPELA_TIMESTAMP + 2000)
    staking_prices = {
        t_pre: Price(FVal(1000)),
        t_post_reward: Price(FVal(1500)),
        t_withdrawal: Price(FVal(2000)),
        t_spend: Price(FVal(3000)),
    }

    def query_historical_price(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        if from_asset in (A_ETH, A_ETH2):
            return staking_prices[timestamp]
        raise NoPriceForGivenTimestamp(from_asset=from_asset, to_asset=to_asset, time=timestamp)

    with database.user_write() as write_cursor:
        database.add_blockchain_accounts(
            write_cursor=write_cursor,
            account_data=[BlockchainAccountData(
                chain=SupportedBlockchain.ETHEREUM,
                address=TEST_ADDR1,
            )],
        )

    events: list[Any] = [
        HistoryEvent(
            group_identifier='pre_shapella_eth2_reward',
            sequence_index=0,
            timestamp=TimestampMS(t_pre * 1000),
            location=LOCATION_ETHEREUM,
            location_label=TEST_ADDR2,
            asset=A_ETH2,
            amount=FVal('1'),
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
        ),
        HistoryEvent(
            group_identifier='kraken_pre_shapella_reward',
            sequence_index=0,
            timestamp=TimestampMS(t_pre * 1000),
            location=LOCATION_KRAKEN,
            location_label='kraken',
            asset=A_ETH2,
            amount=FVal('1'),
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
        ),
        HistoryEvent(
            group_identifier='kraken_post_shapella_reward',
            sequence_index=0,
            timestamp=TimestampMS(t_post_reward * 1000),
            location=LOCATION_KRAKEN,
            location_label='kraken',
            asset=A_ETH2,
            amount=FVal('1'),
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
        ),
        EthWithdrawalEvent(
            validator_index=42,
            timestamp=TimestampMS(t_withdrawal * 1000),
            amount=FVal('1'),
            withdrawal_address=TEST_ADDR1,
            is_exit=False,
        ),
        HistoryEvent(
            group_identifier='kraken_spend',
            sequence_index=0,
            timestamp=TimestampMS(t_spend * 1000),
            location=LOCATION_KRAKEN,
            location_label='kraken',
            asset=A_ETH2,
            amount=FVal('1'),
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
        ),
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=TimestampMS(t_spend * 1000),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal('1'),
            location_label=TEST_ADDR1,
        ),
    ]

    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price = query_historical_price
        (
            pre_eth_reward,
            pre_kraken_reward,
            post_kraken_reward,
            withdrawal,
            kraken_spend,
            eth_spend,
        ) = _process(
            database=database,
            method=CostBasisMethod.FIFO,
            treat_eth2_as_eth=True,
            taxfree_after_period=2500,
            eth_staking_taxable_after_withdrawal_enabled=True,
            events=events,
        )

        # Pre-Shapella Kraken reward is omitted; non-Kraken, post-Shapella, and withdrawal remain.
        assert _rows(database, 'event_identifier, direction, basis_per_unit') == [
            (int(pre_eth_reward), 'receive', '1000'),
            (int(post_kraken_reward), 'receive', '1500'),
            (int(withdrawal), 'receive', '2000'),
            (int(eth_spend), 'spend', None),
            (int(kraken_spend), 'spend', None),
        ]
        rows_by_id = {
            row[0]: row[1:]
            for row in _rows(
                database,
                'event_identifier, lots_consumed_json, realized_pnl, taxfree_pnl',
            )
        }
        # Kraken spend consumes post-Shapella lot (held 1500s < 2500s => taxable $1500 gain).
        lots, realized_pnl, taxfree_pnl = rows_by_id[int(kraken_spend)]
        assert [
            (lot['lot_id'], lot['acquired_at'], lot['taxable']) for lot in json.loads(lots)
        ] == [(post_kraken_reward, t_post_reward, True)]
        assert (realized_pnl, taxfree_pnl) == ('1500', '0')
        # Withdrawal lot was held 1000s (< 2500s), so the gain is taxable against its $2000 basis.
        lots, realized_pnl, taxfree_pnl = rows_by_id[int(eth_spend)]
        assert [
            (lot['lot_id'], lot['acquired_at'], lot['taxable']) for lot in json.loads(lots)
        ] == [(withdrawal, t_withdrawal, True)]
        assert (realized_pnl, taxfree_pnl) == ('1000', '0')

        # Disabling the setting invalidates existing rows and materializes pre-Shapella Kraken.
        with database.user_write() as write_cursor:
            database.set_settings(
                write_cursor,
                ModifiableDBSettings(eth_staking_taxable_after_withdrawal_enabled=False),
            )
        assert _rows(database) == []
        assert process_cost_basis(database, database.msg_aggregator) is True

        assert _rows(database, 'event_identifier, direction, basis_per_unit') == [
            (int(pre_kraken_reward), 'receive', '1000'),
            (int(pre_eth_reward), 'receive', '1000'),
            (int(post_kraken_reward), 'receive', '1500'),
            (int(withdrawal), 'receive', '2000'),
            (int(eth_spend), 'spend', None),
            (int(kraken_spend), 'spend', None),
        ]
        rows_by_id = {
            row[0]: row[1:]
            for row in _rows(
                database,
                'event_identifier, lots_consumed_json, realized_pnl, taxfree_pnl',
            )
        }
        # Pre-Shapella Kraken lot was held 3000s (> 2500s), so the $2000 gain is tax-free.
        lots, realized_pnl, taxfree_pnl = rows_by_id[int(kraken_spend)]
        assert [
            (lot['lot_id'], lot['acquired_at'], lot['taxable']) for lot in json.loads(lots)
        ] == [(pre_kraken_reward, t_pre, False)]
        assert (realized_pnl, taxfree_pnl) == ('0', '2000')


def test_mark_stale_from_ts_advances_modification_markers_monotonically(
        database: DBHandler,
) -> None:
    """Repeated invalidations within the same millisecond still advance both modification markers,
    while from_ts only moves backward."""
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name IN (?, ?, ?, ?)',
            (
                DBCacheStatic.STALE_BALANCES_FROM_TS.value,
                DBCacheStatic.STALE_BALANCES_MODIFICATION_TS.value,
                DBCacheStatic.STALE_COST_BASIS_FROM_TS.value,
                DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS.value,
            ),
        )

    with patch('rotkehlchen.db.cache.ts_now_in_ms', return_value=1000):
        with database.user_write() as write_cursor:
            mark_stale_from_ts(write_cursor=write_cursor, from_ts=5000)
        with database.user_write() as write_cursor:
            mark_stale_from_ts(write_cursor=write_cursor, from_ts=7000)
        with database.user_write() as write_cursor:
            mark_stale_from_ts(write_cursor=write_cursor, from_ts=3000, include_balances=False)

    with database.conn.read_ctx() as cursor:
        assert database.get_static_caches(
            cursor=cursor,
            names=(
                DBCacheStatic.STALE_BALANCES_FROM_TS,
                DBCacheStatic.STALE_BALANCES_MODIFICATION_TS,
                DBCacheStatic.STALE_COST_BASIS_FROM_TS,
                DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS,
            ),
        ) == ('5000', '1001', '3000', '1002')


def test_repeated_append_only_passes_keep_bounded_checkpoints(database: DBHandler) -> None:
    """Repeated incremental append-only passes replace the terminal checkpoint instead of
    accumulating a snapshot per pass, while still keeping periodic interval checkpoints."""
    def query_historical_price(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return Price(FVal(1000 + int(timestamp)))

    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price = query_historical_price
        _process(
            database=database,
            method=CostBasisMethod.FIFO,
            events=[_event(at=1, amount='1', event_type=HistoryEventType.RECEIVE)],
        )
        assert _checkpoint_timestamps(database) == [_ts_ms(1) + 1]

        # With the default 10_000 interval, repeated single-event appends keep 1 checkpoint.
        for second in range(2, 11):
            with database.user_write() as write_cursor:
                DBHistoryEvents(database).add_history_event(
                    write_cursor=write_cursor,
                    event=_event(at=second, amount='1', event_type=HistoryEventType.RECEIVE),
                )
            assert _process_counting_applied(database) == [_ts_ms(second)]
            assert _checkpoint_timestamps(database) == [_ts_ms(second) + 1]

        # With a small interval of 3, checkpoints stay bounded to floor(N / 3) + 1.
        with database.user_write() as write_cursor:
            write_cursor.execute('DELETE FROM event_cost_basis')
            write_cursor.execute('DELETE FROM cost_basis_checkpoints')
            write_cursor.execute('DELETE FROM history_events')
            write_cursor.execute(
                'DELETE FROM key_value_cache WHERE name IN (?, ?, ?)',
                (
                    DBCacheStatic.LAST_COST_BASIS_PROCESSING_TS.value,
                    DBCacheStatic.STALE_COST_BASIS_FROM_TS.value,
                    DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS.value,
                ),
            )

        with patch('rotkehlchen.tasks.cost_basis.COST_BASIS_CHECKPOINT_INTERVAL', 3):
            for second in range(1, 11):
                with database.user_write() as write_cursor:
                    DBHistoryEvents(database).add_history_event(
                        write_cursor=write_cursor,
                        event=_event(at=second, amount='1', event_type=HistoryEventType.RECEIVE),
                    )
                assert _process_counting_applied(database) == [_ts_ms(second)]
                assert len(_checkpoint_timestamps(database)) <= second // 3 + 1

            assert _checkpoint_timestamps(database) == [
                _ts_ms(3) + 1, _ts_ms(6) + 1, _ts_ms(9) + 1, _ts_ms(10) + 1,
            ]
            incremental_rows = _rows(database)

            with database.user_write() as write_cursor:
                write_cursor.execute('DELETE FROM event_cost_basis')
                write_cursor.execute('DELETE FROM cost_basis_checkpoints')
                write_cursor.execute(
                    'DELETE FROM key_value_cache WHERE name = ?',
                    (DBCacheStatic.LAST_COST_BASIS_PROCESSING_TS.value,),
                )
            assert process_cost_basis(database, database.msg_aggregator) is True
            assert _rows(database) == incremental_rows


def test_reset_accounting_rules_invalidates_event_specific_and_custom_rules(
        database: DBHandler,
        queried_prices: list[tuple[str, Timestamp]],
) -> None:
    """Resetting accounting rules marks the whole cost basis stale so events whose deleted
    event-specific or custom type rules are not restored by defaults are reprocessed."""
    _add_rule(database, HistoryEventType.LOSS, HistoryEventSubType.NONE, taxable=True)
    acquired, spend_specific, custom_loss = _process(
        database=database,
        method=CostBasisMethod.FIFO,
        events=[
            _event(at=1, amount='2', event_type=HistoryEventType.RECEIVE),
            _event(at=2, amount='1', event_type=HistoryEventType.SPEND),
            _event(at=4, amount='1', event_type=HistoryEventType.LOSS),
        ],
    )
    # Attach an event-specific override making the spend non-taxable and rematerialize.
    _add_rule(
        database,
        HistoryEventType.SPEND,
        HistoryEventSubType.NONE,
        taxable=False,
        event_ids=[int(spend_specific)],
    )
    assert process_cost_basis(database, database.msg_aggregator) is True
    assert _rows(database, 'event_identifier, realized_pnl') == [
        (int(acquired), None),
        (int(spend_specific), '0'),
        (int(custom_loss), '3000'),
    ]

    # Reset rules to defaults that only include a generic SPEND rule (no LOSS rule and no
    # event-specific rule). Both previously customized events must become stale and update.
    updater = RotkiDataUpdater(msg_aggregator=database.msg_aggregator, user_db=database)
    default_rules = {
        UpdateType.ACCOUNTING_RULES.value: [{
            'event_type': HistoryEventType.SPEND.serialize(),
            'event_subtype': HistoryEventSubType.NONE.serialize(),
            'counterparty': None,
            'taxable': True,
            'count_entire_amount_spend': False,
            'count_cost_basis_pnl': True,
            'accounting_treatment': None,
        }],
    }
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name = ?',
            (DBCacheStatic.STALE_BALANCES_FROM_TS.value,),
        )
    with (
        patch.object(
            updater,
            '_get_remote_info_json',
            return_value={UpdateType.ACCOUNTING_RULES.value: {'latest': 1, 'limits': {}}},
        ),
        patch('rotkehlchen.db.updates.query_file', return_value=default_rules),
    ):
        updater.reset_accounting_rules()

    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        ) == '0'
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_BALANCES_FROM_TS,
        ) is None

    assert process_cost_basis(database, database.msg_aggregator) is True
    # Event-specific non-taxable override is gone (SPEND now realizes 2000 from default rule);
    # custom LOSS rule is gone (LOSS now has no rule and realizes 0).
    assert _rows(database, 'event_identifier, realized_pnl') == [
        (int(acquired), None),
        (int(spend_specific), '2000'),
        (int(custom_loss), '0'),
    ]


def test_ignored_actions_excluded_and_invalidated_on_toggle(
        database: DBHandler,
        queried_prices: list[tuple[str, Timestamp]],
) -> None:
    """Events whose group_identifier is in ignored_actions are excluded from lot tracking and
    realized PnL, and toggling ignored_actions marks cost basis stale from the group's first
    event."""
    ev1 = _event(at=1, amount='1', event_type=HistoryEventType.RECEIVE)
    ev2 = _event(at=2, amount='1', event_type=HistoryEventType.RECEIVE)
    ev3 = _event(at=4, amount='1', event_type=HistoryEventType.SPEND)
    lot1, lot2, spend = _process(
        database=database,
        method=CostBasisMethod.FIFO,
        events=[ev1, ev2, ev3],
    )
    assert _rows(database, 'event_identifier, realized_pnl') == [
        (int(lot1), None),
        (int(lot2), None),
        (int(spend), '3000'),
    ]

    # Ignoring the first acquisition drops its row and shifts the spend onto lot2.
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name = ?',
            (DBCacheStatic.STALE_BALANCES_FROM_TS.value,),
        )
        database.add_to_ignored_action_ids(write_cursor, [ev1.group_identifier])

    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        ) == str(_ts_ms(1))
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_BALANCES_FROM_TS,
        ) is None

    assert process_cost_basis(database, database.msg_aggregator) is True
    assert _rows(database, 'event_identifier, realized_pnl') == [
        (int(lot2), None),
        (int(spend), '1000'),
    ]

    # Ignoring the spend removes its row altogether.
    with database.user_write() as write_cursor:
        database.add_to_ignored_action_ids(write_cursor, [ev3.group_identifier])
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        ) == str(_ts_ms(4))
    assert process_cost_basis(database, database.msg_aggregator) is True
    assert _rows(database, 'event_identifier, realized_pnl') == [(int(lot2), None)]

    # Un-ignoring both restores the original lots and realized PnL.
    with database.user_write() as write_cursor:
        database.remove_from_ignored_action_ids(
            write_cursor,
            [ev1.group_identifier, ev3.group_identifier],
        )
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        ) == str(_ts_ms(1))
    assert process_cost_basis(database, database.msg_aggregator) is True
    assert _rows(database, 'event_identifier, realized_pnl') == [
        (int(lot1), None),
        (int(lot2), None),
        (int(spend), '3000'),
    ]


def test_ignored_assets_invalidate_cost_basis_and_swap_pairing(
        database: DBHandler,
        queried_prices: list[tuple[str, Timestamp]],
) -> None:
    """Ignoring or un-ignoring an asset via add/remove/ignore_multiple marks cost basis stale
    from the affected groups so dropped rows and changed swap pairing are recomputed."""
    swap_tx = make_evm_tx_hash()
    # With include_crypto2crypto=False:
    # - Paired as a swap: ETH spend realizes 0 (crypto-to-crypto excluded), DAI row created.
    # - With DAI ignored: ETH spend is unpaired and realizes 3000 - 1000 = 2000, DAI row gone.
    acquired, swap_out, swap_in = _process(
        database=database,
        method=CostBasisMethod.FIFO,
        include_crypto2crypto=False,
        events=[
            _event(at=1, amount='1', event_type=HistoryEventType.RECEIVE),
            _event(
                at=2,
                amount='1',
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                tx_ref=swap_tx,
                sequence_index=0,
            ),
            _event(
                at=2,
                amount='2000',
                asset=A_DAI,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.RECEIVE,
                tx_ref=swap_tx,
                sequence_index=1,
            ),
        ],
    )
    assert _rows(database, 'event_identifier, realized_pnl') == [
        (int(acquired), None),
        (int(swap_out), '0'),
        (int(swap_in), None),
    ]

    # Ignoring DAI marks cost basis stale from t=2, removes the DAI row, and unpairs the ETH leg.
    with database.user_write() as write_cursor:
        database.add_to_ignored_assets(write_cursor, A_DAI)
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        ) == str(_ts_ms(2))
    assert process_cost_basis(database, database.msg_aggregator) is True
    assert _rows(database, 'event_identifier, realized_pnl') == [
        (int(acquired), None),
        (int(swap_out), '2000'),
    ]

    # Un-ignoring DAI marks cost basis stale from t=2 and restores the swap pairing.
    with database.user_write() as write_cursor:
        database.remove_from_ignored_assets(write_cursor, A_DAI)
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        ) == str(_ts_ms(2))
    assert process_cost_basis(database, database.msg_aggregator) is True
    assert _rows(database, 'event_identifier, realized_pnl') == [
        (int(acquired), None),
        (int(swap_out), '0'),
        (int(swap_in), None),
    ]

    # Bulk-ignoring DAI via ignore_multiple_assets also marks cost basis stale and drops the row.
    with database.user_write() as write_cursor:
        database.ignore_multiple_assets(write_cursor, [A_DAI.identifier])
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        ) == str(_ts_ms(2))
    assert process_cost_basis(database, database.msg_aggregator) is True
    assert _rows(database, 'event_identifier, realized_pnl') == [
        (int(acquired), None),
        (int(swap_out), '2000'),
    ]


def test_process_balances_and_cost_basis_completion_message_on_skip_balances(
        database: DBHandler,
) -> None:
    """`process_balances_and_cost_basis(skip_balances=True)` sends the completion message in a
    finally whenever the pass ran (even on exception), and omits it when another pass is
    running."""
    completed_type = WSMessageType.HISTORICAL_BALANCE_PROCESSING_COMPLETED

    with patch.object(database.msg_aggregator, 'add_message') as add_message:
        def completed_count() -> int:
            count = sum(
                1 for call in add_message.call_args_list
                if call.kwargs.get('message_type') == completed_type
            )
            add_message.reset_mock()
            return count

        # Exception in cost-basis-only pass still emits completion so frontend clears phase.
        with (
            patch(
                'rotkehlchen.tasks.cost_basis.process_cost_basis',
                side_effect=RuntimeError('boom'),
            ),
            pytest.raises(RuntimeError, match='boom'),
        ):
            process_balances_and_cost_basis(
                database=database,
                msg_aggregator=database.msg_aggregator,
                skip_balances=True,
            )
        assert completed_count() == 1

        # Already-running cost-basis-only pass returns None and does NOT emit completion.
        with patch('rotkehlchen.tasks.cost_basis.process_cost_basis', return_value=None):
            assert process_balances_and_cost_basis(
                database=database,
                msg_aggregator=database.msg_aggregator,
                skip_balances=True,
            ) is None
        assert completed_count() == 0

        # Interrupted (rate-limited) cost-basis-only pass returns False and emits completion.
        with patch('rotkehlchen.tasks.cost_basis.process_cost_basis', return_value=False):
            assert process_balances_and_cost_basis(
                database=database,
                msg_aggregator=database.msg_aggregator,
                skip_balances=True,
            ) is False
        assert completed_count() == 1

        # Exception in historical balances pass also emits completion, while None does not.
        with (
            patch(
                'rotkehlchen.tasks.cost_basis.process_historical_balances',
                side_effect=RuntimeError('balance boom'),
            ),
            pytest.raises(RuntimeError, match='balance boom'),
        ):
            process_balances_and_cost_basis(
                database=database,
                msg_aggregator=database.msg_aggregator,
                skip_balances=False,
            )
        assert completed_count() == 1

        with patch('rotkehlchen.tasks.cost_basis.process_historical_balances', return_value=None):
            assert process_balances_and_cost_basis(
                database=database,
                msg_aggregator=database.msg_aggregator,
                skip_balances=False,
            ) is None
        assert completed_count() == 0


@pytest.mark.parametrize('transient_error', ['remote_error', 'no_price_remote_error'])
@pytest.mark.usefixtures('queried_prices')
def test_transient_oracle_failure_keeps_pass_stale_until_recovery(
        database: DBHandler,
        transient_error: str,
) -> None:
    """Transient oracle failures (direct RemoteError or NoPriceForGivenTimestamp with
    remote_error=True) stop the pass and keep the range stale instead of storing zero_cost,
    and a subsequent pass after recovery materializes the real price."""
    def fail_at_two(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        if timestamp == _ts(2):
            if transient_error == 'remote_error':
                raise RemoteError('oracle timeout', cause=FailureCause.NETWORK)
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
                rate_limited=False,
                remote_error=True,
            )
        return Price(FVal(1000))

    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(write_cursor=write_cursor, history=[
            _event(at=1, amount='1', event_type=HistoryEventType.RECEIVE),
            _event(at=2, amount='1', event_type=HistoryEventType.RECEIVE),
        ])
        write_cursor.execute('DELETE FROM key_value_cache WHERE name LIKE ?', ('stale_cost_%',))

    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price = fail_at_two
        assert process_cost_basis(database, database.msg_aggregator) is False

    assert _rows(database, 'timestamp, basis_per_unit, basis_source') == [
        (_ts_ms(1), '1000', 'price_oracle'),
    ]
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        ) == str(_ts_ms(2))
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.COST_BASIS_STALLED_REASON,
        ) == FailureCause.NETWORK.value
        stalled = get_cost_basis_stalled_info(cursor=cursor, database=database)
        assert stalled is not None
        assert stalled['reason'] == FailureCause.NETWORK.value
        assert stalled['since'] > 0

    # After oracle recovery, the next pass materializes the real price instead of zero_cost.
    assert process_cost_basis(database, database.msg_aggregator) is True
    assert _rows(database, 'timestamp, basis_per_unit, basis_source') == [
        (_ts_ms(1), '1000', 'price_oracle'),
        (_ts_ms(2), '3000', 'price_oracle'),
    ]
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        ) is None
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.COST_BASIS_STALLED_REASON,
        ) is None
        assert get_cost_basis_stalled_info(cursor=cursor, database=database) is None


@pytest.mark.parametrize('rate_limit_error', ['no_price_rate_limited', 'remote_rate_limited'])
@pytest.mark.usefixtures('queried_prices')
def test_rate_limit_persists_stalled_reason_and_reports_in_completion_ws(
        database: DBHandler,
        rate_limit_error: str,
) -> None:
    """Rate-limited oracle errors persist COST_BASIS_STALLED_REASON='rate_limited', report it on
    HISTORICAL_BALANCE_PROCESSING_COMPLETED, and clear it on recovery or cost-basis wipe."""
    def fail_at_two(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        if timestamp == _ts(2):
            if rate_limit_error == 'remote_rate_limited':
                raise RemoteError('too many requests', cause=FailureCause.RATE_LIMITED, error_code=429)  # noqa: E501
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
                rate_limited=True,
                remote_error=False,
            )
        return Price(FVal(1000))

    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(write_cursor=write_cursor, history=[
            _event(at=1, amount='1', event_type=HistoryEventType.RECEIVE),
            _event(at=2, amount='1', event_type=HistoryEventType.RECEIVE),
        ])
        write_cursor.execute('DELETE FROM key_value_cache WHERE name LIKE ?', ('stale_cost_%',))

    with (
        patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian,
        patch.object(database.msg_aggregator, 'add_message') as add_message,
    ):
        historian.return_value.query_historical_price = fail_at_two
        assert process_balances_and_cost_basis(
            database=database,
            msg_aggregator=database.msg_aggregator,
            skip_balances=True,
        ) is False

        completed_calls = [
            call for call in add_message.call_args_list
            if call.kwargs.get('message_type') == WSMessageType.HISTORICAL_BALANCE_PROCESSING_COMPLETED  # noqa: E501
        ]
        assert len(completed_calls) == 1
        ws_stalled = completed_calls[0].kwargs['data'].get('cost_basis_stalled')
        assert ws_stalled is not None
        assert ws_stalled['reason'] == FailureCause.RATE_LIMITED.value
        assert ws_stalled['since'] > 0

    with database.conn.read_ctx() as cursor:
        assert get_cost_basis_stalled_info(cursor=cursor, database=database) == ws_stalled

    # Wiping cost basis clears the persisted stall reason.
    with database.user_write() as write_cursor:
        database._wipe_cost_basis(write_cursor)
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.COST_BASIS_STALLED_REASON,
        ) is None
        assert get_cost_basis_stalled_info(cursor=cursor, database=database) is None


@pytest.mark.parametrize(('status', 'transient'), [(401, False), (404, False), (503, True)])
def test_price_historian_sets_remote_error_only_for_transient_oracle_failures(
        status: int,
        transient: bool,
) -> None:
    """PriceHistorian.query_historical_price sets remote_error=True on NoPriceForGivenTimestamp
    only when an oracle fails in a way a retry may get past, including through the
    fiat-to-crypto inverse path. A rejection such as a 401 or a 404 is final."""
    failing_oracle = MagicMock()
    # Real oracles price crypto in fiat, not fiat in crypto; skipping the outer fiat->crypto
    # loop ensures the inverse path is what propagates remote_error.
    failing_oracle.can_query_history.side_effect = (
        lambda from_asset, to_asset, timestamp: from_asset == A_ETH
    )
    failing_oracle.query_historical_price.side_effect = remote_error_for_status(
        status_code=status,
        message=f'upstream {status}',
    )

    fake_historian = MagicMock()
    fake_historian.get_price_for_special_asset.return_value = None
    fake_historian._oracle_state = HistoricalOracleState(
        oracles=(HistoricalPriceOracle.COINGECKO,),
        instances=[failing_oracle],
    )

    with (
        patch.object(PriceHistorian, '__new__', return_value=fake_historian),
        patch('rotkehlchen.history.price.GlobalDBHandler.get_historical_price', return_value=None),
        patch(
            'rotkehlchen.history.price.GlobalDBHandler.get_historical_price_misses_and_guard',
            return_value=(set(), 0),
        ),
    ):
        with pytest.raises(NoPriceForGivenTimestamp) as direct_exc:
            PriceHistorian.query_historical_price(
                from_asset=A_ETH,
                to_asset=A_USD,
                timestamp=_ts(1000),
            )
        assert direct_exc.value.rate_limited is False
        assert direct_exc.value.remote_error is transient

        with pytest.raises(NoPriceForGivenTimestamp) as inverse_exc:
            PriceHistorian.query_historical_price(
                from_asset=A_USD,
                to_asset=A_ETH,
                timestamp=_ts(1000),
            )
        assert inverse_exc.value.rate_limited is False
        assert inverse_exc.value.remote_error is transient


@pytest.mark.parametrize(('status', 'transient'), [(401, False), (404, False), (503, True)])
def test_oracle_rejection_stores_zero_cost_while_outage_stops_pass(
        database: DBHandler,
        status: int,
        transient: bool,
) -> None:
    """An oracle rejecting a price query (a 401 for old history, a 404 for a delisted id)
    lets the pass finish with a zero cost lot, as no retry would get a price. An outage (503)
    stops the pass and keeps the range stale to be retried."""
    def query_oracle(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        if timestamp == _ts(2):
            raise remote_error_for_status(status_code=status, message=f'upstream {status}')
        return Price(FVal(1000))

    oracle = MagicMock()
    oracle.can_query_history.return_value = True
    oracle.query_historical_price.side_effect = query_oracle
    fake_historian = MagicMock()
    fake_historian.get_price_for_special_asset.return_value = None
    fake_historian.query_historical_price = PriceHistorian.query_historical_price
    fake_historian._oracle_state = HistoricalOracleState(
        oracles=(HistoricalPriceOracle.COINGECKO,),
        instances=[oracle],
    )
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(write_cursor=write_cursor, history=[
            _event(at=1, amount='1', event_type=HistoryEventType.RECEIVE),
            _event(at=2, amount='1', event_type=HistoryEventType.RECEIVE),
        ])
        write_cursor.execute('DELETE FROM key_value_cache WHERE name LIKE ?', ('stale_cost_%',))

    with (
        patch.object(PriceHistorian, '__new__', return_value=fake_historian),
        patch('rotkehlchen.history.price.GlobalDBHandler.get_historical_price', return_value=None),
        patch('rotkehlchen.history.price.GlobalDBHandler.add_historical_prices'),
        patch(
            'rotkehlchen.history.price.GlobalDBHandler.get_historical_price_misses_and_guard',
            return_value=(set(), 0),
        ),
    ):
        assert process_cost_basis(database, database.msg_aggregator) is not transient

    expected_rows = [(_ts_ms(1), '1000', 'price_oracle')]
    if not transient:
        expected_rows.append((_ts_ms(2), '0', 'zero_cost'))
    assert _rows(database, 'timestamp, basis_per_unit, basis_source') == expected_rows
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        ) == (str(_ts_ms(2)) if transient else None)


def test_price_query_rejection_raised_directly_stores_zero_cost(database: DBHandler) -> None:
    """A RemoteError that the price query raises directly, e.g. from a node pricing an LP
    token, only stops the pass if a retry may get past it."""
    def reject_at_two(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        if timestamp == _ts(2):
            raise RemoteError('rejected', cause=FailureCause.REMOTE_REJECTED, error_code=404)
        return Price(FVal(1000))

    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(write_cursor=write_cursor, history=[
            _event(at=1, amount='1', event_type=HistoryEventType.RECEIVE),
            _event(at=2, amount='1', event_type=HistoryEventType.RECEIVE),
        ])
        write_cursor.execute('DELETE FROM key_value_cache WHERE name LIKE ?', ('stale_cost_%',))

    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price = reject_at_two
        assert process_cost_basis(database, database.msg_aggregator) is True

    assert _rows(database, 'timestamp, basis_per_unit, basis_source') == [
        (_ts_ms(1), '1000', 'price_oracle'),
        (_ts_ms(2), '0', 'zero_cost'),
    ]


def _stale_cost_basis_from_ts(database: DBHandler) -> str | None:
    with database.conn.read_ctx() as cursor:
        return database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        )


def _clear_stale_cost_basis_markers(database: DBHandler) -> None:
    with database.user_write() as write_cursor:
        write_cursor.execute('DELETE FROM key_value_cache WHERE name LIKE ?', ('stale_cost_%',))


def test_manual_price_change_of_another_profile_marks_cost_basis_stale(
        database: DBHandler,
) -> None:
    """Manual prices are shared by every profile of the data directory. A change made while
    this profile was not logged in marks its cost basis stale when it applies the recorded
    changes at login, and each change is applied only once."""
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(write_cursor=write_cursor, history=[
            _event(at=1, amount='1', event_type=HistoryEventType.RECEIVE),
        ])

    DBHistoryEvents(database).apply_manual_price_changes()  # what the profile saw so far
    _clear_stale_cost_basis_markers(database)
    price = HistoricalPrice(
        from_asset=A_ETH,
        to_asset=A_USD,
        source=HistoricalPriceOracle.MANUAL,
        timestamp=_ts(1),
        price=Price(FVal(1500)),
    )
    # Another profile adds the price: only the global DB changes
    assert GlobalDBHandler.add_single_historical_price(price) is True
    assert _stale_cost_basis_from_ts(database) is None

    DBHistoryEvents(database).apply_manual_price_changes()  # this profile logs in
    assert _stale_cost_basis_from_ts(database) == str(_ts_ms(1))

    _clear_stale_cost_basis_markers(database)
    DBHistoryEvents(database).apply_manual_price_changes()  # and logs in again
    assert _stale_cost_basis_from_ts(database) is None

    assert GlobalDBHandler.edit_manual_price(price._replace(price=Price(FVal(1600)))) is True
    DBHistoryEvents(database).apply_manual_price_changes()
    assert _stale_cost_basis_from_ts(database) == str(_ts_ms(1))

    _clear_stale_cost_basis_markers(database)
    assert GlobalDBHandler.delete_historical_price(
        from_asset=A_ETH,
        to_asset=A_USD,
        timestamp=_ts(1),
        source_type=HistoricalPriceOracle.MANUAL,
    ) is True
    DBHistoryEvents(database).apply_manual_price_changes()
    assert _stale_cost_basis_from_ts(database) == str(_ts_ms(1))


def test_manual_prices_turned_historical_mark_cost_basis_stale(database: DBHandler) -> None:
    """Replacing a manual current price keeps the old one as a manual historical price, and
    saving a balance snapshot stores the manual current prices as historical ones. Both add
    prices the cost basis may use, so both mark it stale, but only for prices actually added."""
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(write_cursor=write_cursor, history=[
            _event(at=1, amount='1', event_type=HistoryEventType.RECEIVE),
        ])

    DBHistoryEvents(database).apply_manual_price_changes()
    _clear_stale_cost_basis_markers(database)
    with patch('rotkehlchen.globaldb.handler.ts_now', return_value=_ts(1)):
        GlobalDBHandler.add_manual_latest_price(
            from_asset=A_ETH,
            to_asset=A_USD,
            price=Price(FVal(1500)),
        )
    DBHistoryEvents(database).apply_manual_price_changes()
    assert _stale_cost_basis_from_ts(database) is None  # a current price is not historical

    with patch('rotkehlchen.globaldb.handler.ts_now', return_value=_ts(5000)):
        GlobalDBHandler.add_manual_latest_price(  # keeps the price at 1 as a historical one
            from_asset=A_ETH,
            to_asset=A_USD,
            price=Price(FVal(1600)),
        )
    DBHistoryEvents(database).apply_manual_price_changes()
    assert _stale_cost_basis_from_ts(database) == str(_ts_ms(1))

    _clear_stale_cost_basis_markers(database)
    snapshot: dict[str, Any] = {'assets': {A_ETH: {}}, 'liabilities': {}}
    with patch('rotkehlchen.rotkehlchen.ts_now', return_value=_ts(2)):
        Rotkehlchen._save_manual_prices_as_historical(snapshot)
    DBHistoryEvents(database).apply_manual_price_changes()
    assert _stale_cost_basis_from_ts(database) == str(_ts_ms(1))

    _clear_stale_cost_basis_markers(database)
    with patch('rotkehlchen.rotkehlchen.ts_now', return_value=_ts(2)):
        Rotkehlchen._save_manual_prices_as_historical(snapshot)  # the price is already stored
    DBHistoryEvents(database).apply_manual_price_changes()
    assert _stale_cost_basis_from_ts(database) is None


def test_old_manual_price_changes_are_pruned(database: DBHandler) -> None:
    """Only the recent manual price changes stay recorded. A profile that applied the removed
    ones keeps applying just the newer changes, while one that missed a removed change marks
    its whole cost basis stale once, since it can't know which prices it missed."""
    def add_price(recorded_at: int, timestamp: int) -> None:
        with patch('rotkehlchen.globaldb.handler.ts_now_in_ms', return_value=recorded_at):
            assert GlobalDBHandler.add_single_historical_price(HistoricalPrice(
                from_asset=A_ETH,
                to_asset=A_USD,
                source=HistoricalPriceOracle.MANUAL,
                timestamp=_ts(timestamp),
                price=Price(FVal(1500)),
            )) is True

    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(write_cursor=write_cursor, history=[
            _event(at=1, amount='1', event_type=HistoryEventType.RECEIVE),
            _event(at=10_000, amount='1', event_type=HistoryEventType.RECEIVE),
        ])

    DBHistoryEvents(database).apply_manual_price_changes()
    add_price(recorded_at=(first_id := 1_700_000_000_000), timestamp=10_000)
    DBHistoryEvents(database).apply_manual_price_changes()
    _clear_stale_cost_basis_markers(database)

    add_price(recorded_at=first_id + MANUAL_PRICE_CHANGES_RETENTION_MS + 1, timestamp=10_001)
    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM general_cache WHERE key=?',
            (CacheType.MANUAL_PRICE_CHANGES.serialize(),),
        ).fetchone()[0] == 1  # the first change was removed

    DBHistoryEvents(database).apply_manual_price_changes()  # applied the removed change
    assert _stale_cost_basis_from_ts(database) == str(_ts_ms(10_000))  # only from the new price

    _clear_stale_cost_basis_markers(database)
    with database.user_write() as write_cursor:  # a profile that never saw the first change
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_MANUAL_PRICE_CHANGE_ID,
            value=str(first_id - 1),
        )
    DBHistoryEvents(database).apply_manual_price_changes()
    assert _stale_cost_basis_from_ts(database) == str(_ts_ms(1))  # from its first event

    _clear_stale_cost_basis_markers(database)
    DBHistoryEvents(database).apply_manual_price_changes()
    assert _stale_cost_basis_from_ts(database) is None


@pytest.mark.parametrize('missing_exc', ['no_price', 'unsupported_asset'])
@pytest.mark.parametrize(('count_cost_basis_pnl', 'count_entire_amount_spend'), [
    (True, False),
    (False, True),
    (True, True),
])
def test_unpriced_taxable_spend_leaves_pnl_null_while_consuming_lots(
        database: DBHandler,
        missing_exc: str,
        count_cost_basis_pnl: bool,
        count_entire_amount_spend: bool,
) -> None:
    """When a rule-counted taxable spend has no market price, proceeds, realized_pnl, and
    taxfree_pnl are stored as NULL rather than booking a phantom loss, while lots are still
    consumed so subsequent spends stay accurate."""
    def missing_price_at_two(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        if timestamp == _ts(2):
            if missing_exc == 'no_price':
                raise NoPriceForGivenTimestamp(
                    from_asset=from_asset,
                    to_asset=to_asset,
                    time=timestamp,
                    rate_limited=False,
                )
            raise PriceQueryUnsupportedAsset(from_asset.identifier)
        return Price(FVal(ETH_PRICES[timestamp]))

    _add_rule(
        database=database,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        taxable=True,
        count_cost_basis_pnl=count_cost_basis_pnl,
        count_entire_amount_spend=count_entire_amount_spend,
    )
    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price = missing_price_at_two
        acquired, unpriced_spend, later_spend = _process(
            database=database,
            method=CostBasisMethod.FIFO,
            events=[
                _event(at=1, amount='2', event_type=HistoryEventType.RECEIVE),
                _event(
                    at=2,
                    amount='1',
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.FEE,
                ),
                _event(at=4, amount='1', event_type=HistoryEventType.SPEND),
            ],
        )

    rows = _rows(
        database=database,
        columns=(
            'event_identifier, lots_consumed_json, proceeds, realized_pnl, taxfree_pnl, '
            'basis_removed, post_spend_basis_remaining'
        ),
    )
    unpriced_row = rows[1]
    assert unpriced_row[0] == int(unpriced_spend)
    assert [(lot['lot_id'], FVal(lot['amount_consumed'])) for lot in json.loads(unpriced_row[1])] == [  # noqa: E501
        (acquired, FVal(1)),
    ]
    assert unpriced_row[2:] == (None, None, None, '1000', '1000')

    # Subsequent priced spend consumes the remaining 1 ETH lot accurately.
    later_row = rows[2]
    assert later_row[0] == int(later_spend)
    assert [(lot['lot_id'], FVal(lot['amount_consumed'])) for lot in json.loads(later_row[1])] == [
        (acquired, FVal(1)),
    ]
    assert later_row[2:] == ('4000', '3000', '0', '1000', '0')


@pytest.mark.parametrize('with_priced_fee', [False, True])
def test_unpriced_swap_leaves_pnl_null_while_consuming_lots(
        database: DBHandler,
        with_priced_fee: bool,
) -> None:
    """A crypto-to-crypto swap with no price for either side stores no proceeds or PnL for
    the spent side instead of a loss of its whole basis, even if a priced fee leg is folded
    into the received side's basis. The lots are still consumed."""
    def no_price_at_two(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        if from_asset == A_DAI:
            return Price(FVal(1))
        if from_asset == A_ETH and timestamp != _ts(2):
            return Price(FVal(ETH_PRICES[timestamp]))
        raise NoPriceForGivenTimestamp(from_asset=from_asset, to_asset=to_asset, time=timestamp)

    tx_ref = make_evm_tx_hash()
    fee_events: list[EvmEvent | HistoryEvent] = [
        _event(at=1, amount='10', event_type=HistoryEventType.RECEIVE, asset=A_DAI),
        _event(
            at=2,
            amount='10',
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_DAI,
            tx_ref=tx_ref,
            sequence_index=2,
        ),
    ] if with_priced_fee else []
    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price = no_price_at_two
        identifiers = _process(
            database=database,
            method=CostBasisMethod.FIFO,
            events=[
                _event(at=1, amount='2', event_type=HistoryEventType.RECEIVE),
                _event(
                    at=2,
                    amount='1',
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.SPEND,
                    tx_ref=tx_ref,
                ),
                _event(
                    at=2,
                    amount='5',
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.RECEIVE,
                    asset=A_BTC,
                    tx_ref=tx_ref,
                    sequence_index=1,
                ),
                _event(at=4, amount='1', event_type=HistoryEventType.SPEND),
                *fee_events,
            ],
        )

    acquired, swapped, later_spend = identifiers[0], identifiers[1], identifiers[3]
    with database.conn.read_ctx() as cursor:
        rows = {
            str(identifier): (
                [(lot['lot_id'], FVal(lot['amount_consumed'])) for lot in json.loads(lots)],
                *rest,
            )
            for identifier, lots, *rest in cursor.execute(
                'SELECT event_identifier, lots_consumed_json, proceeds, realized_pnl, '
                'taxfree_pnl, basis_removed, post_spend_basis_remaining FROM event_cost_basis '
                "WHERE asset='ETH' AND direction='spend'",
            )
        }

    assert rows == {
        swapped: (
            [(acquired, FVal(1))],
            None, None, None, '1000', '1000',
        ),
        later_spend: (
            [(acquired, FVal(1))],
            '4000', '3000', '0', '1000', '0',
        ),
    }
