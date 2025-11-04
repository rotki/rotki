from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.sushiswap.constants import CPT_SUSHISWAP, CPT_SUSHISWAP_V2
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_USDT
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    Location,
    TimestampMS,
    TokenKind,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer

ADDY_1 = string_to_evm_address('0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF')
ADDY_2 = string_to_evm_address('0x1F14bE60172b40dAc0aD9cD72F6f0f2C245992e8')
ADDY_3 = string_to_evm_address('0x3D6a724247c4B133C3b279558e90EdD0c5d25751')


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_1]])
def test_sushiswap_single_swap(ethereum_inquirer):
    tx_hash = deserialize_evm_tx_hash('0xbfe3c8a13c325a32736beb34ea170053cdbbd1740a9c3ceca52060906b7f87bd')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas, swap_amount, received_amount, approved_amount = TimestampMS(1622840771000), '0.001815413', '19.157411925828275084', '18.47349725628421943', '115792089237316195423570985008687907853269984665640564039438.426595987301364851'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=ADDY_1,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=308,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
            amount=FVal(approved_amount),
            location_label=ADDY_1,
            notes=f'Set cvxCRV spending approval of {ADDY_1} by 0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F to {approved_amount}',  # noqa: E501
            counterparty=None,
            address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=309,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=EvmToken('eip155:1/erc20:0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
            amount=FVal(swap_amount),
            location_label=ADDY_1,
            notes=f'Swap {swap_amount} cvxCRV in Sushiswap V2 from {ADDY_1}',
            counterparty=CPT_SUSHISWAP_V2,
            address=string_to_evm_address('0x33F6DDAEa2a8a54062E021873bCaEE006CdF4007'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=310,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=EvmToken('eip155:1/erc20:0xD533a949740bb3306d119CC777fa900bA034cd52'),
            amount=FVal(received_amount),
            location_label=ADDY_1,
            notes=f'Receive {received_amount} CRV in Sushiswap V2 from {ADDY_1}',
            counterparty=CPT_SUSHISWAP_V2,
            address=string_to_evm_address('0x33F6DDAEa2a8a54062E021873bCaEE006CdF4007'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_2]])
