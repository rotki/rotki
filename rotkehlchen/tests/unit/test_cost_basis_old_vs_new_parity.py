"""Side-by-side parity tests comparing the legacy Accountant PnL report against
materialized `event_cost_basis` + `query_realized_pnl()`.
"""
from typing import TYPE_CHECKING, Any, Final
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.accounting.cost_basis.pnl import (
    RealizedPnlGroupBy,
    query_events_cost_basis,
    query_realized_pnl,
)
from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.ethereum.constants import SHAPPELA_TIMESTAMP
from rotkehlchen.chain.ethereum.modules.eth2.constants import CPT_ETH2, MIN_EFFECTIVE_BALANCE
from rotkehlchen.chain.ethereum.modules.eth2.structures import ValidatorDetails, ValidatorType
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_ETH2, A_EUR, A_KFEE, A_USD, A_WETH
from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.history.events.structures.eth2 import (
    EthBlockEvent,
    EthDepositEvent,
    EthWithdrawalEvent,
)
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ETHEREUM, LOCATION_KRAKEN
from rotkehlchen.tasks.cost_basis import process_cost_basis
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import (
    CostBasisMethod,
    Eth2PubKey,
    Price,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash

pytestmark = pytest.mark.accounting_update

BASE_TS: Final = 1_700_000_000


def _ts(offset: int) -> Timestamp:
    return Timestamp(BASE_TS + offset)


def _ts_ms(offset: int) -> TimestampMS:
    return TimestampMS((BASE_TS + offset) * 1000)


def _evm_event(
        at: int,
        amount: str,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType = HistoryEventSubType.NONE,
        asset: Asset = A_ETH,
        location_label: ChecksumEvmAddress = TEST_ADDR1,
        tx_ref: EVMTxHash | None = None,
        sequence_index: int = 0,
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
    )


def _add_rule(
        database: DBHandler,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType = HistoryEventSubType.NONE,
        taxable: bool = True,
        count_entire_amount_spend: bool = False,
        count_cost_basis_pnl: bool = True,
        accounting_treatment: TxAccountingTreatment | None = None,
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
    )


def _make_chains_aggregator_stub() -> MagicMock:
    evm_manager = MagicMock()
    evm_manager.accounting_aggregator.get_accounting_callbacks.return_value = {}
    chains_aggregator = MagicMock()
    chains_aggregator.get_evm_manager.return_value = evm_manager
    return chains_aggregator


def _run_both_pipelines(
        database: DBHandler,
        events: list[HistoryBaseEntry],
        price_fn: Callable[[Asset, Asset, Timestamp], Price],
        start_ts: Timestamp,
        end_ts: Timestamp,
        method: CostBasisMethod = CostBasisMethod.FIFO,
        **settings: Any,
) -> tuple[tuple[FVal, FVal], dict[str, Any]]:
    """Persist `events`, run legacy Accountant and new cost-basis + realized PnL query,
    and return `((old_taxable, old_free), new_realized_pnl_result)`.
    """
    with database.user_write() as write_cursor:
        main_currency = settings.pop('main_currency', A_USD.resolve_to_asset_with_oracles())
        database.set_settings(
            write_cursor,
            ModifiableDBSettings(
                main_currency=main_currency,
                cost_basis_method=method,
                **settings,
            ),
        )
        DBHistoryEvents(database).add_history_events(write_cursor=write_cursor, history=events)

    with (
        patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as new_historian,
        patch('rotkehlchen.accounting.pot.PriceHistorian') as old_historian,
    ):
        new_historian.return_value.query_historical_price = price_fn
        old_historian.return_value.query_historical_price = price_fn

        assert process_cost_basis(database, database.msg_aggregator) is True
        new_result = query_realized_pnl(
            database=database,
            filter_query=HistoryEventFilterQuery.make(
                from_ts=start_ts,
                to_ts=end_ts,
                exclude_ignored_assets=True,
                exclude_ignored_actions=True,
                exclude_untracked_withdrawals=True,
            ),
            group_by=RealizedPnlGroupBy.ASSET,
        )

        with database.conn.read_ctx() as cursor:
            db_events = DBHistoryEvents(database).get_history_events_internal(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    from_ts=Timestamp(0),
                    to_ts=end_ts,
                    exclude_untracked_withdrawals=True,
                ),
                aggregate_by_group_ids=False,
            )
        db_events.sort(key=lambda x: (x.timestamp, x.group_identifier, x.sequence_index))
        premium = MagicMock()
        premium.is_active.return_value = True
        accountant = Accountant(
            db=database,
            msg_aggregator=database.msg_aggregator,
            chains_aggregator=_make_chains_aggregator_stub(),
            premium=premium,
        )
        accountant.process_history(start_ts=start_ts, end_ts=end_ts, events=db_events)
        old_pnls = accountant.pots[0].pnls
        return (old_pnls.taxable, old_pnls.free), new_result


def _assert_pnl_parity(
        old_totals: tuple[FVal, FVal],
        new_result: dict[str, Any],
) -> None:
    old_taxable, old_free = old_totals
    assert FVal(new_result['total_realized_pnl']) == old_taxable
    assert FVal(new_result['total_taxfree_pnl']) == old_free
    assert new_result['stale'] is False


