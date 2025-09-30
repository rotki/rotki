from typing import Final

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.scroll_bridge.decoder import (
    L1_ERC20_GATEWAY,
    L1_ETH_GATEWAY_PROXY,
    L1_GATEWAY_ROUTER,
    L1_MESSENGER_PROXY,
    L1_USDC_GATEWAY,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.scroll.constants import CPT_SCROLL
from rotkehlchen.chain.scroll.modules.scroll_bridge.decoder import (
    L2_ETH_GATEWAY,
    L2_USDC_GATEWAY,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

L2_MESSENGER_PROXY: Final = string_to_evm_address('0x781e90f1c8Fc4611c9b7497C3B47F99Ef6969CbC')


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xfa8666aE51F5b136596248d9411b03AC9040fff0']])
def test_deposit_eth_from_ethereum_to_scroll(ethereum_inquirer, ethereum_accounts):
    evmhash = deserialize_evm_tx_hash('0x1d924e2f2f63cf5a2d78ceaa6289658cf4743e968d23f78064d55c7428f78b60')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1711626707000)
    gas, amount, bridging_fee = '0.006936488814808056', '0.1179', '0.0002604'
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(bridging_fee),
            location_label=user_address,
            notes=f'Spend {bridging_fee} ETH as a fee for bridging to Scroll',
            counterparty=CPT_SCROLL,
            address=L1_MESSENGER_PROXY,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Bridge {amount} ETH from Ethereum to Scroll via Scroll bridge',
            counterparty=CPT_SCROLL,
            address=L1_GATEWAY_ROUTER,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('scroll_accounts', [['0xfa8666aE51F5b136596248d9411b03AC9040fff0']])
def test_receive_eth_on_scroll(scroll_inquirer, scroll_accounts):
    evmhash = deserialize_evm_tx_hash('0xd47e37dc8acb08b86bd90214d1df15549305e6d5fe126b97ff3b66a1b814b801')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=scroll_inquirer, tx_hash=evmhash)
    user_address = scroll_accounts[0]
    timestamp = TimestampMS(1711627620000)
    amount = '0.1179'
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Bridge {amount} ETH from Ethereum to Scroll via Scroll bridge',
            counterparty=CPT_SCROLL,
            address=L2_ETH_GATEWAY,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('scroll_accounts', [['0xEa72f0d67045b2cffbFB18E56744799f9F860CB7']])
def test_withdraw_eth_from_scroll_to_ethereum(scroll_inquirer, scroll_accounts):
    evmhash = deserialize_evm_tx_hash('0x87c44e16cf62a8aa8e56b9677e6c400041b6731a5c24f9b8ca2deb6e00202a42')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=scroll_inquirer, tx_hash=evmhash)
    user_address = scroll_accounts[0]
    timestamp = TimestampMS(1708178454000)
    gas, amount = '0.00021234172322581', '0.6'
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Bridge {amount} ETH from Scroll to Ethereum via Scroll bridge',
            counterparty=CPT_SCROLL,
            address=string_to_evm_address(L2_ETH_GATEWAY),
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xEa72f0d67045b2cffbFB18E56744799f9F860CB7']])
def test_receive_eth_on_ethereum(ethereum_inquirer, ethereum_accounts):
    evmhash = deserialize_evm_tx_hash('0xed4d0ddc99b88caa07d5d15faf376abade6cc06eaf6a28dce47eac66695503c4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1708187711000)
    gas, amount = '0.003718494016624992', '0.6'
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Bridge {amount} ETH from Scroll to Ethereum via Scroll bridge',
            counterparty=CPT_SCROLL,
            address=string_to_evm_address(L1_ETH_GATEWAY_PROXY),
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xD297a2E732537f9fFb2Da53816FC84c7A50a11C2']])
def test_deposit_erc20_from_ethereum_to_scroll(ethereum_inquirer, ethereum_accounts):
    evmhash = deserialize_evm_tx_hash('0xd80e6894bce182c2976bb9fa64e162f1757a087057b00638b43fe0c5154cf1a6')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1711698851000)
    gas, fee, amount = '0.005582179923194343', '0.000122880', '100'
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('ETH'),
            amount=FVal(fee),
            location_label=user_address,
            notes=f'Spend {fee} ETH in L2 fees to bridge ERC20 tokens to Scroll',
            counterparty=CPT_SCROLL,
            address=string_to_evm_address(L1_GATEWAY_ROUTER),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=269,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Bridge {amount} USDC from Ethereum to Scroll via Scroll bridge',
            counterparty=CPT_SCROLL,
            address=L1_USDC_GATEWAY,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('scroll_accounts', [['0xD297a2E732537f9fFb2Da53816FC84c7A50a11C2']])
