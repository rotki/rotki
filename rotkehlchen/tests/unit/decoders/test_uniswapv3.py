import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.base.modules.uniswap.v3.constants import UNISWAP_UNIVERSAL_ROUTER
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.cowswap.constants import CPT_COWSWAP
from rotkehlchen.chain.evm.decoding.safe.constants import CPT_SAFE_MULTISIG
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V3
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import (
    A_ARB,
    A_DAI,
    A_ETH,
    A_LUSD,
    A_OP,
    A_POLYGON_POS_MATIC,
    A_USDC,
    A_USDT,
    A_WETH,
    A_WETH_POLYGON,
)
from rotkehlchen.constants.misc import ONE
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

ADDY = string_to_evm_address('0xb63e0C506dDBa7b0dd106d1937d6D13BE2C62aE2')
ADDY_2 = string_to_evm_address('0xeB312F4921aEbbE99faCaCFE92f22b942Cbd7599')
ADDY_3 = string_to_evm_address('0xdD84Ce1aDcb3A4908Db61A1dFA3353C3974c5a2B')
ADDY_4 = string_to_evm_address('0x354304234329A8d2425965C647e701A72d3438e5')
ADDY_5 = string_to_evm_address('0xa931b486F661540c6D709aE6DfC8BcEF347ea437')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_uniswap_v3_swap(ethereum_inquirer):
    tx_hash = deserialize_evm_tx_hash('0x1c50c336329a7ee41f722ce5d848ebd066b72bf44a1eaafcaa92e8c0282049d2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1635998362000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.038293427380094972')),
            location_label=ADDY,
            notes='Burned 0.038293427380094972 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1635998362000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.632989659350357136'), usd_value=ZERO),
            location_label=ADDY,
            notes='Swap 0.632989659350357136 ETH via uniswap-v3 auto router',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0xE592427A0AEce92De3Edee1F18E0157C05861564'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1635998362000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'),
            balance=Balance(amount=FVal('1000')),
            location_label=ADDY,
            notes=f'Receive 1000 LDO as the result of a swap via {CPT_UNISWAP_V3} auto router',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0xE592427A0AEce92De3Edee1F18E0157C05861564'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_2]])
def test_uniswap_v3_swap_received_token2(ethereum_inquirer):
    """This test checks that the logic is correct when the asset leaving the pool is the token2 of
    the pool."""
    tx_hash = deserialize_evm_tx_hash('0x116b3a9c0b2a4857605e336438c8e4c91897a9ef2af23178f9dbceba85264bd9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1662545418000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('0.001877273972926392')),
            location_label=ADDY_2,
            notes='Burned 0.001877273972926392 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1662545418000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDC,
            balance=Balance(amount=FVal('75000')),
            location_label=ADDY_2,
            notes=f'Swap 75000 USDC via {CPT_UNISWAP_V3} auto router',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1662545418000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('49.523026278486536412')),
            location_label=ADDY_2,
            notes=f'Receive 49.523026278486536412 ETH as the result of a swap via {CPT_UNISWAP_V3} auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_3]])
