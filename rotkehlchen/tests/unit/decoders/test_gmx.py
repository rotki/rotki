import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.arbitrum_one.modules.gmx.constants import (
    CPT_GMX,
    GMX_POSITION_ROUTER,
    GMX_ROUTER_ADDRESS,
    GMX_VAULT_ADDRESS,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_GMX
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x22E798f9440F563B92AAE24E94C75DfA499e3d3E']])
def test_swap_in_gmx(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x5969392c45eaf7e6e3453e2405afb23eb2424e8e4ba2d14e38943fdcdab55d5f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    user_address = arbitrum_one_accounts[0]
    gas_amount, swap_amount, received_amount = '0.0001812982', '14964.074104', '947.4907214801'
    timestamp = TimestampMS(1705481044000)
    a_usdce = Asset('eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8')
    a_link = Asset('eip155:42161/erc20:0xf97f4df75117a78c1A5a0DBb814Af92458539FB4')

    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=a_usdce,
            amount=FVal('18446744073709551614999995512857.612984'),
            location_label=user_address,
            address=GMX_ROUTER_ADDRESS,
            notes='Set USDC.e spending approval of 0x22E798f9440F563B92AAE24E94C75DfA499e3d3E by 0xaBBc5F99639c9B6bCb58544ddf04EFA6802F4064 to 18446744073709551614999995512857.612984',  # noqa: E501
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=a_usdce,
            amount=FVal(swap_amount),
            location_label=user_address,
            notes=f'Swap {swap_amount} USDC.e in GMX',
            counterparty=CPT_GMX,
            address=GMX_VAULT_ADDRESS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=4,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=a_link,
            amount=FVal(received_amount),
            location_label=user_address,
            notes=f'Receive {received_amount} LINK as the result of a GMX swap',
            counterparty=CPT_GMX,
            address=GMX_VAULT_ADDRESS,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x0C0e6d63A7933e1C2dE16E1d5E61dB1cA802BF51']])
def test_long_in_gmx(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x99eed649e7845813353b29dba0ac248dc328253051a778ca895a0a6c34092798')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    user_address = arbitrum_one_accounts[0]
    gas_amount, amount_deposited, fee_amount = '0.0001744401', '0.000785648767580506', '0.00021'
    timestamp = TimestampMS(1705487645000)
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            amount=FVal(amount_deposited),
            location_label=user_address,
            notes=f'Increase long position with {amount_deposited} ETH in GMX',
            address=GMX_POSITION_ROUTER,
            counterparty=CPT_GMX,
            extra_data={'collateral_token': '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1', 'index_token': '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1', 'is_long': True},  # noqa: E501
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=user_address,
            notes=f'Spend {fee_amount} ETH as GMX fee',
            counterparty=CPT_GMX,
            address=GMX_POSITION_ROUTER,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x3D4d8A52D5717b09CA1e1980393d244Ac258C6AA']])
def test_decrease_short_in_gmx(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0xa3dd437d57689479db67ce685c4b70ee9bdbfbcc53f99fc343f73c89edaafe7a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    user_address = arbitrum_one_accounts[0]
    amount_withdrawn, fee_amount = '140.09783', '0.000215'
    timestamp = TimestampMS(1705498390000)
    a_usdc = Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831')
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=18,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=a_usdc,
            amount=FVal(amount_withdrawn),
            location_label=user_address,
            notes=f'Decrease short position withdrawing {amount_withdrawn} USDC in GMX',
            address=GMX_POSITION_ROUTER,
            counterparty=CPT_GMX,
            extra_data={'collateral_token': '0xaf88d065e77c8cC2239327C5EDb3A432268e5831', 'index_token': '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1', 'is_long': '0x3D4d8A52D5717b09CA1e1980393d244Ac258C6AA'},  # noqa: E501
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=20,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=user_address,
            notes=f'Spend {fee_amount} ETH as GMX fee',
            counterparty=CPT_GMX,
            address=string_to_evm_address('0x11D62807dAE812a0F1571243460Bf94325F43BB7'),
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xB5E10681aA81cd65D74912015220999044b9520C']])
def test_stake_gmx(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x682aa15cb8d49021ae5b12c89f6d0138387c4819b1a31b80f67b70aac55d199c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    user_address = arbitrum_one_accounts[0]
    gas_amount, staked_amount = '0.0000631134', '15.9'
    approve_amount = '115792089237316195423570985008687907853269984665640564039169.929301629384984299'  # noqa: E501
    timestamp = TimestampMS(1707120778000)
    sgmx_address = string_to_evm_address('0x908C4D94D34924765f1eDc22A1DD098397c59dD4')
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_GMX,
            amount=FVal(approve_amount),
            location_label=user_address,
            notes=f'Set GMX spending approval of {user_address} by {sgmx_address} to {approve_amount}',  # noqa: E501
            address=sgmx_address,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_GMX,
            amount=FVal(staked_amount),
            location_label=user_address,
            notes=f'Stake {staked_amount} GMX in GMX',
            counterparty=CPT_GMX,
            address=sgmx_address,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:42161/erc20:0x908C4D94D34924765f1eDc22A1DD098397c59dD4'),
            amount=FVal(staked_amount),
            location_label=user_address,
            notes='Receive 15.9 sGMX after staking in GMX',
            counterparty=CPT_GMX,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=4,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:42161/erc20:0x908C4D94D34924765f1eDc22A1DD098397c59dD4'),
            amount=FVal(staked_amount),
            location_label=user_address,
            notes=f'Stake {staked_amount} sGMX in GMX',
            counterparty=CPT_GMX,
            address=string_to_evm_address('0x4d268a7d4C16ceB5a606c173Bd974984343fea13'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=7,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:42161/erc20:0x4d268a7d4C16ceB5a606c173Bd974984343fea13'),
            amount=FVal(staked_amount),
            location_label=user_address,
            notes=f'Receive {staked_amount} sbGMX after staking in GMX',
            counterparty=CPT_GMX,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=8,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:42161/erc20:0x4d268a7d4C16ceB5a606c173Bd974984343fea13'),
            amount=FVal(staked_amount),
            location_label=user_address,
            notes=f'Stake {staked_amount} sbGMX in GMX',
            counterparty=CPT_GMX,
            address=string_to_evm_address('0xd2D1162512F927a7e282Ef43a362659E4F2a728F'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=11,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:42161/erc20:0xd2D1162512F927a7e282Ef43a362659E4F2a728F'),
            amount=FVal(staked_amount),
            location_label=user_address,
            notes=f'Receive {staked_amount} sbfGMX after staking in GMX',
            counterparty=CPT_GMX,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events
