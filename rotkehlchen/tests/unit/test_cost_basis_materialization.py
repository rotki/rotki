import json
from typing import TYPE_CHECKING, Any, Final
from unittest.mock import patch

import pytest

from rotkehlchen.constants.assets import A_BTC, A_DAI, A_ETH, A_USD
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ETHEREUM, LOCATION_KRAKEN
from rotkehlchen.tasks.cost_basis import process_cost_basis
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import CostBasisMethod, Price, Timestamp, TimestampMS

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash

pytestmark = pytest.mark.accounting_update

# The price of ETH at each second the tests place an event at.
ETH_PRICES: Final = {1: 1000, 2: 3000, 3: 2000, 4: 4000, 5: 5000, 6: 1200, 7: 1500, 8: 1700}
ROW_COLUMNS: Final = (
    'event_identifier, location_label, asset, direction, lot_created_id, basis_per_unit, '
    'basis_source, lots_consumed_json, realized_pnl, basis_removed, post_spend_basis_remaining, '
    'method'
)


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
        timestamp=TimestampMS(at * 1000),
        location=LOCATION_ETHEREUM,
        event_type=event_type,
        event_subtype=event_subtype,
        asset=asset,
        amount=FVal(amount),
        location_label=location_label,
        address=address,
    )


def _process(
        database: DBHandler,
        events: list[EvmEvent | HistoryEvent],
        method: CostBasisMethod,
        **settings: Any,
) -> list[str]:
    """Add the events and process the cost basis.

    Returns the identifiers of the events, as the lots that they create are named.
    """
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
                timestamp=TimestampMS(8000),
                location=LOCATION_KRAKEN,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                asset=A_USD,
                amount=FVal('3200'),
                location_label='kraken',
            ), HistoryEvent(
                group_identifier='fiat_buy',
                sequence_index=1,
                timestamp=TimestampMS(8000),
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
    assert _rows(database, 'event_identifier, direction, basis_per_unit, basis_source')[2:] == [
        (int(received), 'receive', '0.75', 'price_oracle'),  # the 1500 the ETH given was worth
        (int(bought), 'receive', '1600', 'event_amount'),  # the fiat paid, which gets no row
    ]


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
@pytest.mark.parametrize('from_ts', [0, 3000, 5000])
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
        )) == ('1000', '5000')

    assert process_cost_basis(database, database.msg_aggregator) is True
    assert queried_prices == [('ETH', 5)]  # the basis of the earlier lots comes from their rows
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
    def rate_limited(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        raise NoPriceForGivenTimestamp(
            from_asset=from_asset,
            to_asset=to_asset,
            time=timestamp,
            rate_limited=True,
        )

    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=_event(at=1, amount='1', event_type=HistoryEventType.RECEIVE),
        )
        # as on a first pass over events that were there before the markers existed
        write_cursor.execute('DELETE FROM key_value_cache WHERE name LIKE ?', ('stale_cost_%',))

    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price = rate_limited
        assert process_cost_basis(database, database.msg_aggregator) is False

    assert _rows(database) == []
    assert process_cost_basis(database, database.msg_aggregator) is True  # prices are back
    assert len(_rows(database)) == 1
