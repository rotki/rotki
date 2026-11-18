import json
from typing import TYPE_CHECKING, Any, Final
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.cost_basis.lots import BucketLots
from rotkehlchen.accounting.cost_basis.pnl import get_unprocessed_from_ts
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.constants.assets import A_BTC, A_DAI, A_ETH, A_ETH2, A_USD
from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.types import DataIssueFilters
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ETHEREUM, LOCATION_KRAKEN
from rotkehlchen.tasks.cost_basis import _CostBasisPass, process_cost_basis
from rotkehlchen.tasks.historical_balances import Bucket, process_historical_balances
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import CostBasisMethod, Price, Timestamp, TimestampMS

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
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
                timestamp=TimestampMS(7000),
                location=LOCATION_KRAKEN,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                asset=A_USD,
                amount=FVal('3200'),
                location_label='kraken',
            ), HistoryEvent(
                group_identifier='fiat_buy',
                sequence_index=1,
                timestamp=TimestampMS(7000),
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
    def rate_limited_at_two(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        if timestamp == 2:
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
        ) == '2000'
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
    ) -> None:
        if event.timestamp == 3000:
            raise AssertionError('the pass dies at the third event')
        apply(self, event=event, next_event=next_event, treat_eth2_as_eth=treat_eth2_as_eth)

    with (
        patch('rotkehlchen.tasks.cost_basis.COST_BASIS_BATCH_SIZE', 1),
        patch.object(_CostBasisPass, 'apply', apply_until_three),
        pytest.raises(AssertionError),
    ):
        process_cost_basis(database, database.msg_aggregator)

    assert unprocessed_from_ts() == 3000
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
        (acquired[0], 1, False),
        (acquired[1], 2, False),
        (acquired[2], 3, True),
    ]
    assert proceeds == '12500'
    assert realized_pnl == '1500'  # half a unit worth 2500 that was bought for 1000
    assert taxfree_pnl == '6000'  # two units worth 10000 that were bought for 4000


@pytest.mark.parametrize('method', list(CostBasisMethod))
def test_crashed_pass_resumes_from_committed_progress(
        database: DBHandler,
        queried_prices: list[tuple[str, Timestamp]],
        method: CostBasisMethod,
) -> None:
    tx_ref = make_evm_tx_hash()
    events: list[EvmEvent | HistoryEvent] = [
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
    ) -> None:
        if event.timestamp == 5000:
            raise RuntimeError('deterministic crash after committed batches')
        apply(self, event=event, next_event=next_event, treat_eth2_as_eth=treat_eth2_as_eth)

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
    assert queried_prices == [('ETH', 4), ('ETH', 5), ('ETH', 6)]
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
        timestamp=Timestamp(1),
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
            timestamp=Timestamp(2),
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
                (DBCacheStatic.STALE_COST_BASIS_FROM_TS.value, '2000'),
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
