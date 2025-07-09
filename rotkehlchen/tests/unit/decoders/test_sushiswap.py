import pytest

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.modules.sushiswap.constants import CPT_SUSHISWAP_V2
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_USDT
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    Location,
    TimestampMS,
    TokenKind,
    deserialize_evm_tx_hash,
)

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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=309,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=EvmToken('eip155:1/erc20:0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
            amount=FVal(swap_amount),
            location_label=ADDY_1,
            notes=f'Swap {swap_amount} cvxCRV in sushiswap-v2 from {ADDY_1}',
            counterparty=CPT_SUSHISWAP_V2,
            address=string_to_evm_address('0x33F6DDAEa2a8a54062E021873bCaEE006CdF4007'),
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=310,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=EvmToken('eip155:1/erc20:0xD533a949740bb3306d119CC777fa900bA034cd52'),
            amount=FVal(received_amount),
            location_label=ADDY_1,
            notes=f'Receive {received_amount} CRV in sushiswap-v2 from {ADDY_1}',
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_ETH,
            amount=FVal(removed_eth),
            location_label=ADDY_2,
            notes=f'Remove {removed_eth} ETH from sushiswap-v2 LP {pool_address}',
            counterparty=CPT_SUSHISWAP_V2,
            address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            extra_data={'pool_address': pool_address},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=23,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0x06da0fd433C1A5d7a4faa01111c044910A184553'),
            amount=FVal(spent_amount),
            location_label=ADDY_2,
            notes=f'Send {spent_amount} SLP WETH-USDT to sushiswap-v2 pool',
            counterparty=CPT_SUSHISWAP_V2,
            address=pool_address,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=30,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_USDT,
            amount=FVal(removed_usdt),
            location_label=ADDY_2,
            notes=f'Remove {removed_usdt} USDT from sushiswap-v2 LP 0x06da0fd433C1A5d7a4faa01111c044910A184553',  # noqa: E501
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal(deposited_eth),
            location_label=ADDY_3,
            notes=f'Deposit {deposited_eth} ETH to sushiswap-v2 LP {pool_address}',
            counterparty=CPT_SUSHISWAP_V2,
            address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            extra_data={'pool_address': pool_address},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=218,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_USDT,
            amount=FVal(deposited_usdt),
            location_label=ADDY_3,
            notes=f'Deposit {deposited_usdt} USDT to sushiswap-v2 LP {pool_address}',
            counterparty=CPT_SUSHISWAP_V2,
            address=pool_address,
            extra_data={'pool_address': pool_address},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=222,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(lp_token_identifier),
            amount=FVal(received_amount),
            location_label=ADDY_3,
            notes=f'Receive {received_amount} SLP WETH-USDT from sushiswap-v2 pool',
            counterparty=CPT_SUSHISWAP_V2,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events
    assert EvmToken(lp_token_identifier).protocol == CPT_SUSHISWAP_V2