@pytest.mark.parametrize('method', list(CostBasisMethod))
def test_baseline_parity_across_cost_basis_methods(
        database: DBHandler,
        method: CostBasisMethod,
) -> None:
    """Single-wallet buys, sells, swaps, fees, and basis transfers match old PnL across methods."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)
    _add_rule(
        database=database,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        accounting_treatment=TxAccountingTreatment.SWAP,
    )
    _add_rule(
        database=database,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        taxable=False,
        accounting_treatment=TxAccountingTreatment.BASIS_TRANSFER,
    )

    prices = {
        (A_ETH, _ts(1)): Price(FVal(1000)),
        (A_ETH, _ts(2)): Price(FVal(3000)),
        (A_ETH, _ts(3)): Price(FVal(2000)),
        (A_ETH, _ts(4)): Price(FVal(4000)),
        (A_ETH, _ts(5)): Price(FVal(5000)),
        (A_WETH, _ts(5)): Price(FVal(5000)),
        (A_WETH, _ts(6)): Price(FVal(6000)),
        (A_DAI, _ts(4)): Price(FVal(1)),
        (A_USD, _ts(6)): Price(FVal(1)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        if (from_asset, timestamp) in prices:
            return prices[from_asset, timestamp]
        raise NoPriceForGivenTimestamp(from_asset=from_asset, to_asset=to_asset, time=timestamp)

    swap_tx = make_evm_tx_hash()
    wrap_tx = make_evm_tx_hash()
    sell_tx = make_evm_tx_hash()
    events: list[HistoryBaseEntry] = [
        _evm_event(at=1, amount='1', event_type=HistoryEventType.RECEIVE),
        _evm_event(at=2, amount='1', event_type=HistoryEventType.RECEIVE),
        _evm_event(at=3, amount='1', event_type=HistoryEventType.RECEIVE),
        # Swap 1 ETH -> 4000 DAI with 0.1 ETH fee
        _evm_event(
            at=4, amount='1', event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND, tx_ref=swap_tx, sequence_index=0,
        ),
        _evm_event(
            at=4, amount='4000', asset=A_DAI, event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE, tx_ref=swap_tx, sequence_index=1,
        ),
        _evm_event(
            at=4, amount='0.1', event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.FEE, tx_ref=swap_tx, sequence_index=2,
        ),
        # Wrap 1 ETH -> 1 WETH (basis transfer)
        _evm_event(
            at=5,
            amount='1',
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            tx_ref=wrap_tx,
            sequence_index=0,
        ),
        _evm_event(
            at=5, amount='1', asset=A_WETH, event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED, tx_ref=wrap_tx, sequence_index=1,
        ),
        # Sell 1 WETH for 6000 USD
        _evm_event(
            at=6, amount='1', asset=A_WETH, event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND, tx_ref=sell_tx, sequence_index=0,
        ),
        _evm_event(
            at=6, amount='6000', asset=A_USD, event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE, tx_ref=sell_tx, sequence_index=1,
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_ts(1),
        end_ts=_ts(10),
        method=method,
        include_crypto2crypto=True,
        include_fees_in_cost_basis=True,
    )
    _assert_pnl_parity(old_totals, new_result)
    assert old_totals[0] > ZERO


def test_taxfree_after_period_parity(database: DBHandler) -> None:
    """Taxable and tax-free gains under `taxfree_after_period` match old PnL."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)

    prices = {
        (A_ETH, _ts(0)): Price(FVal(1000)),     # held 2000s (> 1000s => tax-free)
        (A_ETH, _ts(1500)): Price(FVal(2500)),  # held 500s (< 1000s => taxable)
        (A_ETH, _ts(2000)): Price(FVal(4000)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    events: list[HistoryBaseEntry] = [
        _evm_event(at=0, amount='1', event_type=HistoryEventType.RECEIVE),
        _evm_event(at=1500, amount='1', event_type=HistoryEventType.RECEIVE),
        _evm_event(at=2000, amount='1.5', event_type=HistoryEventType.SPEND),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_ts(0),
        end_ts=_ts(3000),
        taxfree_after_period=1000,
    )
    # 1 ETH tax-free gain: 4000 - 1000 = 3000; 0.5 ETH taxable gain: 2000 - 1250 = 750.
    assert old_totals == (FVal(750), FVal(3000))
    _assert_pnl_parity(old_totals, new_result)
    assert new_result['breakdown'] == [{
        'group_key': 'ETH',
        'realized_pnl': '750',
        'taxfree_pnl': '3000',
        'basis_removed': '2250',
        'num_events': 1,
        'num_unpriced_events': 0,
    }]


def test_taxable_receive_income_parity(database: DBHandler) -> None:
    """Taxable receives (airdrops, staking, Kraken staking) realize income matching old PnL."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)
    _add_rule(
        database=database,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.AIRDROP,
        taxable=True,
    )
    _add_rule(
        database=database,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REWARD,
        taxable=True,
    )

    prices = {
        (A_ETH, _ts(1)): Price(FVal(1000)),  # non-taxable plain receive (no rule)
        (A_ETH, _ts(2)): Price(FVal(2000)),  # taxable airdrop (0.5 ETH = 1000 income)
        (A_ETH, _ts(3)): Price(FVal(2500)),  # taxable staking reward (0.4 ETH = 1000 income)
        # spend 1.5 ETH (1 @ 1000 + 0.5 @ 2000 => 4500 - 2000 = 2500 gain)
        (A_ETH, _ts(4)): Price(FVal(3000)),
        # Kraken staking reward (0.25 ETH2 = 800 income, no explicit rule needed)
        (A_ETH2, _ts(5)): Price(FVal(3200)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    events: list[HistoryBaseEntry] = [
        _evm_event(at=1, amount='1', event_type=HistoryEventType.RECEIVE),
        _evm_event(
            at=2, amount='0.5', event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
        ),
        _evm_event(
            at=3, amount='0.4', event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
        ),
        _evm_event(at=4, amount='1.5', event_type=HistoryEventType.SPEND),
        HistoryEvent(
            group_identifier='kraken_stake_reward',
            sequence_index=0,
            timestamp=_ts_ms(5),
            location=LOCATION_KRAKEN,
            location_label='kraken',
            asset=A_ETH2,
            amount=FVal('0.25'),
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_ts(1),
        end_ts=_ts(10),
    )
    # 1000 (airdrop) + 1000 (staking) + 2500 (disposal) + 800 (kraken staking) = 5300
    assert old_totals == (FVal(5300), ZERO)
    _assert_pnl_parity(old_totals, new_result)


@pytest.mark.parametrize('include_fees_in_cost_basis', [False, True])
def test_fiat_swap_fee_parity(
        database: DBHandler,
        include_fees_in_cost_basis: bool,
) -> None:
    """Swaps with fiat (USD) fees match old PnL whether fees are folded into basis or expensed."""
    _add_rule(
        database=database,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        accounting_treatment=TxAccountingTreatment.SWAP,
    )

    prices = {
        (A_USD, _ts(1)): Price(FVal(1)),
        (A_ETH, _ts(1)): Price(FVal(2000)),
        (A_USD, _ts(2)): Price(FVal(1)),
        (A_ETH, _ts(2)): Price(FVal(3000)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    events: list[HistoryBaseEntry] = [
        # Buy 1 ETH for 2000 USD with a 10 USD fee
        SwapEvent(
            timestamp=_ts_ms(1), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.SPEND, asset=A_USD, amount=FVal(2000),
            group_identifier='buy_eth', sequence_index=0,
        ),
        SwapEvent(
            timestamp=_ts_ms(1), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.RECEIVE, asset=A_ETH, amount=FVal(1),
            group_identifier='buy_eth', sequence_index=1,
        ),
        SwapEvent(
            timestamp=_ts_ms(1), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.FEE, asset=A_USD, amount=FVal(10),
            group_identifier='buy_eth', sequence_index=2,
        ),
        # Sell 1 ETH for 3000 USD with a 15 USD fee
        SwapEvent(
            timestamp=_ts_ms(2), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.SPEND, asset=A_ETH, amount=FVal(1),
            group_identifier='sell_eth', sequence_index=0,
        ),
        SwapEvent(
            timestamp=_ts_ms(2), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.RECEIVE, asset=A_USD, amount=FVal(3000),
            group_identifier='sell_eth', sequence_index=1,
        ),
        SwapEvent(
            timestamp=_ts_ms(2), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.FEE, asset=A_USD, amount=FVal(15),
            group_identifier='sell_eth', sequence_index=2,
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_ts(1),
        end_ts=_ts(10),
        include_fees_in_cost_basis=include_fees_in_cost_basis,
    )
    # Either way, net PnL is (3000 - 2000) - 10 - 15 = 975.
    assert old_totals == (FVal(975), ZERO)
    _assert_pnl_parity(old_totals, new_result)


def test_fiat_asset_movement_fee_and_taxable_income_parity(database: DBHandler) -> None:
    """Fiat AssetMovement FEEs and taxable fiat receives (e.g. interest) match old PnL."""
    _add_rule(
        database=database,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.INTEREST,
        taxable=True,
    )

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        if from_asset == A_USD:
            return Price(FVal(1))
        raise NoPriceForGivenTimestamp(from_asset=from_asset, to_asset=to_asset, time=timestamp)

    events: list[HistoryBaseEntry] = [
        AssetMovement(
            timestamp=_ts_ms(1),
            location=LOCATION_KRAKEN,
            location_label='kraken',
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USD,
            amount=FVal(25),
            group_identifier='usd_wire_fee',
        ),
        HistoryEvent(
            timestamp=_ts_ms(2),
            location=LOCATION_KRAKEN,
            location_label='kraken',
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            asset=A_USD,
            amount=FVal(100),
            group_identifier='usd_interest',
            sequence_index=0,
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_ts(1),
        end_ts=_ts(10),
    )
    assert old_totals == (FVal(75), ZERO)
    _assert_pnl_parity(old_totals, new_result)


@pytest.mark.parametrize('include_fees_in_cost_basis', [False, True])
def test_kfee_swap_and_withdrawal_fees_parity(
        database: DBHandler,
        include_fees_in_cost_basis: bool,
) -> None:
    """Kraken KFEE fees match old PnL: folded into basis at $0.01/KFEE when
    `include_fees_in_cost_basis=True`, and non-taxable (0 PnL, not unpriced) otherwise."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(
        database=database,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        accounting_treatment=TxAccountingTreatment.SWAP,
    )

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        if from_asset == A_KFEE:
            return Price(FVal('0.01'))  # matches PriceHistorian's fixed $0.01 KFEE rate
        if from_asset == A_ETH:
            return Price(FVal(2000 if timestamp == _ts(1) else 3000))
        if from_asset == A_USD:
            return Price(FVal(1))
        raise NoPriceForGivenTimestamp(from_asset=from_asset, to_asset=to_asset, time=timestamp)

    events: list[HistoryBaseEntry] = [
        HistoryEvent(
            timestamp=_ts_ms(1), location=LOCATION_KRAKEN, location_label='kraken',
            event_type=HistoryEventType.RECEIVE, event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH, amount=FVal(1), group_identifier='eth_in', sequence_index=0,
        ),
        SwapEvent(
            timestamp=_ts_ms(2), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.SPEND, asset=A_ETH, amount=FVal(1),
            group_identifier='sell_kfee', sequence_index=0,
        ),
        SwapEvent(
            timestamp=_ts_ms(2), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.RECEIVE, asset=A_USD, amount=FVal(3000),
            group_identifier='sell_kfee', sequence_index=1,
        ),
        SwapEvent(
            timestamp=_ts_ms(2), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.FEE, asset=A_KFEE, amount=FVal(500),
            group_identifier='sell_kfee', sequence_index=2,
        ),
        AssetMovement(
            timestamp=_ts_ms(3), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.FEE,
            asset=A_KFEE, amount=FVal(100), group_identifier='kfee_wd',
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_ts(1),
        end_ts=_ts(10),
        include_fees_in_cost_basis=include_fees_in_cost_basis,
    )
    # 500 KFEE = $5 subtracted from proceeds when folded into basis => 995; else 1000.
    expected = FVal(995) if include_fees_in_cost_basis else FVal(1000)
    assert old_totals == (expected, ZERO)
    _assert_pnl_parity(old_totals, new_result)
    assert new_result['num_unpriced_events'] == 0


def test_fiat_swap_fee_in_non_profit_currency_parity(database: DBHandler) -> None:
    """USD swap fees under EUR profit currency convert identically in both pipelines."""
    _add_rule(
        database=database,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        accounting_treatment=TxAccountingTreatment.SWAP,
    )

    # 1 USD = 0.9 EUR
    prices = {
        (A_USD, _ts(1)): Price(FVal('0.9')),
        (A_ETH, _ts(1)): Price(FVal(1800)),
        (A_USD, _ts(2)): Price(FVal('0.9')),
        (A_ETH, _ts(2)): Price(FVal(2700)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    events: list[HistoryBaseEntry] = [
        SwapEvent(
            timestamp=_ts_ms(1), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.SPEND, asset=A_USD, amount=FVal(2000),
            group_identifier='buy_eth_eur', sequence_index=0,
        ),
        SwapEvent(
            timestamp=_ts_ms(1), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.RECEIVE, asset=A_ETH, amount=FVal(1),
            group_identifier='buy_eth_eur', sequence_index=1,
        ),
        SwapEvent(
            timestamp=_ts_ms(1), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.FEE, asset=A_USD, amount=FVal(10),
            group_identifier='buy_eth_eur', sequence_index=2,
        ),
        SwapEvent(
            timestamp=_ts_ms(2), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.SPEND, asset=A_ETH, amount=FVal(1),
            group_identifier='sell_eth_eur', sequence_index=0,
        ),
        SwapEvent(
            timestamp=_ts_ms(2), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.RECEIVE, asset=A_USD, amount=FVal(3000),
            group_identifier='sell_eth_eur', sequence_index=1,
        ),
        SwapEvent(
            timestamp=_ts_ms(2), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.FEE, asset=A_USD, amount=FVal(20),
            group_identifier='sell_eth_eur', sequence_index=2,
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_ts(1),
        end_ts=_ts(10),
        main_currency=A_EUR.resolve_to_asset_with_oracles(),
        include_fees_in_cost_basis=False,
    )
    # 900 EUR capital gain - 9 EUR buy fee - 18 EUR sell fee = 873 EUR
    assert old_totals == (FVal(873), ZERO)
    _assert_pnl_parity(old_totals, new_result)


def test_asset_movement_receive_never_taxable_and_fee_rule_override_parity(
        database: DBHandler,
) -> None:
    """AssetMovement deposits are never taxable income even with an EXCHANGE_TRANSFER rule,
    and an explicit non-taxable FEE rule overrides the default taxable fee fallback."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(
        database=database,
        event_type=HistoryEventType.EXCHANGE_TRANSFER,
        event_subtype=HistoryEventSubType.RECEIVE,
        taxable=True,
    )
    _add_rule(
        database=database,
        event_type=HistoryEventType.EXCHANGE_TRANSFER,
        event_subtype=HistoryEventSubType.FEE,
        taxable=False,
    )

    prices = {
        (A_ETH, _ts(1)): Price(FVal(1000)),
        (A_ETH, _ts(2)): Price(FVal(2000)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    events: list[HistoryBaseEntry] = [
        HistoryEvent(
            timestamp=_ts_ms(1), location=LOCATION_KRAKEN, location_label='kraken',
            event_type=HistoryEventType.RECEIVE, event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH, amount=FVal(1), group_identifier='eth_in', sequence_index=0,
        ),
        AssetMovement(
            timestamp=_ts_ms(1), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH, amount=FVal(1), group_identifier='eth_dep',
        ),
        AssetMovement(
            timestamp=_ts_ms(2), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH, amount=FVal('0.1'), group_identifier='eth_wd_nontax',
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_ts(1),
        end_ts=_ts(10),
    )
    assert old_totals == (ZERO, ZERO)
    _assert_pnl_parity(old_totals, new_result)


def test_windowed_range_excludes_prior_taxable_income_and_splits_taxfree_fee_parity(
        database: DBHandler,
) -> None:
    """Querying [start_ts, end_ts] excludes prior taxable income while keeping its lot basis,
    and a fee from a tax-free lot splits expense (taxable) and gain (tax-free) identically."""
    _add_rule(
        database=database,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.AIRDROP,
        taxable=True,
    )

    prices = {
        (A_ETH, _ts(0)): Price(FVal(1000)),     # airdrop before query window (t=0)
        (A_ETH, _ts(2000)): Price(FVal(3000)),  # fee inside query window, held 2000s (> 1000s)
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    events: list[HistoryBaseEntry] = [
        HistoryEvent(
            timestamp=_ts_ms(0), location=LOCATION_KRAKEN, location_label='kraken',
            event_type=HistoryEventType.RECEIVE, event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_ETH, amount=FVal(1), group_identifier='old_airdrop', sequence_index=0,
        ),
        AssetMovement(
            timestamp=_ts_ms(2000), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH, amount=FVal('0.1'), group_identifier='taxfree_fee',
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_ts(1000),
        end_ts=_ts(3000),
        taxfree_after_period=1000,
    )
    # Prior airdrop is excluded from [1000, 3000].
    # 0.1 ETH fee @ 3000 from $1000 tax-free lot: -300 taxable expense, +200 tax-free gain.
    assert old_totals == (FVal(-300), FVal(200))
    _assert_pnl_parity(old_totals, new_result)


def test_asset_movement_fee_without_accounting_rule_parity(database: DBHandler) -> None:
    """Crypto AssetMovement FEE defaults to taxable expense + cost-basis PnL even with no rule."""
    # Deliberately add NO accounting rules for AssetMovement FEE (only non-taxable receive).
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    prices = {
        (A_ETH, _ts(1)): Price(FVal(1000)),
        (A_ETH, _ts(2)): Price(FVal(3000)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    events: list[HistoryBaseEntry] = [
        HistoryEvent(
            timestamp=_ts_ms(1), location=LOCATION_KRAKEN, location_label='kraken',
            event_type=HistoryEventType.RECEIVE, event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH, amount=FVal(1), group_identifier='buy_eth', sequence_index=0,
        ),
        AssetMovement(
            timestamp=_ts_ms(2), location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH, amount=FVal('0.1'), group_identifier='eth_wd',
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_ts(1),
        end_ts=_ts(10),
    )
    # 0.1 ETH @ 3000 with basis 100: expense (-300) + capital gain (300 - 100 = 200) = -100.
    assert old_totals == (FVal(-100), ZERO)
    _assert_pnl_parity(old_totals, new_result)


@pytest.mark.parametrize('taxable_after_withdrawal', [True, False])
def test_eth2_block_and_withdrawal_parity(
        database: DBHandler,
        taxable_after_withdrawal: bool,
) -> None:
    """Tracked EthBlockEvent and distributing EthWithdrawalEvent match old PnL."""
    _add_rule(database, HistoryEventType.SPEND)
    with database.user_write() as write_cursor:
        database.add_blockchain_accounts(
            write_cursor=write_cursor,
            account_data=[BlockchainAccountData(
                chain=SupportedBlockchain.ETHEREUM,
                address=TEST_ADDR1,
            )],
        )
        DBEth2(database).add_or_update_validators(
            write_cursor=write_cursor,
            validators=[ValidatorDetails(
                validator_index=42,
                public_key=Eth2PubKey('0x' + 'aa' * 48),
                validator_type=ValidatorType.DISTRIBUTING,
                ownership_proportion=FVal(1),
                withdrawal_address=TEST_ADDR1,
                activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
            )],
        )

    t_block = Timestamp(SHAPPELA_TIMESTAMP + 100)
    t_wd = Timestamp(SHAPPELA_TIMESTAMP + 200)
    t_spend = Timestamp(SHAPPELA_TIMESTAMP + 300)
    prices = {
        (A_ETH, t_block): Price(FVal(2000)),
        (A_ETH, t_wd): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    events: list[HistoryBaseEntry] = [
        # Tracked block reward: always taxable (0.1 ETH @ 2000 = 200)
        EthBlockEvent(
            validator_index=42,
            timestamp=ts_sec_to_ms(t_block),
            amount=FVal('0.1'),
            fee_recipient=TEST_ADDR1,
            fee_recipient_tracked=True,
            block_number=17_000_001,
            is_mev_reward=False,
        ),
        # Untracked block reward: ignored in both pipelines
        EthBlockEvent(
            validator_index=42,
            timestamp=ts_sec_to_ms(t_block),
            amount=FVal('0.5'),
            fee_recipient=TEST_ADDR2,
            fee_recipient_tracked=False,
            block_number=17_000_002,
            is_mev_reward=False,
        ),
        # Distributing partial withdrawal (0.2 ETH @ 2500 = 500 if taxable_after_withdrawal else 0)
        EthWithdrawalEvent(
            validator_index=42,
            timestamp=ts_sec_to_ms(t_wd),
            amount=FVal('0.2'),
            withdrawal_address=TEST_ADDR1,
            is_exit=False,
        ),
        # Spend all 0.3 ETH @ 3000: basis 200 + 500 = 700, proceeds 900 => +200 capital gain
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_spend),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal('0.3'),
            location_label=TEST_ADDR1,
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=Timestamp(SHAPPELA_TIMESTAMP),
        end_ts=Timestamp(SHAPPELA_TIMESTAMP + 1000),
        eth_staking_taxable_after_withdrawal_enabled=taxable_after_withdrawal,
    )
    expected = FVal(900) if taxable_after_withdrawal else FVal(400)
    assert old_totals == (expected, ZERO)
    _assert_pnl_parity(old_totals, new_result)


def test_eth2_accumulating_validator_requested_partial_withdrawal_parity(
        database: DBHandler,
) -> None:
    """A 0x02 accumulating validator's requested partial withdrawal is principal, not income."""
    _add_rule(database, HistoryEventType.SPEND)
    with database.user_write() as write_cursor:
        database.add_blockchain_accounts(
            write_cursor=write_cursor,
            account_data=[BlockchainAccountData(
                chain=SupportedBlockchain.ETHEREUM,
                address=TEST_ADDR1,
            )],
        )
        DBEth2(database).add_or_update_validators(
            write_cursor=write_cursor,
            validators=[ValidatorDetails(
                validator_index=42,
                public_key=Eth2PubKey('0x' + 'bb' * 48),
                validator_type=ValidatorType.ACCUMULATING,
                ownership_proportion=FVal(1),
                withdrawal_address=TEST_ADDR1,
                activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
            )],
        )

    t_block = Timestamp(SHAPPELA_TIMESTAMP + 100)
    t_req = Timestamp(SHAPPELA_TIMESTAMP + 150)
    t_wd = Timestamp(SHAPPELA_TIMESTAMP + 200)
    t_spend = Timestamp(SHAPPELA_TIMESTAMP + 300)
    prices = {
        (A_ETH, t_block): Price(FVal(2000)),
        (A_ETH, t_wd): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    events: list[HistoryBaseEntry] = [
        # Tracked block reward: taxable (0.1 ETH @ 2000 = 200)
        EthBlockEvent(
            validator_index=42,
            timestamp=ts_sec_to_ms(t_block),
            amount=FVal('0.1'),
            fee_recipient=TEST_ADDR1,
            fee_recipient_tracked=True,
            block_number=17_000_001,
            is_mev_reward=False,
        ),
        # EIP-7002 partial withdrawal request for 5 ETH of principal
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_req),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            amount=FVal(5),
            location_label=TEST_ADDR1,
            counterparty=CPT_ETH2,
            extra_data={'validator_index': 42},
        ),
        # Matching 5 ETH partial withdrawal from 0x02 validator: principal, 0 income
        EthWithdrawalEvent(
            validator_index=42,
            timestamp=ts_sec_to_ms(t_wd),
            amount=FVal(5),
            withdrawal_address=TEST_ADDR1,
            is_exit=False,
        ),
        # Spend 0.1 ETH @ 3000 (consumes block reward lot: 300 - 200 = +100 capital gain)
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_spend),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal('0.1'),
            location_label=TEST_ADDR1,
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=Timestamp(SHAPPELA_TIMESTAMP),
        end_ts=Timestamp(SHAPPELA_TIMESTAMP + 1000),
        eth_staking_taxable_after_withdrawal_enabled=True,
    )
    assert old_totals == (FVal(300), ZERO)
    _assert_pnl_parity(old_totals, new_result)
    assert new_result['num_unpriced_events'] == 0


@pytest.mark.parametrize('taxable_after_withdrawal', [True, False])
def test_eth2_accumulating_validator_skimming_withdrawal_parity(
        database: DBHandler,
        taxable_after_withdrawal: bool,
) -> None:
    """A 0x02 skimming withdrawal with no EIP-7002 request is taxable income in both pipelines,
    while a matched requested partial withdrawal on the same validator stays principal."""
    with database.user_write() as write_cursor:
        database.add_blockchain_accounts(
            write_cursor=write_cursor,
            account_data=[BlockchainAccountData(
                chain=SupportedBlockchain.ETHEREUM,
                address=TEST_ADDR1,
            )],
        )
        DBEth2(database).add_or_update_validators(
            write_cursor=write_cursor,
            validators=[ValidatorDetails(
                validator_index=42,
                public_key=Eth2PubKey('0x' + 'cc' * 48),
                validator_type=ValidatorType.ACCUMULATING,
                ownership_proportion=FVal(1),
                withdrawal_address=TEST_ADDR1,
                activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
            )],
        )

    t_skim = Timestamp(SHAPPELA_TIMESTAMP + 100)
    t_req = Timestamp(SHAPPELA_TIMESTAMP + 150)
    t_partial = Timestamp(SHAPPELA_TIMESTAMP + 200)
    prices = {
        (A_ETH, t_skim): Price(FVal(2000)),
        (A_ETH, t_partial): Price(FVal(2500)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    events: list[HistoryBaseEntry] = [
        # Skimming withdrawal (0.05 ETH @ 2000 = 100 taxable when enabled) with no request
        EthWithdrawalEvent(
            validator_index=42,
            timestamp=ts_sec_to_ms(t_skim),
            amount=FVal('0.05'),
            withdrawal_address=TEST_ADDR1,
            is_exit=False,
        ),
        # EIP-7002 partial withdrawal request for 5 ETH of principal
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_req),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            amount=FVal(5),
            location_label=TEST_ADDR1,
            counterparty=CPT_ETH2,
            extra_data={'validator_index': 42},
        ),
        # Matched 5 ETH requested partial withdrawal: principal, 0 income
        EthWithdrawalEvent(
            validator_index=42,
            timestamp=ts_sec_to_ms(t_partial),
            amount=FVal(5),
            withdrawal_address=TEST_ADDR1,
            is_exit=False,
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=Timestamp(SHAPPELA_TIMESTAMP),
        end_ts=Timestamp(SHAPPELA_TIMESTAMP + 1000),
        eth_staking_taxable_after_withdrawal_enabled=taxable_after_withdrawal,
    )
    expected = FVal(100) if taxable_after_withdrawal else ZERO
    assert old_totals == (expected, ZERO)
    _assert_pnl_parity(old_totals, new_result)
    assert new_result['num_unpriced_events'] == 0


def test_eth2_bls_and_unknown_validator_withdrawal_parity(database: DBHandler) -> None:
    """A validator still stored as BLS (0x00) books partial withdrawals as income just like
    legacy, while a withdrawal for a validator missing from eth2_validators realizes nothing."""
    with database.user_write() as write_cursor:
        database.add_blockchain_accounts(
            write_cursor=write_cursor,
            account_data=[BlockchainAccountData(
                chain=SupportedBlockchain.ETHEREUM,
                address=TEST_ADDR1,
            )],
        )
        DBEth2(database).add_or_update_validators(
            write_cursor=write_cursor,
            validators=[ValidatorDetails(
                validator_index=42,
                public_key=Eth2PubKey('0x' + 'dd' * 48),
                validator_type=ValidatorType.BLS,
                ownership_proportion=FVal(1),
                withdrawal_address=TEST_ADDR1,
                activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
            )],
        )

    t_bls = Timestamp(SHAPPELA_TIMESTAMP + 100)
    t_unknown = Timestamp(SHAPPELA_TIMESTAMP + 200)
    prices = {
        (A_ETH, t_bls): Price(FVal(2000)),
        (A_ETH, t_unknown): Price(FVal(2500)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    events: list[HistoryBaseEntry] = [
        # Validator stored as BLS (0x00): 0.05 ETH @ 2000 = 100 taxable
        EthWithdrawalEvent(
            validator_index=42,
            timestamp=ts_sec_to_ms(t_bls),
            amount=FVal('0.05'),
            withdrawal_address=TEST_ADDR1,
            is_exit=False,
        ),
        # Validator not present in eth2_validators: 0 income in both pipelines
        EthWithdrawalEvent(
            validator_index=999,
            timestamp=ts_sec_to_ms(t_unknown),
            amount=FVal('0.1'),
            withdrawal_address=TEST_ADDR1,
            is_exit=False,
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=Timestamp(SHAPPELA_TIMESTAMP),
        end_ts=Timestamp(SHAPPELA_TIMESTAMP + 1000),
        eth_staking_taxable_after_withdrawal_enabled=True,
    )
    assert old_totals == (FVal(100), ZERO)
    _assert_pnl_parity(old_totals, new_result)
    assert new_result['num_unpriced_events'] == 0


def test_multi_bucket_intentional_divergence_vs_global_pot(database: DBHandler) -> None:
    """Deliberate difference (#2438): new cost basis tracks lots per bucket, not globally."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)

    prices = {
        (A_ETH, _ts(1)): Price(FVal(1000)),  # wallet 1 receives 1 ETH @ 1000
        (A_ETH, _ts(2)): Price(FVal(3000)),  # wallet 2 receives 1 ETH @ 3000
        (A_ETH, _ts(3)): Price(FVal(4000)),  # wallet 2 spends 1 ETH @ 4000
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    events: list[HistoryBaseEntry] = [
        _evm_event(
            at=1, amount='1', event_type=HistoryEventType.RECEIVE, location_label=TEST_ADDR1,
        ),
        _evm_event(
            at=2, amount='1', event_type=HistoryEventType.RECEIVE, location_label=TEST_ADDR2,
        ),
        _evm_event(at=3, amount='1', event_type=HistoryEventType.SPEND, location_label=TEST_ADDR2),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_ts(1),
        end_ts=_ts(10),
        method=CostBasisMethod.FIFO,
    )
    # Global FIFO consumes wallet 1's $1000 lot (+3000);
    # per-bucket FIFO consumes wallet 2's $3000 lot (+1000).
    assert old_totals == (FVal(3000), ZERO)
    assert FVal(new_result['total_realized_pnl']) == FVal(1000)
    assert FVal(new_result['total_taxfree_pnl']) == ZERO


def test_eth_account_tracking_flip_invalidates_cost_basis_and_updates_pnl(
        database: DBHandler,
) -> None:
    """Adding or removing an ETH account after a pass marks cost basis stale from its earliest
    EthBlockEvent/EthWithdrawalEvent and updates realized PnL to match legacy."""
    with database.user_write() as write_cursor:
        database.set_settings(
            write_cursor,
            ModifiableDBSettings(
                main_currency=A_USD.resolve_to_asset_with_oracles(),
                cost_basis_method=CostBasisMethod.FIFO,
                eth_staking_taxable_after_withdrawal_enabled=True,
            ),
        )
        DBEth2(database).add_or_update_validators(
            write_cursor=write_cursor,
            validators=[ValidatorDetails(
                validator_index=42,
                public_key=Eth2PubKey('0x' + 'ee' * 48),
                validator_type=ValidatorType.DISTRIBUTING,
                ownership_proportion=FVal(1),
                withdrawal_address=TEST_ADDR1,
                activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
            )],
        )

    t_block = Timestamp(SHAPPELA_TIMESTAMP + 100)
    t_wd = Timestamp(SHAPPELA_TIMESTAMP + 200)
    start_ts = Timestamp(SHAPPELA_TIMESTAMP)
    end_ts = Timestamp(SHAPPELA_TIMESTAMP + 1000)
    prices = {
        (A_ETH, t_block): Price(FVal(2000)),
        (A_ETH, t_wd): Price(FVal(2500)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    events: list[HistoryBaseEntry] = [
        # Block reward (0.1 ETH @ 2000 = 200) to cold address TEST_ADDR1 (untracked initially)
        EthBlockEvent(
            validator_index=42,
            timestamp=ts_sec_to_ms(t_block),
            amount=FVal('0.1'),
            fee_recipient=TEST_ADDR1,
            fee_recipient_tracked=False,
            block_number=17_000_001,
            is_mev_reward=False,
        ),
        # Partial withdrawal (0.05 ETH @ 2500 = 125) to cold address TEST_ADDR1 (no EVM txs)
        EthWithdrawalEvent(
            validator_index=42,
            timestamp=ts_sec_to_ms(t_wd),
            amount=FVal('0.05'),
            withdrawal_address=TEST_ADDR1,
            is_exit=False,
        ),
    ]
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(write_cursor=write_cursor, history=events)

    pnl_filter = HistoryEventFilterQuery.make(
        from_ts=start_ts,
        to_ts=end_ts,
        exclude_ignored_assets=True,
        exclude_ignored_actions=True,
        exclude_untracked_withdrawals=True,
    )

    def _run_pass_and_query() -> tuple[tuple[FVal, FVal], dict[str, Any]]:
        with (
            patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as new_historian,
            patch('rotkehlchen.accounting.pot.PriceHistorian') as old_historian,
        ):
            new_historian.return_value.query_historical_price = price_fn
            old_historian.return_value.query_historical_price = price_fn
            assert process_cost_basis(database, database.msg_aggregator) is True
            new_result = query_realized_pnl(
                database=database,
                filter_query=pnl_filter,
                group_by=RealizedPnlGroupBy.ASSET,
            )
            with database.conn.read_ctx() as cursor:
                db_events = DBHistoryEvents(database).get_history_events_internal(
                    cursor=cursor,
                    filter_query=HistoryEventFilterQuery.make(
                        from_ts=Timestamp(0),
                        to_ts=end_ts,
                        exclude_untracked_withdrawals=True,
                    ),
                    aggregate_by_group_ids=False,
                )
            db_events.sort(key=lambda x: (x.timestamp, x.group_identifier, x.sequence_index))
            premium = MagicMock()
            premium.is_active.return_value = True
            accountant = Accountant(
                db=database,
                msg_aggregator=database.msg_aggregator,
                chains_aggregator=_make_chains_aggregator_stub(),
                premium=premium,
            )
            accountant.process_history(start_ts=start_ts, end_ts=end_ts, events=db_events)
            old_pnls = accountant.pots[0].pnls
            return (old_pnls.taxable, old_pnls.free), new_result

    # Pass 1: TEST_ADDR1 untracked -> 0 income, not stale
    old_totals, new_result = _run_pass_and_query()
    assert old_totals == (ZERO, ZERO)
    _assert_pnl_parity(old_totals, new_result)
    assert new_result['stale'] is False

    # Add TEST_ADDR1 as tracked ETH account -> stale from earliest block/withdrawal event (t_block)
    with database.user_write() as write_cursor:
        database.add_blockchain_accounts(
            write_cursor=write_cursor,
            account_data=[BlockchainAccountData(
                chain=SupportedBlockchain.ETHEREUM,
                address=TEST_ADDR1,
            )],
        )
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor, DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        ) == str(ts_sec_to_ms(t_block))
    assert query_realized_pnl(
        database=database, filter_query=pnl_filter, group_by=RealizedPnlGroupBy.ASSET,
    )['stale'] is True

    # Pass 2: TEST_ADDR1 tracked -> 200 + 125 = 325 income, not stale
    old_totals, new_result = _run_pass_and_query()
    assert old_totals == (FVal(325), ZERO)
    _assert_pnl_parity(old_totals, new_result)
    assert new_result['stale'] is False

    # Remove TEST_ADDR1 -> stale from earliest block/withdrawal event (t_block)
    with database.user_write() as write_cursor:
        database.remove_single_blockchain_accounts(
            write_cursor=write_cursor,
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=[TEST_ADDR1],
        )
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor, DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        ) == str(ts_sec_to_ms(t_block))
    assert query_realized_pnl(
        database=database, filter_query=pnl_filter, group_by=RealizedPnlGroupBy.ASSET,
    )['stale'] is True

    # Pass 3: TEST_ADDR1 untracked again -> 0 income, not stale
    old_totals, new_result = _run_pass_and_query()
    assert old_totals == (ZERO, ZERO)
    _assert_pnl_parity(old_totals, new_result)
    assert new_result['stale'] is False


def test_eth2_validator_changes_invalidate_cost_basis_and_update_pnl(
        database: DBHandler,
) -> None:
    """Adding a validator, changing validator_type between 0x01 and 0x02, and deleting a validator
    after a pass each mark cost basis stale from its earliest withdrawal and update realized PnL."""  # noqa: E501
    pubkey = Eth2PubKey('0x' + 'ff' * 48)
    with database.user_write() as write_cursor:
        database.set_settings(
            write_cursor,
            ModifiableDBSettings(
                main_currency=A_USD.resolve_to_asset_with_oracles(),
                cost_basis_method=CostBasisMethod.FIFO,
                eth_staking_taxable_after_withdrawal_enabled=True,
            ),
        )
        database.add_blockchain_accounts(
            write_cursor=write_cursor,
            account_data=[BlockchainAccountData(
                chain=SupportedBlockchain.ETHEREUM,
                address=TEST_ADDR1,
            )],
        )

    t_req = Timestamp(SHAPPELA_TIMESTAMP + 150)
    t_wd = Timestamp(SHAPPELA_TIMESTAMP + 200)
    start_ts = Timestamp(SHAPPELA_TIMESTAMP)
    end_ts = Timestamp(SHAPPELA_TIMESTAMP + 1000)
    prices = {(A_ETH, t_wd): Price(FVal(2000))}

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    events: list[HistoryBaseEntry] = [
        # EIP-7002 partial withdrawal request for 5 ETH of principal
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_req),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            amount=FVal(5),
            location_label=TEST_ADDR1,
            counterparty=CPT_ETH2,
            extra_data={'validator_index': 42},
        ),
        # 5 ETH partial withdrawal (taxable as 0x01 distributing, principal as 0x02 accumulating)
        EthWithdrawalEvent(
            validator_index=42,
            timestamp=ts_sec_to_ms(t_wd),
            amount=FVal(5),
            withdrawal_address=TEST_ADDR1,
            is_exit=False,
        ),
    ]
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(write_cursor=write_cursor, history=events)

    pnl_filter = HistoryEventFilterQuery.make(
        from_ts=start_ts,
        to_ts=end_ts,
        exclude_ignored_assets=True,
        exclude_ignored_actions=True,
        exclude_untracked_withdrawals=True,
    )

    def _run_pass_and_query() -> dict[str, Any]:
        with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as new_historian:
            new_historian.return_value.query_historical_price = price_fn
            assert process_cost_basis(database, database.msg_aggregator) is True
        return query_realized_pnl(
            database=database,
            filter_query=pnl_filter,
            group_by=RealizedPnlGroupBy.ASSET,
        )

    # Pass 1: validator not in eth2_validators -> 0 income
    result = _run_pass_and_query()
    assert result['stale'] is False
    assert FVal(result['total_realized_pnl']) == ZERO

    # Add validator as 0x01 DISTRIBUTING -> stale from earliest withdrawal (t_wd)
    dbeth2 = DBEth2(database)
    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators(
            write_cursor=write_cursor,
            validators=[ValidatorDetails(
                validator_index=42,
                public_key=pubkey,
                validator_type=ValidatorType.DISTRIBUTING,
                ownership_proportion=FVal(1),
                withdrawal_address=TEST_ADDR1,
                activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
            )],
        )
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor, DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        ) == str(ts_sec_to_ms(t_wd))

    # Pass 2: 5 ETH @ 2000 = 10_000 distributing income
    result = _run_pass_and_query()
    assert result['stale'] is False
    assert FVal(result['total_realized_pnl']) == FVal(10_000)

    # Change validator_type 0x01 -> 0x02 ACCUMULATING -> stale from t_wd
    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators_except_ownership(
            write_cursor=write_cursor,
            validators=[ValidatorDetails(
                validator_index=42,
                public_key=pubkey,
                validator_type=ValidatorType.ACCUMULATING,
                ownership_proportion=FVal(1),
                withdrawal_address=TEST_ADDR1,
                activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
            )],
        )
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor, DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        ) == str(ts_sec_to_ms(t_wd))

    # Pass 3: matched EIP-7002 partial withdrawal reclassified as principal -> 0 income
    result = _run_pass_and_query()
    assert result['stale'] is False
    assert FVal(result['total_realized_pnl']) == ZERO

    # Change validator_type back 0x02 -> 0x01 -> 10_000 income again
    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators(
            write_cursor=write_cursor,
            validators=[ValidatorDetails(
                validator_index=42,
                public_key=pubkey,
                validator_type=ValidatorType.DISTRIBUTING,
                ownership_proportion=FVal(1),
                withdrawal_address=TEST_ADDR1,
                activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
            )],
        )
    result = _run_pass_and_query()
    assert result['stale'] is False
    assert FVal(result['total_realized_pnl']) == FVal(10_000)

    # Delete validator -> stale from t_wd and PnL drops back to 0
    dbeth2.delete_validators([42])
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor, DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        ) == str(ts_sec_to_ms(t_wd))
    result = _run_pass_and_query()
    assert result['stale'] is False
    assert FVal(result['total_realized_pnl']) == ZERO


def _setup_eth2_accounts_and_validators(
        database: DBHandler,
        accounts: list[ChecksumEvmAddress],
        validators: list[ValidatorDetails],
) -> None:
    with database.user_write() as write_cursor:
        database.add_blockchain_accounts(
            write_cursor=write_cursor,
            account_data=[
                BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=addr)
                for addr in accounts
            ],
        )
        DBEth2(database).add_or_update_validators(
            write_cursor=write_cursor,
            validators=validators,
        )


@pytest.mark.parametrize('validator_type', [ValidatorType.DISTRIBUTING, ValidatorType.BLS])
@pytest.mark.parametrize('taxable_after_withdrawal', [True, False])
def test_eth2_non_accumulating_exit_profit_parity(
        database: DBHandler,
        validator_type: ValidatorType,
        taxable_after_withdrawal: bool,
) -> None:
    """0x01 and 0x00 exits > 32 ETH book only the excess as income and preserve deposit basis."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)
    _setup_eth2_accounts_and_validators(
        database=database,
        accounts=[TEST_ADDR1],
        validators=[ValidatorDetails(
            validator_index=42,
            public_key=Eth2PubKey('0x' + '11' * 48),
            validator_type=validator_type,
            ownership_proportion=FVal(1),
            withdrawal_address=TEST_ADDR1,
            activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
        )],
    )

    t_buy = Timestamp(SHAPPELA_TIMESTAMP + 10)
    t_dep = Timestamp(SHAPPELA_TIMESTAMP + 20)
    t_exit = Timestamp(SHAPPELA_TIMESTAMP + 200)
    t_spend = Timestamp(SHAPPELA_TIMESTAMP + 300)
    prices = {
        (A_ETH, t_buy): Price(FVal(1000)),
        (A_ETH, t_dep): Price(FVal(1500)),
        (A_ETH, t_exit): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    exit_event = EthWithdrawalEvent(
        validator_index=42,
        timestamp=ts_sec_to_ms(t_exit),
        amount=FVal('32.5'),
        withdrawal_address=TEST_ADDR1,
        is_exit=True,
    )
    events: list[HistoryBaseEntry] = [
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_buy),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=MIN_EFFECTIVE_BALANCE,
            location_label=TEST_ADDR1,
        ),
        EthDepositEvent(
            tx_ref=make_evm_tx_hash(),
            validator_index=42,
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_dep),
            amount=MIN_EFFECTIVE_BALANCE,
            depositor=TEST_ADDR1,
        ),
        exit_event,
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_spend),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal('32.5'),
            location_label=TEST_ADDR1,
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=Timestamp(SHAPPELA_TIMESTAMP),
        end_ts=Timestamp(SHAPPELA_TIMESTAMP + 1000),
        eth_staking_taxable_after_withdrawal_enabled=taxable_after_withdrawal,
    )
    # 32 ETH capital gain: 32 * (3000 - 1000) = 64_000; 0.5 ETH capital gain: 250.
    # Exit income: 0.5 * 2500 = 1250 if taxable else 0.
    expected = FVal(65_500) if taxable_after_withdrawal else FVal(64_250)
    assert old_totals == (expected, ZERO)
    _assert_pnl_parity(old_totals, new_result)
    assert new_result['num_unpriced_events'] == 0

    with database.conn.read_ctx() as cursor:
        exit_id = cursor.execute(
            'SELECT identifier FROM history_events WHERE group_identifier = ?',
            (exit_event.group_identifier,),
        ).fetchone()[0]
    exit_cb = query_events_cost_basis(database, [exit_id])
    assert exit_cb['stale'] == []
    exit_entries = exit_cb['entries'][str(exit_id)]
    spend_entries = [entry for entry in exit_entries if entry['direction'] == 'spend']
    assert len(spend_entries) == 1
    assert spend_entries[0]['protocol'] == CPT_ETH2
    assert spend_entries[0]['basis_remaining'] == '0'


@pytest.mark.parametrize('validator_type', [ValidatorType.DISTRIBUTING, ValidatorType.BLS])
@pytest.mark.parametrize('taxable_after_withdrawal', [True, False])
def test_eth2_non_accumulating_exit_slashing_loss_parity(
        database: DBHandler,
        validator_type: ValidatorType,
        taxable_after_withdrawal: bool,
) -> None:
    """0x01 and 0x00 exits < 32 ETH realize slashing loss and keep surviving principal basis."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)
    _setup_eth2_accounts_and_validators(
        database=database,
        accounts=[TEST_ADDR1],
        validators=[ValidatorDetails(
            validator_index=42,
            public_key=Eth2PubKey('0x' + '22' * 48),
            validator_type=validator_type,
            ownership_proportion=FVal(1),
            withdrawal_address=TEST_ADDR1,
            activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
        )],
    )

    t_buy = Timestamp(SHAPPELA_TIMESTAMP + 10)
    t_dep = Timestamp(SHAPPELA_TIMESTAMP + 20)
    t_exit = Timestamp(SHAPPELA_TIMESTAMP + 200)
    t_spend = Timestamp(SHAPPELA_TIMESTAMP + 300)
    prices = {
        (A_ETH, t_buy): Price(FVal(1000)),
        (A_ETH, t_dep): Price(FVal(1500)),
        (A_ETH, t_exit): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    exit_event = EthWithdrawalEvent(
        validator_index=42,
        timestamp=ts_sec_to_ms(t_exit),
        amount=FVal(30),
        withdrawal_address=TEST_ADDR1,
        is_exit=True,
    )
    events: list[HistoryBaseEntry] = [
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_buy),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=MIN_EFFECTIVE_BALANCE,
            location_label=TEST_ADDR1,
        ),
        EthDepositEvent(
            tx_ref=make_evm_tx_hash(),
            validator_index=42,
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_dep),
            amount=MIN_EFFECTIVE_BALANCE,
            depositor=TEST_ADDR1,
        ),
        exit_event,
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_spend),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(30),
            location_label=TEST_ADDR1,
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=Timestamp(SHAPPELA_TIMESTAMP),
        end_ts=Timestamp(SHAPPELA_TIMESTAMP + 1000),
        eth_staking_taxable_after_withdrawal_enabled=taxable_after_withdrawal,
    )
    # 2 ETH slashing loss @ 2500 with 2000 basis: -5000 + 3000 = -2000 if taxable else 0.
    # 30 ETH capital gain @ 3000 with 30_000 basis: +60_000.
    expected = FVal(58_000) if taxable_after_withdrawal else FVal(60_000)
    assert old_totals == (expected, ZERO)
    _assert_pnl_parity(old_totals, new_result)
    assert new_result['num_unpriced_events'] == 0

    with database.conn.read_ctx() as cursor:
        row = cursor.execute(
            'SELECT cb.post_spend_basis_remaining FROM event_cost_basis cb '
            'JOIN history_events he ON he.identifier = cb.event_identifier '
            'WHERE he.group_identifier = ? AND cb.direction = ?',
            (exit_event.group_identifier, 'spend'),
        ).fetchone()
    assert row == ('0',)


def test_eth2_distributing_exit_preserves_taxfree_holding_period_parity(
        database: DBHandler,
) -> None:
    """Returned principal on exit keeps its original acquisition timestamp for taxfree_after_period."""  # noqa: E501
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)
    _setup_eth2_accounts_and_validators(
        database=database,
        accounts=[TEST_ADDR1],
        validators=[ValidatorDetails(
            validator_index=42,
            public_key=Eth2PubKey('0x' + '33' * 48),
            validator_type=ValidatorType.DISTRIBUTING,
            ownership_proportion=FVal(1),
            withdrawal_address=TEST_ADDR1,
            activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
        )],
    )

    t_buy = Timestamp(SHAPPELA_TIMESTAMP + 10)
    t_dep = Timestamp(SHAPPELA_TIMESTAMP + 20)
    t_exit = Timestamp(SHAPPELA_TIMESTAMP + 1500)
    t_spend = Timestamp(SHAPPELA_TIMESTAMP + 1600)  # >1000s after buy, <1000s after exit
    prices = {
        (A_ETH, t_buy): Price(FVal(1000)),
        (A_ETH, t_dep): Price(FVal(1500)),
        (A_ETH, t_exit): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    events: list[HistoryBaseEntry] = [
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_buy),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=MIN_EFFECTIVE_BALANCE,
            location_label=TEST_ADDR1,
        ),
        EthDepositEvent(
            tx_ref=make_evm_tx_hash(),
            validator_index=42,
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_dep),
            amount=MIN_EFFECTIVE_BALANCE,
            depositor=TEST_ADDR1,
        ),
        EthWithdrawalEvent(
            validator_index=42,
            timestamp=ts_sec_to_ms(t_exit),
            amount=FVal('32.5'),
            withdrawal_address=TEST_ADDR1,
            is_exit=True,
        ),
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_spend),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal('32.5'),
            location_label=TEST_ADDR1,
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=Timestamp(SHAPPELA_TIMESTAMP),
        end_ts=Timestamp(SHAPPELA_TIMESTAMP + 2000),
        taxfree_after_period=1000,
        eth_staking_taxable_after_withdrawal_enabled=True,
    )
    # 0.5 ETH exit reward (1250) + 0.5 ETH short-term gain (250) = 1500 taxable;
    # 32 ETH principal gain (32 * (3000 - 1000)) = 64_000 tax-free.
    assert old_totals == (FVal(1500), FVal(64_000))
    _assert_pnl_parity(old_totals, new_result)


@pytest.mark.parametrize('taxable_after_withdrawal', [True, False])
def test_eth2_distributing_slashing_loss_unpriced_parity(
        database: DBHandler,
        taxable_after_withdrawal: bool,
) -> None:
    """An unpriced taxable slashing exit marks the event unpriced; non-taxable does not."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _setup_eth2_accounts_and_validators(
        database=database,
        accounts=[TEST_ADDR1],
        validators=[ValidatorDetails(
            validator_index=42,
            public_key=Eth2PubKey('0x' + '44' * 48),
            validator_type=ValidatorType.DISTRIBUTING,
            ownership_proportion=FVal(1),
            withdrawal_address=TEST_ADDR1,
            activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
        )],
    )

    t_buy = Timestamp(SHAPPELA_TIMESTAMP + 10)
    t_dep = Timestamp(SHAPPELA_TIMESTAMP + 20)
    t_exit = Timestamp(SHAPPELA_TIMESTAMP + 200)

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        if timestamp in (t_buy, t_dep):
            return Price(FVal(1000))
        raise NoPriceForGivenTimestamp(from_asset=from_asset, to_asset=to_asset, time=timestamp)

    events: list[HistoryBaseEntry] = [
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_buy),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=MIN_EFFECTIVE_BALANCE,
            location_label=TEST_ADDR1,
        ),
        EthDepositEvent(
            tx_ref=make_evm_tx_hash(),
            validator_index=42,
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_dep),
            amount=MIN_EFFECTIVE_BALANCE,
            depositor=TEST_ADDR1,
        ),
        EthWithdrawalEvent(
            validator_index=42,
            timestamp=ts_sec_to_ms(t_exit),
            amount=FVal(30),
            withdrawal_address=TEST_ADDR1,
            is_exit=True,
        ),
    ]

    with database.user_write() as write_cursor:
        database.set_settings(
            write_cursor,
            ModifiableDBSettings(
                main_currency=A_USD.resolve_to_asset_with_oracles(),
                cost_basis_method=CostBasisMethod.FIFO,
                eth_staking_taxable_after_withdrawal_enabled=taxable_after_withdrawal,
            ),
        )
        DBHistoryEvents(database).add_history_events(write_cursor=write_cursor, history=events)

    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as new_historian:
        new_historian.return_value.query_historical_price = price_fn
        assert process_cost_basis(database, database.msg_aggregator) is True

    new_result = query_realized_pnl(
        database=database,
        filter_query=HistoryEventFilterQuery.make(
            from_ts=Timestamp(SHAPPELA_TIMESTAMP),
            to_ts=Timestamp(SHAPPELA_TIMESTAMP + 1000),
            exclude_ignored_assets=True,
            exclude_ignored_actions=True,
            exclude_untracked_withdrawals=True,
        ),
        group_by=RealizedPnlGroupBy.ASSET,
    )
    assert FVal(new_result['total_realized_pnl']) == ZERO
    assert new_result['num_unpriced_events'] == (1 if taxable_after_withdrawal else 0)