def test_uniswap_v3_swap_by_aggregator(ethereum_inquirer):
    """This checks that swap(s) initiated by an aggregator is decoded properly."""
    tx_hash = deserialize_evm_tx_hash('0x14e73a3bbced025ae22245eae0045972c1664fc01038b2ba6b1153590f536948')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=253,
            timestamp=TimestampMS(1669210175000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=EvmToken(ethaddress_to_identifier('0xd9Fcd98c322942075A5C3860693e9f4f03AAE07b')),
            balance=Balance(amount=FVal('115792089237316195423570985008687907853269984665640564038943.947794834569945164')),
            location_label=ADDY_3,
            notes='Set EUL spending approval of 0xdD84Ce1aDcb3A4908Db61A1dFA3353C3974c5a2B by 0xC92E8bdf79f0507f65a392b0ab4667716BFE0110 to 115792089237316195423570985008687907853269984665640564038943.947794834569945164',  # noqa: E501
            address=string_to_evm_address('0xC92E8bdf79f0507f65a392b0ab4667716BFE0110'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=254,
            timestamp=TimestampMS(1669210175000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0xd9Fcd98c322942075A5C3860693e9f4f03AAE07b'),
            balance=Balance(amount=FVal('213.775675238143698145')),
            location_label=ADDY_3,
            notes='Swap 213.775675238143698145 EUL in a cowswap market order',
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=255,
            timestamp=TimestampMS(1669210175000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.738572737905232914')),
            location_label=ADDY_3,
            notes='Receive 0.738572737905232914 ETH as the result of a cowswap market order',
            address=string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41'),
            counterparty=CPT_COWSWAP,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=256,
            timestamp=TimestampMS(1669210175000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('eip155:1/erc20:0xd9Fcd98c322942075A5C3860693e9f4f03AAE07b'),
            balance=Balance(amount=FVal('0.426141931873249088')),
            location_label=ADDY_3,
            notes='Spend 0.426141931873249088 EUL as a cowswap fee',
            address=string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41'),
            counterparty=CPT_COWSWAP,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd6f2F8a2D6BD2f06234a95e61b55f41676CbE50d']])
def test_swap_eth_to_tokens(ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0xaf8755f0ab8a0cfa8901fe2a9250a8727cca54825210061aab90f34b7a3ed9ba')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1641528717000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('0.082968903798164815')),
            location_label=user_address,
            notes='Burned 0.082968903798164815 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1641528717000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('262')),
            location_label=user_address,
            notes=f'Swap 262 ETH via {CPT_UNISWAP_V3} auto router',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1641528717000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            balance=Balance(amount=FVal('841047.621362')),
            location_label=user_address,
            notes=f'Receive 841047.621362 USDC as the result of a swap via {CPT_UNISWAP_V3} auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x4bBa290826C253BD854121346c370a9886d1bC26']])
def test_swap_eth_to_tokens_refund(ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x265c15c2b77090afb164f4c723b158f10d94853a705eda67410a340fc0113ece')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1669924223000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00142634334688392')),
            location_label=user_address,
            notes='Burned 0.00142634334688392 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1669924223000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.003918934703639028')),
            location_label=user_address,
            notes=f'Swap 0.003918934703639028 ETH via {CPT_UNISWAP_V3} auto router',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1669924223000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USDT,
            balance=Balance(amount=FVal('5')),
            location_label=user_address,
            notes=f'Receive 5 USDT as the result of a swap via {CPT_UNISWAP_V3} auto router',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd6f2F8a2D6BD2f06234a95e61b55f41676CbE50d']])
def test_swap_tokens_to_eth(ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x1b6c3fe84ed4f8f273a54c3e3f6ba80f843522c6a19220a05089104fc54b09ba')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1655541881000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('0.03490929635453643')),
            location_label=user_address,
            notes='Burned 0.03490929635453643 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1655541881000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            balance=Balance(amount=FVal('150000')),
            location_label=user_address,
            notes=f'Swap 150000 USDC via {CPT_UNISWAP_V3} auto router',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1655541881000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('150.306972002256248665')),
            location_label=user_address,
            notes=f'Receive 150.306972002256248665 ETH as the result of a swap via {CPT_UNISWAP_V3} auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xCDeBA740656640fCA1A7b573e925f8C3b92f76b6']])
def test_swap_tokens_to_tokens_single_receipt(ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x3ae92fa63a9cf672906036beb18ece09592a8a471bd7f15e4385ca5011615e51')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1643060358000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.074007294410979132')),
            location_label=user_address,
            notes='Burned 0.074007294410979132 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1643060358000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0xa47c8bf37f92aBed4A126BDA807A7b7498661acD'),
            balance=Balance(amount=FVal('3000000')),
            location_label=user_address,
            notes=f'Swap 3000000 UST via {CPT_UNISWAP_V3} auto router',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1643060358000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            balance=Balance(amount=FVal('2994089.109716')),
            location_label=user_address,
            notes=f'Receive 2994089.109716 USDC as the result of a swap via {CPT_UNISWAP_V3} auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x73264d8bE9EDDfCD25E4d54BF1b69828c9631A1C']])
def test_swap_tokens_to_tokens_multiple_receipts(ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0xa4e0dbf77bf7a9721e1ba4ecf44ed6ea8dcb1c16e9e784b6fefa30749f64e7c0')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1658331886000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.049823244141159502')),
            location_label=user_address,
            notes='Burned 0.049823244141159502 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1658331886000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'),
            balance=Balance(amount=FVal('224.18247796')),
            location_label=user_address,
            notes=f'Swap 224.18247796 WBTC via {CPT_UNISWAP_V3} auto router',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1658331886000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'),
            balance=Balance(amount=FVal('5326023.631679255788142165')),
            location_label=user_address,
            notes=f'Receive 5326023.631679255788142165 DAI as the result of a swap via {CPT_UNISWAP_V3} auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_4]])
