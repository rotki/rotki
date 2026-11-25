"""Stage 2 Shard 4: Settings, filters, and accounting rules old-vs-new PnL parity tests."""
from typing import TYPE_CHECKING, Final

import pytest

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.accounting.structures import TxAccountingTreatment
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_BTC, A_DAI, A_ETH, A_USD, A_WETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ETHEREUM, LOCATION_KRAKEN
from rotkehlchen.tests.unit.accounting.parity.harness import (
    DEFAULT_EVM_ADDRESS,
    SECOND_EVM_ADDRESS,
    ParityScenario,
    RuleSpec,
    evm_event,
    history_event,
    run_parity_scenario,
    swap_group,
    ts,
)
from rotkehlchen.tests.utils.constants import A_DASH
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import CostBasisMethod, Price, SupportedBlockchain, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

pytestmark = pytest.mark.accounting_update

ONE_YEAR_SECS: Final = 365 * 86400

# ---------------------------------------------------------------------------
# 1. include_crypto2crypto_false
# ---------------------------------------------------------------------------


def test_include_crypto2crypto_false(database: DBHandler) -> None:
    """Buy ETH with USD -> swap ETH->DAI -> sell DAI for USD with include_crypto2crypto=False.

    Both legacy (`history_base_entries.py:277`) and new (`cost_basis.py:309`) mark the
    crypto-to-crypto ETH->DAI disposal non-taxable (0 realized PnL) while acquiring DAI at
    the swap value ($2000), so only the final DAI->USD disposal realizes +500 taxable PnL.
    """
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=100,
            group_id='buy-eth',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_USD, '1000'),
            receive=(A_ETH, '1'),
        ),
        *swap_group(
            at=200,
            group_id='eth-to-dai',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_ETH, '1'),
            receive=(A_DAI, '2000'),
        ),
        *swap_group(
            at=300,
            group_id='sell-dai',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_DAI, '2000'),
            receive=(A_USD, '2500'),
        ),
    ]
    scenario = ParityScenario(
        id='include_crypto2crypto_false',
        events=events,
        prices={
            (A_USD, ts(100)): Price(FVal('1')),
            (A_ETH, ts(100)): Price(FVal('1000')),
            (A_ETH, ts(200)): Price(FVal('2000')),
            (A_DAI, ts(200)): Price(FVal('1')),
            (A_DAI, ts(300)): Price(FVal('1.25')),
            (A_USD, ts(300)): Price(FVal('1')),
        },
        settings={
            'include_crypto2crypto': False,
            'taxfree_after_period': -1,
            'include_fees_in_cost_basis': False,
        },
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    assert diff.old_taxable == FVal('500')
    assert diff.old_free == ZERO


# ---------------------------------------------------------------------------
# 2. include_gas_costs_false
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(('include_gas_costs', 'expected_taxable', 'expected_free'), [
    (False, FVal('1000'), ZERO),
    (True, FVal('950'), FVal('20')),
])
def test_include_gas_costs_false(
        database: DBHandler,
        include_gas_costs: bool,
        expected_taxable: FVal,
        expected_free: FVal,
) -> None:
    """EVM swap + SPEND/FEE gas (within and after 1yr) with include_gas_costs toggled."""
    t_after_year = 200 + ONE_YEAR_SECS + 86400
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=100,
            group_id='buy-eth',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_USD, '10000'),
            receive=(A_ETH, '10'),
        ),
        *swap_group(
            at=200,
            group_id='swap-eth-dai',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_ETH, '2'),
            receive=(A_DAI, '3000'),
        ),
        evm_event(
            at=200,
            amount='0.01',
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            counterparty=CPT_GAS,
        ),
        evm_event(
            at=t_after_year,
            amount='0.02',
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            counterparty=CPT_GAS,
        ),
    ]
    scenario = ParityScenario(
        id=f'include_gas_costs_{include_gas_costs}',
        events=events,
        prices={
            (A_USD, ts(100)): Price(FVal('1')),
            (A_ETH, ts(100)): Price(FVal('1000')),
            (A_ETH, ts(200)): Price(FVal('1500')),
            (A_DAI, ts(200)): Price(FVal('1')),
            (A_ETH, ts(t_after_year)): Price(FVal('2000')),
        },
        settings={
            'include_gas_costs': include_gas_costs,
            'taxfree_after_period': ONE_YEAR_SECS,
            'include_fees_in_cost_basis': False,
        },
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    assert diff.old_taxable == expected_taxable
    assert diff.old_free == expected_free


# ---------------------------------------------------------------------------
# 3. calculate_past_cost_basis_false
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('calculate_past_cost_basis', [False, True])
def test_calculate_past_cost_basis_false(
        database: DBHandler,
        calculate_past_cost_basis: bool,
) -> None:
    """Buy in year 1, sell in year 2, query year 2 with calculate_past_cost_basis=False vs True."""
    t_buy = Timestamp(1_685_577_600)  # 2023-06-01
    t_start = Timestamp(1_704_067_200)  # 2024-01-01
    t_sell = Timestamp(1_717_200_000)  # 2024-06-01
    t_end = Timestamp(1_735_689_599)  # 2024-12-31

    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=t_buy,
            group_id='buy-btc-y1',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_USD, '5000'),
            receive=(A_BTC, '5'),
        ),
        *swap_group(
            at=t_sell,
            group_id='sell-btc-y2',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_BTC, '2'),
            receive=(A_USD, '6000'),
            fee=(A_USD, '10'),
        ),
    ]
    scenario = ParityScenario(
        id=f'calculate_past_cost_basis_{calculate_past_cost_basis}',
        events=events,
        prices={
            (A_USD, t_buy): Price(FVal('1')),
            (A_BTC, t_buy): Price(FVal('1000')),
            (A_BTC, t_sell): Price(FVal('3000')),
            (A_USD, t_sell): Price(FVal('1')),
        },
        start_ts=t_start,
        end_ts=t_end,
        settings={
            'calculate_past_cost_basis': calculate_past_cost_basis,
            'taxfree_after_period': -1,
            'include_fees_in_cost_basis': False,
        },
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    if calculate_past_cost_basis:
        diff.assert_parity()
        assert diff.old_taxable == FVal('3990')
        assert diff.old_free == ZERO
    else:
        diff.assert_expected_divergence(
            reason=(
                'DELIBERATE: process_cost_basis() always builds lots from timestamp 0 '
                '(cost_basis.py:1294) and ignores legacy calculate_past_cost_basis=False'
            ),
            old_taxable=FVal('5990'),
            new_taxable=FVal('3990'),
            per_asset={
                A_BTC.identifier: (FVal('6000'), ZERO, FVal('4000'), ZERO),
                A_USD.identifier: (FVal('-10'), ZERO, FVal('-10'), ZERO),
            },
        )


# ---------------------------------------------------------------------------
# 4. ignored_asset_standalone_and_in_swap
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(('variant', 'expected_taxable'), [
    ('standalone', FVal('1000')),
    ('ignored_spend_leg', FVal('4000')),
    ('ignored_receive_leg', FVal('1000')),
    ('ignored_fee_leg', ZERO),
])
def test_ignored_asset_standalone_and_in_swap(
        database: DBHandler,
        variant: str,
        expected_taxable: FVal,
) -> None:
    """Ignored asset held/sold standalone and as spend, receive, or fee leg in a swap."""
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=100,
            group_id='buy-eth',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_USD, '2000'),
            receive=(A_ETH, '2'),
        ),
    ]
    prices = {
        (A_USD, ts(100)): Price(FVal('1')),
        (A_ETH, ts(100)): Price(FVal('1000')),
        (A_DASH, ts(150)): Price(FVal('100')),
        (A_USD, ts(150)): Price(FVal('1')),
        (A_ETH, ts(200)): Price(FVal('1500')),
        (A_DASH, ts(200)): Price(FVal('150')),
        (A_USD, ts(200)): Price(FVal('1')),
        (A_ETH, ts(300)): Price(FVal('2000')),
        (A_DASH, ts(300)): Price(FVal('200')),
        (A_USD, ts(300)): Price(FVal('1')),
    }

    if variant == 'standalone':
        events.extend([
            history_event(
                at=150,
                location=LOCATION_KRAKEN,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_DASH,
                amount='10',
            ),
            history_event(
                at=200,
                location=LOCATION_KRAKEN,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_DASH,
                amount='5',
            ),
            *swap_group(
                at=300,
                group_id='sell-eth',
                location=LOCATION_KRAKEN,
                location_label=None,
                spend=(A_ETH, '1'),
                receive=(A_USD, '2000'),
            ),
        ])
    elif variant == 'ignored_spend_leg':
        events.extend([
            *swap_group(
                at=150,
                group_id='buy-dash',
                location=LOCATION_KRAKEN,
                location_label=None,
                spend=(A_USD, '1000'),
                receive=(A_DASH, '10'),
            ),
            *swap_group(
                at=200,
                group_id='dash-to-eth',
                location=LOCATION_KRAKEN,
                location_label=None,
                spend=(A_DASH, '10'),
                receive=(A_ETH, '1'),
            ),
            *swap_group(
                at=300,
                group_id='sell-all-eth',
                location=LOCATION_KRAKEN,
                location_label=None,
                spend=(A_ETH, '3'),
                receive=(A_USD, '6000'),
            ),
        ])
    elif variant == 'ignored_receive_leg':
        events.extend([
            *swap_group(
                at=200,
                group_id='eth-to-dash',
                location=LOCATION_KRAKEN,
                location_label=None,
                spend=(A_ETH, '1'),
                receive=(A_DASH, '10'),
            ),
            *swap_group(
                at=300,
                group_id='sell-eth',
                location=LOCATION_KRAKEN,
                location_label=None,
                spend=(A_ETH, '1'),
                receive=(A_USD, '2000'),
            ),
        ])
    elif variant == 'ignored_fee_leg':
        events.extend([
            *swap_group(
                at=150,
                group_id='buy-dash',
                location=LOCATION_KRAKEN,
                location_label=None,
                spend=(A_USD, '100'),
                receive=(A_DASH, '1'),
            ),
            *swap_group(
                at=200,
                group_id='sell-eth-dash-fee',
                location=LOCATION_KRAKEN,
                location_label=None,
                spend=(A_ETH, '1'),
                receive=(A_USD, '1500'),
                fee=(A_DASH, '0.1'),
            ),
        ])

    scenario = ParityScenario(
        id=f'ignored_asset_{variant}',
        events=events,
        prices=prices,
        ignored_assets=(A_DASH,),
        settings={
            'taxfree_after_period': -1,
            'include_fees_in_cost_basis': False,
        },
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    assert diff.old_taxable == expected_taxable
    assert diff.old_free == ZERO


def test_ignored_asset_swap_preserves_gas_fee_and_skips_basis_transfer(
        database: DBHandler,
) -> None:
    """Gas fees sharing a tx group with an ignored-asset swap are kept; ignored basis transfers skip."""  # noqa: E501
    swap_tx = make_evm_tx_hash()
    bt_tx = make_evm_tx_hash()
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=100,
            group_id='buy-eth',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_USD, '2000'),
            receive=(A_ETH, '2'),
        ),
        # Ignored-asset swap sharing an EVM tx hash with a normal CPT_GAS SPEND/FEE
        evm_event(
            at=200,
            sequence_index=0,
            tx_ref=swap_tx,
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount='1',
        ),
        evm_event(
            at=200,
            sequence_index=1,
            tx_ref=swap_tx,
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_DASH,
            amount='10',
        ),
        evm_event(
            at=200,
            sequence_index=2,
            tx_ref=swap_tx,
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount='0.01',
            counterparty=CPT_GAS,
        ),
        # Paired BASIS_TRANSFER where destination asset is ignored -> whole pair skipped
        evm_event(
            at=250,
            sequence_index=0,
            tx_ref=bt_tx,
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_ETH,
            amount='0.5',
        ),
        evm_event(
            at=250,
            sequence_index=1,
            tx_ref=bt_tx,
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_DASH,
            amount='0.5',
        ),
        # Sell 1 ETH: still consumes the $1000 lot (both ignored swap & basis transfer skipped)
        *swap_group(
            at=300,
            group_id='sell-eth',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_ETH, '1'),
            receive=(A_USD, '2000'),
        ),
    ]
    scenario = ParityScenario(
        id='ignored_asset_swap_preserves_gas_fee_and_skips_basis_transfer',
        events=events,
        prices={
            (A_USD, ts(100)): Price(FVal('1')),
            (A_ETH, ts(100)): Price(FVal('1000')),
            (A_ETH, ts(200)): Price(FVal('1500')),
            (A_DASH, ts(200)): Price(FVal('150')),
            (A_ETH, ts(250)): Price(FVal('1600')),
            (A_DASH, ts(250)): Price(FVal('1600')),
            (A_ETH, ts(300)): Price(FVal('2000')),
            (A_USD, ts(300)): Price(FVal('1')),
        },
        ignored_assets=(A_DASH,),
        settings={
            'include_gas_costs': True,
            'taxfree_after_period': -1,
            'include_fees_in_cost_basis': False,
        },
        use_default_rules=True,
        rules=(
            RuleSpec(
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
                taxable=False,
                accounting_treatment=TxAccountingTreatment.BASIS_TRANSFER,
            ),
        ),
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    # Gas fee (0.01 ETH: -15 expense + 5 disposal gain = -10) + sell 1 ETH (+1000) = 990
    assert diff.old_taxable == FVal('990')
    assert diff.old_free == ZERO


# ---------------------------------------------------------------------------
# 5. ignored_action_excluded
# ---------------------------------------------------------------------------


def test_ignored_action_excluded(database: DBHandler) -> None:
    """Events added to ignored_actions are excluded from both lots and realized PnL."""
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=100,
            group_id='kept-buy-eth',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_USD, '2000'),
            receive=(A_ETH, '2'),
        ),
        *swap_group(
            at=200,
            group_id='ignored-buy-eth',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_USD, '4000'),
            receive=(A_ETH, '2'),
        ),
        history_event(
            at=250,
            location=LOCATION_KRAKEN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount='1',
            group_identifier='ignored-income',
        ),
        *swap_group(
            at=300,
            group_id='kept-sell-eth',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_ETH, '2'),
            receive=(A_USD, '6000'),
        ),
        *swap_group(
            at=400,
            group_id='ignored-sell-eth',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_ETH, '1'),
            receive=(A_USD, '3500'),
        ),
    ]
    scenario = ParityScenario(
        id='ignored_action_excluded',
        events=events,
        prices={
            (A_USD, ts(100)): Price(FVal('1')),
            (A_ETH, ts(100)): Price(FVal('1000')),
            (A_USD, ts(200)): Price(FVal('1')),
            (A_ETH, ts(200)): Price(FVal('2000')),
            (A_ETH, ts(250)): Price(FVal('2500')),
            (A_ETH, ts(300)): Price(FVal('3000')),
            (A_USD, ts(300)): Price(FVal('1')),
            (A_ETH, ts(400)): Price(FVal('3500')),
            (A_USD, ts(400)): Price(FVal('1')),
        },
        ignored_actions=('ignored-buy-eth', 'ignored-income', 'ignored-sell-eth'),
        settings={
            'taxfree_after_period': -1,
            'include_fees_in_cost_basis': False,
        },
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    assert diff.old_taxable == FVal('4000')
    assert diff.old_free == ZERO


# ---------------------------------------------------------------------------
# 6. swap_fee_taxable_ratio_mixed_lots
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(('fee_asset', 'expected_taxable', 'expected_free'), [
    (A_USD, FVal('1400'), FVal('2000')),
    (A_ETH, FVal('1350'), FVal('2000')),
    (A_BTC, FVal('1200'), FVal('2200')),
])
def test_swap_fee_taxable_ratio_mixed_lots(
        database: DBHandler,
        fee_asset: Asset,
        expected_taxable: FVal,
        expected_free: FVal,
) -> None:
    """Swap 2 ETH (1 tax-free >1yr + 1 taxable <1yr) with USD, taxable ETH, or tax-free BTC fee.

    Legacy sets `fee_taxable_amount_ratio = trade_taxable_amount / out_event.amount` on
    swap fees (`history_base_entries.py:314`), but for fiat fees `calculate_pnl` sums
    `taxable_value + free_value` into taxable expense (`processed_event.py:215`), and for
    crypto fees `pot.py:382` uses the fee lot's own `spend_cost.taxable_amount` instead of
    the ratio — matching the new pipeline in all three fee cases.
    """
    t_old = 0
    t_recent = 300 * 86400
    t_swap = 400 * 86400

    if fee_asset == A_USD:
        fee_leg = (A_USD, '100')
    elif fee_asset == A_ETH:
        fee_leg = (A_ETH, '0.1')
    else:
        fee_leg = (A_BTC, '0.1')

    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=t_old,
            group_id='buy-old-eth',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_USD, '1000'),
            receive=(A_ETH, '1'),
        ),
        *swap_group(
            at=t_recent,
            group_id='buy-recent-eth',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_USD, '1650' if fee_asset == A_ETH else '1500'),
            receive=(A_ETH, '1.1' if fee_asset == A_ETH else '1'),
        ),
    ]
    if fee_asset == A_BTC:
        events.extend(swap_group(
            at=t_old,
            group_id='buy-old-btc-for-fee',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_USD, '100'),
            receive=(A_BTC, '0.1'),
        ))
    events.extend(swap_group(
        at=t_swap,
        group_id='swap-mixed-lots',
        location=LOCATION_KRAKEN,
        location_label=None,
        spend=(A_ETH, '2'),
        receive=(A_USD, '6000'),
        fee=fee_leg,
    ))
    scenario = ParityScenario(
        id=f'swap_fee_taxable_ratio_mixed_lots_{fee_asset.identifier}',
        events=events,
        prices={
            (A_USD, ts(t_old)): Price(FVal('1')),
            (A_ETH, ts(t_old)): Price(FVal('1000')),
            (A_BTC, ts(t_old)): Price(FVal('1000')),
            (A_USD, ts(t_recent)): Price(FVal('1')),
            (A_ETH, ts(t_recent)): Price(FVal('1500')),
            (A_USD, ts(t_swap)): Price(FVal('1')),
            (A_ETH, ts(t_swap)): Price(FVal('3000')),
            (A_BTC, ts(t_swap)): Price(FVal('3000')),
        },
        settings={
            'taxfree_after_period': ONE_YEAR_SECS,
            'include_fees_in_cost_basis': False,
        },
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    assert diff.old_taxable == expected_taxable
    assert diff.old_free == expected_free


# ---------------------------------------------------------------------------
# 7. rule_count_cost_basis_pnl_false
# ---------------------------------------------------------------------------


def test_rule_count_cost_basis_pnl_false(database: DBHandler) -> None:
    """Spend with count_cost_basis_pnl=False followed by a ruled spend."""
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=100,
            group_id='buy-lot-1',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_USD, '1000'),
            receive=(A_ETH, '1'),
        ),
        *swap_group(
            at=200,
            group_id='buy-lot-2',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_USD, '2000'),
            receive=(A_ETH, '1'),
        ),
        history_event(
            at=300,
            location=LOCATION_KRAKEN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount='1',
        ),
        *swap_group(
            at=400,
            group_id='sell-remaining',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_ETH, '1'),
            receive=(A_USD, '4000'),
        ),
    ]
    scenario = ParityScenario(
        id='rule_count_cost_basis_pnl_false',
        events=events,
        prices={
            (A_USD, ts(100)): Price(FVal('1')),
            (A_ETH, ts(100)): Price(FVal('1000')),
            (A_USD, ts(200)): Price(FVal('1')),
            (A_ETH, ts(200)): Price(FVal('2000')),
            (A_ETH, ts(300)): Price(FVal('3000')),
            (A_ETH, ts(400)): Price(FVal('4000')),
            (A_USD, ts(400)): Price(FVal('1')),
        },
        settings={'taxfree_after_period': -1},
        rules=(
            RuleSpec(
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                taxable=True,
                accounting_treatment=TxAccountingTreatment.SWAP,
            ),
            RuleSpec(
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                taxable=True,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
            ),
        ),
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_expected_divergence(
        reason=(
            'DELIBERATE: new pipeline always consumes lots on spend (cost_basis.py:618) '
            'even when count_cost_basis_pnl=False, whereas legacy leaves lots untouched '
            '(pot.py:370)'
        ),
        old_taxable=FVal('3000'),
        new_taxable=FVal('2000'),
        per_asset={A_ETH.identifier: (FVal('3000'), ZERO, FVal('2000'), ZERO)},
    )


# ---------------------------------------------------------------------------
# 8. rule_count_entire_amount_spend
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('count_cost_basis_pnl', [True, False])
def test_rule_count_entire_amount_spend(
        database: DBHandler,
        count_cost_basis_pnl: bool,
) -> None:
    """Spend with count_entire_amount_spend=True (both count_cost_basis_pnl True & False)."""
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=100,
            group_id='buy-lot-1',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_USD, '1000'),
            receive=(A_ETH, '1'),
        ),
        *swap_group(
            at=150,
            group_id='buy-lot-2',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_USD, '1200'),
            receive=(A_ETH, '1'),
        ),
        history_event(
            at=200,
            location=LOCATION_KRAKEN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount='1',
        ),
        *swap_group(
            at=300,
            group_id='sell-remaining',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_ETH, '1'),
            receive=(A_USD, '2000'),
        ),
    ]
    scenario = ParityScenario(
        id=f'rule_count_entire_amount_spend_cb_{count_cost_basis_pnl}',
        events=events,
        prices={
            (A_USD, ts(100)): Price(FVal('1')),
            (A_ETH, ts(100)): Price(FVal('1000')),
            (A_USD, ts(150)): Price(FVal('1')),
            (A_ETH, ts(150)): Price(FVal('1200')),
            (A_ETH, ts(200)): Price(FVal('1500')),
            (A_ETH, ts(300)): Price(FVal('2000')),
            (A_USD, ts(300)): Price(FVal('1')),
        },
        settings={'taxfree_after_period': -1},
        rules=(
            RuleSpec(
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                taxable=True,
                accounting_treatment=TxAccountingTreatment.SWAP,
            ),
            RuleSpec(
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                taxable=True,
                count_entire_amount_spend=True,
                count_cost_basis_pnl=count_cost_basis_pnl,
            ),
        ),
    )
    diff = run_parity_scenario(database, scenario)
    if count_cost_basis_pnl:
        diff.assert_parity()
        assert diff.old_taxable == FVal('-200')
        assert diff.old_free == ZERO
    else:
        diff.assert_expected_divergence(
            reason=(
                'DELIBERATE: both deduct -1500 expense, but new pipeline consumes lot-1 ($1000) '
                'even with count_cost_basis_pnl=False (cost_basis.py:618) so the subsequent sell '
                'consumes lot-2 ($1200) instead of lot-1 ($1000)'
            ),
            old_taxable=FVal('-500'),
            new_taxable=FVal('-700'),
            per_asset={A_ETH.identifier: (FVal('-500'), ZERO, FVal('-700'), ZERO)},
        )


