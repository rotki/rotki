from typing import TYPE_CHECKING, Final

import pytest

from rotkehlchen.chain.arbitrum_one.modules.umami.constants import (
    CPT_UMAMI,
    UMAMI_STAKING_CONTRACT,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ARB, A_ETH, Asset
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.types import ChecksumEvmAddress

GM_USDC_WBTC_ADDRESS: Final = string_to_evm_address('0x5f851F67D24419982EcD7b7765deFD64fBb50a97')
A_GM_USDC_WBTC: Final = Asset('eip155:42161/erc20:0x5f851F67D24419982EcD7b7765deFD64fBb50a97')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_umami_deposit_request(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x228e4ec7b253a3609c4e28638e0281a0458f541e380d39731fb5249cccc115f5')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_amount, fee_amount, protocol_fee, deposit_amount = arbitrum_one_accounts[0], TimestampMS(1728996957000), '0.00002373823', '0.00024', '0.0300', '19.9700'  # noqa: E501
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} USDC into Umami',
            tx_hash=tx_hash,
            counterparty=CPT_UMAMI,
            address=GM_USDC_WBTC_ADDRESS,
        ), EvmEvent(
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
            amount=FVal(protocol_fee),
            location_label=user_address,
            notes=f'Spend {protocol_fee} USDC as Umami protocol fee',
            tx_hash=tx_hash,
            counterparty=CPT_UMAMI,
            address=GM_USDC_WBTC_ADDRESS,
        ), EvmEvent(
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=user_address,
            notes=f'Spend {fee_amount} ETH as Umami execution fee',
            tx_hash=tx_hash,
            counterparty=CPT_UMAMI,
            address=GM_USDC_WBTC_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_umami_deposit_execution(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x7a75250baab694c1801ff04580d105dbc2274eb995bca683d1f34541d6012f40')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, receive_amount = arbitrum_one_accounts[0], TimestampMS(1728996966000), '18.62964'  # noqa: E501
    assert events == [
        EvmEvent(
            sequence_index=8,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_GM_USDC_WBTC,
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} gmUSDC_WBTC after a deposit in Umami',
            tx_hash=tx_hash,
            counterparty=CPT_UMAMI,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x4f49D938c3Ad2437c52eb314F9bD7Bdb7FA58Da9']])
def test_umami_withdraw_request(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x10d22492ae775ddc5bda58cb0ce494aefe03f3c1f1caf35dd974f2e4a93dbb13')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_amount, fee_amount, return_amount = arbitrum_one_accounts[0], TimestampMS(1728854533000), '0.0000267323', '0.00024', '62.23329'  # noqa: E501
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_GM_USDC_WBTC,
            amount=FVal(return_amount),
            location_label=user_address,
            notes=f'Return {return_amount} gmUSDC_WBTC to Umami',
            tx_hash=tx_hash,
            counterparty=CPT_UMAMI,
            address=GM_USDC_WBTC_ADDRESS,
        ), EvmEvent(
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=user_address,
            notes=f'Spend {fee_amount} ETH as Umami execution fee',
            tx_hash=tx_hash,
            counterparty=CPT_UMAMI,
            address=GM_USDC_WBTC_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x4f49D938c3Ad2437c52eb314F9bD7Bdb7FA58Da9']])
def test_umami_withdraw_execution(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xc604c2d451f0266bd2906360daca3459fd8a1a3b5b3c0d6e8c340197a665f9ee')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, receive_amount, fee_amount = arbitrum_one_accounts[0], TimestampMS(1728854540000), '66.6301365115', '0.0997955115'  # noqa: E501
    assert events == [EvmEvent(
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
        amount=FVal(receive_amount),
        location_label=user_address,
        notes=f'Withdraw {receive_amount} USDC from Umami',
        tx_hash=tx_hash,
        counterparty=CPT_UMAMI,
        address=string_to_evm_address('0x1E914730B4Cd343aE14530F0BBF6b350d83B833d'),
    ), EvmEvent(
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.FEE,
        asset=Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} USDC as Umami protocol fee',
        tx_hash=tx_hash,
        counterparty=CPT_UMAMI,
        address=string_to_evm_address('0x1E914730B4Cd343aE14530F0BBF6b350d83B833d'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_umami_stake(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x11512234980f9eb05def3f3330d78101a22b56a41aa6edf9bce25acc7c7b0b67')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_amount, stake_amount = arbitrum_one_accounts[0], TimestampMS(1729085072000), '0.00000248034', '18.62964'  # noqa: E501
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=5,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_GM_USDC_WBTC,
            amount=FVal(stake_amount),
            location_label=user_address,
            notes=f'Stake {stake_amount} gmUSDC_WBTC in Umami',
            tx_hash=tx_hash,
            counterparty=CPT_UMAMI,
            address=UMAMI_STAKING_CONTRACT,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_umami_unstake(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x53beec70aa852f1a61688b19618fad13ae107a2db4b0851b6da8bc9894456f47')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_amount, reward_amount, unstake_amount = arbitrum_one_accounts[0], TimestampMS(1729093741000), '0.00000249101', '0.000072393809519512', '18.62964'  # noqa: E501
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=23,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ARB,
            amount=FVal(reward_amount),
            location_label=user_address,
            notes=f'Receive staking reward of {reward_amount} ARB from Umami',
            tx_hash=tx_hash,
            counterparty=CPT_UMAMI,
            address=UMAMI_STAKING_CONTRACT,
        ), EvmEvent(
            sequence_index=25,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_GM_USDC_WBTC,
            amount=FVal(unstake_amount),
            location_label=user_address,
            notes=f'Unstake {unstake_amount} gmUSDC_WBTC from Umami',
            tx_hash=tx_hash,
            counterparty=CPT_UMAMI,
            address=UMAMI_STAKING_CONTRACT,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_umami_claim_rewards(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x2e75a4298336cab07ebf2bd71fa78173e10f8b95d8848a070e0f9d3b294ab7a7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_amount, reward_amount = arbitrum_one_accounts[0], TimestampMS(1729091703000), '0.00000316615', '0.000236004503783333'  # noqa: E501
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=10,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ARB,
            amount=FVal(reward_amount),
            location_label=user_address,
            notes=f'Receive staking reward of {reward_amount} ARB from Umami',
            tx_hash=tx_hash,
            counterparty=CPT_UMAMI,
            address=UMAMI_STAKING_CONTRACT,
        ),
    ]