def test_uniswap_v3_remove_liquidity(ethereum_inquirer):
    """
    Check that removing liquidity from Uniswap V3 LP is decoded properly.

    Data is taken from:
    https://etherscan.io/tx/0x76c312fe1c8604de5175c37dcbbb99cc8699336f3e4840e9e29e3383970f6c6d
    """
    tx_hash = deserialize_evm_tx_hash('0x76c312fe1c8604de5175c37dcbbb99cc8699336f3e4840e9e29e3383970f6c6d ')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert len(events) == 3
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1672413263000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.004505819651212348')),
            location_label=ADDY_4,
            notes='Burned 0.004505819651212348 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1672413263000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal('1000.374356073654694973')),
            location_label=ADDY_4,
            notes='Remove 1000.374356073654694973 ETH from uniswap-v3 LP 389043',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=55,
            timestamp=TimestampMS(1672413263000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_USDC,
            balance=Balance(amount=FVal('198401.464386')),
            location_label=ADDY_4,
            notes='Remove 198401.464386 USDC from uniswap-v3 LP 389043',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_5]])
def test_uniswap_v3_add_liquidity(ethereum_inquirer):
    """Check that adding liquidity to a Uniswap V3 LP is decoded properly."""
    tx_hash = deserialize_evm_tx_hash('0x6bf3588f669a784adf5def3c0db149b0cdbcca775e472bb35f00acedee263c4c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1672409279000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.005657780314871785')),
            location_label=ADDY_5,
            notes='Burned 0.005657780314871785 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=308,
            timestamp=TimestampMS(1672409279000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_DAI,
            balance=Balance(amount=FVal('11257.999999195502514358')),
            location_label=ADDY_5,
            notes='Deposit 11257.999999195502514358 DAI to uniswap-v3 LP 401357',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x5777d92f208679DB4b9778590Fa3CAB3aC9e2168'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=309,
            timestamp=TimestampMS(1672409279000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_USDC,
            balance=Balance(amount=FVal('13732.357062')),
            location_label=ADDY_5,
            notes='Deposit 13732.357062 USDC to uniswap-v3 LP 401357',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x5777d92f208679DB4b9778590Fa3CAB3aC9e2168'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=311,
            timestamp=TimestampMS(1672409279000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPLOY,
            event_subtype=HistoryEventSubType.NFT,
            asset=Asset('eip155:1/erc721:0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
            balance=Balance(amount=FVal(1)),
            location_label=ADDY_5,
            notes='Create uniswap-v3 LP with id 401357',
            counterparty=CPT_UNISWAP_V3,
            address=ZERO_ADDRESS,
            extra_data={'token_id': 401357, 'token_name': 'Uniswap V3 Positions NFT-V1'},
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xf615a55e686499511557b3F75Ea9166DD455bFd5']])
def test_uniswap_v3_swap_by_universal_router(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xd2fe13a9727b2ff3f9458154afb8e59216864b57e0aacffeedc3d3d4cff1c43d')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1698949487000)
    assert events == [EvmEvent(
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(0.007013719187732112)),
        location_label=user_address,
        notes='Burned 0.007013719187732112 ETH for gas',
        tx_hash=tx_hash,
        counterparty=CPT_GAS,
    ), EvmEvent(
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_LUSD,
        balance=Balance(amount=FVal('29998.270067672164822565')),
        location_label=user_address,
        notes='Swap 29998.270067672164822565 LUSD via uniswap-v3 auto router',
        tx_hash=tx_hash,
        counterparty=CPT_UNISWAP_V3,
        address='0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD',
    ), EvmEvent(
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        balance=Balance(amount=FVal('16.48341101375048316')),
        location_label=user_address,
        notes='Receive 16.48341101375048316 ETH as the result of a swap via uniswap-v3 auto router',  # noqa: E501
        tx_hash=tx_hash,
        counterparty=CPT_UNISWAP_V3,
        address='0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD',
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xb26655EBEe9DFA2f8D20523FE7CaE45CBe0122A2']])
def test_uniswap_v3_weth_deposit(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xdb9a489fa0404facc9ee514ce9e08a8dffdd5bbc051ed1fbc8d165cc4dc408f3 ')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1705025555000)
    rai_amount, weth_amount = '5409.802671424102374943', '5.964487282596591371'
    nft_id = '645638'

    assert events == [EvmEvent(
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        balance=Balance(amount=ZERO),
        location_label=string_to_evm_address('0x9e753054aedE94A2648d4D9d4Efa4f7e5aE82cb5'),
        notes='Successfully executed safe transaction 0xaae7b65fed168006d9d786c6f60f0f6c549e0189df7f6b101b185bbc538a8469 for multisig 0xb26655EBEe9DFA2f8D20523FE7CaE45CBe0122A2',  # noqa: E501
        tx_hash=tx_hash,
        counterparty=CPT_SAFE_MULTISIG,
        address='0xb26655EBEe9DFA2f8D20523FE7CaE45CBe0122A2',
    ), EvmEvent(
        sequence_index=97,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=Asset('eip155:1/erc20:0x03ab458634910AaD20eF5f1C8ee96F1D6ac54919'),
        balance=Balance(amount=FVal(rai_amount)),
        location_label=user_address,
        notes=f'Deposit {rai_amount} RAI to uniswap-v3 LP {nft_id}',
        tx_hash=tx_hash,
        counterparty=CPT_UNISWAP_V3,
        address='0x0dc9877F6024CCf16a470a74176C9260beb83AB6',
    ), EvmEvent(
        sequence_index=98,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_WETH,
        balance=Balance(amount=FVal(weth_amount)),
        location_label=user_address,
        notes=f'Deposit {weth_amount} WETH to uniswap-v3 LP {nft_id}',
        tx_hash=tx_hash,
        counterparty=CPT_UNISWAP_V3,
        address='0x0dc9877F6024CCf16a470a74176C9260beb83AB6',
    ), EvmEvent(
        sequence_index=100,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPLOY,
        event_subtype=HistoryEventSubType.NFT,
        asset=Asset('eip155:1/erc721:0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
        balance=Balance(amount=ONE),
        location_label=string_to_evm_address('0xb26655EBEe9DFA2f8D20523FE7CaE45CBe0122A2'),
        notes=f'Create uniswap-v3 LP with id {nft_id}',
        tx_hash=tx_hash,
        counterparty=CPT_UNISWAP_V3,
        address=ZERO_ADDRESS,
        extra_data={
            'token_id': int(nft_id),
            'token_name': 'Uniswap V3 Positions NFT-V1',
        },
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xEEb775c27a0d476B145d2e3B4dCd10A0A5Bd064F']])
def test_swap_on_arbitrum(arbitrum_one_inquirer, arbitrum_one_accounts):
    evmhash = deserialize_evm_tx_hash('0x8fe6f4f80e34eebc8e61ad638d57fde3ec4a975817ee08ab209562d00a6aa217')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=evmhash,
    )
    timestamp, swap_amount, receive_amount, gas_fees = TimestampMS(1710224315000), '0.21', '416.708088668961143612', '0.0001952302'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=arbitrum_one_accounts[0],
            notes=f'Burned {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal(swap_amount)),
            location_label=arbitrum_one_accounts[0],
            notes=f'Swap {swap_amount} ETH via {CPT_UNISWAP_V3} auto router',
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ARB,
            balance=Balance(amount=FVal(receive_amount)),
            location_label=arbitrum_one_accounts[0],
            notes=f'Receive {receive_amount} ARB as the result of a swap via {CPT_UNISWAP_V3} auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x3A4E1e525FaE9001037936164fC440df6E71f412']])
def test_swap_on_base(base_inquirer, base_accounts):
    evmhash = deserialize_evm_tx_hash('0x2125ff35709009b9782f8351db3cb5a44a0bf088c3f38de08d92eb3906394635')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=evmhash)
    timestamp, swap_amount, receive_amount, gas_fees = TimestampMS(1710230035000), '0.005', '10083924.460996717903453391', '0.000189731906791024'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=base_accounts[0],
            notes=f'Burned {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal(swap_amount)),
            location_label=base_accounts[0],
            notes=f'Swap {swap_amount} ETH via {CPT_UNISWAP_V3} auto router',
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:8453/erc20:0x7299cD731d0712dB09E7dF43fD670D75Db3319Bc'),
            balance=Balance(amount=FVal(receive_amount)),
            location_label=base_accounts[0],
            notes=f'Receive {receive_amount} NESSY as the result of a swap via {CPT_UNISWAP_V3} auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x8BAf1bBae7C3Cc1F9c5Bf20b3d13BBfe674B01B7']])
def test_swap_on_optimism(optimism_inquirer, optimism_accounts):
    evmhash = deserialize_evm_tx_hash('0xfbaacab45a9d788c993f08a65652e7a363a82ee2343152ffa41d07c5456d1fe7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=evmhash)
    timestamp, swap_amount, receive_amount, gas_fees = TimestampMS(1710230523000), '23.093637251974648887', '23.084554', '0.000335793972468462'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=optimism_accounts[0],
            notes=f'Burned {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:10/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1'),
            balance=Balance(amount=FVal(swap_amount)),
            location_label=optimism_accounts[0],
            notes=f'Swap {swap_amount} DAI via {CPT_UNISWAP_V3} auto router',
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
            balance=Balance(amount=FVal(receive_amount)),
            location_label=optimism_accounts[0],
            notes=f'Receive {receive_amount} USDC.e as the result of a swap via {CPT_UNISWAP_V3} auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x9d38bC769b4E88da3f4c31a06b626ef88a21065C']])