# ---------------------------------------------------------------------------
# 9. no_rule_event_lot_movement
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('direction', ['receive', 'spend'])
def test_no_rule_event_lot_movement(database: DBHandler, direction: str) -> None:
    """Receive or spend event with no matching rule followed by a ruled swap."""
    if direction == 'receive':
        events: list[HistoryBaseEntry] = [
            history_event(
                at=100,
                location=LOCATION_KRAKEN,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.AIRDROP,
                asset=A_ETH,
                amount='2',
            ),
            *swap_group(
                at=200,
                group_id='sell-after-no-rule-receive',
                location=LOCATION_KRAKEN,
                location_label=None,
                spend=(A_ETH, '1'),
                receive=(A_USD, '1500'),
            ),
        ]
    else:
        events = [
            *swap_group(
                at=100,
                group_id='buy-lot-1',
                location=LOCATION_KRAKEN,
                location_label=None,
                spend=(A_USD, '2000'),
                receive=(A_ETH, '2'),
            ),
            *swap_group(
                at=150,
                group_id='buy-lot-2',
                location=LOCATION_KRAKEN,
                location_label=None,
                spend=(A_USD, '2000'),
                receive=(A_ETH, '1'),
            ),
            history_event(
                at=200,
                location=LOCATION_KRAKEN,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.DONATE,
                asset=A_ETH,
                amount='2',
            ),
            *swap_group(
                at=300,
                group_id='sell-after-no-rule-spend',
                location=LOCATION_KRAKEN,
                location_label=None,
                spend=(A_ETH, '1'),
                receive=(A_USD, '2500'),
            ),
        ]

    scenario = ParityScenario(
        id=f'no_rule_event_lot_movement_{direction}',
        events=events,
        prices={
            (A_USD, ts(100)): Price(FVal('1')),
            (A_ETH, ts(100)): Price(FVal('1000')),
            (A_USD, ts(150)): Price(FVal('1')),
            (A_ETH, ts(150)): Price(FVal('2000')),
            (A_ETH, ts(200)): Price(FVal('1500')),
            (A_USD, ts(200)): Price(FVal('1')),
            (A_ETH, ts(300)): Price(FVal('2500')),
            (A_USD, ts(300)): Price(FVal('1')),
        },
        settings={'taxfree_after_period': -1},
        rules=(
            RuleSpec(
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                taxable=True,
                accounting_treatment=TxAccountingTreatment.SWAP,
            ),
        ),
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_expected_divergence(
        reason=(
            f'DELIBERATE: new pipeline still moves lots for no-rule {direction} events at 0 PnL '
            f'(cost_basis.py:572,618), whereas legacy skips unruled events entirely'
        ),
        old_taxable=FVal('1500'),
        new_taxable=FVal('500'),
        per_asset={A_ETH.identifier: (FVal('1500'), ZERO, FVal('500'), ZERO)},
    )


# ---------------------------------------------------------------------------
# 10. unpriced_swap_and_spend
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('variant', [
    'swap_missing_spend_price',
    'swap_missing_receive_price',
    'swap_missing_both_prices',
    'standalone_unpriced_spend',
])
def test_unpriced_swap_and_spend(database: DBHandler, variant: str) -> None:
    """Missing price on swap spend leg, receive leg, both legs, and standalone spend."""
    prices = {
        (A_USD, ts(100)): Price(FVal('1')),
        (A_ETH, ts(100)): Price(FVal('1000')),
        (A_USD, ts(150)): Price(FVal('1')),
        (A_ETH, ts(150)): Price(FVal('1200')),
        (A_USD, ts(300)): Price(FVal('1')),
        (A_DAI, ts(300)): Price(FVal('1.2')),
        (A_ETH, ts(300)): Price(FVal('2000')),
    }
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=100,
            group_id='buy-eth-1',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_USD, '1000'),
            receive=(A_ETH, '1'),
        ),
    ]

    if variant == 'swap_missing_spend_price':
        prices[A_DAI, ts(200)] = Price(FVal('1'))
        events.extend([
            *swap_group(
                at=200,
                group_id='swap-no-eth-price',
                location=LOCATION_KRAKEN,
                location_label=None,
                spend=(A_ETH, '1'),
                receive=(A_DAI, '1500'),
            ),
            *swap_group(
                at=300,
                group_id='sell-dai',
                location=LOCATION_KRAKEN,
                location_label=None,
                spend=(A_DAI, '1500'),
                receive=(A_USD, '1800'),
            ),
        ])
    elif variant == 'swap_missing_receive_price':
        prices[A_ETH, ts(200)] = Price(FVal('1500'))
        events.extend([
            *swap_group(
                at=200,
                group_id='swap-no-dai-price',
                location=LOCATION_KRAKEN,
                location_label=None,
                spend=(A_ETH, '1'),
                receive=(A_DAI, '1500'),
            ),
            *swap_group(
                at=300,
                group_id='sell-dai',
                location=LOCATION_KRAKEN,
                location_label=None,
                spend=(A_DAI, '1500'),
                receive=(A_USD, '1800'),
            ),
        ])
    elif variant == 'swap_missing_both_prices':
        events.extend(swap_group(
            at=200,
            group_id='swap-no-prices',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_ETH, '1'),
            receive=(A_DAI, '1500'),
        ))
    elif variant == 'standalone_unpriced_spend':
        events.extend([
            *swap_group(
                at=150,
                group_id='buy-eth-2',
                location=LOCATION_KRAKEN,
                location_label=None,
                spend=(A_USD, '1200'),
                receive=(A_ETH, '1'),
            ),
            history_event(
                at=200,
                location=LOCATION_KRAKEN,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount='1',
            ),
            *swap_group(
                at=300,
                group_id='sell-remaining-eth',
                location=LOCATION_KRAKEN,
                location_label=None,
                spend=(A_ETH, '1'),
                receive=(A_USD, '2000'),
            ),
        ])

    scenario = ParityScenario(
        id=f'unpriced_{variant}',
        events=events,
        prices=prices,
        settings={'taxfree_after_period': -1},
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    if variant in ('swap_missing_spend_price', 'swap_missing_receive_price'):
        diff.assert_parity()
        assert diff.old_taxable == FVal('800')
        assert diff.old_free == ZERO
        assert len(diff.old_missing_prices) == 0
        assert diff.new_unpriced_events == 0
    elif variant == 'swap_missing_both_prices':
        diff.assert_parity()
        assert diff.old_taxable == ZERO
        assert diff.old_free == ZERO
        # Legacy get_prices_for_swap() silently skips when both legs lack non-rate-limited
        # prices (pot.py:487-503), while new records an unpriced spend row with NULL PnL.
        assert len(diff.old_missing_prices) == 0
        assert diff.new_unpriced_events == 1
        unpriced_rows = [
            row for row in diff.new_cost_basis_rows
            if row['group_identifier'] == 'swap-no-prices' and row['direction'] == 'spend'
        ]
        assert len(unpriced_rows) == 1
        assert unpriced_rows[0]['realized_pnl'] is None
    else:
        diff.assert_expected_divergence(
            reason=(
                'DELIBERATE: unpriced standalone spend consumes lot-1 ($1000) and stores '
                'NULL realized_pnl in new pipeline (cost_basis.py:550,618), whereas legacy '
                'skips the spend and leaves lot-1 untouched for the subsequent sell'
            ),
            old_taxable=FVal('1000'),
            new_taxable=FVal('800'),
            per_asset={A_ETH.identifier: (FVal('1000'), ZERO, FVal('800'), ZERO)},
        )
        assert len(diff.old_missing_prices) == 1
        assert diff.new_unpriced_events == 1


# ---------------------------------------------------------------------------
# 11. transfer_missing_history
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('transfer_kind', [
    'transfer',
    'basis_transfer_same_bucket',
    'basis_transfer_distinct_asset',
])
def test_transfer_missing_history(database: DBHandler, transfer_kind: str) -> None:
    """Transfer / BASIS_TRANSFER of 5 ETH when source bucket only has 2 ETH."""
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=100,
            group_id='buy-2-eth',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_USD, '2000'),
            receive=(A_ETH, '2'),
        ),
    ]
    extra_rules: tuple[RuleSpec, ...] = ()
    if transfer_kind == 'transfer':
        events.extend([
            evm_event(
                at=200,
                amount='5',
                event_type=HistoryEventType.TRANSFER,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                location=LOCATION_ETHEREUM,
                location_label=DEFAULT_EVM_ADDRESS,
                address=SECOND_EVM_ADDRESS,
            ),
            *swap_group(
                at=300,
                group_id='sell-5-eth',
                location=LOCATION_ETHEREUM,
                location_label=SECOND_EVM_ADDRESS,
                spend=(A_ETH, '5'),
                receive=(A_USD, '10000'),
            ),
        ])
    else:
        dest_asset = A_WETH if transfer_kind == 'basis_transfer_same_bucket' else A_DAI
        wrap_tx = make_evm_tx_hash()
        extra_rules = (
            RuleSpec(
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
                taxable=False,
                accounting_treatment=TxAccountingTreatment.BASIS_TRANSFER,
            ),
        )
        events.extend([
            evm_event(
                at=200,
                amount='5',
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
                asset=A_ETH,
                location=LOCATION_ETHEREUM,
                location_label=DEFAULT_EVM_ADDRESS,
                tx_ref=wrap_tx,
                sequence_index=0,
            ),
            evm_event(
                at=200,
                amount='5',
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                asset=dest_asset,
                location=LOCATION_ETHEREUM,
                location_label=DEFAULT_EVM_ADDRESS,
                tx_ref=wrap_tx,
                sequence_index=1,
            ),
            *swap_group(
                at=300,
                group_id='sell-5-dest',
                location=LOCATION_ETHEREUM,
                location_label=DEFAULT_EVM_ADDRESS,
                spend=(dest_asset, '5'),
                receive=(A_USD, '10000'),
            ),
        ])

    scenario = ParityScenario(
        id=f'transfer_missing_history_{transfer_kind}',
        events=events,
        prices={
            (A_USD, ts(100)): Price(FVal('1')),
            (A_ETH, ts(100)): Price(FVal('1000')),
            (A_ETH, ts(200)): Price(FVal('1500')),
            (A_WETH, ts(200)): Price(FVal('1500')),
            (A_DAI, ts(200)): Price(FVal('1500')),
            (A_ETH, ts(300)): Price(FVal('2000')),
            (A_WETH, ts(300)): Price(FVal('2000')),
            (A_DAI, ts(300)): Price(FVal('2000')),
            (A_USD, ts(300)): Price(FVal('1')),
        },
        blockchain_accounts=(
            BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=DEFAULT_EVM_ADDRESS),
            BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=SECOND_EVM_ADDRESS),
        ),
        settings={'taxfree_after_period': -1},
        rules=extra_rules,
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    if transfer_kind in ('transfer', 'basis_transfer_same_bucket'):
        diff.assert_parity()
        assert diff.old_taxable == FVal('8000')
        assert diff.old_free == ZERO
    else:
        diff.assert_expected_divergence(
            reason=(
                'DELIBERATE: distinct-asset BASIS_TRANSFER with uncovered 3 units creates a '
                'ZERO-basis lot in new pipeline (cost_basis.py:379-385), whereas legacy adds '
                'an oracle-priced acquisition at $1500 (history_base_entries.py:155-165)'
            ),
            old_taxable=FVal('3500'),
            new_taxable=FVal('8000'),
            per_asset={A_DAI.identifier: (FVal('3500'), ZERO, FVal('8000'), ZERO)},
        )


