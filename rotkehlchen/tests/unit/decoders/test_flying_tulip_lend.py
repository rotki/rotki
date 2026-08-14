import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.flying_tulip.constants import CPT_FLYING_TULIP
from rotkehlchen.chain.evm.decoding.flying_tulip.lend.constants import (
    FLYING_TULIP_LEND_DEPLOYMENTS,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_USDC, A_USDT, A_WETH, A_WSTETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChainID, Location, TimestampMS, deserialize_evm_tx_hash

A_FTUSD = Asset('eip155:1/erc20:0xF7D85EC4E7710f71992752eac2111312e73E9C9C')
POSITIONS_MANAGER = FLYING_TULIP_LEND_DEPLOYMENTS[ChainID.ETHEREUM].positions_manager


@pytest.mark.parametrize('ethereum_accounts', [['0x3c42749709BF354B3aE0Db29Fd2dd88089b21B4E']])
def test_lend_deposit(ethereum_inquirer, ethereum_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x295b8dae0b18ae6738d7f3bd47a4174e436a8887780f84edc5145beb76c2c15e')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1786445039000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000244695742006959'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=278,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_USDT,
            amount=FVal(amount := '5465.0009'),
            location_label=user_address,
            notes=f'Deposit {amount} USDT in Flying Tulip Lend',
            counterparty=CPT_FLYING_TULIP,
            address=POSITIONS_MANAGER,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [['0xD28b633345340334782521Eb769DfBdb23178308']])
def test_lend_deposit_via_session(ethereum_inquirer, ethereum_accounts):
    """A relayed (session) deposit: the user's single transfer carries the deposit
    plus the relayer fee, which is split into its own event."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xbb4c279ce9b9babc56b4629795dd571b0c5090059b461cdd6b67c4b3aa0be31d')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=147,
            timestamp=(timestamp := TimestampMS(1786615931000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_WSTETH,
            amount=FVal(amount := '5.377817360119760607'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Deposit {amount} wstETH in Flying Tulip Lend',
            counterparty=CPT_FLYING_TULIP,
            address=POSITIONS_MANAGER,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=148,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_WSTETH,
            amount=FVal(approval_amount := '115792089237316195423570985008687907853269984665640564039451.192356186392853834'),  # noqa: E501
            location_label=user_address,
            notes=f'Set wstETH spending approval of {user_address} by 0x4f83aC5c8A79986D0916a8849730d9CEF63a3497 to {approval_amount}',  # noqa: E501
            address=string_to_evm_address('0x4f83aC5c8A79986D0916a8849730d9CEF63a3497'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=163,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_WSTETH,
            amount=FVal(fee_amount := '0.000056681962730268'),
            location_label=user_address,
            notes=f'Spend {fee_amount} wstETH as a Flying Tulip relayer fee',
            counterparty=CPT_FLYING_TULIP,
            address=POSITIONS_MANAGER,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [['0xD0CA88388d1732594D611535314e9B6745396f5A']])
def test_lend_withdraw(ethereum_inquirer, ethereum_accounts):
    """A relayed withdrawal: the relayer fee is deducted from the payout before it
    reaches the wallet, so the withdrawal is grossed up and the fee made explicit."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x8a932f4d8b943d72099dfe3a937574da380c8bedbe8358f7db5cf3aa46d8a6b1')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=352,
            timestamp=(timestamp := TimestampMS(1786454147000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_USDC,
            amount=FVal(amount := '42.621211'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Withdraw {amount} USDC from Flying Tulip Lend',
            counterparty=CPT_FLYING_TULIP,
            address=POSITIONS_MANAGER,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=354,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USDC,
            amount=FVal(fee_amount := '0.228288'),
            location_label=user_address,
            notes=f'Spend {fee_amount} USDC as a Flying Tulip relayer fee',
            counterparty=CPT_FLYING_TULIP,
            address=POSITIONS_MANAGER,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [['0x125DBE70459b36A4C71664DcC97224EafEb4AeE0']])
def test_lend_borrow(ethereum_inquirer, ethereum_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x84dfebb43989ad185ba61d493762501e421e862b2ed15c86c81359d9b6e7f490')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=158,
            timestamp=(timestamp := TimestampMS(1786597487000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_FTUSD,
            amount=FVal(amount := '800'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Borrow {amount} ftUSD from Flying Tulip Lend',
            counterparty=CPT_FLYING_TULIP,
            address=POSITIONS_MANAGER,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=160,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_FTUSD,
            amount=FVal(fee_amount := '0.107274'),
            location_label=user_address,
            notes=f'Spend {fee_amount} ftUSD as a Flying Tulip relayer fee',
            counterparty=CPT_FLYING_TULIP,
            address=POSITIONS_MANAGER,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [['0x268c0342c0151830c6963FE095cec630b3Ac3854']])
def test_lend_repay(ethereum_inquirer, ethereum_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x211fea04a79fe3ea39f6b4cd4d8bc5abb0c64eb7213c0fdb7cac6becf818dca8')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1786266071000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000055191083688456'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=181,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_USDC,
            amount=FVal(amount := '0.000183'),
            location_label=user_address,
            notes=f'Repay {amount} USDC in Flying Tulip Lend',
            counterparty=CPT_FLYING_TULIP,
            address=POSITIONS_MANAGER,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [['0x031f3bAb8f21057D1D7218E3B90cec42aEF3C885']])
def test_lend_full_repay_with_refund(ethereum_inquirer, ethereum_accounts):
    """A relayed full repayment that uses less than the sent amount: the unused
    funds are refunded, and only the actual relayer fee is decoded as a fee."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x4462e7bbb2dfee0d053c9936f045f4c7a4a6f63e538b6e3df7561d2b55ba76bc')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=228,
            timestamp=(timestamp := TimestampMS(1780006871000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_USDC,
            amount=FVal(amount := '400.277826'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Repay {amount} USDC in Flying Tulip Lend',
            counterparty=CPT_FLYING_TULIP,
            address=POSITIONS_MANAGER,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=242,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USDC,
            amount=FVal(fee_amount := '0.157393'),
            location_label=user_address,
            notes=f'Spend {fee_amount} USDC as a Flying Tulip relayer fee',
            counterparty=CPT_FLYING_TULIP,
            address=POSITIONS_MANAGER,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [['0xe0E445967256EE60111e243e0F0F94DD1D351A59']])
def test_leverage_open_fill(ethereum_inquirer, ethereum_accounts):
    """A leverage RFQ engine open fill: the funds move inside the positions
    manager, so the fill decodes into an informational entry that attributes
    the activity and seeds the balance discovery of the position owner."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xc570ee469d3e187fa1e5d0782a38dc75288e1cf6fa510ce3edaa4dd69edabbef')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=170,
        timestamp=TimestampMS(1786546955000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_WETH,
        amount=FVal(sell_amount := '10'),
        location_label=ethereum_accounts[0],
        notes=f'Open a Flying Tulip leverage position selling {sell_amount} WETH',
        counterparty=CPT_FLYING_TULIP,
        address=FLYING_TULIP_LEND_DEPLOYMENTS[ChainID.ETHEREUM].leverage_engine,
    )]