def test_eth2_distributing_large_partial_withdrawal_parity(database: DBHandler) -> None:
    """A distributing partial withdrawal >= 32 ETH books only amount - 32 ETH as income."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)
    _setup_eth2_accounts_and_validators(
        database=database,
        accounts=[TEST_ADDR1],
        validators=[ValidatorDetails(
            validator_index=42,
            public_key=Eth2PubKey('0x' + '55' * 48),
            validator_type=ValidatorType.DISTRIBUTING,
            ownership_proportion=FVal(1),
            withdrawal_address=TEST_ADDR1,
            activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
        )],
    )

    t_buy = Timestamp(SHAPPELA_TIMESTAMP + 10)
    t_dep = Timestamp(SHAPPELA_TIMESTAMP + 20)
    t_wd = Timestamp(SHAPPELA_TIMESTAMP + 200)
    t_spend = Timestamp(SHAPPELA_TIMESTAMP + 300)
    prices = {
        (A_ETH, t_buy): Price(FVal(1000)),
        (A_ETH, t_dep): Price(FVal(1500)),
        (A_ETH, t_wd): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    events: list[HistoryBaseEntry] = [
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_buy),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=MIN_EFFECTIVE_BALANCE,
            location_label=TEST_ADDR1,
        ),
        EthDepositEvent(
            tx_ref=make_evm_tx_hash(),
            validator_index=42,
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_dep),
            amount=MIN_EFFECTIVE_BALANCE,
            depositor=TEST_ADDR1,
        ),
        EthWithdrawalEvent(
            validator_index=42,
            timestamp=ts_sec_to_ms(t_wd),
            amount=FVal('32.5'),
            withdrawal_address=TEST_ADDR1,
            is_exit=False,
        ),
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_spend),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal('32.5'),
            location_label=TEST_ADDR1,
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=Timestamp(SHAPPELA_TIMESTAMP),
        end_ts=Timestamp(SHAPPELA_TIMESTAMP + 1000),
        eth_staking_taxable_after_withdrawal_enabled=True,
    )
    assert old_totals == (FVal(65_500), ZERO)
    _assert_pnl_parity(old_totals, new_result)


def test_eth2_accumulating_requested_partial_withdrawal_preserves_basis_parity(
        database: DBHandler,
) -> None:
    """A 0x02 requested partial withdrawal carries the original deposit basis to the wallet."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)
    _setup_eth2_accounts_and_validators(
        database=database,
        accounts=[TEST_ADDR1],
        validators=[ValidatorDetails(
            validator_index=42,
            public_key=Eth2PubKey('0x' + '66' * 48),
            validator_type=ValidatorType.ACCUMULATING,
            ownership_proportion=FVal(1),
            withdrawal_address=TEST_ADDR1,
            activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
        )],
    )

    t_buy = Timestamp(SHAPPELA_TIMESTAMP + 10)
    t_dep = Timestamp(SHAPPELA_TIMESTAMP + 20)
    t_req = Timestamp(SHAPPELA_TIMESTAMP + 150)
    t_wd = Timestamp(SHAPPELA_TIMESTAMP + 200)
    t_spend = Timestamp(SHAPPELA_TIMESTAMP + 300)
    prices = {
        (A_ETH, t_buy): Price(FVal(1000)),
        (A_ETH, t_dep): Price(FVal(1500)),
        (A_ETH, t_wd): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    events: list[HistoryBaseEntry] = [
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_buy),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(40),
            location_label=TEST_ADDR1,
        ),
        EthDepositEvent(
            tx_ref=make_evm_tx_hash(),
            validator_index=42,
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_dep),
            amount=FVal(40),
            depositor=TEST_ADDR1,
        ),
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_req),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            amount=FVal(10),
            location_label=TEST_ADDR1,
            counterparty=CPT_ETH2,
            extra_data={'validator_index': 42},
        ),
        EthWithdrawalEvent(
            validator_index=42,
            timestamp=ts_sec_to_ms(t_wd),
            amount=FVal(10),
            withdrawal_address=TEST_ADDR1,
            is_exit=False,
        ),
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_spend),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(10),
            location_label=TEST_ADDR1,
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=Timestamp(SHAPPELA_TIMESTAMP),
        end_ts=Timestamp(SHAPPELA_TIMESTAMP + 1000),
        eth_staking_taxable_after_withdrawal_enabled=True,
    )
    # 0 income on withdrawal; spending 10 ETH @ 3000 uses $1000 deposit basis -> +20_000 gain.
    assert old_totals == (FVal(20_000), ZERO)
    _assert_pnl_parity(old_totals, new_result)


