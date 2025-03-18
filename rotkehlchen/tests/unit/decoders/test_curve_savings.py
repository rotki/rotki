from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xBFF9C95D12eA2661bbC9ea2d18C4D1b3868C9Fe0']])
def test_deposit_into_crvusd_savings(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x516d98ed5c091bb2f452742b1a4079f2084f525be3662b026159a1ed7a9bef66')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, approval_amount, deposit_amount, receive_amount = TimestampMS(1741194983000), ethereum_accounts[0], '0.00019683257061538', '9999900000', '27292.191642525541816366', '26201.448750994790858145'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=285,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'),
            amount=FVal(approval_amount),
            location_label=user_address,
            notes=f'Set crvUSD spending approval of {user_address} by 0x0655977FEb2f289A4aB78af67BAB0d17aAb84367 to {approval_amount}',  # noqa: E501
            address=string_to_evm_address('0x0655977FEb2f289A4aB78af67BAB0d17aAb84367'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=286,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:1/erc20:0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'),
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} crvUSD in Curve Savings',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x0655977FEb2f289A4aB78af67BAB0d17aAb84367'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=287,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0x0655977FEb2f289A4aB78af67BAB0d17aAb84367'),
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} scrvUSD from depositing into Curve Savings',
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5275817b74021E97c980E95EdE6bbAc0D0d6f3a2']])
def test_withdraw_from_crvusd_savings(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x1d5db358dfdec9f554e81dedf0395b857db30fdca838c36c05cceaae00768cad')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, return_amount, withdrawn_amount = TimestampMS(1741204907000), ethereum_accounts[0], '0.000056238373116988', '53747.564298310073222919', '55985.692533876701394441'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=800,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0x0655977FEb2f289A4aB78af67BAB0d17aAb84367'),
            amount=FVal(return_amount),
            location_label=user_address,
            notes=f'Return {return_amount} scrvUSD into Curve Savings',
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=801,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:1/erc20:0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'),
            amount=FVal(withdrawn_amount),
            location_label=user_address,
            notes=f'Remove {withdrawn_amount} crvUSD from Curve Savings',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x0655977FEb2f289A4aB78af67BAB0d17aAb84367'),
        ),
    ]