def test_receive_erc20_on_scroll(scroll_inquirer, scroll_accounts):
    evmhash = deserialize_evm_tx_hash('0x630cd85723676d993f4afdd9f182cd2468444748eb7b1c6c0c8cc1db0d925c15')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=scroll_inquirer, tx_hash=evmhash)
    user_address = scroll_accounts[0]
    timestamp = TimestampMS(1711699803000)
    amount = '100'
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=9,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:534352/erc20:0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4'),
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Bridge {amount} USDC from Ethereum to Scroll via Scroll bridge',
            counterparty=CPT_SCROLL,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('scroll_accounts', [['0x182A0c65bCB008adAaE404e30A813c9797BD717c']])
def test_withdraw_erc20_from_scroll_to_ethereum(scroll_inquirer, scroll_accounts, caplog):
    """Test that USDT withdrawals from scroll to L1 work fine"""
    evmhash = deserialize_evm_tx_hash('0x0ff9e74db99dc2224fac1ab4e20cc8dba1cd1b0d089d657f0f005488b37cc20c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=scroll_inquirer, tx_hash=evmhash)
    user_address = scroll_accounts[0]
    timestamp = TimestampMS(1708535681000)
    gas, amount = '0.000430578838556533', '1000.001993'
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:534352/erc20:0xf55BEC9cafDbE8730f096Aa55dad6D22d44099Df'),
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Bridge {amount} USDT from Scroll to Ethereum via Scroll bridge',
            counterparty=CPT_SCROLL,
            address=ZERO_ADDRESS,
        ),
    ]
    # also check that we only capture the erc20 log event and nothing else. Regression test for
    # https://github.com/orgs/rotki/projects/11?pane=issue&itemId=54372368
    assert '_decode_eth_withdraw_event failed due to Invalid ethereum address' not in caplog.text


@pytest.mark.vcr
@pytest.mark.parametrize('scroll_accounts', [['0xa6145DFB72ADBd7D018c30f611bde7D943EE2E17']])
def test_withdraw_usdc_from_scroll_to_ethereum(scroll_inquirer, scroll_accounts):
    """
    Test that USDC withdrawals from scroll to L1 work fine. This is just to test that
    our code is not token/gateway specific"""
    evmhash = deserialize_evm_tx_hash('0xc21fbdc6b7a2051eb10a53a255ed55c11f776a053d4dbd72954120ebe0120307')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=scroll_inquirer, tx_hash=evmhash)

    user_address = scroll_accounts[0]
    timestamp = TimestampMS(1708534727000)
    gas, amount = '0.000383984852231895', '450'
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=25,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:534352/erc20:0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4'),
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Bridge {amount} USDC from Scroll to Ethereum via Scroll bridge',
            counterparty=CPT_SCROLL,
            address=L2_USDC_GATEWAY,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x59ceD3eeB1cb01AfE92ADbC994D1CE78310E668E']])
def test_receive_erc20_on_ethereum(ethereum_inquirer, ethereum_accounts):
    evmhash = deserialize_evm_tx_hash('0xbe6e98db62ee719922c7d01b0b623e16c8ee162a2bf9143603f11eba3e3dd474')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1708223951000)
    gas, amount = '0.002531473518821568', '1647'
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=549,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'),
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Bridge {amount} USDT from Scroll to Ethereum via Scroll bridge',
            counterparty=CPT_SCROLL,
            address=L1_ERC20_GATEWAY,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd32dEe97C7D7Fdfb826CC3bB210dD009D2750ae2']])
def test_deposit_send_message_ethereum(ethereum_inquirer, ethereum_accounts):
    evmhash = deserialize_evm_tx_hash('0x7ae1e3ef6e4d87e2e44446a683b9ca624241a24d294b60ddec39af1309aeb37a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1708771043000)
    gas, fee, amount = '0.00353129959117221', '0.0000811440', '0.034'
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee),
            location_label=user_address,
            notes=f'Spend {fee} ETH as a fee for bridging to Scroll',
            counterparty=CPT_SCROLL,
            address=L1_MESSENGER_PROXY,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Bridge {amount} ETH from Ethereum to Scroll via Scroll bridge',
            counterparty=CPT_SCROLL,
            address=L1_MESSENGER_PROXY,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('scroll_accounts', [['0xd32dEe97C7D7Fdfb826CC3bB210dD009D2750ae2']])
def test_receive_deposit_message_scroll(scroll_inquirer, scroll_accounts):
    evmhash = deserialize_evm_tx_hash('0x2844533993f614da06a4a81ee692f10562b4b2d077265a33605ca9415d0dcacb')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=scroll_inquirer, tx_hash=evmhash)
    user_address = scroll_accounts[0]
    timestamp = TimestampMS(1708772190000)
    amount = '0.034'
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Bridge {amount} ETH from Ethereum to Scroll via Scroll bridge',
            counterparty=CPT_SCROLL,
            address=L2_MESSENGER_PROXY,
        ),
    ]
