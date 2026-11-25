"""Old-vs-new PnL parity tests for DeFi protocol events (Stage 2, Shard 1)."""
from typing import TYPE_CHECKING, Final

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.liquity.constants import CPT_LIQUITY
from rotkehlchen.chain.ethereum.modules.makerdao.constants import CPT_DSR, CPT_VAULT
from rotkehlchen.chain.evm.accounting.structures import TxAccountingTreatment
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V2
from rotkehlchen.chain.evm.decoding.cowswap.constants import CPT_COWSWAP
from rotkehlchen.chain.evm.decoding.paraswap.constants import CPT_PARASWAP
from rotkehlchen.chain.evm.decoding.thegraph.constants import CPT_THEGRAPH
from rotkehlchen.chain.evm.decoding.weth.constants import CPT_WETH
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_GRT, A_USD, A_USDC, A_WBTC, A_WETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ETHEREUM
from rotkehlchen.tests.unit.accounting.parity.harness import (
    DEFAULT_EVM_ADDRESS,
    ParityScenario,
    RuleSpec,
    evm_event,
    run_parity_scenario,
    swap_group,
    ts,
)
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import Price

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

pytestmark = pytest.mark.accounting_update

A_ADAI: Final = Asset('eip155:1/erc20:0x028171bCA77440897B824Ca71D1c56caC55b68A3')
SECONDS_PER_DAY: Final = 86_400
ONE_YEAR_SECONDS: Final = 365 * SECONDS_PER_DAY
TAXFREE_DISABLED: Final = -1


