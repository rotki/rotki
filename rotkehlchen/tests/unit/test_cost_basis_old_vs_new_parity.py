"""Side-by-side parity tests comparing the legacy Accountant PnL report against
materialized `event_cost_basis` + `query_realized_pnl()`.
"""
import json
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
UNIX_TS_THRESHOLD: Final = 1_000_000_000


def _ts(offset: int) -> Timestamp:
    return Timestamp(BASE_TS + offset)


def _ts_ms(offset: int) -> TimestampMS:
    return TimestampMS((BASE_TS + offset) * 1000)


def _shappela(offset: int) -> Timestamp:
    return Timestamp(SHAPPELA_TIMESTAMP + offset)


def _to_ts_ms(at: int | Timestamp) -> TimestampMS:
    return ts_sec_to_ms(Timestamp(at)) if at >= UNIX_TS_THRESHOLD else _ts_ms(at)


def _price_lookup(
        prices: dict[tuple[Asset, Timestamp], Price],
) -> Callable[[Asset, Asset, Timestamp], Price]:
    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        if (from_asset, timestamp) in prices:
            return prices[from_asset, timestamp]
        raise NoPriceForGivenTimestamp(from_asset=from_asset, to_asset=to_asset, time=timestamp)

    return price_fn


def _evm_event(
        at: int | Timestamp,
        amount: str | FVal,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType = HistoryEventSubType.NONE,
        asset: Asset = A_ETH,
        location_label: ChecksumEvmAddress = TEST_ADDR1,
        tx_ref: EVMTxHash | None = None,
        sequence_index: int = 0,
        counterparty: str | None = None,
        extra_data: dict[str, Any] | None = None,
) -> EvmEvent:
    return EvmEvent(
        tx_ref=make_evm_tx_hash() if tx_ref is None else tx_ref,
        sequence_index=sequence_index,
        timestamp=_to_ts_ms(at),
        location=LOCATION_ETHEREUM,
        event_type=event_type,
        event_subtype=event_subtype,
        asset=asset,
        amount=FVal(amount),
        location_label=location_label,
        counterparty=counterparty,
        extra_data=extra_data,
    )


def _kraken_swap(
        at: int,
        group_identifier: str,
        spend: tuple[Asset, str | int],
        receive: tuple[Asset, str | int],
        fee: tuple[Asset, str | int] | None = None,
) -> list[SwapEvent]:
    ts = _ts_ms(at)
    entries = [
        SwapEvent(
            timestamp=ts, location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.SPEND, asset=spend[0], amount=FVal(spend[1]),
            group_identifier=group_identifier, sequence_index=0,
        ),
        SwapEvent(
            timestamp=ts, location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.RECEIVE, asset=receive[0], amount=FVal(receive[1]),
            group_identifier=group_identifier, sequence_index=1,
        ),
    ]
    if fee is not None:
        entries.append(SwapEvent(
            timestamp=ts, location=LOCATION_KRAKEN, location_label='kraken',
            event_subtype=HistoryEventSubType.FEE, asset=fee[0], amount=FVal(fee[1]),
            group_identifier=group_identifier, sequence_index=2,
        ))
    return entries


def _validator(
        index: int = 42,
        validator_type: ValidatorType = ValidatorType.DISTRIBUTING,
        withdrawal_address: ChecksumEvmAddress = TEST_ADDR1,
        pubkey: Eth2PubKey | None = None,
) -> ValidatorDetails:
    return ValidatorDetails(
        validator_index=index,
        public_key=Eth2PubKey(f'0x{index:096x}') if pubkey is None else pubkey,
        validator_type=validator_type,
        ownership_proportion=FVal(1),
        withdrawal_address=withdrawal_address,
        activation_timestamp=Timestamp(SHAPPELA_TIMESTAMP - 10_000),
    )


def _eth_block(
        at: Timestamp,
        amount: str | FVal,
        validator_index: int = 42,
        fee_recipient: ChecksumEvmAddress = TEST_ADDR1,
        fee_recipient_tracked: bool = True,
        block_number: int = 17_000_001,
) -> EthBlockEvent:
    return EthBlockEvent(
        validator_index=validator_index,
        timestamp=ts_sec_to_ms(at),
        amount=FVal(amount),
        fee_recipient=fee_recipient,
        fee_recipient_tracked=fee_recipient_tracked,
        block_number=block_number,
        is_mev_reward=False,
    )


def _eth_deposit(
        at: Timestamp,
        amount: str | FVal = MIN_EFFECTIVE_BALANCE,
        validator_index: int = 42,
        depositor: ChecksumEvmAddress = TEST_ADDR1,
) -> EthDepositEvent:
    return EthDepositEvent(
        tx_ref=make_evm_tx_hash(),
        validator_index=validator_index,
        sequence_index=0,
        timestamp=ts_sec_to_ms(at),
        amount=FVal(amount),
        depositor=depositor,
    )


def _eth_withdrawal(
        at: Timestamp,
        amount: str | FVal,
        validator_index: int = 42,
        withdrawal_address: ChecksumEvmAddress = TEST_ADDR1,
        is_exit: bool = False,
        group_identifier: str | None = None,
) -> EthWithdrawalEvent:
    return EthWithdrawalEvent(
        validator_index=validator_index,
        timestamp=ts_sec_to_ms(at),
        amount=FVal(amount),
        withdrawal_address=withdrawal_address,
        is_exit=is_exit,
        group_identifier=group_identifier,
    )


def _eth2_request(
        at: Timestamp,
        amount: str | FVal,
        validator_index: int = 42,
        location_label: ChecksumEvmAddress = TEST_ADDR1,
) -> EvmEvent:
    return _evm_event(
        at=at,
        amount=amount,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        location_label=location_label,
        counterparty=CPT_ETH2,
        extra_data={'validator_index': validator_index},
    )


def _eth2_consolidate(
        at: Timestamp,
        source_index: int,
        target_index: int,
        location_label: ChecksumEvmAddress = TEST_ADDR1,
) -> EvmEvent:
    return _evm_event(
        at=at,
        amount=ZERO,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.CONSOLIDATE,
        location_label=location_label,
        counterparty=CPT_ETH2,
        extra_data={
            'source_validator_index': source_index,
            'target_validator_index': target_index,
        },
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


def _setup_eth2_accounts_and_validators(
        database: DBHandler,
        accounts: list[ChecksumEvmAddress],
        validators: list[ValidatorDetails],
) -> None:
    with database.user_write() as write_cursor:
        if accounts:
            database.add_blockchain_accounts(
                write_cursor=write_cursor,
                account_data=[
                    BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=addr)
                    for addr in accounts
                ],
            )
        if validators:
            DBEth2(database).add_or_update_validators(
                write_cursor=write_cursor,
                validators=validators,
            )


def _write_settings_and_events(
        database: DBHandler,
        events: list[HistoryBaseEntry],
        method: CostBasisMethod = CostBasisMethod.FIFO,
        **settings: Any,
) -> None:
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
        if events:
            DBHistoryEvents(database).add_history_events(
                write_cursor=write_cursor,
                history=events,
            )


