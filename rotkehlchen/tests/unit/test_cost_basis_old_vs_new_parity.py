"""Side-by-side parity tests comparing the legacy Accountant PnL report against
materialized `event_cost_basis` + `query_realized_pnl()`.
"""
from typing import TYPE_CHECKING, Any, Final
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.accounting.cost_basis.pnl import RealizedPnlGroupBy, query_realized_pnl
from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.ethereum.constants import SHAPPELA_TIMESTAMP
from rotkehlchen.chain.ethereum.modules.eth2.constants import CPT_ETH2
from rotkehlchen.chain.ethereum.modules.eth2.structures import ValidatorDetails, ValidatorType
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_ETH2, A_EUR, A_KFEE, A_USD, A_WETH
from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.history.events.structures.eth2 import EthBlockEvent, EthWithdrawalEvent
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