@pytest.mark.parametrize(
    'run_balance_pass',
    [False, True],
    ids=['no_balance_pass', 'balance_pass'],
)
def test_aave_v2_deposit_withdraw_profit(
        database: DBHandler,
        run_balance_pass: bool,
) -> None:
    """Deposit 100 DAI to Aave v2 and withdraw 120 DAI (+20 DAI interest gain).

    KNOWN_GAP: Legacy `Aavev2Accountant._process_withdraw` emits a synthetic +20 DAI
    taxable gain on `WITHDRAWAL/REDEEM_WRAPPED`, whereas `process_cost_basis` has no
    protocol accountant callbacks and `process_historical_balances` does not synthesize
    profit events for wrapped rebasing receipt tokens (`DEPOSIT_FOR_WRAPPED`/`REDEEM_WRAPPED`).
    """
    deposit_tx = make_evm_tx_hash()
    withdraw_tx = make_evm_tx_hash()
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=10,
            group_id='buy-dai',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_USD, '100'),
            receive=(A_DAI, '100'),
        ),
        evm_event(
            at=20,
            amount='100',
            asset=A_DAI,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            tx_ref=deposit_tx,
            sequence_index=0,
            counterparty=CPT_AAVE_V2,
            notes='Deposit 100 DAI into AAVE v2',
        ),
        evm_event(
            at=20,
            amount='100',
            asset=A_ADAI,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            tx_ref=deposit_tx,
            sequence_index=1,
            counterparty=CPT_AAVE_V2,
            notes='Receive 100 aDAI from AAVE v2',
        ),
        evm_event(
            at=30,
            amount='120',
            asset=A_ADAI,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            tx_ref=withdraw_tx,
            sequence_index=0,
            counterparty=CPT_AAVE_V2,
            notes='Return 120 aDAI to AAVE v2',
        ),
        evm_event(
            at=30,
            amount='120',
            asset=A_DAI,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            tx_ref=withdraw_tx,
            sequence_index=1,
            counterparty=CPT_AAVE_V2,
            notes='Withdraw 120 DAI from AAVE v2',
        ),
    ]
    scenario = ParityScenario(
        id=f'aave_v2_deposit_withdraw_profit[balance_pass={run_balance_pass}]',
        events=events,
        default_prices={
            A_DAI: Price(ONE),
            A_ADAI: Price(ONE),
            A_USD: Price(ONE),
        },
        settings={'auto_create_profit_events': True} if run_balance_pass else {},
        use_default_rules=True,
        use_real_evm_accountants=True,
        run_balance_pass=run_balance_pass,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_expected_divergence(
        reason=(
            'KNOWN_GAP: Aavev2Accountant._process_withdraw emits synthetic +20 DAI '
            'interest gain; unported in new cost_basis pipeline (and balance pass '
            'does not synthesize profit for DEPOSIT_FOR_WRAPPED/REDEEM_WRAPPED)'
        ),
        old_taxable=FVal('20'),
        new_taxable=ZERO,
        per_asset={A_DAI.identifier: (FVal('20'), ZERO, ZERO, ZERO)},
    )


def test_aave_v2_borrow_payback_loss(database: DBHandler) -> None:
    """Borrow 100 DAI on Aave v2 and payback 115 DAI (-15 DAI debt interest loss).

    KNOWN_GAP: Legacy `Aavev2Accountant._process_payback` emits a synthetic -15 DAI
    taxable debt loss; unported in new cost_basis pipeline.
    """
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=10,
            group_id='buy-dai-interest',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_USD, '15'),
            receive=(A_DAI, '15'),
        ),
        evm_event(
            at=20,
            amount='100',
            asset=A_DAI,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            counterparty=CPT_AAVE_V2,
            notes='Borrow 100 DAI from AAVE v2',
        ),
        evm_event(
            at=30,
            amount='115',
            asset=A_DAI,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            counterparty=CPT_AAVE_V2,
            notes='Repay 115 DAI on AAVE v2',
        ),
    ]
    scenario = ParityScenario(
        id='aave_v2_borrow_payback_loss',
        events=events,
        default_prices={A_DAI: Price(ONE), A_USD: Price(ONE)},
        use_default_rules=True,
        use_real_evm_accountants=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_expected_divergence(
        reason=(
            'KNOWN_GAP: Aavev2Accountant._process_payback emits synthetic -15 DAI '
            'debt loss; unported in new cost_basis pipeline'
        ),
        old_taxable=FVal('-15'),
        new_taxable=ZERO,
        per_asset={A_DAI.identifier: (FVal('-15'), ZERO, ZERO, ZERO)},
    )


@pytest.mark.parametrize(
    'run_balance_pass',
    [False, True],
    ids=['no_balance_pass', 'balance_pass'],
)
def test_makerdao_dsr_deposit_withdraw_profit(
        database: DBHandler,
        run_balance_pass: bool,
) -> None:
    """Deposit 1000 DAI to MakerDAO DSR and withdraw 1050 DAI (+50 DAI profit).

    Note: `DEPOSIT/DEPOSIT_TO_PROTOCOL` and `WITHDRAWAL/WITHDRAW_FROM_PROTOCOL` have
    `EventDirection.NEUTRAL`, so legacy `EventsAccountant.process()` skips them before
    invoking `MakerdaoAccountant._process_dsr_*`. Without `run_balance_pass`, both
    pipelines produce 0; with `run_balance_pass=True`, `process_historical_balances`
    synthesizes a +50 DAI `RECEIVE/REWARD` event and both pipelines produce +50 DAI.
    """
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=10,
            group_id='buy-dai-dsr',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_USD, '1000'),
            receive=(A_DAI, '1000'),
        ),
        evm_event(
            at=20,
            amount='1000',
            asset=A_DAI,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            counterparty=CPT_DSR,
            notes='Deposit 1000 DAI into MakerDAO DSR',
        ),
        evm_event(
            at=30,
            amount='1050',
            asset=A_DAI,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            counterparty=CPT_DSR,
            notes='Withdraw 1050 DAI from MakerDAO DSR',
        ),
    ]
    scenario = ParityScenario(
        id=f'makerdao_dsr_deposit_withdraw_profit[balance_pass={run_balance_pass}]',
        events=events,
        default_prices={A_DAI: Price(ONE), A_USD: Price(ONE)},
        settings={'auto_create_profit_events': True} if run_balance_pass else {},
        use_default_rules=True,
        use_real_evm_accountants=True,
        run_balance_pass=run_balance_pass,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    expected_taxable = FVal('50') if run_balance_pass else ZERO
    assert diff.old_taxable == expected_taxable
    assert diff.old_free == ZERO


def test_makerdao_vault_generate_payback_loss(database: DBHandler) -> None:
    """Generate 500 DAI from MakerDAO Vault CDP #1 and payback 525 DAI (-25 DAI loss).

    KNOWN_GAP: Legacy `MakerdaoAccountant._process_vault_dai_payback` emits a synthetic
    -25 DAI taxable debt loss; unported in new cost_basis pipeline.
    """
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=10,
            group_id='buy-dai-vault-fee',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_USD, '25'),
            receive=(A_DAI, '25'),
        ),
        evm_event(
            at=20,
            amount='500',
            asset=A_DAI,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            counterparty=CPT_VAULT,
            extra_data={'cdp_id': '1'},
            notes='Generate 500 DAI from MakerDAO Vault 1',
        ),
        evm_event(
            at=30,
            amount='525',
            asset=A_DAI,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            counterparty=CPT_VAULT,
            extra_data={'cdp_id': '1'},
            notes='Payback 525 DAI to MakerDAO Vault 1',
        ),
    ]
    scenario = ParityScenario(
        id='makerdao_vault_generate_payback_loss',
        events=events,
        default_prices={A_DAI: Price(ONE), A_USD: Price(ONE)},
        use_default_rules=True,
        use_real_evm_accountants=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_expected_divergence(
        reason=(
            'KNOWN_GAP: MakerdaoAccountant._process_vault_dai_payback emits synthetic '
            '-25 DAI debt loss; unported in new cost_basis pipeline'
        ),
        old_taxable=FVal('-25'),
        new_taxable=ZERO,
        per_asset={A_DAI.identifier: (FVal('-25'), ZERO, ZERO, ZERO)},
    )


@pytest.mark.parametrize(
    'run_balance_pass',
    [False, True],
    ids=['no_balance_pass', 'balance_pass'],
)
def test_thegraph_delegation_reward(
        database: DBHandler,
        run_balance_pass: bool,
) -> None:
    """Delegate 995 GRT (+5 GRT tax), undelegate 1005 GRT (+10 GRT reward).

    Without `run_balance_pass`: KNOWN_GAP because legacy `ThegraphAccountant._process_withdraw`
    emits +10 GRT reward while new pipeline lacks protocol callbacks (old=1005, new=995).
    With `run_balance_pass=True`: PARITY (both=1005) because `process_historical_balances`
    synthesizes the +10 GRT `RECEIVE/REWARD` and adjusts `REMOVE_ASSET` from 1005 to 995.
    """
    delegate_tx = make_evm_tx_hash()
    events: list[HistoryBaseEntry] = [
        evm_event(
            at=10,
            amount='1000',
            asset=A_GRT,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            notes='Acquire 1000 GRT',
        ),
        evm_event(
            at=20,
            amount='995',
            asset=A_GRT,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            tx_ref=delegate_tx,
            sequence_index=0,
            counterparty=CPT_THEGRAPH,
            notes='Delegate 995 GRT to indexer',
        ),
        evm_event(
            at=20,
            amount='5',
            asset=A_GRT,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            tx_ref=delegate_tx,
            sequence_index=1,
            counterparty=CPT_THEGRAPH,
            notes='Burn 5 GRT as delegation tax',
        ),
        evm_event(
            at=30,
            amount='1005',
            asset=A_GRT,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            counterparty=CPT_THEGRAPH,
            notes='Withdraw 1005 GRT from indexer',
        ),
    ]
    scenario = ParityScenario(
        id=f'thegraph_delegation_reward[balance_pass={run_balance_pass}]',
        events=events,
        default_prices={A_GRT: Price(ONE)},
        settings={'auto_create_profit_events': True} if run_balance_pass else {},
        use_default_rules=True,
        use_real_evm_accountants=True,
        run_balance_pass=run_balance_pass,
    )
    diff = run_parity_scenario(database, scenario)
    if run_balance_pass:
        diff.assert_parity()
        assert diff.old_taxable == FVal('1005')
        assert diff.old_free == ZERO
    else:
        diff.assert_expected_divergence(
            reason=(
                'KNOWN_GAP: ThegraphAccountant._process_withdraw emits synthetic +10 GRT '
                'delegation reward without balance pass; unported in new cost_basis pipeline'
            ),
            old_taxable=FVal('1005'),
            new_taxable=FVal('995'),
            per_asset={A_GRT.identifier: (FVal('1005'), ZERO, FVal('995'), ZERO)},
        )


@pytest.mark.parametrize(
    ('include_fees_in_cost_basis', 'expected_taxable'),
    [
        (True, FVal('12570')),
        (False, FVal('12670')),
    ],
    ids=['fees_in_basis', 'fees_separate'],
)
def test_cowswap_swap_with_fee(
        database: DBHandler,
        include_fees_in_cost_basis: bool,
        expected_taxable: FVal,
) -> None:
    """CowSwap TRADE SPEND/RECEIVE/FEE with fee folded into basis vs separate expense."""
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=10,
            group_id='buy-wbtc',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_USD, '20000'),
            receive=(A_WBTC, '1'),
        ),
        *swap_group(
            at=20,
            group_id='cowswap-wbtc-usdc',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_WBTC, '0.99'),
            receive=(A_USDC, '29700'),
            fee=(A_WBTC, '0.01'),
            counterparty=CPT_COWSWAP,
        ),
        *swap_group(
            at=30,
            group_id='sell-usdc',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_USDC, '29700'),
            receive=(A_USD, '32670'),
        ),
    ]
    scenario = ParityScenario(
        id=f'cowswap_swap_with_fee[fees_in_basis={include_fees_in_cost_basis}]',
        events=events,
        prices={
            (A_WBTC, ts(10)): Price(FVal('20000')),
            (A_WBTC, ts(20)): Price(FVal('30000')),
            (A_USDC, ts(20)): Price(ONE),
            (A_USDC, ts(30)): Price(FVal('1.1')),
        },
        default_prices={A_USD: Price(ONE)},
        settings={'include_fees_in_cost_basis': include_fees_in_cost_basis},
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    assert diff.old_taxable == expected_taxable
    assert diff.old_free == ZERO


@pytest.mark.parametrize(
    ('fee_in', 'include_fees_in_cost_basis', 'expected_taxable'),
    [
        ('spent', True, FVal('15')),
        ('spent', False, FVal('16')),
        ('received', True, FVal('19.801')),
        ('received', False, FVal('19.8')),
    ],
    ids=[
        'fee_in_spent-fees_in_basis',
        'fee_in_spent-fees_separate',
        'fee_in_received-fees_in_basis',
        'fee_in_received-fees_separate',
    ],
)
def test_paraswap_swap_with_fee(
        database: DBHandler,
        fee_in: str,
        include_fees_in_cost_basis: bool,
        expected_taxable: FVal,
) -> None:
    """ParaSwap swap with fee paid in spent asset vs received asset."""
    if fee_in == 'spent':
        swap_events = swap_group(
            at=20,
            group_id='paraswap-wbtc-eth',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_WBTC, '0.8'),
            receive=(A_ETH, '80'),
            fee=(A_WBTC, '0.2'),
            counterparty=CPT_PARASWAP,
        )
        sell_eth_amount = '80'
        sell_usd_amount = '16'
    else:
        swap_events = swap_group(
            at=20,
            group_id='paraswap-wbtc-eth',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_WBTC, '1'),
            receive=(A_ETH, '100'),
            fee=(A_ETH, '1'),
            counterparty=CPT_PARASWAP,
        )
        sell_eth_amount = '99'
        sell_usd_amount = '19.8'

    events: list[HistoryBaseEntry] = [
        evm_event(
            at=10,
            amount='1',
            asset=A_WBTC,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            notes='Receive 1 WBTC',
        ),
        *swap_events,
        *swap_group(
            at=30,
            group_id='sell-eth',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_ETH, sell_eth_amount),
            receive=(A_USD, sell_usd_amount),
        ),
    ]
    scenario = ParityScenario(
        id=f'paraswap_swap_with_fee[fee_in={fee_in},fees_in_basis={include_fees_in_cost_basis}]',
        events=events,
        prices={
            (A_WBTC, ts(10)): Price(FVal('5')),
            (A_WBTC, ts(20)): Price(FVal('10')),
            (A_ETH, ts(20)): Price(FVal('0.1')),
            (A_ETH, ts(30)): Price(FVal('0.2')),
        },
        default_prices={A_USD: Price(ONE)},
        settings={'include_fees_in_cost_basis': include_fees_in_cost_basis},
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    assert diff.old_taxable == expected_taxable
    assert diff.old_free == ZERO


@pytest.mark.parametrize(
    ('taxfree_after_period', 'expected_taxable', 'expected_free'),
    [
        (TAXFREE_DISABLED, FVal('1500'), ZERO),
        (ONE_YEAR_SECONDS, ZERO, FVal('1500')),
    ],
    ids=['taxable', 'taxfree_1yr'],
)
def test_protocol_deposit_withdraw_basis_transfer(
        database: DBHandler,
        taxfree_after_period: int,
        expected_taxable: FVal,
        expected_free: FVal,
) -> None:
    """DEPOSIT_TO_PROTOCOL + WITHDRAW_FROM_PROTOCOL preserves lot basis and holding date."""
    t_buy = 0
    t_deposit = 100 * SECONDS_PER_DAY
    t_withdraw = 200 * SECONDS_PER_DAY
    t_sell = 400 * SECONDS_PER_DAY
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=t_buy,
            group_id='buy-eth',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_USD, '1000'),
            receive=(A_ETH, '1'),
        ),
        evm_event(
            at=t_deposit,
            amount='1',
            asset=A_ETH,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            counterparty=CPT_LIQUITY,
            notes='Deposit 1 ETH to Liquity',
        ),
        evm_event(
            at=t_withdraw,
            amount='1',
            asset=A_ETH,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            counterparty=CPT_LIQUITY,
            notes='Withdraw 1 ETH from Liquity',
        ),
        *swap_group(
            at=t_sell,
            group_id='sell-eth',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_ETH, '1'),
            receive=(A_USD, '2500'),
        ),
    ]
    scenario = ParityScenario(
        id=f'protocol_deposit_withdraw_basis_transfer[taxfree={taxfree_after_period}]',
        events=events,
        prices={
            (A_ETH, ts(t_buy)): Price(FVal('1000')),
            (A_ETH, ts(t_deposit)): Price(FVal('1500')),
            (A_ETH, ts(t_withdraw)): Price(FVal('1800')),
            (A_ETH, ts(t_sell)): Price(FVal('2500')),
        },
        default_prices={A_USD: Price(ONE)},
        settings={'taxfree_after_period': taxfree_after_period},
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    assert diff.old_taxable == expected_taxable
    assert diff.old_free == expected_free


def test_protocol_withdraw_with_balance_pass_profit(database: DBHandler) -> None:
    """Deposit 10 USDC, withdraw 12 USDC with balance pass creating +2 USDC profit event."""
    events: list[HistoryBaseEntry] = [
        *swap_group(
            at=10,
            group_id='buy-usdc',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_USD, '10'),
            receive=(A_USDC, '10'),
        ),
        evm_event(
            at=20,
            amount='10',
            asset=A_USDC,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            counterparty=CPT_LIQUITY,
            notes='Deposit 10 USDC to protocol',
        ),
        evm_event(
            at=30,
            amount='12',
            asset=A_USDC,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            counterparty=CPT_LIQUITY,
            notes='Withdraw 12 USDC from protocol',
        ),
        *swap_group(
            at=40,
            group_id='sell-usdc',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_USDC, '12'),
            receive=(A_USD, '13.2'),
        ),
    ]
    scenario = ParityScenario(
        id='protocol_withdraw_with_balance_pass_profit',
        events=events,
        prices={
            (A_USDC, ts(10)): Price(ONE),
            (A_USDC, ts(20)): Price(ONE),
            (A_USDC, ts(30)): Price(ONE),
            (A_USDC, ts(40)): Price(FVal('1.1')),
        },
        default_prices={A_USD: Price(ONE)},
        settings={'auto_create_profit_events': True},
        use_default_rules=True,
        run_balance_pass=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    assert diff.old_taxable == FVal('3.2')
    assert diff.old_free == ZERO


@pytest.mark.parametrize('direction', ['wrap', 'unwrap'], ids=['eth_to_weth', 'weth_to_eth'])
@pytest.mark.parametrize(
    ('taxfree_after_period', 'expected_taxable', 'expected_free'),
    [
        (TAXFREE_DISABLED, FVal('500'), ZERO),
        (ONE_YEAR_SECONDS, ZERO, FVal('500')),
    ],
    ids=['taxable', 'taxfree_1yr'],
)
def test_eth_weth_wrap_unwrap_basis_transfer(
        database: DBHandler,
        direction: str,
        taxfree_after_period: int,
        expected_taxable: FVal,
        expected_free: FVal,
) -> None:
    """BASIS_TRANSFER wrap/unwrap preserves original lot basis and acquisition timestamp."""
    t_buy = 0
    t_convert = 300 * SECONDS_PER_DAY
    t_sell = 400 * SECONDS_PER_DAY
    convert_tx = make_evm_tx_hash()

    if direction == 'wrap':
        events: list[HistoryBaseEntry] = [
            *swap_group(
                at=t_buy,
                group_id='buy-eth',
                location=LOCATION_ETHEREUM,
                location_label=DEFAULT_EVM_ADDRESS,
                spend=(A_USD, '1000'),
                receive=(A_ETH, '1'),
            ),
            evm_event(
                at=t_convert,
                amount='1',
                asset=A_ETH,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
                tx_ref=convert_tx,
                sequence_index=0,
                counterparty=CPT_WETH,
                notes='Wrap 1 ETH to WETH',
            ),
            evm_event(
                at=t_convert,
                amount='1',
                asset=A_WETH,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                tx_ref=convert_tx,
                sequence_index=1,
                counterparty=CPT_WETH,
                notes='Receive 1 WETH',
            ),
            *swap_group(
                at=t_sell,
                group_id='sell-weth',
                location=LOCATION_ETHEREUM,
                location_label=DEFAULT_EVM_ADDRESS,
                spend=(A_WETH, '1'),
                receive=(A_USD, '1500'),
            ),
        ]
    else:
        events = [
            *swap_group(
                at=t_buy,
                group_id='buy-weth',
                location=LOCATION_ETHEREUM,
                location_label=DEFAULT_EVM_ADDRESS,
                spend=(A_USD, '1000'),
                receive=(A_WETH, '1'),
            ),
            evm_event(
                at=t_convert,
                amount='1',
                asset=A_WETH,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.RETURN_WRAPPED,
                tx_ref=convert_tx,
                sequence_index=0,
                counterparty=CPT_WETH,
                notes='Unwrap 1 WETH to ETH',
            ),
            evm_event(
                at=t_convert,
                amount='1',
                asset=A_ETH,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
                tx_ref=convert_tx,
                sequence_index=1,
                counterparty=CPT_WETH,
                notes='Receive 1 ETH',
            ),
            *swap_group(
                at=t_sell,
                group_id='sell-eth',
                location=LOCATION_ETHEREUM,
                location_label=DEFAULT_EVM_ADDRESS,
                spend=(A_ETH, '1'),
                receive=(A_USD, '1500'),
            ),
        ]

    scenario = ParityScenario(
        id=f'eth_weth_wrap_unwrap_basis_transfer[{direction},taxfree={taxfree_after_period}]',
        events=events,
        prices={
            (A_ETH, ts(t_buy)): Price(FVal('1000')),
            (A_WETH, ts(t_buy)): Price(FVal('1000')),
            (A_ETH, ts(t_convert)): Price(FVal('1200')),
            (A_WETH, ts(t_convert)): Price(FVal('1200')),
            (A_ETH, ts(t_sell)): Price(FVal('1500')),
            (A_WETH, ts(t_sell)): Price(FVal('1500')),
        },
        default_prices={A_USD: Price(ONE)},
        settings={'taxfree_after_period': taxfree_after_period},
        rules=[
            RuleSpec(
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
                counterparty=CPT_WETH,
                taxable=False,
                count_cost_basis_pnl=False,
                accounting_treatment=TxAccountingTreatment.BASIS_TRANSFER,
            ),
            RuleSpec(
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.RETURN_WRAPPED,
                counterparty=CPT_WETH,
                taxable=False,
                count_cost_basis_pnl=False,
                accounting_treatment=TxAccountingTreatment.BASIS_TRANSFER,
            ),
        ],
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    assert diff.old_taxable == expected_taxable
    assert diff.old_free == expected_free


@pytest.mark.parametrize(
    ('sell_price', 'sell_usd', 'expected_taxable'),
    [
        (Price(FVal('3')), '150', FVal('250')),
        (Price(FVal('1.5')), '75', FVal('175')),
    ],
    ids=['sell_higher', 'sell_lower'],
)
def test_defi_claim_reward_and_sell(
        database: DBHandler,
        sell_price: Price,
        sell_usd: str,
        expected_taxable: FVal,
) -> None:
    """Claim taxable STAKING/REWARD then sell half at higher or lower price."""
    events: list[HistoryBaseEntry] = [
        evm_event(
            at=10,
            amount='100',
            asset=A_GRT,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            notes='Claim 100 GRT staking reward',
        ),
        *swap_group(
            at=20,
            group_id='sell-half-grt',
            location=LOCATION_ETHEREUM,
            location_label=DEFAULT_EVM_ADDRESS,
            spend=(A_GRT, '50'),
            receive=(A_USD, sell_usd),
        ),
    ]
    scenario = ParityScenario(
        id=f'defi_claim_reward_and_sell[sell_price={sell_price}]',
        events=events,
        prices={
            (A_GRT, ts(10)): Price(FVal('2')),
            (A_GRT, ts(20)): sell_price,
        },
        default_prices={A_USD: Price(ONE)},
        use_default_rules=True,
    )
    diff = run_parity_scenario(database, scenario)
    diff.assert_parity()
    assert diff.old_taxable == expected_taxable
    assert diff.old_free == ZERO
