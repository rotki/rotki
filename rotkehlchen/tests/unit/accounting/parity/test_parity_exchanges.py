"""Old-vs-new PnL parity tests for exchange special cases (Stage 2 Shard 3)."""
from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.ethereum.constants import SHAPPELA_TIMESTAMP
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import (
    A_BTC,
    A_ETH,
    A_ETH2,
    A_EUR,
    A_KFEE,
    A_KSM,
    A_LINK,
    A_USD,
    A_USDC,
    A_USDT,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import (
    LOCATION_BINANCE,
    LOCATION_BLOCKCHAIN,
    LOCATION_COINBASE,
    LOCATION_ETHEREUM,
    LOCATION_EXTERNAL,
    LOCATION_KRAKEN,
)
from rotkehlchen.tasks.events import (
    resolve_asset_movement_external,
    update_asset_movement_matched_event,
)
from rotkehlchen.tests.unit.accounting.parity.harness import (
    DEFAULT_EVM_ADDRESS,
    ParityScenario,
    RuleSpec,
    asset_movement,
    evm_event,
    history_event,
    run_parity_scenario,
    swap_group,
    ts,
    ts_ms,
)
from rotkehlchen.tests.utils.constants import A_GBP
from rotkehlchen.types import (
    CostBasisMethod,
    Price,
    SupportedBlockchain,
    Timestamp,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

pytestmark = pytest.mark.accounting_update

A_BNB = Asset('BNB')
A_ETHW = Asset('ETHW')


@pytest.mark.parametrize(
    ('include_fees_in_cost_basis', 'expected_bnb', 'expected_usdc'),
    [
        (True, ZERO, FVal('-20')),
        (False, FVal('-20'), ZERO),
    ],
)
def test_binance_third_asset_bnb_fee(
        database: DBHandler,
        include_fees_in_cost_basis: bool,
        expected_bnb: FVal,
        expected_usdc: FVal,
) -> None:
    """Buy BNB and ETH, swap ETH->USDC on Binance paying fee in BNB, then sell half the USDC.

    Tests third-asset fee handling: with `include_fees_in_cost_basis=True`, the $40 BNB fee
    folds into USDC basis (BNB=0, USDC=-20 on half-sell); with `False`, the BNB fee realizes
    disposal gain (+20) minus expense (-40) = -20 on BNB while USDC basis stays $1 (USDC=0).
    """
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=100,
            group_id='bnb-buy',
            location=LOCATION_BINANCE,
            location_label='binance',
            spend=(A_USD, '200'),
            receive=(A_BNB, '1'),
        ),
        *swap_group(
            at=200,
            group_id='eth-buy',
            location=LOCATION_BINANCE,
            location_label='binance',
            spend=(A_USD, '2000'),
            receive=(A_ETH, '1'),
        ),
        *swap_group(
            at=300,
            group_id='eth-to-usdc-bnb-fee',
            location=LOCATION_BINANCE,
            location_label='binance',
            spend=(A_ETH, '1'),
            receive=(A_USDC, '3000'),
            fee=(A_BNB, '0.1'),
        ),
        *swap_group(
            at=400,
            group_id='usdc-partial-sell',
            location=LOCATION_BINANCE,
            location_label='binance',
            spend=(A_USDC, '1500'),
            receive=(A_USD, '1500'),
        ),
    ]
    scenario = ParityScenario(
        id=f'binance_third_asset_bnb_fee_fold_{include_fees_in_cost_basis}',
        events=events,
        prices={
            (A_BNB, ts(100)): Price(FVal('200')),
            (A_ETH, ts(200)): Price(FVal('2000')),
            (A_ETH, ts(300)): Price(FVal('3000')),
            (A_USDC, ts(300)): Price(ONE),
            (A_BNB, ts(300)): Price(FVal('400')),
            (A_USDC, ts(400)): Price(ONE),
        },
        default_prices={A_USD: Price(ONE)},
        settings={'include_fees_in_cost_basis': include_fees_in_cost_basis},
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    assert diff.old_taxable == FVal('980')
    assert diff.old_free == ZERO
    assert diff.per_asset[A_BNB.identifier].old_taxable == expected_bnb
    assert diff.per_asset[A_USDC.identifier].old_taxable == expected_usdc


@pytest.mark.parametrize(
    ('pair_kind', 'include_fees_in_cost_basis', 'expected_taxable'),
    [
        ('fiat_to_crypto', True, FVal('475.2')),
        ('fiat_to_crypto', False, FVal('475')),
        ('crypto_to_crypto', True, FVal('2500') - FVal('1490') * FVal('10') / FVal('1500')),
        ('crypto_to_crypto', False, FVal('2490')),
    ],
)
def test_exchange_fee_in_received_asset(
        database: DBHandler,
        pair_kind: str,
        include_fees_in_cost_basis: bool,
        expected_taxable: FVal,
) -> None:
    """Swap where the fee leg is denominated in the received asset, then sell the net amount.

    Covers both USD->ETH with ETH fee and ETH->USDT with USDT fee (mirroring
    `test_fees_in_received_asset` in `test_misc.py`) under both fee-folding modes.
    """
    if pair_kind == 'fiat_to_crypto':
        events: list[HistoryBaseEntry] = [
            *swap_group(
                at=100,
                group_id='usd-to-eth-eth-fee',
                location=LOCATION_BINANCE,
                location_label='binance',
                spend=(A_USD, '2000'),
                receive=(A_ETH, '1'),
                fee=(A_ETH, '0.01'),
            ),
            *swap_group(
                at=200,
                group_id='sell-net-eth',
                location=LOCATION_BINANCE,
                location_label='binance',
                spend=(A_ETH, '0.99'),
                receive=(A_USD, '2475'),
            ),
        ]
        prices = {
            (A_ETH, ts(100)): Price(FVal('2000')),
            (A_ETH, ts(200)): Price(FVal('2500')),
        }
    else:
        events = [
            history_event(
                at=50,
                location=LOCATION_BINANCE,
                location_label='binance',
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount='1',
            ),
            *swap_group(
                at=100,
                group_id='eth-to-usdt-usdt-fee',
                location=LOCATION_BINANCE,
                location_label='binance',
                spend=(A_ETH, '0.5'),
                receive=(A_USDT, '1500'),
                fee=(A_USDT, '10'),
            ),
            *swap_group(
                at=200,
                group_id='sell-net-usdt',
                location=LOCATION_BINANCE,
                location_label='binance',
                spend=(A_USDT, '1490'),
                receive=(A_USD, '1490'),
            ),
        ]
        prices = {
            (A_ETH, ts(50)): Price(FVal('2000')),
            (A_ETH, ts(100)): Price(FVal('3000')),
            (A_USDT, ts(100)): Price(ONE),
            (A_USDT, ts(200)): Price(ONE),
        }

    scenario = ParityScenario(
        id=f'exchange_fee_in_received_asset_{pair_kind}_fold_{include_fees_in_cost_basis}',
        events=events,
        prices=prices,
        default_prices={A_USD: Price(ONE)},
        settings={'include_fees_in_cost_basis': include_fees_in_cost_basis},
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    assert diff.old_taxable.is_close(expected_taxable)
    assert diff.old_free == ZERO


def test_coinbase_income_and_expense(database: DBHandler) -> None:
    """Coinbase RECEIVE/REWARD (learn/earn), SPEND/FEE, and spot trades.

    Mirrors `test_account_for_coinbase_income_expense`.
    """
    events: list[HistoryBaseEntry] = [
        history_event(
            at=100,
            location=LOCATION_COINBASE,
            location_label='coinbase',
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ETH,
            amount='1',
            notes='Coinbase Earn reward',
        ),
        history_event(
            at=200,
            location=LOCATION_COINBASE,
            location_label='coinbase',
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount='0.05',
            notes='Coinbase expense fee',
        ),
        *swap_group(
            at=300,
            group_id='cb-buy-btc',
            location=LOCATION_COINBASE,
            location_label='coinbase',
            spend=(A_USD, '20000'),
            receive=(A_BTC, '0.5'),
            fee=(A_USD, '50'),
        ),
        *swap_group(
            at=400,
            group_id='cb-sell-eth',
            location=LOCATION_COINBASE,
            location_label='coinbase',
            spend=(A_ETH, '0.5'),
            receive=(A_USD, '1500'),
            fee=(A_USD, '10'),
        ),
        *swap_group(
            at=500,
            group_id='cb-sell-btc',
            location=LOCATION_COINBASE,
            location_label='coinbase',
            spend=(A_BTC, '0.5'),
            receive=(A_USD, '25000'),
            fee=(A_USD, '25'),
        ),
    ]
    scenario = ParityScenario(
        id='coinbase_income_and_expense',
        events=events,
        prices={
            (A_ETH, ts(100)): Price(FVal('2000')),
            (A_ETH, ts(200)): Price(FVal('2400')),
            (A_BTC, ts(300)): Price(FVal('40000')),
            (A_ETH, ts(400)): Price(FVal('3000')),
            (A_BTC, ts(500)): Price(FVal('50000')),
        },
        default_prices={A_USD: Price(ONE)},
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    # 2000 (reward) - 100 (0.05 ETH fee: -120 expense + 20 disposal gain)
    # + 490 (0.5 ETH sell: 1500 - 1000 - 10) + 4925 (0.5 BTC sell: 25000 - 20050 - 25) = 7315
    assert diff.old_taxable == FVal('7315')
    assert diff.old_free == ZERO


@pytest.mark.parametrize('treat_eth2_as_eth', [False, True])
def test_kraken_staking_and_ledger_events(
        database: DBHandler,
        treat_eth2_as_eth: bool,
) -> None:
    """Kraken staking rewards (non-ETH2 + pre/post-Shapella ETH2), ADJUSTMENT, A_KFEE, fiat trades.

    Mirrors `test_process_kraken_events` and `test_kfee_price_in_accounting`.
    With `treat_eth2_as_eth=False`, both pipelines match identically.
    With `treat_eth2_as_eth=True` (default), the new pipeline deliberately folds Kraken `A_ETH2`
    lots into the `A_ETH` bucket while legacy `AccountingPot` ignores `treat_eth2_as_eth`.
    """
    pre_shapella = Timestamp(SHAPPELA_TIMESTAMP - 86_400)
    post_shapella = Timestamp(SHAPPELA_TIMESTAMP + 86_400)
    trade_ts = Timestamp(SHAPPELA_TIMESTAMP + 172_800)
    sell_ts = Timestamp(SHAPPELA_TIMESTAMP + 259_200)

    events: list[HistoryBaseEntry] = [
        history_event(
            at=pre_shapella,
            location=LOCATION_KRAKEN,
            location_label='kraken',
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_KSM,
            amount='2',
            notes='Kraken KSM staking reward',
        ),
        history_event(
            at=pre_shapella,
            sequence_index=1,
            location=LOCATION_KRAKEN,
            location_label='kraken',
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ETH2,
            amount='0.1',
            notes='Pre-Shapella Kraken ETH2 staking reward',
        ),
        history_event(
            at=post_shapella,
            location=LOCATION_KRAKEN,
            location_label='kraken',
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ETH2,
            amount='0.2',
            notes='Post-Shapella Kraken ETH2 staking reward',
        ),
        history_event(
            at=post_shapella,
            sequence_index=1,
            location=LOCATION_KRAKEN,
            location_label='kraken',
            event_type=HistoryEventType.ADJUSTMENT,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETHW,
            amount='1',
            notes='Receive forked asset',
        ),
        history_event(
            at=post_shapella,
            sequence_index=2,
            location=LOCATION_KRAKEN,
            location_label='kraken',
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_KFEE,
            amount='100',
            notes='Kraken fee credit',
        ),
        history_event(
            at=post_shapella,
            sequence_index=3,
            location=LOCATION_KRAKEN,
            location_label='kraken',
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_BTC,
            amount='1',
            notes='Neutral BTC deposit on Kraken',
        ),
        *swap_group(
            at=trade_ts,
            group_id='kraken-fiat-buy-eth',
            location=LOCATION_KRAKEN,
            location_label='kraken',
            spend=(A_EUR, '1800'),
            receive=(A_ETH, '1'),
            fee=(A_KFEE, '30'),
        ),
        *swap_group(
            at=sell_ts,
            group_id='kraken-sell-eth-eur',
            location=LOCATION_KRAKEN,
            location_label='kraken',
            spend=(A_ETH, '1'),
            receive=(A_EUR, '2200'),
            fee=(A_KFEE, '20'),
        ),
        *swap_group(
            at=sell_ts,
            sequence_offset=10,
            group_id='kraken-sell-ksm',
            location=LOCATION_KRAKEN,
            location_label='kraken',
            spend=(A_KSM, '1'),
            receive=(A_USD, '40'),
        ),
    ]
    scenario = ParityScenario(
        id=f'kraken_staking_and_ledger_events_eth2_as_eth_{treat_eth2_as_eth}',
        events=events,
        settings={'treat_eth2_as_eth': treat_eth2_as_eth},
        prices={
            (A_KSM, pre_shapella): Price(FVal('30')),
            (A_ETH2, pre_shapella): Price(FVal('1800')),
            (A_ETH2, post_shapella): Price(FVal('2100')),
            (A_ETHW, post_shapella): Price(FVal('3')),
            (A_KFEE, post_shapella): Price(FVal('0.01')),
            (A_BTC, post_shapella): Price(FVal('30000')),
            (A_EUR, trade_ts): Price(FVal('1.10')),
            (A_ETH, trade_ts): Price(FVal('1980')),
            (A_KFEE, trade_ts): Price(FVal('0.01')),
            (A_EUR, sell_ts): Price(FVal('1.10')),
            (A_ETH, sell_ts): Price(FVal('2420')),
            (A_KFEE, sell_ts): Price(FVal('0.01')),
            (A_KSM, sell_ts): Price(FVal('40')),
        },
        default_prices={A_USD: Price(ONE)},
        use_default_rules=True,
        rules=[
            RuleSpec(
                event_type=HistoryEventType.ADJUSTMENT,
                event_subtype=HistoryEventSubType.RECEIVE,
                taxable=True,
                count_entire_amount_spend=True,
                count_cost_basis_pnl=True,
            ),
        ],
    )
    diff = run_parity_scenario(database, scenario)
    if treat_eth2_as_eth:
        diff.assert_expected_divergence(
            reason=(
                'DELIBERATE: new pipeline respects treat_eth2_as_eth=True by merging Kraken '
                'A_ETH2 staking lots into the A_ETH bucket (cost_basis.py:1352 -> '
                'Bucket.from_event), whereas legacy AccountingPot ignores treat_eth2_as_eth '
                'and tracks A_ETH2 separately'
            ),
            old_taxable=FVal('933.5'),
            new_taxable=FVal('909.56'),
            per_asset={
                A_ETH.identifier: (FVal('439.5'), ZERO, FVal('835.56'), ZERO),
                A_ETH2.identifier: (FVal('420'), ZERO, ZERO, ZERO),
                A_KSM.identifier: (FVal('70'), ZERO, FVal('70'), ZERO),
                A_ETHW.identifier: (FVal('3'), ZERO, FVal('3'), ZERO),
                A_KFEE.identifier: (FVal('1'), ZERO, FVal('1'), ZERO),
            },
        )
    else:
        diff.assert_parity()
        assert diff.old_taxable == FVal('933.5')
        assert diff.old_free == ZERO


def test_kraken_margin_positions(database: DBHandler) -> None:
    """MarginPosition profit & loss passed in extra_legacy_events alongside spot trades.

    Surfaces the unported margin_positions gap explicitly as KNOWN_GAP (both direct margin
    PnL/fees and downstream spot sell lot consumption).
    """
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=100,
            group_id='kraken-spot-buy',
            location=LOCATION_KRAKEN,
            location_label='kraken',
            spend=(A_USD, '2000'),
            receive=(A_ETH, '1'),
        ),
        *swap_group(
            at=400,
            group_id='kraken-spot-sell',
            location=LOCATION_KRAKEN,
            location_label='kraken',
            spend=(A_ETH, '1'),
            receive=(A_USD, '2500'),
        ),
    ]
    margin_positions = [
        MarginPosition(
            location=LOCATION_KRAKEN,
            open_time=ts(150),
            close_time=ts(200),
            profit_loss=FVal('0.5'),
            pl_currency=A_ETH,
            fee=FVal('0.01'),
            fee_currency=A_ETH,
            link='margin-profit-1',
            notes='Winning ETH margin position',
        ),
        MarginPosition(
            location=LOCATION_KRAKEN,
            open_time=ts(250),
            close_time=ts(300),
            profit_loss=FVal('-0.2'),
            pl_currency=A_ETH,
            fee=FVal('0.01'),
            fee_currency=A_ETH,
            link='margin-loss-2',
            notes='Losing ETH margin position',
        ),
    ]
    scenario = ParityScenario(
        id='kraken_margin_positions',
        events=events,
        extra_legacy_events=margin_positions,
        prices={
            (A_ETH, ts(100)): Price(FVal('2000')),
            (A_ETH, ts(200)): Price(FVal('2400')),
            (A_ETH, ts(300)): Price(FVal('2600')),
            (A_ETH, ts(400)): Price(FVal('2500')),
        },
        default_prices={A_USD: Price(ONE)},
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_expected_divergence(
        reason=(
            'KNOWN_GAP: MarginPosition records are not yet ingested by process_cost_basis '
            '(only legacy Accountant processes margin_positions)'
        ),
        old_taxable=FVal('1172'),
        new_taxable=FVal('500'),
        per_asset={
            A_ETH.identifier: (FVal('1172'), ZERO, FVal('500'), ZERO),
        },
    )


@pytest.mark.parametrize(
    'mode',
    [
        'internal_transfer',
        'unresolved_withdrawal',
        'resolved_external',
    ],
)
def test_asset_movement_internal_vs_external(
        database: DBHandler,
        mode: str,
) -> None:
    """Exchange withdrawal matched to tracked wallet vs unresolved vs resolved as external spend.

    Mirrors `test_asset_movement_resolved_as_external_is_accounted` and tests real matched
    exchange-to-wallet transfers created by `update_asset_movement_matched_event`.
    """
    dbevents = DBHistoryEvents(database)
    if mode == 'internal_transfer':
        withdrawal = AssetMovement(
            timestamp=ts_ms(200),
            location=LOCATION_COINBASE,
            location_label='coinbase',
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('0.99'),
            group_identifier='cb-withdraw-1',
        )
        fee_movement = AssetMovement(
            timestamp=ts_ms(200),
            location=LOCATION_COINBASE,
            location_label='coinbase',
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.01'),
            group_identifier='cb-withdraw-1',
        )
        wallet_receive = evm_event(
            at=201,
            sequence_index=0,
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount='0.99',
        )
        with database.user_write() as write_cursor:
            dbevents.add_history_events(
                write_cursor=write_cursor,
                history=swap_group(
                    at=100,
                    group_id='cb-buy-eth',
                    location=LOCATION_COINBASE,
                    location_label='coinbase',
                    spend=(A_USD, '2000'),
                    receive=(A_ETH, '1'),
                ),
            )
            withdrawal.identifier = dbevents.add_history_event(
                write_cursor=write_cursor,
                event=withdrawal,
            )
            fee_movement.identifier = dbevents.add_history_event(
                write_cursor=write_cursor,
                event=fee_movement,
            )
            wallet_receive.identifier = dbevents.add_history_event(
                write_cursor=write_cursor,
                event=wallet_receive,
            )
            dbevents.add_history_events(
                write_cursor=write_cursor,
                history=swap_group(
                    at=300,
                    group_id='eth-sell-wallet',
                    location=LOCATION_ETHEREUM,
                    location_label=DEFAULT_EVM_ADDRESS,
                    spend=(A_ETH, '0.99'),
                    receive=(A_USDC, '2970'),
                ),
            )
        update_asset_movement_matched_event(
            events_db=dbevents,
            asset_movement=withdrawal,
            fee_event=fee_movement,
            matched_event=wallet_receive,
            is_deposit=False,
        )
        scenario = ParityScenario(
            id='asset_movement_internal_transfer',
            events=[],
            blockchain_accounts=[
                BlockchainAccountData(
                    address=DEFAULT_EVM_ADDRESS,
                    chain=SupportedBlockchain.ETHEREUM,
                ),
            ],
            prices={
                (A_ETH, ts(100)): Price(FVal('2000')),
                (A_ETH, ts(200)): Price(FVal('2500')),
                (A_ETH, ts(201)): Price(FVal('2500')),
                (A_ETH, ts(300)): Price(FVal('3000')),
                (A_USDC, ts(300)): Price(ONE),
            },
            default_prices={A_USD: Price(ONE)},
            use_default_rules=True,
        )
        diff = run_parity_scenario(database, scenario)
        diff.assert_parity()
        assert diff.old_taxable == FVal('970')
        assert diff.old_free == ZERO
        return

    # Unresolved or resolved external withdrawal on Coinbase (mirrors test_exchanges.py)
    withdrawal = AssetMovement(
        timestamp=ts_ms(200),
        location=LOCATION_COINBASE,
        location_label='coinbase',
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_BTC,
        amount=FVal('0.5'),
        group_identifier='cb-btc-withdraw',
    )
    fee_movement = AssetMovement(
        timestamp=ts_ms(200),
        location=LOCATION_COINBASE,
        location_label='coinbase',
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=FVal('0.01'),
        group_identifier='cb-btc-withdraw',
    )
    if mode == 'resolved_external':
        with database.user_write() as write_cursor:
            dbevents.add_history_events(
                write_cursor=write_cursor,
                history=swap_group(
                    at=100,
                    group_id='cb-buy-btc',
                    location=LOCATION_COINBASE,
                    location_label='coinbase',
                    spend=(A_USD, '10000'),
                    receive=(A_BTC, '1'),
                ),
            )
            withdrawal.identifier = dbevents.add_history_event(
                write_cursor=write_cursor,
                event=withdrawal,
            )
            dbevents.add_history_event(
                write_cursor=write_cursor,
                event=fee_movement,
            )
        assert resolve_asset_movement_external(events_db=dbevents, event=withdrawal) is True
        events: list[HistoryBaseEntry] = []
        expected_taxable = FVal('-5100')  # -(0.5 + 0.01) * 10000
    else:
        events = [
            *swap_group(
                at=100,
                group_id='cb-buy-btc',
                location=LOCATION_COINBASE,
                location_label='coinbase',
                spend=(A_USD, '10000'),
                receive=(A_BTC, '1'),
            ),
            withdrawal,
            fee_movement,
        ]
        expected_taxable = FVal('-100')  # -0.01 * 10000

    scenario = ParityScenario(
        id=f'asset_movement_{mode}',
        events=events,
        prices={
            (A_BTC, ts(100)): Price(FVal('10000')),
            (A_BTC, ts(200)): Price(FVal('15000')),
        },
        default_prices={A_USD: Price(ONE)},
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    assert diff.old_taxable == expected_taxable
    assert diff.old_free == ZERO


@pytest.mark.parametrize(
    ('fee_mode', 'expected_taxable'),
    [
        ('eth_fee', FVal('-20')),
        ('fiat_fee', FVal('-25')),
        ('non_taxable_rule', ZERO),
    ],
)
def test_asset_movement_fee_in_different_asset(
        database: DBHandler,
        fee_mode: str,
        expected_taxable: FVal,
) -> None:
    """Withdraw ERC-20 token from exchange with ETH or fiat fee, plus rule handling."""
    fee_asset = A_USD if fee_mode == 'fiat_fee' else A_ETH
    fee_amount = FVal('25') if fee_mode == 'fiat_fee' else FVal('0.01')
    rules: list[RuleSpec] = []
    if fee_mode == 'non_taxable_rule':
        rules.append(
            RuleSpec(
                event_type=HistoryEventType.EXCHANGE_TRANSFER,
                event_subtype=HistoryEventSubType.FEE,
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
            ),
        )

    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=100,
            group_id='buy-eth',
            location=LOCATION_BINANCE,
            location_label='binance',
            spend=(A_USD, '2000'),
            receive=(A_ETH, '1'),
        ),
        *swap_group(
            at=150,
            group_id='buy-link',
            location=LOCATION_BINANCE,
            location_label='binance',
            spend=(A_USD, '1000'),
            receive=(A_LINK, '100'),
        ),
        *asset_movement(
            at=200,
            location=LOCATION_BINANCE,
            location_label='binance',
            subtype=HistoryEventSubType.SPEND,
            asset=A_LINK,
            amount='100',
            fee=(fee_asset, fee_amount),
            group_id='withdraw-link',
        ),
    ]
    scenario = ParityScenario(
        id=f'asset_movement_fee_in_different_asset_{fee_mode}',
        events=events,
        prices={
            (A_ETH, ts(100)): Price(FVal('2000')),
            (A_LINK, ts(150)): Price(FVal('10')),
            (A_LINK, ts(200)): Price(FVal('15')),
            (A_ETH, ts(200)): Price(FVal('3000')),
        },
        default_prices={A_USD: Price(ONE)},
        use_default_rules=True,
        rules=rules,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    assert diff.old_taxable == expected_taxable
    assert diff.old_free == ZERO


@pytest.mark.parametrize(
    ('main_currency', 'quote_fiat', 'quote_rate_t1', 'quote_rate_t2', 'expected_taxable'),
    [
        # Buy 1 ETH for 2000+10 USD @ 0.90 EUR/USD = 1809 EUR
        # Sell 1 ETH for 2500-15 USD @ 0.95 EUR/USD = 2360.75 EUR => trade PnL = +551.75
        # Withdraw fee 5 USD @ 0.95 EUR/USD = -4.75 EUR => total = 547.00 EUR
        (A_EUR, A_USD, FVal('0.90'), FVal('0.95'), FVal('547')),
        # Buy 1 ETH for 2010 EUR @ 1.10 = 2211; sell for 2485 EUR @ 1.15 = 2857.75 => +646.75
        # Withdraw fee 5 EUR @ 1.15 = -5.75 => total = 641.00 USD
        (A_USD, A_EUR, FVal('1.10'), FVal('1.15'), FVal('641')),
        # Buy 1 ETH for 2010 USD @ 0.75 = 1507.5; sell for 2485 USD @ 0.80 = 1988 => +480.5
        # Withdraw fee 5 USD @ 0.80 = -4 => total = 476.5 GBP
        (A_GBP, A_USD, FVal('0.75'), FVal('0.80'), FVal('476.5')),
    ],
)
def test_non_profit_currency_fiat_trades(
        database: DBHandler,
        main_currency: Asset,
        quote_fiat: Asset,
        quote_rate_t1: FVal,
        quote_rate_t2: FVal,
        expected_taxable: FVal,
) -> None:
    """Non-profit-currency fiat trades, deposits/withdrawals, and fees.

    Mirrors `test_main_currency_is_respected`.
    """
    events: list[HistoryBaseEntry] = [
        *asset_movement(
            at=50,
            location=LOCATION_KRAKEN,
            location_label='kraken',
            subtype=HistoryEventSubType.RECEIVE,
            asset=quote_fiat,
            amount='5000',
            group_id='fiat-deposit',
        ),
        *swap_group(
            at=100,
            group_id='buy-eth-non-profit-fiat',
            location=LOCATION_KRAKEN,
            location_label='kraken',
            spend=(quote_fiat, '2000'),
            receive=(A_ETH, '1'),
            fee=(quote_fiat, '10'),
        ),
        *swap_group(
            at=200,
            group_id='sell-eth-non-profit-fiat',
            location=LOCATION_KRAKEN,
            location_label='kraken',
            spend=(A_ETH, '1'),
            receive=(quote_fiat, '2500'),
            fee=(quote_fiat, '15'),
        ),
        *asset_movement(
            at=300,
            location=LOCATION_KRAKEN,
            location_label='kraken',
            subtype=HistoryEventSubType.SPEND,
            asset=quote_fiat,
            amount='1000',
            fee=(quote_fiat, '5'),
            group_id='fiat-withdraw',
        ),
    ]
    scenario = ParityScenario(
        id=(
            f'non_profit_currency_fiat_trades_{main_currency.identifier}'
            f'_quote_{quote_fiat.identifier}'
        ),
        events=events,
        settings={'main_currency': main_currency},
        prices={
            (quote_fiat, ts(50)): Price(quote_rate_t1),
            (quote_fiat, ts(100)): Price(quote_rate_t1),
            (A_ETH, ts(100)): Price(FVal('2000') * quote_rate_t1),
            (quote_fiat, ts(200)): Price(quote_rate_t2),
            (A_ETH, ts(200)): Price(FVal('2500') * quote_rate_t2),
            (quote_fiat, ts(300)): Price(quote_rate_t2),
        },
        default_prices={main_currency: Price(ONE)},
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    assert diff.old_taxable == expected_taxable
    assert diff.old_free == ZERO


@pytest.mark.parametrize(
    ('method', 'expected_taxable'),
    [
        (CostBasisMethod.FIFO, FVal('1500')),
        (CostBasisMethod.LIFO, FVal('500')),
    ],
)
def test_duplicate_timestamp_events(
        database: DBHandler,
        method: CostBasisMethod,
        expected_taxable: FVal,
) -> None:
    """Multiple swaps/movements at the exact same timestamp verifying deterministic tie-breaking.

    Mirrors `test_process_events_with_duplicate_timestamps`. FIFO consumes the $1000 lot
    (+1500) while LIFO consumes the $2000 lot (+500), confirming identical ordering.
    """
    events: list[HistoryBaseEntry] = [
        *asset_movement(
            at=100,
            location=LOCATION_KRAKEN,
            location_label='kraken',
            subtype=HistoryEventSubType.RECEIVE,
            asset=A_USD,
            amount='5000',
            group_id='0-deposit',
        ),
        *swap_group(
            at=200,
            group_id='1-buy-low',
            location=LOCATION_KRAKEN,
            location_label='kraken',
            spend=(A_USD, '1000'),
            receive=(A_ETH, '1'),
            sequence_offset=0,
        ),
        *swap_group(
            at=200,
            group_id='2-buy-high',
            location=LOCATION_KRAKEN,
            location_label='kraken',
            spend=(A_USD, '2000'),
            receive=(A_ETH, '1'),
            sequence_offset=10,
        ),
        *swap_group(
            at=200,
            group_id='3-sell-one',
            location=LOCATION_KRAKEN,
            location_label='kraken',
            spend=(A_ETH, '1'),
            receive=(A_USD, '2500'),
            sequence_offset=20,
        ),
    ]
    scenario = ParityScenario(
        id=f'duplicate_timestamp_events_{method.name.lower()}',
        events=events,
        method=method,
        prices={
            (A_ETH, ts(200)): Price(FVal('2500')),
        },
        default_prices={A_USD: Price(ONE)},
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    assert diff.old_taxable == expected_taxable
    assert diff.old_free == ZERO


@pytest.mark.parametrize('subcase', ['fiat_income', 'deposit_neutrality'])
def test_fiat_income_and_deposit_neutrality(
        database: DBHandler,
        subcase: str,
) -> None:
    """Taxable fiat income (RECEIVE/REWARD & RECEIVE/NONE) and neutral DEPOSIT/DEPOSIT_ASSET.

    Mirrors `test_fiat_income_taxable_pnl` & `test_deposit_asset_is_neutral`.
    """
    if subcase == 'fiat_income':
        events: list[HistoryBaseEntry] = [
            history_event(
                at=100,
                location=LOCATION_EXTERNAL,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_USD,
                amount='100',
                notes='Fiat income in profit currency',
            ),
            history_event(
                at=200,
                location=LOCATION_COINBASE,
                location_label='coinbase',
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.REWARD,
                asset=A_EUR,
                amount='50',
                notes='Fiat reward in non-profit currency',
            ),
            history_event(
                at=300,
                location=LOCATION_COINBASE,
                location_label='coinbase',
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=A_USD,
                amount='500',
                notes='Neutral fiat deposit',
            ),
        ]
        scenario = ParityScenario(
            id='fiat_income_and_deposit_neutrality_income',
            events=events,
            prices={
                (A_EUR, ts(200)): Price(FVal('1.10')),
            },
            default_prices={A_USD: Price(ONE)},
            use_default_rules=True,
        )
        diff = run_parity_scenario(database, scenario)
        diff.assert_parity()
        assert diff.old_taxable == FVal('155')
        assert diff.old_free == ZERO
        return

    # Deposit neutrality: receive ETH -> unmatched withdrawal -> DEPOSIT/DEPOSIT_ASSET -> swap
    events = [
        history_event(
            at=100,
            location=LOCATION_EXTERNAL,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount='0.5',
            group_identifier='eth-receive',
        ),
        *asset_movement(
            at=100,
            location=LOCATION_EXTERNAL,
            location_label=None,
            subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount='0.5',
            group_id='eth-withdraw',
        ),
        history_event(
            at=200,
            location=LOCATION_BLOCKCHAIN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            amount='0.5',
            group_identifier='eth-deposit-neutral',
        ),
        *swap_group(
            at=300,
            group_id='eth-to-usdt',
            location=LOCATION_BLOCKCHAIN,
            location_label=None,
            spend=(A_ETH, '0.5'),
            receive=(A_USDT, '1500'),
        ),
    ]
    scenario = ParityScenario(
        id='fiat_income_and_deposit_neutrality_deposit',
        events=events,
        prices={
            (A_ETH, ts(100)): Price(FVal('2000')),
            (A_ETH, ts(200)): Price(FVal('2500')),
            (A_ETH, ts(300)): Price(FVal('3000')),
            (A_USDT, ts(300)): Price(ONE),
        },
        default_prices={A_USD: Price(ONE)},
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    # DEPOSIT/DEPOSIT_ASSET itself is non-taxable in both pipelines, but across unmatched
    # locations (external -> blockchain) the per-bucket engine removes the $2000 lot from
    # `external` and creates a new $2500 oracle-priced lot in `blockchain`, whereas legacy's
    # global pot ignores both movements and reuses the $2000 lot.
    deposit_rows = [
        row for row in diff.new_cost_basis_rows
        if row['group_identifier'] == 'eth-deposit-neutral'
    ]
    assert len(deposit_rows) == 1
    assert deposit_rows[0]['is_taxable'] is False
    assert deposit_rows[0]['realized_pnl'] is None
    diff.assert_expected_divergence(
        reason=(
            'DELIBERATE: per-bucket lot isolation on unmatched cross-location '
            'AssetMovement(SPEND) + DEPOSIT/DEPOSIT_ASSET re-prices the destination bucket '
            'at oracle price (cost_basis.py:963-965 via Bucket.from_event), whereas legacy '
            'global pot skips neutral DEPOSIT/DEPOSIT_ASSET (history_base_entries.py:73-75)'
        ),
        old_taxable=FVal('1500'),
        new_taxable=FVal('1250'),
        per_asset={
            A_ETH.identifier: (FVal('1500'), ZERO, FVal('1250'), ZERO),
        },
    )


@pytest.mark.parametrize(
    ('direction', 'taxfree_after_period', 'expected_taxable', 'expected_free'),
    [
        ('wallet_to_exchange', -1, FVal('1000'), ZERO),
        ('wallet_to_exchange', 365 * 86_400, ZERO, FVal('1000')),
        ('exchange_to_wallet', 365 * 86_400, ZERO, FVal('1000')),
        ('exchange_to_exchange', 365 * 86_400, ZERO, FVal('1000')),
    ],
)
def test_asset_movement_matched_directions_and_holding_period(
        database: DBHandler,
        direction: str,
        taxfree_after_period: int,
        expected_taxable: FVal,
        expected_free: FVal,
) -> None:
    """Matched transfers carry over basis and acquisition age in all directions.

    Covers wallet->exchange deposits (`is_deposit=True`), exchange->wallet withdrawals, and
    exchange->exchange symmetric links, verifying `taxfree_after_period` holding periods are
    preserved across a transfer near the 1-year boundary.
    """
    dbevents = DBHistoryEvents(database)
    t_buy = 100
    t_move = t_buy + 300 * 86_400
    t_arrive = t_move + 60
    t_sell = t_buy + 400 * 86_400

    with database.user_write() as write_cursor:
        if direction == 'wallet_to_exchange':
            dbevents.add_history_events(
                write_cursor=write_cursor,
                history=swap_group(
                    at=t_buy,
                    group_id='wallet-buy-eth',
                    location=LOCATION_ETHEREUM,
                    location_label=DEFAULT_EVM_ADDRESS,
                    spend=(A_USD, '2000'),
                    receive=(A_ETH, '1'),
                ),
            )
            wallet_send = evm_event(
                at=t_move,
                sequence_index=0,
                location=LOCATION_ETHEREUM,
                location_label=DEFAULT_EVM_ADDRESS,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount='1',
            )
            exchange_deposit = AssetMovement(
                timestamp=ts_ms(t_arrive),
                location=LOCATION_COINBASE,
                location_label='coinbase',
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_ETH,
                amount=FVal('1'),
                group_identifier='cb-deposit-1',
            )
            wallet_send.identifier = dbevents.add_history_event(
                write_cursor=write_cursor,
                event=wallet_send,
            )
            exchange_deposit.identifier = dbevents.add_history_event(
                write_cursor=write_cursor,
                event=exchange_deposit,
            )
            dbevents.add_history_events(
                write_cursor=write_cursor,
                history=swap_group(
                    at=t_sell,
                    group_id='cb-sell-eth',
                    location=LOCATION_COINBASE,
                    location_label='coinbase',
                    spend=(A_ETH, '1'),
                    receive=(A_USD, '3000'),
                ),
            )
        elif direction == 'exchange_to_wallet':
            dbevents.add_history_events(
                write_cursor=write_cursor,
                history=swap_group(
                    at=t_buy,
                    group_id='cb-buy-eth',
                    location=LOCATION_COINBASE,
                    location_label='coinbase',
                    spend=(A_USD, '2000'),
                    receive=(A_ETH, '1'),
                ),
            )
            withdrawal = AssetMovement(
                timestamp=ts_ms(t_move),
                location=LOCATION_COINBASE,
                location_label='coinbase',
                event_subtype=HistoryEventSubType.SPEND,
                asset=A_ETH,
                amount=FVal('1'),
                group_identifier='cb-withdraw-hp',
            )
            wallet_receive = evm_event(
                at=t_arrive,
                sequence_index=0,
                location=LOCATION_ETHEREUM,
                location_label=DEFAULT_EVM_ADDRESS,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount='1',
            )
            withdrawal.identifier = dbevents.add_history_event(
                write_cursor=write_cursor,
                event=withdrawal,
            )
            wallet_receive.identifier = dbevents.add_history_event(
                write_cursor=write_cursor,
                event=wallet_receive,
            )
            dbevents.add_history_events(
                write_cursor=write_cursor,
                history=swap_group(
                    at=t_sell,
                    group_id='wallet-sell-eth',
                    location=LOCATION_ETHEREUM,
                    location_label=DEFAULT_EVM_ADDRESS,
                    spend=(A_ETH, '1'),
                    receive=(A_USDC, '3000'),
                ),
            )
        else:  # exchange_to_exchange
            dbevents.add_history_events(
                write_cursor=write_cursor,
                history=swap_group(
                    at=t_buy,
                    group_id='cb-buy-eth',
                    location=LOCATION_COINBASE,
                    location_label='coinbase',
                    spend=(A_USD, '2000'),
                    receive=(A_ETH, '1'),
                ),
            )
            withdrawal = AssetMovement(
                timestamp=ts_ms(t_move),
                location=LOCATION_COINBASE,
                location_label='coinbase',
                event_subtype=HistoryEventSubType.SPEND,
                asset=A_ETH,
                amount=FVal('1'),
                group_identifier='cb-withdraw-ex',
            )
            binance_deposit = AssetMovement(
                timestamp=ts_ms(t_arrive),
                location=LOCATION_BINANCE,
                location_label='binance',
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_ETH,
                amount=FVal('1'),
                group_identifier='bn-deposit-ex',
            )
            withdrawal.identifier = dbevents.add_history_event(
                write_cursor=write_cursor,
                event=withdrawal,
            )
            binance_deposit.identifier = dbevents.add_history_event(
                write_cursor=write_cursor,
                event=binance_deposit,
            )
            dbevents.add_history_events(
                write_cursor=write_cursor,
                history=swap_group(
                    at=t_sell,
                    group_id='bn-sell-eth',
                    location=LOCATION_BINANCE,
                    location_label='binance',
                    spend=(A_ETH, '1'),
                    receive=(A_USD, '3000'),
                ),
            )

    if direction == 'wallet_to_exchange':
        update_asset_movement_matched_event(
            events_db=dbevents,
            asset_movement=exchange_deposit,
            fee_event=None,
            matched_event=wallet_send,
            is_deposit=True,
        )
    elif direction == 'exchange_to_wallet':
        update_asset_movement_matched_event(
            events_db=dbevents,
            asset_movement=withdrawal,
            fee_event=None,
            matched_event=wallet_receive,
            is_deposit=False,
        )
    else:
        update_asset_movement_matched_event(
            events_db=dbevents,
            asset_movement=withdrawal,
            fee_event=None,
            matched_event=binance_deposit,
            is_deposit=False,
        )

    scenario = ParityScenario(
        id=f'asset_movement_matched_{direction}_tf_{taxfree_after_period}',
        events=[],
        blockchain_accounts=[
            BlockchainAccountData(
                address=DEFAULT_EVM_ADDRESS,
                chain=SupportedBlockchain.ETHEREUM,
            ),
        ],
        prices={
            (A_ETH, ts(t_buy)): Price(FVal('2000')),
            (A_ETH, ts(t_move)): Price(FVal('2500')),
            (A_ETH, ts(t_arrive)): Price(FVal('2500')),
            (A_ETH, ts(t_sell)): Price(FVal('3000')),
            (A_USDC, ts(t_sell)): Price(ONE),
        },
        default_prices={A_USD: Price(ONE)},
        settings={'taxfree_after_period': taxfree_after_period},
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    assert diff.old_taxable == expected_taxable
    assert diff.old_free == expected_free
