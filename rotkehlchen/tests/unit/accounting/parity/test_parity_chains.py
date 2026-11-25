"""Old-vs-new PnL parity tests for multi-chain (L2, non-EVM, bridges) and prefork assets."""
from typing import TYPE_CHECKING, Final

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.accounting.structures import TxAccountingTreatment
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import (
    A_BCH,
    A_BSV,
    A_BTC,
    A_DOT,
    A_ETC,
    A_ETH,
    A_EUR,
    A_POL,
    A_SOL,
    A_USD,
    A_XDAI,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.bitcoin_event import BitcoinEvent
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.history.events.structures.solana_swap import SolanaSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import (
    LOCATION_ARBITRUM_ONE,
    LOCATION_BASE,
    LOCATION_BITCOIN,
    LOCATION_ETHEREUM,
    LOCATION_GNOSIS,
    LOCATION_KRAKEN,
    LOCATION_OPTIMISM,
    LOCATION_POLKADOT,
    LOCATION_POLYGON_POS,
)
from rotkehlchen.tests.unit.accounting.parity.harness import (
    DEFAULT_EVM_ADDRESS,
    ParityScenario,
    RuleSpec,
    evm_event,
    history_event,
    run_parity_scenario,
    swap_group,
    to_ts,
    to_ts_ms,
    ts,
)
from rotkehlchen.tests.utils.factories import (
    UNIT_BTC_ADDRESS1,
    make_btc_tx_id,
    make_evm_tx_hash,
    make_solana_address,
    make_solana_signature,
)
from rotkehlchen.types import CostBasisMethod, Price, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.locations.types import LocationIdentifier

pytestmark = pytest.mark.accounting_update

A_SOL_USDC: Final = Asset('solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')
ONE_YEAR_SECS: Final = 365 * 86400
ONE_DAY_SECS: Final = 86400


@pytest.mark.parametrize(
    ('chain_name', 'location', 'gas_asset'),
    [
        ('arbitrum_one', LOCATION_ARBITRUM_ONE, A_ETH),
        ('optimism', LOCATION_OPTIMISM, A_ETH),
        ('base', LOCATION_BASE, A_ETH),
        ('polygon_pos', LOCATION_POLYGON_POS, A_POL),
        ('gnosis', LOCATION_GNOSIS, A_XDAI),
    ],
)
@pytest.mark.parametrize('include_gas_costs', [True, False])
def test_l2_native_gas_fees(
        database: DBHandler,
        chain_name: str,
        location: LocationIdentifier,
        gas_asset: Asset,
        include_gas_costs: bool,
) -> None:
    """Swaps + native gas SPEND/FEE across L2 chains with include_gas_costs True and False."""
    swap_tx = make_evm_tx_hash()
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=10,
            group_id=f'buy1-{chain_name}',
            location=location,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_USD, '1000'),
            receive=(gas_asset, '1'),
        ),
        *swap_group(
            at=15,
            group_id=f'buy2-{chain_name}',
            location=location,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_USD, '1200'),
            receive=(gas_asset, '1'),
        ),
        evm_event(
            at=18,
            amount='0.1',
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=gas_asset,
            location=location,
            location_label=DEFAULT_EVM_ADDRESS,
            sequence_index=0,
            counterparty=CPT_GAS,
        ),
        *swap_group(
            at=20,
            group_id=f'sell-{chain_name}',
            location=location,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(gas_asset, '1'),
            receive=(A_USD, '1500'),
            tx_ref=swap_tx,
            sequence_offset=0,
        ),
    ]
    scenario = ParityScenario(
        id=f'l2_native_gas_fees_{chain_name}_gas_{include_gas_costs}',
        events=events,
        prices={
            (gas_asset, ts(10)): Price(FVal('1000')),
            (gas_asset, ts(15)): Price(FVal('1200')),
            (gas_asset, ts(18)): Price(FVal('1500')),
            (gas_asset, ts(20)): Price(FVal('1500')),
            (A_USD, ts(10)): Price(ONE),
            (A_USD, ts(15)): Price(ONE),
            (A_USD, ts(20)): Price(ONE),
        },
        start_ts=ts(0),
        end_ts=ts(100),
        method=CostBasisMethod.FIFO,
        settings={
            'include_gas_costs': include_gas_costs,
            'include_fees_in_cost_basis': False,
            'taxfree_after_period': None,
        },
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    # Gas 0.1 @ 1500 consumes 0.1 of lot 1 (basis 100): disposal +50, expense -150 -> net -100
    # when included, 0 when excluded. Sell 1 @ 1500 consumes 0.9 @ 1000 + 0.1 @ 1200 = 1020 (+480).
    expected_taxable = FVal('380') if include_gas_costs else FVal('480')
    assert diff.old_taxable == expected_taxable
    assert diff.new_taxable == expected_taxable
    assert diff.old_free == ZERO
    assert diff.new_free == ZERO


def test_cross_chain_bridge_basis_transfer(database: DBHandler) -> None:
    """Buy ETH on Ethereum, bridge via BASIS_TRANSFER to Arbitrum, sell before & after 1 year."""
    t_buy = 0
    t_bridge = 200 * ONE_DAY_SECS
    t_sell_taxable = 250 * ONE_DAY_SECS
    t_sell_taxfree = 400 * ONE_DAY_SECS

    bridge_group = 'bridge-eth-to-arb-1'
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=t_buy,
            group_id='buy-eth-mainnet',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_USD, '2000'),
            receive=(A_ETH, '2'),
        ),
        evm_event(
            at=t_bridge,
            amount='2',
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            sequence_index=0,
            group_identifier=bridge_group,
        ),
        evm_event(
            at=t_bridge,
            amount='2',
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            location=LOCATION_ARBITRUM_ONE,
            location_label=DEFAULT_EVM_ADDRESS,
            sequence_index=1,
            group_identifier=bridge_group,
        ),
        *swap_group(
            at=t_sell_taxable,
            group_id='sell-eth-arb-1',
            location=LOCATION_ARBITRUM_ONE,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_ETH, '1'),
            receive=(A_USD, '1600'),
        ),
        *swap_group(
            at=t_sell_taxfree,
            group_id='sell-eth-arb-2',
            location=LOCATION_ARBITRUM_ONE,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_ETH, '1'),
            receive=(A_USD, '1800'),
        ),
    ]
    scenario = ParityScenario(
        id='cross_chain_bridge_basis_transfer',
        events=events,
        prices={
            (A_ETH, ts(t_buy)): Price(FVal('1000')),
            (A_ETH, ts(t_bridge)): Price(FVal('1300')),
            (A_ETH, ts(t_sell_taxable)): Price(FVal('1600')),
            (A_ETH, ts(t_sell_taxfree)): Price(FVal('1800')),
            (A_USD, ts(t_buy)): Price(ONE),
            (A_USD, ts(t_sell_taxable)): Price(ONE),
            (A_USD, ts(t_sell_taxfree)): Price(ONE),
        },
        start_ts=ts(0),
        end_ts=ts(t_sell_taxfree + 100),
        method=CostBasisMethod.FIFO,
        settings={'taxfree_after_period': ONE_YEAR_SECS},
        rules=[
            RuleSpec(
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                accounting_treatment=TxAccountingTreatment.SWAP,
            ),
            RuleSpec(
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.BRIDGE,
                taxable=False,
                accounting_treatment=TxAccountingTreatment.BASIS_TRANSFER,
            ),
        ],
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    assert diff.old_taxable == FVal('600')
    assert diff.new_taxable == FVal('600')
    assert diff.old_free == FVal('800')
    assert diff.new_free == FVal('800')


def test_same_address_two_evm_chains(database: DBHandler) -> None:
    """Deliberate divergence (#2438): same EVM address on Ethereum vs Arbitrum uses separate buckets."""  # noqa: E501
    events: list[HistoryBaseEntry] = [
        evm_event(
            at=10,
            amount='1',
            event_type=HistoryEventType.RECEIVE,
            asset=A_ETH,
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
        ),
        evm_event(
            at=20,
            amount='1',
            event_type=HistoryEventType.RECEIVE,
            asset=A_ETH,
            location=LOCATION_ARBITRUM_ONE,
            location_label=DEFAULT_EVM_ADDRESS,
        ),
        evm_event(
            at=30,
            amount='1',
            event_type=HistoryEventType.SPEND,
            asset=A_ETH,
            location=LOCATION_ARBITRUM_ONE,
            location_label=DEFAULT_EVM_ADDRESS,
        ),
    ]
    scenario = ParityScenario(
        id='same_address_two_evm_chains',
        events=events,
        prices={
            (A_ETH, ts(10)): Price(FVal('1000')),
            (A_ETH, ts(20)): Price(FVal('2000')),
            (A_ETH, ts(30)): Price(FVal('2500')),
        },
        start_ts=ts(0),
        end_ts=ts(100),
        method=CostBasisMethod.FIFO,
        settings={'taxfree_after_period': None},
        rules=[
            RuleSpec(event_type=HistoryEventType.RECEIVE, taxable=False),
            RuleSpec(event_type=HistoryEventType.SPEND, taxable=True),
        ],
    )
    diff = run_parity_scenario(database, scenario)
    # Legacy global pot FIFO consumes the Ethereum $1000 lot (+1500);
    # new per-bucket FIFO isolates by (location, address) and consumes Arbitrum $2000 lot (+500).
    diff.assert_expected_divergence(
        reason=(
            'DELIBERATE: per-bucket lot isolation by (location, address) '
            'vs legacy global pot (#2438)'
        ),
        old_taxable=FVal('1500'),
        new_taxable=FVal('500'),
        per_asset={A_ETH.identifier: (FVal('1500'), ZERO, FVal('500'), ZERO)},
    )


@pytest.mark.parametrize('include_gas_costs', [True, False])
def test_bitcoin_utxo_spend_and_fee(database: DBHandler, include_gas_costs: bool) -> None:
    """Bitcoin OnchainEvent receive, spend, and separate network fee SPEND/FEE."""
    receive_tx = make_btc_tx_id()
    spend_tx = make_btc_tx_id()
    events: list[HistoryBaseEntry] = [
        BitcoinEvent(
            tx_ref=receive_tx,
            sequence_index=0,
            timestamp=to_ts_ms(10),
            location=LOCATION_BITCOIN,
            location_label=UNIT_BTC_ADDRESS1,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_BTC,
            amount=FVal('2'),
        ),
        BitcoinEvent(
            tx_ref=spend_tx,
            sequence_index=0,
            timestamp=to_ts_ms(20),
            location=LOCATION_BITCOIN,
            location_label=UNIT_BTC_ADDRESS1,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_BTC,
            amount=FVal('1'),
        ),
        BitcoinEvent(
            tx_ref=spend_tx,
            sequence_index=1,
            timestamp=to_ts_ms(20),
            location=LOCATION_BITCOIN,
            location_label=UNIT_BTC_ADDRESS1,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_BTC,
            amount=FVal('0.001'),
            counterparty=CPT_GAS,
        ),
    ]
    scenario = ParityScenario(
        id=f'bitcoin_utxo_spend_and_fee_gas_{include_gas_costs}',
        events=events,
        prices={
            (A_BTC, ts(10)): Price(FVal('20000')),
            (A_BTC, ts(20)): Price(FVal('30000')),
        },
        start_ts=ts(0),
        end_ts=ts(100),
        method=CostBasisMethod.FIFO,
        settings={
            'include_gas_costs': include_gas_costs,
            'taxfree_after_period': None,
        },
        use_default_rules=True,
        rules=[
            RuleSpec(event_type=HistoryEventType.RECEIVE, taxable=False),
            RuleSpec(event_type=HistoryEventType.SPEND, taxable=True),
        ],
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    # Spend 1 BTC: 30000 - 20000 = +10000.
    # Fee 0.001 BTC @ 30000 (basis 20): disposal +10, expense -30 -> net -20 when included.
    expected_taxable = FVal('9980') if include_gas_costs else FVal('10000')
    assert diff.old_taxable == expected_taxable
    assert diff.new_taxable == expected_taxable
    assert diff.old_free == ZERO
    assert diff.new_free == ZERO


@pytest.mark.parametrize('include_fees_in_cost_basis', [False, True])
def test_solana_swap_and_staking_reward(
        database: DBHandler,
        include_fees_in_cost_basis: bool,
) -> None:
    """Solana receive, SPL swap with SOL fee, STAKING/REWARD, and subsequent SOL sale."""
    sol_addr = make_solana_address()
    rx_sig = make_solana_signature()
    swap_sig = make_solana_signature()
    stake_sig = make_solana_signature()
    sell_sig = make_solana_signature()

    events: list[HistoryBaseEntry] = [
        SolanaEvent(
            tx_ref=rx_sig,
            sequence_index=0,
            timestamp=to_ts_ms(10),
            location_label=sol_addr,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_SOL,
            amount=FVal('10'),
        ),
        SolanaSwapEvent(
            tx_ref=swap_sig,
            sequence_index=0,
            timestamp=to_ts_ms(20),
            location_label=sol_addr,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_SOL,
            amount=FVal('4'),
        ),
        SolanaSwapEvent(
            tx_ref=swap_sig,
            sequence_index=1,
            timestamp=to_ts_ms(20),
            location_label=sol_addr,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_SOL_USDC,
            amount=FVal('320'),
        ),
        SolanaSwapEvent(
            tx_ref=swap_sig,
            sequence_index=2,
            timestamp=to_ts_ms(20),
            location_label=sol_addr,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_SOL,
            amount=FVal('0.01'),
        ),
        SolanaEvent(
            tx_ref=stake_sig,
            sequence_index=0,
            timestamp=to_ts_ms(30),
            location_label=sol_addr,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_SOL,
            amount=FVal('2'),
        ),
        SolanaSwapEvent(
            tx_ref=sell_sig,
            sequence_index=0,
            timestamp=to_ts_ms(40),
            location_label=sol_addr,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_SOL,
            amount=FVal('7'),
        ),
        SolanaSwapEvent(
            tx_ref=sell_sig,
            sequence_index=1,
            timestamp=to_ts_ms(40),
            location_label=sol_addr,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_SOL_USDC,
            amount=FVal('840'),
        ),
    ]
    scenario = ParityScenario(
        id=f'solana_swap_and_staking_reward_fee_in_basis_{include_fees_in_cost_basis}',
        events=events,
        prices={
            (A_SOL, ts(10)): Price(FVal('50')),
            (A_SOL, ts(20)): Price(FVal('80')),
            (A_SOL_USDC, ts(20)): Price(ONE),
            (A_SOL, ts(30)): Price(FVal('100')),
            (A_SOL, ts(40)): Price(FVal('120')),
            (A_SOL_USDC, ts(40)): Price(ONE),
        },
        start_ts=ts(0),
        end_ts=ts(100),
        method=CostBasisMethod.FIFO,
        settings={
            'include_fees_in_cost_basis': include_fees_in_cost_basis,
            'taxfree_after_period': None,
        },
        use_default_rules=True,
        rules=[
            RuleSpec(event_type=HistoryEventType.RECEIVE, taxable=False),
        ],
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    # Swap 4 SOL @ 80 (basis 50): +120; 0.01 SOL fee @ 80 (basis 50):
    #   fee_in_basis=False -> disposal +0.30, expense -0.80 (net -0.50);
    #   fee_in_basis=True  -> fee event is non-taxable (0 PnL; 0.80 folded into SPL-USDC basis);
    # Staking reward 2 SOL @ 100: +200;
    # Sell 7 SOL @ 120: 5.99 * (120 - 50) + 1.01 * (120 - 100) = 419.30 + 20.20 = +439.50.
    expected_taxable = FVal('759.5') if include_fees_in_cost_basis else FVal('759')
    assert diff.old_taxable == expected_taxable
    assert diff.new_taxable == expected_taxable
    assert diff.old_free == ZERO
    assert diff.new_free == ZERO


def test_substrate_polkadot_staking_reward(database: DBHandler) -> None:
    """Polkadot receive DOT, STAKING/REWARD DOT, and subsequent disposal."""
    dot_addr = '15oF4uVJwmo4TdGW7VfQxNLavjCXviqxT9S1MgbjMNHr6Sp5'
    events: list[HistoryBaseEntry] = [
        history_event(
            at=10,
            location=LOCATION_POLKADOT,
            location_label=dot_addr,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_DOT,
            amount='100',
        ),
        history_event(
            at=20,
            location=LOCATION_POLKADOT,
            location_label=dot_addr,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_DOT,
            amount='20',
        ),
        history_event(
            at=30,
            location=LOCATION_POLKADOT,
            location_label=dot_addr,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_DOT,
            amount='110',
        ),
    ]
    scenario = ParityScenario(
        id='substrate_polkadot_staking_reward',
        events=events,
        prices={
            (A_DOT, ts(10)): Price(FVal('5')),
            (A_DOT, ts(20)): Price(FVal('8')),
            (A_DOT, ts(30)): Price(FVal('10')),
        },
        start_ts=ts(0),
        end_ts=ts(100),
        method=CostBasisMethod.FIFO,
        settings={'taxfree_after_period': None},
        use_default_rules=True,
        rules=[
            RuleSpec(event_type=HistoryEventType.RECEIVE, taxable=False),
            RuleSpec(event_type=HistoryEventType.SPEND, taxable=True),
        ],
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    # Staking income: 20 * 8 = +160; disposal: 100 * (10 - 5) + 10 * (10 - 8) = +520; total = 680.
    assert diff.old_taxable == FVal('680')
    assert diff.new_taxable == FVal('680')
    assert diff.old_free == ZERO
    assert diff.new_free == ZERO


def test_prefork_eth_etc_daofork(database: DBHandler) -> None:
    """Buy/sell ETH before DAO fork, sell ETC & ETH after fork (mirrors test_prefork_assets.py)."""
    t1 = Timestamp(1446979735)  # 2015-11-08 (pre-fork)
    t2 = Timestamp(1461021812)  # 2016-04-18 (pre-fork)
    t3 = Timestamp(1481979135)  # 2016-12-17 (post-fork, >1yr)
    t4 = Timestamp(1482138141)  # 2016-12-19 (post-fork, >1yr)

    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=t1,
            group_id='eth-buy-prefork',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_EUR, FVal('0.2315893') * FVal(1450)),
            receive=(A_ETH, FVal(1450)),
        ),
        *swap_group(
            at=t2,
            group_id='eth-sell-prefork',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_ETH, FVal(50)),
            receive=(A_EUR, FVal('7.88') * FVal(50)),
            fee=(A_EUR, FVal('0.5215')),
        ),
        *swap_group(
            at=t3,
            group_id='etc-sell-postfork',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_ETC, FVal(550)),
            receive=(A_EUR, FVal('1.78') * FVal(550)),
            fee=(A_EUR, FVal('0.9375')),
        ),
        *swap_group(
            at=t4,
            group_id='eth-sell-postfork',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_ETH, FVal(10)),
            receive=(A_EUR, FVal('7.45') * FVal(10)),
            fee=(A_EUR, FVal('0.12')),
        ),
    ]
    scenario = ParityScenario(
        id='prefork_eth_etc_daofork',
        events=events,
        prices={
            (A_ETH, to_ts(t1)): Price(FVal('0.2315893')),
            (A_ETH, to_ts(t2)): Price(FVal('7.88')),
            (A_ETC, to_ts(t3)): Price(FVal('1.78')),
            (A_ETH, to_ts(t4)): Price(FVal('7.45')),
            (A_EUR, to_ts(t1)): Price(ONE),
            (A_EUR, to_ts(t2)): Price(ONE),
            (A_EUR, to_ts(t3)): Price(ONE),
            (A_EUR, to_ts(t4)): Price(ONE),
        },
        start_ts=Timestamp(1436979735),
        end_ts=Timestamp(1495751688),
        method=CostBasisMethod.FIFO,
        settings={
            'main_currency': A_EUR,
            'include_fees_in_cost_basis': False,
            'taxfree_after_period': ONE_YEAR_SECS,
        },
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    # Legacy AccountingPot invokes handle_prefork_asset_acquisitions/spends (pot.py:260,350),
    # giving 550 ETC the pre-fork ETH basis (0.2315893 EUR @ 2015-11-08 -> +851.625885 tax-free).
    # New process_cost_basis (tasks/cost_basis.py) does not wire prefork.py yet, so ETC sells
    # with zero basis as taxable (+979 EUR). ETH and EUR match identically.
    diff.assert_expected_divergence(
        reason=(
            'KNOWN_GAP: prefork_lots (rotkehlchen/accounting/cost_basis/prefork.py) '
            'not yet wired into tasks/cost_basis.py'
        ),
        old_taxable=FVal('380.841535'),
        old_free=FVal('923.809992'),
        new_taxable=FVal('1359.841535'),
        new_free=FVal('72.184107'),
        per_asset={
            A_ETC.identifier: (ZERO, FVal('851.625885'), FVal('979'), ZERO),
            A_ETH.identifier: (
                FVal('382.420535'),
                FVal('72.184107'),
                FVal('382.420535'),
                FVal('72.184107'),
            ),
            A_EUR.identifier: (FVal('-1.579'), ZERO, FVal('-1.579'), ZERO),
        },
    )


def test_prefork_btc_bch_bsv(database: DBHandler) -> None:
    """Buy/sell BTC before BCH fork, trade BCH before/after BSV fork, sell BSV after BSV fork."""
    t1 = Timestamp(1491593374)  # 2017-04-07 (pre-BCH-fork)
    t2 = Timestamp(1500595200)  # 2017-07-21 (pre-BCH-fork)
    t3 = Timestamp(1512693374)  # 2017-12-08 (post-BCH, pre-BSV)
    t4 = Timestamp(1514937600)  # 2018-01-03 (post-BCH, pre-BSV)
    t5 = Timestamp(1524937600)  # 2018-04-28 (pre-BSV, >1yr from t1)
    t6 = Timestamp(1525937600)  # 2018-05-10 (pre-BSV, >1yr from t1)
    t7 = Timestamp(1552304352)  # 2019-03-11 (post-BSV, >1yr from t1)
    t8 = Timestamp(1552400000)  # 2019-03-12 (post-BSV, >1yr from t1)

    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=t1,
            group_id='btc-buy-prefork',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_EUR, FVal('1128.905') * FVal('6.5')),
            receive=(A_BTC, FVal('6.5')),
            fee=(A_EUR, FVal('0.55')),
        ),
        *swap_group(
            at=t2,
            group_id='btc-sell-prefork',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_BTC, FVal('0.5')),
            receive=(A_EUR, FVal('2380.835') * FVal('0.5')),
            fee=(A_EUR, FVal('0.15')),
        ),
        *swap_group(
            at=t3,
            group_id='bch-sell-post-bch-fork',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_BCH, FVal('2.1')),
            receive=(A_EUR, FVal('995.935') * FVal('2.1')),
            fee=(A_EUR, FVal('0.26')),
        ),
        *swap_group(
            at=t4,
            group_id='btc-sell-post-bch-fork',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_BTC, FVal('1.2')),
            receive=(A_EUR, FVal('12404.88') * FVal('1.2')),
            fee=(A_EUR, FVal('0.52')),
        ),
        *swap_group(
            at=t5,
            group_id='bch-buy-pre-bsv-fork',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_EUR, FVal('1146.98')),
            receive=(A_BCH, ONE),
            fee=(A_EUR, FVal('0.52')),
        ),
        *swap_group(
            at=t6,
            group_id='bch-sell-pre-bsv-fork',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_BCH, FVal('0.3')),
            receive=(A_EUR, FVal('1272.05') * FVal('0.3')),
            fee=(A_EUR, FVal('0.52')),
        ),
        *swap_group(
            at=t7,
            group_id='bch-sell-post-bsv-fork',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_BCH, FVal('0.5')),
            receive=(A_EUR, FVal('114.27') * FVal('0.5')),
            fee=(A_EUR, FVal('0.52')),
        ),
        *swap_group(
            at=t8,
            group_id='bsv-sell-post-bsv-fork',
            location=LOCATION_KRAKEN,
            location_label=None,
            spend=(A_BSV, ONE),
            receive=(A_EUR, FVal('60')),
            fee=(A_EUR, FVal('0.50')),
        ),
    ]
    scenario = ParityScenario(
        id='prefork_btc_bch_bsv',
        events=events,
        prices={
            (A_BTC, to_ts(t1)): Price(FVal('1128.905')),
            (A_BTC, to_ts(t2)): Price(FVal('2380.835')),
            (A_BCH, to_ts(t3)): Price(FVal('995.935')),
            (A_BTC, to_ts(t4)): Price(FVal('12404.88')),
            (A_BCH, to_ts(t5)): Price(FVal('1146.98')),
            (A_BCH, to_ts(t6)): Price(FVal('1272.05')),
            (A_BCH, to_ts(t7)): Price(FVal('114.27')),
            (A_BSV, to_ts(t8)): Price(FVal('60')),
        },
        default_prices={A_EUR: Price(ONE)},
        start_ts=Timestamp(1436979735),
        end_ts=Timestamp(1569693374),
        method=CostBasisMethod.FIFO,
        settings={
            'main_currency': A_EUR,
            'include_fees_in_cost_basis': False,
            'taxfree_after_period': ONE_YEAR_SECS,
        },
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    # Legacy AccountingPot creates prefork BCH & BSV lots from the 2017-04-07 BTC buy
    # (1128.905 EUR) and BSV from the 2018-04-28 BCH buy (pot.py:260,350).
    # New process_cost_basis (tasks/cost_basis.py) lacks prefork lot wiring, so post-fork BCH
    # (before the t5 buy) and BSV sell with zero basis, and t6/t7 BCH sells consume the t5 buy
    # as taxable instead of the >1yr prefork lot as tax-free. BTC and EUR match identically.
    diff.assert_expected_divergence(
        reason=(
            'KNOWN_GAP: prefork_lots (rotkehlchen/accounting/cost_basis/prefork.py) '
            'not yet wired into tasks/cost_basis.py'
        ),
        old_taxable=FVal('13874.358'),
        old_free=FVal('-1533.279'),
        new_taxable=FVal('15826.2245'),
        new_free=ZERO,
        per_asset={
            A_BCH.identifier: (FVal('-279.237'), FVal('-464.374'), FVal('1612.6295'), ZERO),
            A_BSV.identifier: (ZERO, FVal('-1068.905'), FVal('60'), ZERO),
            A_BTC.identifier: (FVal('14157.135'), ZERO, FVal('14157.135'), ZERO),
            A_EUR.identifier: (FVal('-3.54'), ZERO, FVal('-3.54'), ZERO),
        },
    )
