import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.arbitrum_one.modules.gmx.constants import (
    CPT_GMX,
    GMX_POSITION_ROUTER,
    GMX_ROUTER_ADDRESS,
    GMX_VAULT_ADDRESS,
)
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr()
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x22E798f9440F563B92AAE24E94C75DfA499e3d3E']])
def test_swap_in_gmx(database, arbitrum_one_inquirer, arbitrum_one_accounts):
    evmhash = deserialize_evm_tx_hash('0x5969392c45eaf7e6e3453e2405afb23eb2424e8e4ba2d14e38943fdcdab55d5f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    user_address = arbitrum_one_accounts[0]
    gas_amount, swap_amount, received_amount = '0.0001812982', '14964.074104', '947.4907214801'
    timestamp = TimestampMS(1705481044000)
    a_usdce = Asset('eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8')
    a_link = Asset('eip155:42161/erc20:0xf97f4df75117a78c1A5a0DBb814Af92458539FB4')

    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_amount)),
            location_label=user_address,
            notes=f'Burned {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=a_usdce,
            balance=Balance(FVal('18446744073709551614999995512857.612984')),
            location_label=user_address,
            address=GMX_ROUTER_ADDRESS,
            notes='Set USDC.e spending approval of 0x22E798f9440F563B92AAE24E94C75DfA499e3d3E by 0xaBBc5F99639c9B6bCb58544ddf04EFA6802F4064 to 18446744073709551614999995512857.612984',  # noqa: E501
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=a_usdce,
            balance=Balance(amount=FVal(swap_amount)),
            location_label=user_address,
            notes=f'Swap {swap_amount} USDC.e in GMX',
            counterparty=CPT_GMX,
            address=GMX_VAULT_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=4,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=a_link,
            balance=Balance(amount=FVal(received_amount)),
            location_label=user_address,
            notes=f'Receive {received_amount} LINK as the result of a GMX swap',
            counterparty=CPT_GMX,
            address=GMX_VAULT_ADDRESS,
        ),
    ]


@pytest.mark.vcr()
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x0C0e6d63A7933e1C2dE16E1d5E61dB1cA802BF51']])
def test_long_in_gmx(database, arbitrum_one_inquirer, arbitrum_one_accounts):
    evmhash = deserialize_evm_tx_hash('0x99eed649e7845813353b29dba0ac248dc328253051a778ca895a0a6c34092798')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    user_address = arbitrum_one_accounts[0]
    gas_amount, amount_deposited, fee_amount = '0.0001744401', '0.000785648767580506', '0.00021'
    timestamp = TimestampMS(1705487645000)
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_amount)),
            location_label=user_address,
            notes=f'Burned {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            balance=Balance(FVal(amount_deposited)),
            location_label=user_address,
            notes=f'Increase long position with {amount_deposited} ETH in GMX',
            address=GMX_POSITION_ROUTER,
            counterparty=CPT_GMX,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal(fee_amount)),
            location_label=user_address,
            notes=f'Spend {fee_amount} ETH as GMX fee',
            counterparty=CPT_GMX,
            address=GMX_POSITION_ROUTER,
        ),
    ]


@pytest.mark.vcr()
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x3D4d8A52D5717b09CA1e1980393d244Ac258C6AA']])
def test_decrease_short_in_gmx(database, arbitrum_one_inquirer, arbitrum_one_accounts):
    evmhash = deserialize_evm_tx_hash('0xa3dd437d57689479db67ce685c4b70ee9bdbfbcc53f99fc343f73c89edaafe7a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    user_address = arbitrum_one_accounts[0]
    amount_withdrawn, fee_amount = '140.09783', '0.000215'
    timestamp = TimestampMS(1705498390000)
    a_usdc = Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831')
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=18,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=a_usdc,
            balance=Balance(FVal(amount_withdrawn)),
            location_label=user_address,
            notes=f'Decrease short position withdrawing {amount_withdrawn} USDC in GMX',
            address=GMX_POSITION_ROUTER,
            counterparty=CPT_GMX,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=20,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal(fee_amount)),
            location_label=user_address,
            notes=f'Spend {fee_amount} ETH as GMX fee',
            counterparty=CPT_GMX,
            address=string_to_evm_address('0x11D62807dAE812a0F1571243460Bf94325F43BB7'),
        ),
    ]