def test_eth2_accumulating_exit_with_skimming_and_consensus_rewards(
        database: DBHandler,
) -> None:
    """A 0x02 exit books only rewards not already taxed via skimming, matching DBEth2 PnL.

    Intentional divergence from legacy `EthWithdrawalEvent.process()`: legacy checks
    `max(ZERO, amount - MAX_EFFECTIVE_BALANCE)` (2048 ETH) so it misses consensus profit on
    exits below 2048 ETH, whereas `DBEth2.process_accumulating_validators_balances_and_pnl()`
    and the materialized cost-basis pass both compute `amount - principal - skimmed`.
    """
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)
    _setup_eth2_accounts_and_validators(
        database=database,
        accounts=[TEST_ADDR1],
        validators=[ValidatorDetails(
            validator_index=42,
            public_key=Eth2PubKey('0x' + '77' * 48),
            validator_type=ValidatorType.ACCUMULATING,
            ownership_proportion=FVal(1),
            withdrawal_address=TEST_ADDR1,
            activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
        )],
    )

    t_buy = Timestamp(SHAPPELA_TIMESTAMP + 10)
    t_dep = Timestamp(SHAPPELA_TIMESTAMP + 20)
    t_skim1 = Timestamp(SHAPPELA_TIMESTAMP + 100)
    t_skim2 = Timestamp(SHAPPELA_TIMESTAMP + 150)
    t_exit = Timestamp(SHAPPELA_TIMESTAMP + 200)
    t_spend = Timestamp(SHAPPELA_TIMESTAMP + 300)
    prices = {
        (A_ETH, t_buy): Price(FVal(1000)),
        (A_ETH, t_dep): Price(FVal(1500)),
        (A_ETH, t_skim1): Price(FVal(2000)),
        (A_ETH, t_skim2): Price(FVal(2000)),
        (A_ETH, t_exit): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    events: list[HistoryBaseEntry] = [
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_buy),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(64),
            location_label=TEST_ADDR1,
        ),
        EthDepositEvent(
            tx_ref=make_evm_tx_hash(),
            validator_index=42,
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_dep),
            amount=FVal(64),
            depositor=TEST_ADDR1,
        ),
        EthWithdrawalEvent(
            validator_index=42,
            timestamp=ts_sec_to_ms(t_skim1),
            amount=FVal(1),
            withdrawal_address=TEST_ADDR1,
            is_exit=False,
            group_identifier='eth2_skim_1',
        ),
        EthWithdrawalEvent(
            validator_index=42,
            timestamp=ts_sec_to_ms(t_skim2),
            amount=FVal(1),
            withdrawal_address=TEST_ADDR1,
            is_exit=False,
            group_identifier='eth2_skim_2',
        ),
        EthWithdrawalEvent(
            validator_index=42,
            timestamp=ts_sec_to_ms(t_exit),
            amount=FVal('67.5'),
            withdrawal_address=TEST_ADDR1,
            is_exit=True,
            group_identifier='eth2_exit_42',
        ),
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_spend),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal('69.5'),
            location_label=TEST_ADDR1,
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=Timestamp(SHAPPELA_TIMESTAMP),
        end_ts=Timestamp(SHAPPELA_TIMESTAMP + 1000),
        eth_staking_taxable_after_withdrawal_enabled=True,
    )
    # Skimming: 2 ETH @ 2000 = 4000.
    # Exit: excess = 67.5 - 64 = 3.5 ETH, minus 2 ETH skimmed = 1.5 ETH taxable @ 2500 = 3750.
    # Spend 69.5 ETH @ 3000: 64 @ 1000 (+128k) + 2 @ 2000 (+2k) + 3.5 @ 2500 (+1.75k) = +131_750.
    assert FVal(new_result['total_realized_pnl']) == FVal(139_500)
    assert new_result['stale'] is False
    # Verify DBEth2 agrees on exits_pnl == 1.5 ETH (whereas legacy Accountant missed it).
    _, withdrawals_pnl, exits_pnl = DBEth2(database).process_validators_balances_and_pnl(
        from_ts=Timestamp(SHAPPELA_TIMESTAMP),
        to_ts=Timestamp(SHAPPELA_TIMESTAMP + 1000),
        validator_indices={42},
    )
    assert withdrawals_pnl[42] == FVal(2)
    assert exits_pnl[42] == FVal('1.5')
    assert old_totals[0] != FVal(new_result['total_realized_pnl'])