def test_sushiswap_v2_remove_liquidity(ethereum_inquirer):
    """This checks that removing liquidity to Sushiswap V2 pool is decoded properly"""
    tx_hash = deserialize_evm_tx_hash('0x4720a52fc768591cb3997da3a2eab76c54b69176f3c3f8d9a817c2d60dd449ac')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas_amount, spent_amount, removed_eth, removed_usdt, pool_address = TimestampMS(1672888271000), '0.006668386', '0.0000243611620791', '1.122198589808876532', '1408.739932', string_to_evm_address('0x06da0fd433C1A5d7a4faa01111c044910A184553')  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=ADDY_2,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0x06da0fd433C1A5d7a4faa01111c044910A184553'),
            amount=FVal(spent_amount),
            location_label=ADDY_2,
            notes=f'Send {spent_amount} SLP WETH-USDT to Sushiswap V2 pool',
            counterparty=CPT_SUSHISWAP_V2,
            address=pool_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_ETH,
            amount=FVal(removed_eth),
            location_label=ADDY_2,
            notes=f'Remove {removed_eth} ETH from Sushiswap V2 LP {pool_address}',
            counterparty=CPT_SUSHISWAP_V2,
            address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            extra_data={'pool_address': pool_address},
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=30,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_USDT,
            amount=FVal(removed_usdt),
            location_label=ADDY_2,
            notes=f'Remove {removed_usdt} USDT from Sushiswap V2 LP 0x06da0fd433C1A5d7a4faa01111c044910A184553',  # noqa: E501
            counterparty=CPT_SUSHISWAP_V2,
            address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            extra_data={'pool_address': pool_address},
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_3]])
def test_sushiswap_v2_add_liquidity(ethereum_inquirer):
    """This checks that adding liquidity to Sushiswap V2 pool is decoded properly"""
    tx_hash = deserialize_evm_tx_hash('0x2ce6f92f4020fdc4ed69a173b10c1dd2811184fac34d56188270950db1152f3a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas_amount, received_amount, deposited_eth, deposited_usdt, pool_address = TimestampMS(1672893947000), '0.0030789891485573', '0.000000017297304741', '0.000797012710918264', '0.999992', string_to_evm_address('0x06da0fd433C1A5d7a4faa01111c044910A184553')  # noqa: E501
    lp_token_identifier = evm_address_to_identifier(
        address=pool_address,
        chain_id=ChainID.ETHEREUM,
        token_type=TokenKind.ERC20,
    )
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=ADDY_3,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal(deposited_eth),
            location_label=ADDY_3,
            notes=f'Deposit {deposited_eth} ETH to Sushiswap V2 LP {pool_address}',
            counterparty=CPT_SUSHISWAP_V2,
            address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            extra_data={'pool_address': pool_address},
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_USDT,
            amount=FVal(deposited_usdt),
            location_label=ADDY_3,
            notes=f'Deposit {deposited_usdt} USDT to Sushiswap V2 LP {pool_address}',
            counterparty=CPT_SUSHISWAP_V2,
            address=pool_address,
            extra_data={'pool_address': pool_address},
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(lp_token_identifier),
            amount=FVal(received_amount),
            location_label=ADDY_3,
            notes=f'Receive {received_amount} SLP WETH-USDT from Sushiswap V2 pool',
            counterparty=CPT_SUSHISWAP_V2,
            address=pool_address,
        ),
    ]
    assert events == expected_events
    assert EvmToken(lp_token_identifier).protocol == CPT_SUSHISWAP_V2


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xb5C562D66eaCd89c1A9ED07eF6e45A08BF0C6003']])
def test_sushiswap_redsnwap_token_to_token(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x55131a53c42c7d1785737b1ff020bb51ad3ceea63f0cb0c8c8e3b936f5ac9144')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1760078567000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000043563301848849')),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
        notes=f'Burn {gas_amount} ETH for gas',
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:1/erc20:0x514910771AF9Ca656af840dff83E8264EcF986CA'),
        amount=(spend_amount := FVal('8.890996408033060582')),
        location_label=user_address,
        notes=f'Swap {spend_amount} LINK in Sushiswap',
        counterparty=CPT_SUSHISWAP,
        address=string_to_evm_address('0x3B0AA7d38Bf3C103bf02d1De2E37568cBED3D6e8'),
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc20:0x77777FeDdddFfC19Ff86DB637967013e6C6A116C'),
        amount=(receive_amount := FVal('11.439525179948619688')),
        location_label=user_address,
        notes=f'Receive {receive_amount} TORN from Sushiswap swap',
        counterparty=CPT_SUSHISWAP,
        address=string_to_evm_address('0x3B0AA7d38Bf3C103bf02d1De2E37568cBED3D6e8'),
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.FEE,
        asset=Asset('eip155:1/erc20:0x77777FeDdddFfC19Ff86DB637967013e6C6A116C'),
        amount=(receive_amount := FVal('0.028455818885122196')),
        location_label=user_address,
        notes=f'Spend {receive_amount} TORN as Sushiswap swap fee',
        counterparty=CPT_SUSHISWAP,
        address=string_to_evm_address('0x3B0AA7d38Bf3C103bf02d1De2E37568cBED3D6e8'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x873b5A8bFb25c48344F544A1B036cc4EA424966d']])
def test_sushiswap_redsnwap_token_to_eth(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x8968cb8b8bc3dd567b1b0f7d47c349b12a22d8421b2ecf003b6bbbc9a8b1749c')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1762279331000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.001957758654149046')),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
        notes=f'Burn {gas_amount} ETH for gas',
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=348,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=(a_tbtc := Asset('eip155:1/erc20:0x18084fbA666a33d37592fA2633fD49a74DD93a88')),
        location_label=user_address,
        amount=ZERO,
        address=string_to_evm_address('0xAC4c6e212A361c968F1725b4d055b47E63F80b75'),
        notes=f'Revoke tBTC spending approval of {user_address} by 0xAC4c6e212A361c968F1725b4d055b47E63F80b75',  # noqa: E501
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=349,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=a_tbtc,
        amount=(spend_amount := FVal('0.0145')),
        location_label=user_address,
        notes=f'Swap {spend_amount} tBTC in Sushiswap',
        counterparty=CPT_SUSHISWAP,
        address=string_to_evm_address('0xd2b37aDE14708bf18904047b1E31F8166d39612b'),
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=350,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=(receive_amount := FVal('0.434746824162264576')),
        location_label=user_address,
        notes=f'Receive {receive_amount} ETH from Sushiswap swap',
        counterparty=CPT_SUSHISWAP,
        address=string_to_evm_address('0xd2b37aDE14708bf18904047b1E31F8166d39612b'),
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=351,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(fee_amount := FVal('0.001081432725103633')),
        location_label=user_address,
        notes=f'Spend {fee_amount} ETH as Sushiswap swap fee',
        counterparty=CPT_SUSHISWAP,
        address=string_to_evm_address('0xd2b37aDE14708bf18904047b1E31F8166d39612b'),
    )]