# ---------------------------------------------------------------------------
# 12. multi_year_windowed_tax_years
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(('method', 'tax_year', 'expected_taxable', 'expected_free'), [
    (CostBasisMethod.FIFO, 2024, FVal('835'), FVal('3040')),
    (CostBasisMethod.FIFO, 2025, FVal('-30'), FVal('3550')),
    (CostBasisMethod.LIFO, 2024, FVal('2855'), ZERO),
    (CostBasisMethod.LIFO, 2025, FVal('290'), FVal('3200')),
    (CostBasisMethod.HIFO, 2024, FVal('1855'), ZERO),
    (CostBasisMethod.HIFO, 2025, FVal('290'), FVal('4200')),
    (CostBasisMethod.ACB, 2024, FVal('2917.222222222222222222222222'), ZERO),
    (CostBasisMethod.ACB, 2025, FVal('4236.666666666666666666666667'), ZERO),
])
def test_multi_year_windowed_tax_years(
        database: DBHandler,
        method: CostBasisMethod,
        tax_year: int,
        expected_taxable: FVal,
        expected_free: FVal,
) -> None:
    """Acquisitions in 2023, partial sells/rewards/fees in 2024, remaining sells in 2025."""
    t_2023_jan = Timestamp(1_673_740_800)  # 2023-01-15
    t_2023_jun = Timestamp(1_686_787_200)  # 2023-06-15
    t_2023_nov = Timestamp(1_700_006_400)  # 2023-11-15
    t_2024_mar = Timestamp(1_710_460_800)  # 2024-03-15
    t_2024_jul = Timestamp(1_721_001_600)  # 2024-07-15
    t_2024_oct = Timestamp(1_728_950_400)  # 2024-10-15
    t_2025_feb = Timestamp(1_739_577_600)  # 2025-02-15

    windows = {
        2024: (Timestamp(1_704_067_200), Timestamp(1_735_689_599)),
        2025: (Timestamp(1_735_689_600), Timestamp(1_767_225_599)),
    }
    start_ts, end_ts = windows[tax_year]

    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=t_2023_jan,
            group_id='2023-buy-1',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_USD, '2000'),
            receive=(A_ETH, '2'),
        ),
        *swap_group(
            at=t_2023_jun,
            group_id='2023-buy-2',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_USD, '4000'),
            receive=(A_ETH, '2'),
        ),
        *swap_group(
            at=t_2023_nov,
            group_id='2023-buy-3',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_USD, '3000'),
            receive=(A_ETH, '2'),
        ),
        *swap_group(
            at=t_2024_mar,
            group_id='2024-sell-1',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_ETH, '2'),
            receive=(A_USD, '5000'),
            fee=(A_USD, '25'),
        ),
        evm_event(
            at=t_2024_jul,
            amount='0.5',
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ETH,
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
        ),
        evm_event(
            at=t_2024_oct,
            amount='0.1',
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            counterparty=CPT_GAS,
        ),
        *swap_group(
            at=t_2025_feb,
            group_id='2025-sell-1',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_ETH, '3'),
            receive=(A_USD, '9000'),
            fee=(A_USD, '30'),
        ),
    ]
    scenario = ParityScenario(
        id=f'multi_year_{tax_year}_{method.name}',
        events=events,
        prices={
            (A_USD, t_2023_jan): Price(FVal('1')),
            (A_ETH, t_2023_jan): Price(FVal('1000')),
            (A_USD, t_2023_jun): Price(FVal('1')),
            (A_ETH, t_2023_jun): Price(FVal('2000')),
            (A_USD, t_2023_nov): Price(FVal('1')),
            (A_ETH, t_2023_nov): Price(FVal('1500')),
            (A_USD, t_2024_mar): Price(FVal('1')),
            (A_ETH, t_2024_mar): Price(FVal('2500')),
            (A_ETH, t_2024_jul): Price(FVal('2200')),
            (A_ETH, t_2024_oct): Price(FVal('2400')),
            (A_USD, t_2025_feb): Price(FVal('1')),
            (A_ETH, t_2025_feb): Price(FVal('3000')),
        },
        start_ts=start_ts,
        end_ts=end_ts,
        method=method,
        settings={
            'taxfree_after_period': -1 if method == CostBasisMethod.ACB else ONE_YEAR_SECS,
            'include_fees_in_cost_basis': False,
            'include_gas_costs': True,
        },
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    tolerance = FVal('1e-12') if method == CostBasisMethod.ACB else ZERO
    diff.assert_parity(tolerance=tolerance)
    assert abs(diff.old_taxable - expected_taxable) <= tolerance
    assert abs(diff.old_free - expected_free) <= tolerance