def test_swap_on_polygon_pos(polygon_pos_inquirer, polygon_pos_accounts):
    evmhash = deserialize_evm_tx_hash('0x2004f7b593d4ddf9372d78adb4b89852fa70eafa42418793b142a881b4171974')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=evmhash,
    )
    timestamp, swap_amount, receive_amount, gas_fees = TimestampMS(1710231022000), '0.017521626565388156', '0.00097703', '0.025131590391178764'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POLYGON_POS_MATIC,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=polygon_pos_accounts[0],
            notes=f'Burned {gas_fees} MATIC for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_WETH_POLYGON,
            balance=Balance(amount=FVal(swap_amount)),
            location_label=polygon_pos_accounts[0],
            notes=f'Swap {swap_amount} WETH via {CPT_UNISWAP_V3} auto router',
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:137/erc20:0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6'),
            balance=Balance(amount=FVal(receive_amount)),
            location_label=polygon_pos_accounts[0],
            notes=f'Receive {receive_amount} WBTC as the result of a swap via {CPT_UNISWAP_V3} auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x9A539f692cDE873D6B882fc326c8d62D4cEA8048']])
def test_add_liquidity_on_optimism(optimism_inquirer, optimism_accounts):
    evmhash = deserialize_evm_tx_hash('0x96bd0e37e1734b5e73f9abdf30b39c4e4a6879667c2d01a7be2d95a85cc0b0cc')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=evmhash)
    timestamp, approval, op_deposit, usdc_deposit, gas_fees = TimestampMS(1713269405000), '0.000129292741769402', '10975.908530657738737186', '32.212735', '0.000027353637451875'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=optimism_accounts[0],
            notes=f'Burned {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=45,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:10/erc20:0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'),  # USDC
            balance=Balance(amount=FVal(usdc_deposit)),
            location_label=optimism_accounts[0],
            notes=f'Deposit {usdc_deposit} USDC to uniswap-v3 LP 550709',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0xB533c12fB4e7b53b5524EAb9b47d93fF6C7A456F'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=46,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_OP,
            balance=Balance(amount=FVal(approval)),
            location_label=optimism_accounts[0],
            notes=f'Set OP spending approval of 0x9A539f692cDE873D6B882fc326c8d62D4cEA8048 by 0xC36442b4a4522E871399CD717aBDD847Ab11FE88 to {approval}',  # noqa: E501
            address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=47,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_OP,
            balance=Balance(amount=FVal(op_deposit)),
            location_label=optimism_accounts[0],
            notes=f'Deposit {op_deposit} OP to uniswap-v3 LP 550709',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0xB533c12fB4e7b53b5524EAb9b47d93fF6C7A456F'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=49,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPLOY,
            event_subtype=HistoryEventSubType.NFT,
            asset=Asset('eip155:10/erc721:0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
            balance=Balance(amount=FVal(1)),
            location_label=optimism_accounts[0],
            notes='Create uniswap-v3 LP with id 550709',
            counterparty=CPT_UNISWAP_V3,
            address=ZERO_ADDRESS,
            extra_data={'token_id': 550709, 'token_name': 'Uniswap V3 Positions NFT-V1'},
        ),
    ]
    assert events == expected_events