def _pnl_filter(start_ts: Timestamp, end_ts: Timestamp) -> HistoryEventFilterQuery:
    return HistoryEventFilterQuery.make(
        from_ts=start_ts,
        to_ts=end_ts,
        exclude_ignored_assets=True,
        exclude_ignored_actions=True,
        exclude_untracked_withdrawals=True,
    )


def _make_chains_aggregator_stub() -> MagicMock:
    evm_manager = MagicMock()
    evm_manager.accounting_aggregator.get_accounting_callbacks.return_value = {}
    chains_aggregator = MagicMock()
    chains_aggregator.get_evm_manager.return_value = evm_manager
    return chains_aggregator


def _run_new_pipeline(
        database: DBHandler,
        price_fn: Callable[[Asset, Asset, Timestamp], Price],
        start_ts: Timestamp,
        end_ts: Timestamp,
) -> dict[str, Any]:
    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as new_historian:
        new_historian.return_value.query_historical_price = price_fn
        assert process_cost_basis(database, database.msg_aggregator) is True
    return query_realized_pnl(
        database=database,
        filter_query=_pnl_filter(start_ts, end_ts),
        group_by=RealizedPnlGroupBy.ASSET,
    )


def _execute_both_pipelines(
        database: DBHandler,
        price_fn: Callable[[Asset, Asset, Timestamp], Price],
        start_ts: Timestamp,
        end_ts: Timestamp,
) -> tuple[tuple[FVal, FVal], dict[str, Any]]:
    """Run both cost-basis and legacy Accountant passes against events already persisted in `database`."""  # noqa: E501
    with (
        patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as new_historian,
        patch('rotkehlchen.accounting.pot.PriceHistorian') as old_historian,
    ):
        new_historian.return_value.query_historical_price = price_fn
        old_historian.return_value.query_historical_price = price_fn

        assert process_cost_basis(database, database.msg_aggregator) is True
        new_result = query_realized_pnl(
            database=database,
            filter_query=_pnl_filter(start_ts, end_ts),
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
    _write_settings_and_events(database=database, events=events, method=method, **settings)
    return _execute_both_pipelines(
        database=database,
        price_fn=price_fn,
        start_ts=start_ts,
        end_ts=end_ts,
    )


def _assert_pnl_parity(
        old_totals: tuple[FVal, FVal],
        new_result: dict[str, Any],
) -> None:
    old_taxable, old_free = old_totals
    assert FVal(new_result['total_realized_pnl']) == old_taxable
    assert FVal(new_result['total_taxfree_pnl']) == old_free
    assert new_result['stale'] is False


def _get_stale_from_ts(database: DBHandler) -> str | None:
    with database.conn.read_ctx() as cursor:
        return database.get_static_cache(cursor, DBCacheStatic.STALE_COST_BASIS_FROM_TS)


def _get_latest_checkpoint_state(database: DBHandler) -> dict[str, Any]:
    with database.conn.read_ctx() as cursor:
        row = cursor.execute(
            'SELECT state FROM cost_basis_checkpoints ORDER BY timestamp DESC LIMIT 1',
        ).fetchone()
    assert row is not None
    return json.loads(row[0])


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

    price_fn = _price_lookup({
        (A_ETH, _ts(1)): Price(FVal(1000)),
        (A_ETH, _ts(2)): Price(FVal(3000)),
        (A_ETH, _ts(3)): Price(FVal(2000)),
        (A_ETH, _ts(4)): Price(FVal(4000)),
        (A_ETH, _ts(5)): Price(FVal(5000)),
        (A_WETH, _ts(5)): Price(FVal(5000)),
        (A_WETH, _ts(6)): Price(FVal(6000)),
        (A_DAI, _ts(4)): Price(FVal(1)),
        (A_USD, _ts(6)): Price(FVal(1)),
    })

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
            at=5, amount='1', event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            tx_ref=wrap_tx, sequence_index=0,
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

    price_fn = _price_lookup({
        (A_ETH, _ts(0)): Price(FVal(1000)),     # held 2000s (> 1000s => tax-free)
        (A_ETH, _ts(1500)): Price(FVal(2500)),  # held 500s (< 1000s => taxable)
        (A_ETH, _ts(2000)): Price(FVal(4000)),
    })

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
    _add_rule(database, HistoryEventType.RECEIVE, HistoryEventSubType.AIRDROP, taxable=True)
    _add_rule(database, HistoryEventType.STAKING, HistoryEventSubType.REWARD, taxable=True)

    price_fn = _price_lookup({
        (A_ETH, _ts(1)): Price(FVal(1000)),  # non-taxable plain receive
        (A_ETH, _ts(2)): Price(FVal(2000)),  # taxable airdrop (0.5 ETH = 1000 income)
        (A_ETH, _ts(3)): Price(FVal(2500)),  # taxable staking reward (0.4 ETH = 1000 income)
        (A_ETH, _ts(4)): Price(FVal(3000)),  # spend 1.5 ETH => +2500 gain
        (A_ETH2, _ts(5)): Price(FVal(3200)),  # Kraken staking reward (0.25 ETH2 = 800 income)
    })

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

    price_fn = _price_lookup({
        (A_USD, _ts(1)): Price(FVal(1)),
        (A_ETH, _ts(1)): Price(FVal(2000)),
        (A_USD, _ts(2)): Price(FVal(1)),
        (A_ETH, _ts(2)): Price(FVal(3000)),
    })

    events: list[HistoryBaseEntry] = [
        *_kraken_swap(at=1, group_identifier='buy_eth', spend=(A_USD, 2000), receive=(A_ETH, 1), fee=(A_USD, 10)),  # noqa: E501
        *_kraken_swap(at=2, group_identifier='sell_eth', spend=(A_ETH, 1), receive=(A_USD, 3000), fee=(A_USD, 15)),  # noqa: E501
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
    _add_rule(database, HistoryEventType.RECEIVE, HistoryEventSubType.INTEREST, taxable=True)

    price_fn = _price_lookup({
        (A_USD, _ts(1)): Price(FVal(1)),
        (A_USD, _ts(2)): Price(FVal(1)),
    })

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

    price_fn = _price_lookup({
        (A_ETH, _ts(1)): Price(FVal(2000)),
        (A_ETH, _ts(2)): Price(FVal(3000)),
        (A_USD, _ts(2)): Price(FVal(1)),
        (A_KFEE, _ts(2)): Price(FVal('0.01')),  # matches PriceHistorian's fixed $0.01 KFEE rate
        (A_KFEE, _ts(3)): Price(FVal('0.01')),
    })

    events: list[HistoryBaseEntry] = [
        HistoryEvent(
            timestamp=_ts_ms(1), location=LOCATION_KRAKEN, location_label='kraken',
            event_type=HistoryEventType.RECEIVE, event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH, amount=FVal(1), group_identifier='eth_in', sequence_index=0,
        ),
        *_kraken_swap(at=2, group_identifier='sell_kfee', spend=(A_ETH, 1), receive=(A_USD, 3000), fee=(A_KFEE, 500)),  # noqa: E501
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
    price_fn = _price_lookup({
        (A_USD, _ts(1)): Price(FVal('0.9')),
        (A_ETH, _ts(1)): Price(FVal(1800)),
        (A_USD, _ts(2)): Price(FVal('0.9')),
        (A_ETH, _ts(2)): Price(FVal(2700)),
    })

    events: list[HistoryBaseEntry] = [
        *_kraken_swap(at=1, group_identifier='buy_eth_eur', spend=(A_USD, 2000), receive=(A_ETH, 1), fee=(A_USD, 10)),  # noqa: E501
        *_kraken_swap(at=2, group_identifier='sell_eth_eur', spend=(A_ETH, 1), receive=(A_USD, 3000), fee=(A_USD, 20)),  # noqa: E501
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
    _add_rule(database, HistoryEventType.EXCHANGE_TRANSFER, HistoryEventSubType.RECEIVE, taxable=True)  # noqa: E501
    _add_rule(database, HistoryEventType.EXCHANGE_TRANSFER, HistoryEventSubType.FEE, taxable=False)

    price_fn = _price_lookup({
        (A_ETH, _ts(1)): Price(FVal(1000)),
        (A_ETH, _ts(2)): Price(FVal(2000)),
    })

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
    _add_rule(database, HistoryEventType.RECEIVE, HistoryEventSubType.AIRDROP, taxable=True)

    price_fn = _price_lookup({
        (A_ETH, _ts(0)): Price(FVal(1000)),     # airdrop before query window (t=0)
        (A_ETH, _ts(2000)): Price(FVal(3000)),  # fee inside query window, held 2000s (> 1000s)
    })

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
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    price_fn = _price_lookup({
        (A_ETH, _ts(1)): Price(FVal(1000)),
        (A_ETH, _ts(2)): Price(FVal(3000)),
    })

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
    _setup_eth2_accounts_and_validators(database, [TEST_ADDR1], [_validator()])

    t_block, t_wd, t_spend = _shappela(100), _shappela(200), _shappela(300)
    price_fn = _price_lookup({
        (A_ETH, t_block): Price(FVal(2000)),
        (A_ETH, t_wd): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    })

    events: list[HistoryBaseEntry] = [
        # Tracked block reward: always taxable (0.1 ETH @ 2000 = 200)
        _eth_block(at=t_block, amount='0.1', block_number=17_000_001),
        # Untracked block reward: ignored in both pipelines
        _eth_block(
            at=t_block, amount='0.5', fee_recipient=TEST_ADDR2,
            fee_recipient_tracked=False, block_number=17_000_002,
        ),
        # Distributing partial withdrawal (0.2 ETH @ 2500 = 500 if taxable_after_withdrawal else 0)
        _eth_withdrawal(at=t_wd, amount='0.2'),
        # Spend all 0.3 ETH @ 3000: basis 200 + 500 = 700, proceeds 900 => +200 capital gain
        _evm_event(at=t_spend, amount='0.3', event_type=HistoryEventType.SPEND),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_shappela(0),
        end_ts=_shappela(1000),
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
    _setup_eth2_accounts_and_validators(
        database, [TEST_ADDR1], [_validator(validator_type=ValidatorType.ACCUMULATING)],
    )

    t_block, t_req, t_wd, t_spend = _shappela(100), _shappela(150), _shappela(200), _shappela(300)
    price_fn = _price_lookup({
        (A_ETH, t_block): Price(FVal(2000)),
        (A_ETH, t_wd): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    })

    events: list[HistoryBaseEntry] = [
        _eth_block(at=t_block, amount='0.1'),
        _eth2_request(at=t_req, amount='5'),
        _eth_withdrawal(at=t_wd, amount='5'),
        _evm_event(at=t_spend, amount='0.1', event_type=HistoryEventType.SPEND),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_shappela(0),
        end_ts=_shappela(1000),
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
    _setup_eth2_accounts_and_validators(
        database, [TEST_ADDR1], [_validator(validator_type=ValidatorType.ACCUMULATING)],
    )

    t_skim, t_req, t_partial = _shappela(100), _shappela(150), _shappela(200)
    price_fn = _price_lookup({
        (A_ETH, t_skim): Price(FVal(2000)),
        (A_ETH, t_partial): Price(FVal(2500)),
    })

    events: list[HistoryBaseEntry] = [
        _eth_withdrawal(at=t_skim, amount='0.05', group_identifier='eth2_skim'),
        _eth2_request(at=t_req, amount='5'),
        _eth_withdrawal(at=t_partial, amount='5', group_identifier='eth2_partial'),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_shappela(0),
        end_ts=_shappela(1000),
        eth_staking_taxable_after_withdrawal_enabled=taxable_after_withdrawal,
    )
    expected = FVal(100) if taxable_after_withdrawal else ZERO
    assert old_totals == (expected, ZERO)
    _assert_pnl_parity(old_totals, new_result)
    assert new_result['num_unpriced_events'] == 0


def test_eth2_bls_and_unknown_validator_withdrawal_parity(database: DBHandler) -> None:
    """A validator still stored as BLS (0x00) books partial withdrawals as income just like
    legacy, while a withdrawal for a validator missing from eth2_validators realizes nothing."""
    _setup_eth2_accounts_and_validators(
        database, [TEST_ADDR1], [_validator(validator_type=ValidatorType.BLS)],
    )

    t_bls, t_unknown = _shappela(100), _shappela(200)
    price_fn = _price_lookup({
        (A_ETH, t_bls): Price(FVal(2000)),
        (A_ETH, t_unknown): Price(FVal(2500)),
    })

    events: list[HistoryBaseEntry] = [
        _eth_withdrawal(at=t_bls, amount='0.05', validator_index=42),
        _eth_withdrawal(at=t_unknown, amount='0.1', validator_index=999),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_shappela(0),
        end_ts=_shappela(1000),
        eth_staking_taxable_after_withdrawal_enabled=True,
    )
    assert old_totals == (FVal(100), ZERO)
    _assert_pnl_parity(old_totals, new_result)
    assert new_result['num_unpriced_events'] == 0


def test_multi_bucket_intentional_divergence_vs_global_pot(database: DBHandler) -> None:
    """Deliberate difference (#2438): new cost basis tracks lots per bucket, not globally."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)

    price_fn = _price_lookup({
        (A_ETH, _ts(1)): Price(FVal(1000)),  # wallet 1 receives 1 ETH @ 1000
        (A_ETH, _ts(2)): Price(FVal(3000)),  # wallet 2 receives 1 ETH @ 3000
        (A_ETH, _ts(3)): Price(FVal(4000)),  # wallet 2 spends 1 ETH @ 4000
    })

    events: list[HistoryBaseEntry] = [
        _evm_event(at=1, amount='1', event_type=HistoryEventType.RECEIVE, location_label=TEST_ADDR1),  # noqa: E501
        _evm_event(at=2, amount='1', event_type=HistoryEventType.RECEIVE, location_label=TEST_ADDR2),  # noqa: E501
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
    _setup_eth2_accounts_and_validators(database, [], [_validator()])

    t_block, t_wd = _shappela(100), _shappela(200)
    start_ts, end_ts = _shappela(0), _shappela(1000)
    price_fn = _price_lookup({
        (A_ETH, t_block): Price(FVal(2000)),
        (A_ETH, t_wd): Price(FVal(2500)),
    })

    _write_settings_and_events(
        database=database,
        events=[
            _eth_block(at=t_block, amount='0.1', fee_recipient_tracked=False),
            _eth_withdrawal(at=t_wd, amount='0.05'),
        ],
        eth_staking_taxable_after_withdrawal_enabled=True,
    )

    # Pass 1: TEST_ADDR1 untracked -> 0 income, not stale
    old_totals, new_result = _execute_both_pipelines(database, price_fn, start_ts, end_ts)
    assert old_totals == (ZERO, ZERO)
    _assert_pnl_parity(old_totals, new_result)

    # Add TEST_ADDR1 as tracked ETH account -> stale from earliest block/withdrawal event (t_block)
    _setup_eth2_accounts_and_validators(database, [TEST_ADDR1], [])
    assert _get_stale_from_ts(database) == str(ts_sec_to_ms(t_block))
    assert query_realized_pnl(
        database=database, filter_query=_pnl_filter(start_ts, end_ts),
        group_by=RealizedPnlGroupBy.ASSET,
    )['stale'] is True

    # Pass 2: TEST_ADDR1 tracked -> 200 + 125 = 325 income, not stale
    old_totals, new_result = _execute_both_pipelines(database, price_fn, start_ts, end_ts)
    assert old_totals == (FVal(325), ZERO)
    _assert_pnl_parity(old_totals, new_result)

    # Remove TEST_ADDR1 -> stale from earliest block/withdrawal event (t_block)
    with database.user_write() as write_cursor:
        database.remove_single_blockchain_accounts(
            write_cursor=write_cursor,
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=[TEST_ADDR1],
        )
    assert _get_stale_from_ts(database) == str(ts_sec_to_ms(t_block))
    assert query_realized_pnl(
        database=database, filter_query=_pnl_filter(start_ts, end_ts),
        group_by=RealizedPnlGroupBy.ASSET,
    )['stale'] is True

    # Pass 3: TEST_ADDR1 untracked again -> 0 income, not stale
    old_totals, new_result = _execute_both_pipelines(database, price_fn, start_ts, end_ts)
    assert old_totals == (ZERO, ZERO)
    _assert_pnl_parity(old_totals, new_result)


def test_eth2_validator_changes_invalidate_cost_basis_and_update_pnl(
        database: DBHandler,
) -> None:
    """Adding a validator, changing validator_type between 0x01 and 0x02, and deleting a validator
    after a pass each mark cost basis stale from its earliest withdrawal and update realized PnL."""  # noqa: E501
    pubkey = Eth2PubKey('0x' + 'ff' * 48)
    _setup_eth2_accounts_and_validators(database, [TEST_ADDR1], [])

    t_req, t_wd = _shappela(150), _shappela(200)
    start_ts, end_ts = _shappela(0), _shappela(1000)
    price_fn = _price_lookup({(A_ETH, t_wd): Price(FVal(2000))})

    _write_settings_and_events(
        database=database,
        events=[
            _eth2_request(at=t_req, amount='5'),
            _eth_withdrawal(at=t_wd, amount='5'),
        ],
        eth_staking_taxable_after_withdrawal_enabled=True,
    )

    # Pass 1: validator not in eth2_validators -> 0 income
    old_totals, new_result = _execute_both_pipelines(database, price_fn, start_ts, end_ts)
    assert old_totals == (ZERO, ZERO)
    _assert_pnl_parity(old_totals, new_result)

    # Add validator as 0x01 DISTRIBUTING -> stale from earliest withdrawal (t_wd)
    dbeth2 = DBEth2(database)
    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators(
            write_cursor=write_cursor,
            validators=[_validator(validator_type=ValidatorType.DISTRIBUTING, pubkey=pubkey)],
        )
    assert _get_stale_from_ts(database) == str(ts_sec_to_ms(t_wd))

    # Pass 2: 5 ETH @ 2000 = 10_000 distributing income
    old_totals, new_result = _execute_both_pipelines(database, price_fn, start_ts, end_ts)
    assert old_totals == (FVal(10_000), ZERO)
    _assert_pnl_parity(old_totals, new_result)

    # Change validator_type 0x01 -> 0x02 ACCUMULATING -> stale from t_wd
    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators_except_ownership(
            write_cursor=write_cursor,
            validators=[_validator(validator_type=ValidatorType.ACCUMULATING, pubkey=pubkey)],
        )
    assert _get_stale_from_ts(database) == str(ts_sec_to_ms(t_wd))

    # Pass 3: matched EIP-7002 partial withdrawal reclassified as principal -> 0 income
    old_totals, new_result = _execute_both_pipelines(database, price_fn, start_ts, end_ts)
    assert old_totals == (ZERO, ZERO)
    _assert_pnl_parity(old_totals, new_result)

    # Change validator_type back 0x02 -> 0x01 -> 10_000 income again
    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators(
            write_cursor=write_cursor,
            validators=[_validator(validator_type=ValidatorType.DISTRIBUTING, pubkey=pubkey)],
        )
    old_totals, new_result = _execute_both_pipelines(database, price_fn, start_ts, end_ts)
    assert old_totals == (FVal(10_000), ZERO)
    _assert_pnl_parity(old_totals, new_result)

    # Delete validator -> stale from t_wd and PnL drops back to 0
    dbeth2.delete_validators([42])
    assert _get_stale_from_ts(database) == str(ts_sec_to_ms(t_wd))
    old_totals, new_result = _execute_both_pipelines(database, price_fn, start_ts, end_ts)
    assert old_totals == (ZERO, ZERO)
    _assert_pnl_parity(old_totals, new_result)


@pytest.mark.parametrize(
    ('validator_type', 'withdrawal_amount', 'is_exit', 'expected_taxable', 'expected_nontaxable'),
    [
        pytest.param(
            ValidatorType.DISTRIBUTING, '32.5', True, FVal(65_500), FVal(64_250),
            id='0x01_exit_profit',
        ),
        pytest.param(
            ValidatorType.BLS, '32.5', True, FVal(65_500), FVal(64_250),
            id='0x00_exit_profit',
        ),
        pytest.param(
            ValidatorType.DISTRIBUTING, '30', True, FVal(58_000), FVal(60_000),
            id='0x01_exit_slashing',
        ),
        pytest.param(
            ValidatorType.BLS, '30', True, FVal(58_000), FVal(60_000),
            id='0x00_exit_slashing',
        ),
        pytest.param(
            ValidatorType.DISTRIBUTING, '32.5', False, FVal(65_500), FVal(64_250),
            id='0x01_large_partial',
        ),
    ],
)
@pytest.mark.parametrize('taxable_after_withdrawal', [True, False])
def test_eth2_non_accumulating_exit_and_large_withdrawal_parity(
        database: DBHandler,
        validator_type: ValidatorType,
        withdrawal_amount: str,
        is_exit: bool,
        expected_taxable: FVal,
        expected_nontaxable: FVal,
        taxable_after_withdrawal: bool,
) -> None:
    """0x01/0x00 profit exits (>32 ETH), slashing exits (<32 ETH), and large partial withdrawals
    (>=32 ETH) preserve deposit basis and match legacy PnL."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)
    _setup_eth2_accounts_and_validators(
        database, [TEST_ADDR1], [_validator(validator_type=validator_type)],
    )

    t_buy, t_dep, t_wd, t_spend = _shappela(10), _shappela(20), _shappela(200), _shappela(300)
    price_fn = _price_lookup({
        (A_ETH, t_buy): Price(FVal(1000)),
        (A_ETH, t_dep): Price(FVal(1500)),
        (A_ETH, t_wd): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    })

    withdrawal = _eth_withdrawal(at=t_wd, amount=withdrawal_amount, is_exit=is_exit)
    events: list[HistoryBaseEntry] = [
        _evm_event(at=t_buy, amount=MIN_EFFECTIVE_BALANCE, event_type=HistoryEventType.RECEIVE),
        _eth_deposit(at=t_dep),
        withdrawal,
        _evm_event(at=t_spend, amount=withdrawal_amount, event_type=HistoryEventType.SPEND),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_shappela(0),
        end_ts=_shappela(1000),
        eth_staking_taxable_after_withdrawal_enabled=taxable_after_withdrawal,
    )
    expected = expected_taxable if taxable_after_withdrawal else expected_nontaxable
    assert old_totals == (expected, ZERO)
    _assert_pnl_parity(old_totals, new_result)
    assert new_result['num_unpriced_events'] == 0

    if is_exit:
        with database.conn.read_ctx() as cursor:
            exit_id = cursor.execute(
                'SELECT identifier FROM history_events WHERE group_identifier = ?',
                (withdrawal.group_identifier,),
            ).fetchone()[0]
        exit_cb = query_events_cost_basis(database, [exit_id])
        assert exit_cb['stale'] == []
        spend_entries = [
            entry for entry in exit_cb['entries'][str(exit_id)]
            if entry['direction'] == 'spend'
        ]
        assert len(spend_entries) == 1
        assert spend_entries[0]['protocol'] == CPT_ETH2
        assert spend_entries[0]['basis_remaining'] == '0'


def test_eth2_distributing_exit_preserves_taxfree_holding_period_parity(
        database: DBHandler,
) -> None:
    """Returned principal on exit keeps its original acquisition timestamp for taxfree_after_period."""  # noqa: E501
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)
    _setup_eth2_accounts_and_validators(database, [TEST_ADDR1], [_validator()])

    # Spend is >1000s after buy, <1000s after exit
    t_buy, t_dep, t_exit, t_spend = _shappela(10), _shappela(20), _shappela(1500), _shappela(1600)
    price_fn = _price_lookup({
        (A_ETH, t_buy): Price(FVal(1000)),
        (A_ETH, t_dep): Price(FVal(1500)),
        (A_ETH, t_exit): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    })

    events: list[HistoryBaseEntry] = [
        _evm_event(at=t_buy, amount=MIN_EFFECTIVE_BALANCE, event_type=HistoryEventType.RECEIVE),
        _eth_deposit(at=t_dep),
        _eth_withdrawal(at=t_exit, amount='32.5', is_exit=True),
        _evm_event(at=t_spend, amount='32.5', event_type=HistoryEventType.SPEND),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_shappela(0),
        end_ts=_shappela(2000),
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
    _setup_eth2_accounts_and_validators(database, [TEST_ADDR1], [_validator()])

    t_buy, t_dep, t_exit = _shappela(10), _shappela(20), _shappela(200)
    price_fn = _price_lookup({
        (A_ETH, t_buy): Price(FVal(1000)),
        (A_ETH, t_dep): Price(FVal(1000)),
    })

    _write_settings_and_events(
        database=database,
        events=[
            _evm_event(at=t_buy, amount=MIN_EFFECTIVE_BALANCE, event_type=HistoryEventType.RECEIVE),  # noqa: E501
            _eth_deposit(at=t_dep),
            _eth_withdrawal(at=t_exit, amount='30', is_exit=True),
        ],
        eth_staking_taxable_after_withdrawal_enabled=taxable_after_withdrawal,
    )

    new_result = _run_new_pipeline(database, price_fn, _shappela(0), _shappela(1000))
    assert FVal(new_result['total_realized_pnl']) == ZERO
    assert new_result['num_unpriced_events'] == (1 if taxable_after_withdrawal else 0)


def test_eth2_accumulating_requested_partial_withdrawal_preserves_basis_parity(
        database: DBHandler,
) -> None:
    """A 0x02 requested partial withdrawal carries the original deposit basis to the wallet."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)
    _setup_eth2_accounts_and_validators(
        database, [TEST_ADDR1], [_validator(validator_type=ValidatorType.ACCUMULATING)],
    )

    t_buy, t_dep, t_req = _shappela(10), _shappela(20), _shappela(150)
    t_wd, t_spend = _shappela(200), _shappela(300)
    price_fn = _price_lookup({
        (A_ETH, t_buy): Price(FVal(1000)),
        (A_ETH, t_dep): Price(FVal(1500)),
        (A_ETH, t_wd): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    })

    events: list[HistoryBaseEntry] = [
        _evm_event(at=t_buy, amount='40', event_type=HistoryEventType.RECEIVE),
        _eth_deposit(at=t_dep, amount='40'),
        _eth2_request(at=t_req, amount='10'),
        _eth_withdrawal(at=t_wd, amount='10'),
        _evm_event(at=t_spend, amount='10', event_type=HistoryEventType.SPEND),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_shappela(0),
        end_ts=_shappela(1000),
        eth_staking_taxable_after_withdrawal_enabled=True,
    )
    # 0 income on withdrawal; spending 10 ETH @ 3000 uses $1000 deposit basis -> +20_000 gain.
    assert old_totals == (FVal(20_000), ZERO)
    _assert_pnl_parity(old_totals, new_result)


def test_eth2_accumulating_exit_with_skimming_and_consensus_rewards(
        database: DBHandler,
) -> None:
    """A 0x02 exit taxes the full `amount - principal` excess remaining in the validator.

    Skimming withdrawals already left the validator when they were taxed, so `amount - principal`
    is strictly the remaining untaxed rewards still held in the validator at exit time.
    """
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)
    _setup_eth2_accounts_and_validators(
        database, [TEST_ADDR1], [_validator(validator_type=ValidatorType.ACCUMULATING)],
    )

    t_buy, t_dep = _shappela(10), _shappela(20)
    t_skim1, t_skim2 = _shappela(100), _shappela(150)
    t_exit, t_spend = _shappela(200), _shappela(300)
    price_fn = _price_lookup({
        (A_ETH, t_buy): Price(FVal(1000)),
        (A_ETH, t_dep): Price(FVal(1500)),
        (A_ETH, t_skim1): Price(FVal(2000)),
        (A_ETH, t_skim2): Price(FVal(2000)),
        (A_ETH, t_exit): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    })

    events: list[HistoryBaseEntry] = [
        _evm_event(at=t_buy, amount='64', event_type=HistoryEventType.RECEIVE),
        _eth_deposit(at=t_dep, amount='64'),
        _eth_withdrawal(at=t_skim1, amount='1', group_identifier='eth2_skim_1'),
        _eth_withdrawal(at=t_skim2, amount='1', group_identifier='eth2_skim_2'),
        _eth_withdrawal(at=t_exit, amount='67.5', is_exit=True, group_identifier='eth2_exit_42'),
        _evm_event(at=t_spend, amount='69.5', event_type=HistoryEventType.SPEND),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_shappela(0),
        end_ts=_shappela(1000),
        eth_staking_taxable_after_withdrawal_enabled=True,
    )
    # Skimming: 2 ETH @ 2000 = 4000.
    # Exit: excess = 67.5 - 64 = 3.5 ETH taxable @ 2500 = 8750 (skims already left the validator).
    # Spend 69.5 ETH @ 3000: 64 @ 1000 (+128k) + 2 @ 2000 (+2k) + 3.5 @ 2500 (+1.75k) = +131_750.
    # Total realized PnL = 4000 + 8750 + 131_750 = 144_500 == 69.5 * 3000 - 64 * 1000.
    assert old_totals == (FVal(144_500), ZERO)
    _assert_pnl_parity(old_totals, new_result)
    with database.conn.read_ctx() as cursor:
        exit_row = cursor.execute(
            'SELECT cb.realized_pnl FROM event_cost_basis cb '
            'JOIN history_events he ON he.identifier = cb.event_identifier '
            'WHERE he.group_identifier = ? AND cb.direction = ?',
            ('eth2_exit_42', 'receive'),
        ).fetchone()
    assert exit_row == ('8750',)


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
            _validator(10, ValidatorType.DISTRIBUTING, withdrawal_address=TEST_ADDR1),
            _validator(20, ValidatorType.ACCUMULATING, withdrawal_address=TEST_ADDR2),
        ],
    )

    t_buy1, t_buy2 = _shappela(10), _shappela(20)
    t_dep1, t_dep2 = _shappela(30), _shappela(40)
    t_cons, t_exit, t_spend = _shappela(100), _shappela(200), _shappela(300)
    price_fn = _price_lookup({
        (A_ETH, t_buy1): Price(FVal(1000)),
        (A_ETH, t_buy2): Price(FVal(2000)),
        (A_ETH, t_dep1): Price(FVal(1500)),
        (A_ETH, t_dep2): Price(FVal(2200)),
        (A_ETH, t_cons): Price(FVal(2300)),
        (A_ETH, t_exit): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    })

    exit_event = _eth_withdrawal(
        at=t_exit, amount='60', validator_index=20, withdrawal_address=TEST_ADDR2, is_exit=True,
    )
    events: list[HistoryBaseEntry] = [
        _evm_event(
            at=t_buy1, amount=MIN_EFFECTIVE_BALANCE, event_type=HistoryEventType.RECEIVE,
            location_label=TEST_ADDR1,
        ),
        _evm_event(
            at=t_buy2, amount=MIN_EFFECTIVE_BALANCE, event_type=HistoryEventType.RECEIVE,
            location_label=TEST_ADDR2,
        ),
        _eth_deposit(at=t_dep1, validator_index=10, depositor=TEST_ADDR1),
        _eth_deposit(at=t_dep2, validator_index=20, depositor=TEST_ADDR2),
        _eth2_consolidate(at=t_cons, source_index=10, target_index=20, location_label=TEST_ADDR1),
        exit_event,
        _evm_event(
            at=t_spend, amount='60', event_type=HistoryEventType.SPEND, location_label=TEST_ADDR2,
        ),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_shappela(0),
        end_ts=_shappela(1000),
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
    resuming from a cost-basis checkpoint preserves validator principal and consolidated state."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)
    _setup_eth2_accounts_and_validators(
        database=database,
        accounts=[TEST_ADDR1],
        validators=[
            _validator(10, ValidatorType.DISTRIBUTING),
            _validator(20, ValidatorType.ACCUMULATING),
        ],
    )

    t_buy, t_dep = _shappela(10), _shappela(20)
    t_cons, t_skim = _shappela(100), _shappela(150)
    t_src_exit, t_tgt_exit, t_spend = _shappela(200), _shappela(300), _shappela(400)
    price_fn = _price_lookup({
        (A_ETH, t_buy): Price(FVal(1000)),
        (A_ETH, t_dep): Price(FVal(1500)),
        (A_ETH, t_skim): Price(FVal(2000)),
        (A_ETH, t_src_exit): Price(FVal(2200)),
        (A_ETH, t_tgt_exit): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    })

    initial_events: list[HistoryBaseEntry] = [
        _evm_event(at=t_buy, amount=MIN_EFFECTIVE_BALANCE, event_type=HistoryEventType.RECEIVE),
        _eth_deposit(at=t_dep, validator_index=10),
        _eth2_consolidate(at=t_cons, source_index=10, target_index=20),
        _eth_withdrawal(
            at=t_skim, amount='1', validator_index=20, group_identifier='eth2_skim_20',
        ),
    ]
    later_events: list[HistoryBaseEntry] = [
        # Consolidated 0x01 source exit sweep of 0.1 ETH -> reward income (220), not slashing loss
        _eth_withdrawal(at=t_src_exit, amount='0.1', validator_index=10, is_exit=True),
        # Target 0x02 exit of 34.5 ETH: 32 principal + 2.5 remaining rewards (6250)
        _eth_withdrawal(
            at=t_tgt_exit, amount='34.5', validator_index=20,
            is_exit=True, group_identifier='eth2_exit_20',
        ),
        _evm_event(at=t_spend, amount='35.6', event_type=HistoryEventType.SPEND),
    ]

    _write_settings_and_events(
        database=database,
        events=initial_events,
        eth_staking_taxable_after_withdrawal_enabled=True,
    )
    _run_new_pipeline(database, price_fn, _shappela(0), _shappela(1000))

    # Append later events and resume incrementally from the terminal checkpoint.
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=later_events,
        )
    resumed_result = _run_new_pipeline(database, price_fn, _shappela(0), _shappela(1000))

    # Skim (1 * 2000 = 2000) + src_exit (0.1 * 2200 = 220) + tgt_exit (2.5 * 2500 = 6250)
    # + spend 35.6 @ 3000 (106_800) minus basis (32*1000 + 1*2000 + 0.1*2200 + 2.5*2500 = 40_470)
    # = 8470 + 66_330 = 74_800 == 35.6 * 3000 - 32 * 1000.
    assert FVal(resumed_result['total_realized_pnl']) == FVal(74_800)
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
    full_result = _run_new_pipeline(database, price_fn, _shappela(0), _shappela(1000))
    assert full_result == resumed_result


@pytest.mark.parametrize(
    ('validator_type', 'deposit_amount', 'exit_amount', 'expected_pnl'),
    [
        pytest.param(
            ValidatorType.DISTRIBUTING, '32', '32.5', FVal(65_500),
            id='0x01_distributing',
        ),
        pytest.param(
            ValidatorType.ACCUMULATING, '64', '65.5', FVal(132_500),
            id='0x02_accumulating',
        ),
    ],
)
def test_eth2_exit_with_rewards_single_receive_row_and_incremental_replay(
        database: DBHandler,
        validator_type: ValidatorType,
        deposit_amount: str,
        exit_amount: str,
        expected_pnl: FVal,
) -> None:
    """An ETH2 exit with both principal and excess reward emits exactly one RECEIVE row for
    the wallet bucket, returns one receive entry in `query_events_cost_basis`, and preserves
    identical subsequent spend PnL across incremental stale replay."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)
    _setup_eth2_accounts_and_validators(
        database, [TEST_ADDR1], [_validator(validator_type=validator_type)],
    )

    t_buy, t_dep, t_exit, t_spend = _shappela(10), _shappela(20), _shappela(200), _shappela(300)
    start_ts, end_ts = _shappela(0), _shappela(1000)
    price_fn = _price_lookup({
        (A_ETH, t_buy): Price(FVal(1000)),
        (A_ETH, t_dep): Price(FVal(1500)),
        (A_ETH, t_exit): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    })

    exit_event = _eth_withdrawal(at=t_exit, amount=exit_amount, is_exit=True)
    # Persist through the exit first so a checkpoint is saved right after the exit.
    _write_settings_and_events(
        database=database,
        events=[
            _evm_event(at=t_buy, amount=deposit_amount, event_type=HistoryEventType.RECEIVE),
            _eth_deposit(at=t_dep, amount=deposit_amount),
            exit_event,
        ],
        eth_staking_taxable_after_withdrawal_enabled=True,
    )
    _run_new_pipeline(database, price_fn, start_ts, end_ts)

    # Append the subsequent spend and execute both pipelines.
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[
                _evm_event(at=t_spend, amount=exit_amount, event_type=HistoryEventType.SPEND),
            ],
        )
    old_totals, new_result = _execute_both_pipelines(database, price_fn, start_ts, end_ts)
    assert FVal(new_result['total_realized_pnl']) == expected_pnl
    assert new_result['stale'] is False
    if validator_type == ValidatorType.DISTRIBUTING:
        _assert_pnl_parity(old_totals, new_result)

    with database.conn.read_ctx() as cursor:
        exit_id = cursor.execute(
            'SELECT identifier FROM history_events WHERE group_identifier = ?',
            (exit_event.group_identifier,),
        ).fetchone()[0]
        rows = cursor.execute(
            'SELECT event_identifier, location, location_label, protocol, asset, direction '
            'FROM event_cost_basis WHERE event_identifier = ?',
            (exit_id,),
        ).fetchall()

    receive_rows = [row for row in rows if row[5] == 'receive']
    assert len(receive_rows) == 1
    assert len(rows) == len(set(rows))

    exit_cb = query_events_cost_basis(database, [exit_id])
    receive_entries = [
        entry for entry in exit_cb['entries'][str(exit_id)]
        if entry['direction'] == 'receive'
    ]
    assert len(receive_entries) == 1

    # Mark stale right after the exit and replay incrementally; subsequent spend PnL must match.
    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor,
            DBCacheStatic.STALE_COST_BASIS_FROM_TS,
            str(ts_sec_to_ms(t_spend)),
        )
    replayed_result = _run_new_pipeline(database, price_fn, start_ts, end_ts)
    assert replayed_result == new_result


def test_eth2_distributing_exit_overdeposited_drains_validator_before_spend_row(
        database: DBHandler,
) -> None:
    """On a 0x01 exit with >32 ETH deposited and loss_eth == 0, leftover validator lots are
    drained before emitting the exit SPEND row so post_spend_basis_remaining is '0' and
    basis_removed accounts for all deposited lots."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _setup_eth2_accounts_and_validators(database, [TEST_ADDR1], [_validator()])

    t_buy, t_dep, t_exit = _shappela(10), _shappela(20), _shappela(200)
    price_fn = _price_lookup({
        (A_ETH, t_buy): Price(FVal(1000)),
        (A_ETH, t_dep): Price(FVal(1500)),
        (A_ETH, t_exit): Price(FVal(2500)),
    })

    exit_event = _eth_withdrawal(at=t_exit, amount='32.5', is_exit=True)
    _write_settings_and_events(
        database=database,
        events=[
            _evm_event(at=t_buy, amount='34', event_type=HistoryEventType.RECEIVE),
            _eth_deposit(at=t_dep, amount='34'),
            exit_event,
        ],
        eth_staking_taxable_after_withdrawal_enabled=True,
    )
    _run_new_pipeline(database, price_fn, _shappela(0), _shappela(1000))

    with database.conn.read_ctx() as cursor:
        row = cursor.execute(
            'SELECT cb.post_spend_basis_remaining, cb.basis_removed '
            'FROM event_cost_basis cb '
            'JOIN history_events he ON he.identifier = cb.event_identifier '
            'WHERE he.group_identifier = ? AND cb.direction = ?',
            (exit_event.group_identifier, 'spend'),
        ).fetchone()
    assert row == ('0', '34000')


def test_dbeth2_set_validator_exit_idempotent_does_not_mark_cost_basis_stale(
        database: DBHandler,
) -> None:
    """`DBEth2.set_validator_exit()` marks cost basis stale on the initial transition to exited,
    but an idempotent re-run with the same arguments leaves cost basis fresh."""
    _setup_eth2_accounts_and_validators(database, [TEST_ADDR1], [_validator()])

    t_exit = _shappela(200)
    start_ts, end_ts = _shappela(0), _shappela(1000)
    price_fn = _price_lookup({(A_ETH, t_exit): Price(FVal(2500))})

    _write_settings_and_events(
        database=database,
        events=[_eth_withdrawal(at=t_exit, amount='32.5', is_exit=False)],
        eth_staking_taxable_after_withdrawal_enabled=True,
    )
    result = _run_new_pipeline(database, price_fn, start_ts, end_ts)
    assert _get_stale_from_ts(database) is None
    assert result['stale'] is False

    # First transition from non-exit to exit MUST mark cost basis stale.
    dbeth2 = DBEth2(database)
    with database.user_write() as write_cursor:
        dbeth2.set_validator_exit(write_cursor=write_cursor, index=42, withdrawable_timestamp=t_exit)  # noqa: E501
    assert _get_stale_from_ts(database) == str(ts_sec_to_ms(t_exit))
    assert query_realized_pnl(
        database=database, filter_query=_pnl_filter(start_ts, end_ts),
        group_by=RealizedPnlGroupBy.ASSET,
    )['stale'] is True

    # Re-run cost basis so stale marker clears.
    result = _run_new_pipeline(database, price_fn, start_ts, end_ts)
    assert _get_stale_from_ts(database) is None
    assert result['stale'] is False

    # Idempotent re-run on already-exited validator MUST NOT mark cost basis stale again.
    with database.user_write() as write_cursor:
        dbeth2.set_validator_exit(write_cursor=write_cursor, index=42, withdrawable_timestamp=t_exit)  # noqa: E501
    assert _get_stale_from_ts(database) is None
    assert query_realized_pnl(
        database=database, filter_query=_pnl_filter(start_ts, end_ts),
        group_by=RealizedPnlGroupBy.ASSET,
    )['stale'] is False


def test_eth2_deposit_from_blocked_bucket_does_not_update_validator_principal(
        database: DBHandler,
) -> None:
    """When the depositor's ETH bucket is blocked, an `EthDepositEvent` must not mutate
    `validator_principal` in the persisted checkpoint state."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _setup_eth2_accounts_and_validators(
        database, [TEST_ADDR1], [_validator(validator_type=ValidatorType.ACCUMULATING)],
    )

    t_neg, t_dep = _shappela(10), _shappela(20)
    price_fn = _price_lookup({
        (A_ETH, t_neg): Price(FVal(1000)),
        (A_ETH, t_dep): Price(FVal(1500)),
    })

    _write_settings_and_events(
        database=database,
        events=[
            _evm_event(at=t_neg, amount='-1', event_type=HistoryEventType.RECEIVE),
            _eth_deposit(at=t_dep, amount='64'),
        ],
        eth_staking_taxable_after_withdrawal_enabled=True,
    )
    _run_new_pipeline(database, price_fn, _shappela(0), _shappela(1000))

    state = _get_latest_checkpoint_state(database)
    assert '42' not in state['validator_principal']


def test_eth2_checkpoint_prunes_stale_consolidated_sources(
        database: DBHandler,
) -> None:
    """Checkpoint state drops `consolidated_sources` once the non-accumulating source completes
    its exit sweep and does not persist unused skimmed-reward state."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _setup_eth2_accounts_and_validators(
        database=database,
        accounts=[TEST_ADDR1],
        validators=[
            _validator(11, ValidatorType.DISTRIBUTING),
            _validator(20, ValidatorType.ACCUMULATING),
        ],
    )

    t_buy, t_dep11, t_dep20 = _shappela(10), _shappela(30), _shappela(40)
    t_cons11, t_exit11 = _shappela(140), _shappela(200)
    price_fn = _price_lookup({
        (A_ETH, t_buy): Price(FVal(1000)),
        (A_ETH, t_dep11): Price(FVal(1500)),
        (A_ETH, t_dep20): Price(FVal(1500)),
        (A_ETH, t_exit11): Price(FVal(2200)),
    })

    _write_settings_and_events(
        database=database,
        events=[
            _evm_event(at=t_buy, amount='64', event_type=HistoryEventType.RECEIVE),
            _eth_deposit(at=t_dep11, validator_index=11),
            _eth_deposit(at=t_dep20, validator_index=20),
            _eth2_consolidate(at=t_cons11, source_index=11, target_index=20),
            _eth_withdrawal(at=t_exit11, amount='0.1', validator_index=11, is_exit=True),
        ],
        eth_staking_taxable_after_withdrawal_enabled=True,
    )
    _run_new_pipeline(database, price_fn, _shappela(0), _shappela(1000))

    state = _get_latest_checkpoint_state(database)
    assert 'validator_skimmed' not in state
    assert 11 not in state['consolidated_sources']


def test_eth2_withdrawal_request_checkpoint_roundtrip_across_validator_upgrade(
        database: DBHandler,
) -> None:
    """An EIP-7002 partial withdrawal request buffered before a checkpoint while the validator is
    still 0x01 DISTRIBUTING survives the checkpoint and matches as principal once the validator is
    upgraded to 0x02 ACCUMULATING."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)
    pubkey = Eth2PubKey('0x' + 'ab' * 48)
    _setup_eth2_accounts_and_validators(
        database, [TEST_ADDR1], [_validator(validator_type=ValidatorType.DISTRIBUTING, pubkey=pubkey)],  # noqa: E501
    )

    t_buy, t_dep, t_req = _shappela(10), _shappela(20), _shappela(150)
    t_wd, t_spend = _shappela(200), _shappela(300)
    start_ts, end_ts = _shappela(0), _shappela(1000)
    price_fn = _price_lookup({
        (A_ETH, t_buy): Price(FVal(1000)),
        (A_ETH, t_dep): Price(FVal(1500)),
        (A_ETH, t_wd): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    })

    # Pass 1: run while validator is still 0x01 DISTRIBUTING, checkpointing right after t_req.
    _write_settings_and_events(
        database=database,
        events=[
            _evm_event(at=t_buy, amount='40', event_type=HistoryEventType.RECEIVE),
            _eth_deposit(at=t_dep, amount='40'),
            _eth2_request(at=t_req, amount='10'),
        ],
        eth_staking_taxable_after_withdrawal_enabled=True,
    )
    _run_new_pipeline(database, price_fn, start_ts, end_ts)

    # Append withdrawal + spend and upgrade validator 0x01 -> 0x02; stale starts at t_wd (> t_req),
    # so Pass 2 resumes from the checkpoint at t_req.
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[
                _eth_withdrawal(at=t_wd, amount='10'),
                _evm_event(at=t_spend, amount='10', event_type=HistoryEventType.SPEND),
            ],
        )
        DBEth2(database).add_or_update_validators(
            write_cursor=write_cursor,
            validators=[_validator(validator_type=ValidatorType.ACCUMULATING, pubkey=pubkey)],
        )

    old_totals, new_result = _execute_both_pipelines(database, price_fn, start_ts, end_ts)
    # 0 income on matched principal withdrawal; 10 ETH @ 3000 vs $1000 deposit basis -> +20_000.
    assert old_totals == (FVal(20_000), ZERO)
    _assert_pnl_parity(old_totals, new_result)
    state = _get_latest_checkpoint_state(database)
    assert '42' not in state.get('validator_withdrawal_requests', {})


def test_eth2_accumulating_same_timestamp_withdrawal_before_request_parity(
        database: DBHandler,
) -> None:
    """When an EthWithdrawalEvent sorts before its matching EIP-7002 request at the exact same
    timestamp, same-timestamp lookahead matches it as principal and preserves legacy parity."""
    _add_rule(database, HistoryEventType.RECEIVE, taxable=False)
    _add_rule(database, HistoryEventType.SPEND)
    _setup_eth2_accounts_and_validators(
        database, [TEST_ADDR1], [_validator(validator_type=ValidatorType.ACCUMULATING)],
    )

    t_buy, t_dep, t_same, t_spend = _shappela(10), _shappela(20), _shappela(200), _shappela(300)
    price_fn = _price_lookup({
        (A_ETH, t_buy): Price(FVal(1000)),
        (A_ETH, t_dep): Price(FVal(1500)),
        (A_ETH, t_same): Price(FVal(2500)),
        (A_ETH, t_spend): Price(FVal(3000)),
    })

    # Withdrawal has earlier identifier and lexicographically smaller group_identifier ('0000_*'
    # < '0x*') than the request at the same timestamp, forcing the lookahead/prebuffered path.
    events: list[HistoryBaseEntry] = [
        _evm_event(at=t_buy, amount='40', event_type=HistoryEventType.RECEIVE),
        _eth_deposit(at=t_dep, amount='40'),
        _eth_withdrawal(at=t_same, amount='10', group_identifier='0000_same_ts_wd'),
        _eth2_request(at=t_same, amount='10'),
        _evm_event(at=t_spend, amount='10', event_type=HistoryEventType.SPEND),
    ]

    old_totals, new_result = _run_both_pipelines(
        database=database,
        events=events,
        price_fn=price_fn,
        start_ts=_shappela(0),
        end_ts=_shappela(1000),
        eth_staking_taxable_after_withdrawal_enabled=True,
    )
    assert old_totals == (FVal(20_000), ZERO)
    _assert_pnl_parity(old_totals, new_result)
    assert new_result['num_unpriced_events'] == 0
    state = _get_latest_checkpoint_state(database)
    assert '42' not in state.get('validator_withdrawal_requests', {})