@pytest.mark.parametrize('taxable_after_withdrawal', [True, False])
def test_eth2_accumulating_exit_slashing_consolidate_and_different_depositor_parity(
        database: DBHandler,
        taxable_after_withdrawal: bool,
) -> None:
    """0x02 slashing exit after CONSOLIDATE preserves basis across different depositor/withdrawal addresses."""  # noqa: E501
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)
    _setup_eth2_accounts_and_validators(
        database=database,
        accounts=[TEST_ADDR1, TEST_ADDR2],
        validators=[
            ValidatorDetails(
                validator_index=10,
                public_key=Eth2PubKey('0x' + '88' * 48),
                validator_type=ValidatorType.DISTRIBUTING,
                ownership_proportion=FVal(1),
                withdrawal_address=TEST_ADDR1,
                activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
            ),
            ValidatorDetails(
                validator_index=20,
                public_key=Eth2PubKey('0x' + '99' * 48),
                validator_type=ValidatorType.ACCUMULATING,
                ownership_proportion=FVal(1),
                withdrawal_address=TEST_ADDR2,
                activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
            ),
        ],
    )

    t_buy1 = Timestamp(SHAPPELA_TIMESTAMP + 10)
    t_buy2 = Timestamp(SHAPPELA_TIMESTAMP + 20)
    t_dep1 = Timestamp(SHAPPELA_TIMESTAMP + 30)
    t_dep2 = Timestamp(SHAPPELA_TIMESTAMP + 40)
    t_cons = Timestamp(SHAPPELA_TIMESTAMP + 100)
    t_exit = Timestamp(SHAPPELA_TIMESTAMP + 200)
    t_spend = Timestamp(SHAPPELA_TIMESTAMP + 300)
    prices = {
        (A_ETH, t_buy1): Price(FVal(1000)),
        (A_ETH, t_buy2): Price(FVal(2000)),
        (A_ETH, t_dep1): Price(FVal(1500)),
        (A_ETH, t_dep2): Price(FVal(2200)),
        (A_ETH, t_cons): Price(FVal(2300)),
        (A_ETH, t_exit): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    exit_event = EthWithdrawalEvent(
        validator_index=20,
        timestamp=ts_sec_to_ms(t_exit),
        amount=FVal(60),
        withdrawal_address=TEST_ADDR2,
        is_exit=True,
    )
    events: list[HistoryBaseEntry] = [
        # TEST_ADDR1 buys 32 ETH @ 1000 and deposits into 0x01 validator 10
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_buy1),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=MIN_EFFECTIVE_BALANCE,
            location_label=TEST_ADDR1,
        ),
        # TEST_ADDR2 buys 32 ETH @ 2000 and deposits into 0x02 validator 20
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_buy2),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=MIN_EFFECTIVE_BALANCE,
            location_label=TEST_ADDR2,
        ),
        EthDepositEvent(
            tx_ref=make_evm_tx_hash(),
            validator_index=10,
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_dep1),
            amount=MIN_EFFECTIVE_BALANCE,
            depositor=TEST_ADDR1,
        ),
        EthDepositEvent(
            tx_ref=make_evm_tx_hash(),
            validator_index=20,
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_dep2),
            amount=MIN_EFFECTIVE_BALANCE,
            depositor=TEST_ADDR2,
        ),
        # Consolidate 10 -> 20 (amount=0 informational event)
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_cons),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.CONSOLIDATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=TEST_ADDR1,
            counterparty=CPT_ETH2,
            extra_data={'source_validator_index': 10, 'target_validator_index': 20},
        ),
        # Exit 60 ETH (4 ETH slashing loss) to TEST_ADDR2
        exit_event,
        # Spend 60 ETH from TEST_ADDR2 @ 3000
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_spend),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(60),
            location_label=TEST_ADDR2,
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=Timestamp(SHAPPELA_TIMESTAMP),
        end_ts=Timestamp(SHAPPELA_TIMESTAMP + 1000),
        eth_staking_taxable_after_withdrawal_enabled=taxable_after_withdrawal,
    )
    # 4 ETH slashing loss consumes 4 ETH @ 1000 -> -4000 when taxable else 0.
    # Remaining 28 @ 1000 + 32 @ 2000 = 92_000 basis; proceeds 180_000 -> +88_000 capital gain.
    expected = FVal(84_000) if taxable_after_withdrawal else FVal(88_000)
    assert old_totals == (expected, ZERO)
    _assert_pnl_parity(old_totals, new_result)

    with database.conn.read_ctx() as cursor:
        row = cursor.execute(
            'SELECT cb.post_spend_basis_remaining FROM event_cost_basis cb '
            'JOIN history_events he ON he.identifier = cb.event_identifier '
            'WHERE he.group_identifier = ? AND cb.direction = ?',
            (exit_event.group_identifier, 'spend'),
        ).fetchone()
    assert row == ('0',)


def test_eth2_consolidated_source_exit_sweep_and_checkpoint_resume(database: DBHandler) -> None:
    """Consolidated 0x01 source exit sweep is treated as reward income (not slashing), and
    resuming from a cost-basis checkpoint preserves validator principal, skimmed, and consolidated state."""  # noqa: E501
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)
    _setup_eth2_accounts_and_validators(
        database=database,
        accounts=[TEST_ADDR1],
        validators=[
            ValidatorDetails(
                validator_index=10,
                public_key=Eth2PubKey('0x' + 'aa' * 48),
                validator_type=ValidatorType.DISTRIBUTING,
                ownership_proportion=FVal(1),
                withdrawal_address=TEST_ADDR1,
                activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
            ),
            ValidatorDetails(
                validator_index=20,
                public_key=Eth2PubKey('0x' + 'bb' * 48),
                validator_type=ValidatorType.ACCUMULATING,
                ownership_proportion=FVal(1),
                withdrawal_address=TEST_ADDR1,
                activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
            ),
        ],
    )

    t_buy = Timestamp(SHAPPELA_TIMESTAMP + 10)
    t_dep = Timestamp(SHAPPELA_TIMESTAMP + 20)
    t_cons = Timestamp(SHAPPELA_TIMESTAMP + 100)
    t_skim = Timestamp(SHAPPELA_TIMESTAMP + 150)
    t_src_exit = Timestamp(SHAPPELA_TIMESTAMP + 200)
    t_tgt_exit = Timestamp(SHAPPELA_TIMESTAMP + 300)
    t_spend = Timestamp(SHAPPELA_TIMESTAMP + 400)
    prices = {
        (A_ETH, t_buy): Price(FVal(1000)),
        (A_ETH, t_dep): Price(FVal(1500)),
        (A_ETH, t_skim): Price(FVal(2000)),
        (A_ETH, t_src_exit): Price(FVal(2200)),
        (A_ETH, t_tgt_exit): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    }

    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return prices[from_asset, timestamp]

    target_exit = EthWithdrawalEvent(
        validator_index=20,
        timestamp=ts_sec_to_ms(t_tgt_exit),
        amount=FVal('34.5'),
        withdrawal_address=TEST_ADDR1,
        is_exit=True,
        group_identifier='eth2_exit_20',
    )
    initial_events: list[HistoryBaseEntry] = [
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_buy),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=MIN_EFFECTIVE_BALANCE,
            location_label=TEST_ADDR1,
        ),
        EthDepositEvent(
            tx_ref=make_evm_tx_hash(),
            validator_index=10,
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_dep),
            amount=MIN_EFFECTIVE_BALANCE,
            depositor=TEST_ADDR1,
        ),
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_cons),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.CONSOLIDATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=TEST_ADDR1,
            counterparty=CPT_ETH2,
            extra_data={'source_validator_index': 10, 'target_validator_index': 20},
        ),
        EthWithdrawalEvent(
            validator_index=20,
            timestamp=ts_sec_to_ms(t_skim),
            amount=FVal(1),
            withdrawal_address=TEST_ADDR1,
            is_exit=False,
            group_identifier='eth2_skim_20',
        ),
    ]
    later_events: list[HistoryBaseEntry] = [
        # Consolidated 0x01 source exit sweep of 0.1 ETH -> reward income (220), not slashing loss
        EthWithdrawalEvent(
            validator_index=10,
            timestamp=ts_sec_to_ms(t_src_exit),
            amount=FVal('0.1'),
            withdrawal_address=TEST_ADDR1,
            is_exit=True,
        ),
        # Target 0x02 exit of 34.5 ETH: 32 principal + 1 already skimmed + 1.5 new reward (3750)
        target_exit,
        # Spend all 35.6 ETH @ 3000
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(t_spend),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal('35.6'),
            location_label=TEST_ADDR1,
        ),
    ]

    with database.user_write() as write_cursor:
        database.set_settings(
            write_cursor,
            ModifiableDBSettings(
                main_currency=A_USD.resolve_to_asset_with_oracles(),
                cost_basis_method=CostBasisMethod.FIFO,
                eth_staking_taxable_after_withdrawal_enabled=True,
            ),
        )
        DBHistoryEvents(database).add_history_events(write_cursor=write_cursor, history=initial_events)  # noqa: E501

    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as new_historian:
        new_historian.return_value.query_historical_price = price_fn
        assert process_cost_basis(database, database.msg_aggregator) is True

    # Append later events and resume incrementally from the terminal checkpoint.
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=later_events,
        )

    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as new_historian:
        new_historian.return_value.query_historical_price = price_fn
        assert process_cost_basis(database, database.msg_aggregator) is True

    pnl_filter = HistoryEventFilterQuery.make(
        from_ts=Timestamp(SHAPPELA_TIMESTAMP),
        to_ts=Timestamp(SHAPPELA_TIMESTAMP + 1000),
        exclude_ignored_assets=True,
        exclude_ignored_actions=True,
        exclude_untracked_withdrawals=True,
    )
    resumed_result = query_realized_pnl(
        database=database, filter_query=pnl_filter, group_by=RealizedPnlGroupBy.ASSET,
    )
    # Skim (1 * 2000 = 2000) + src_exit (0.1 * 2200 = 220) + tgt_exit (1.5 * 2500 = 3750)
    # + spend 35.6 @ 3000 (106_800) minus basis (32*1000 + 1*2000 + 0.1*2200 + 2.5*2500 = 40_470)
    # = 5970 + 66_330 = 72_300.
    assert FVal(resumed_result['total_realized_pnl']) == FVal(72_300)
    assert resumed_result['stale'] is False

    # Verify a fresh full pass (without checkpoints) yields the exact same result.
    with database.user_write() as write_cursor:
        write_cursor.execute('DELETE FROM event_cost_basis')
        write_cursor.execute('DELETE FROM cost_basis_checkpoints')
        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name IN (?, ?)',
            (
                DBCacheStatic.LAST_COST_BASIS_PROCESSING_TS.value,
                DBCacheStatic.STALE_COST_BASIS_FROM_TS.value,
            ),
        )
    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as new_historian:
        new_historian.return_value.query_historical_price = price_fn
        assert process_cost_basis(database, database.msg_aggregator) is True
    full_result = query_realized_pnl(
        database=database, filter_query=pnl_filter, group_by=RealizedPnlGroupBy.ASSET,
    )
    assert full_result == resumed_result
