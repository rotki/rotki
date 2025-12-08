from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.utils import get_evm_token
from rotkehlchen.chain.base.modules.uniswap.v3.constants import UNISWAP_UNIVERSAL_ROUTER
from rotkehlchen.chain.binance_sc.modules.uniswap.v3.constants import (
    UNISWAP_UNIVERSAL_ROUTER as UNISWAP_UNIVERSAL_ROUTER_BINANCE_SC,
)
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.uniswap.v3.constants import UNISWAP_UNIVERSAL_ROUTER_V2
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.cowswap.constants import CPT_COWSWAP
from rotkehlchen.chain.evm.decoding.safe.constants import CPT_SAFE_MULTISIG
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V3
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import (
    A_ARB,
    A_BSC_BNB,
    A_DAI,
    A_ETH,
    A_LUSD,
    A_OP,
    A_POL,
    A_USDC,
    A_USDT,
    A_WETH,
    A_WETH_POLYGON,
)
from rotkehlchen.constants.misc import ONE
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.unit.test_types import LEGACY_TESTS_INDEXER_ORDER
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
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer

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
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1635998362000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.038293427380094972'),
            location_label=ADDY,
            notes='Burn 0.038293427380094972 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1635998362000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('0.632989659350357136'),
            location_label=ADDY,
            notes='Swap 0.632989659350357136 ETH via Uniswap V3 auto router',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0xE592427A0AEce92De3Edee1F18E0157C05861564'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1635998362000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'),
            amount=FVal('1000'),
            location_label=ADDY,
            notes='Receive 1000 LDO as the result of a swap via Uniswap V3 auto router',
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
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1662545418000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            amount=FVal('0.001877273972926392'),
            location_label=ADDY_2,
            notes='Burn 0.001877273972926392 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1662545418000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDC,
            amount=FVal('75000'),
            location_label=ADDY_2,
            notes='Swap 75000 USDC via Uniswap V3 auto router',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1662545418000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('ETH'),
            amount=FVal('49.523026278486536412'),
            location_label=ADDY_2,
            notes='Receive 49.523026278486536412 ETH as the result of a swap via Uniswap V3 auto router',  # noqa: E501
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
            tx_ref=tx_hash,
            sequence_index=253,
            timestamp=TimestampMS(1669210175000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=EvmToken(ethaddress_to_identifier('0xd9Fcd98c322942075A5C3860693e9f4f03AAE07b')),
            amount=FVal('115792089237316195423570985008687907853269984665640564038943.947794834569945164'),
            location_label=ADDY_3,
            notes='Set EUL spending approval of 0xdD84Ce1aDcb3A4908Db61A1dFA3353C3974c5a2B by 0xC92E8bdf79f0507f65a392b0ab4667716BFE0110 to 115792089237316195423570985008687907853269984665640564038943.947794834569945164',  # noqa: E501
            address=string_to_evm_address('0xC92E8bdf79f0507f65a392b0ab4667716BFE0110'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=254,
            timestamp=TimestampMS(1669210175000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0xd9Fcd98c322942075A5C3860693e9f4f03AAE07b'),
            amount=FVal('213.775675238143698145'),
            location_label=ADDY_3,
            notes='Swap 213.775675238143698145 EUL in a cowswap market order',
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=255,
            timestamp=TimestampMS(1669210175000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('0.738572737905232914'),
            location_label=ADDY_3,
            notes='Receive 0.738572737905232914 ETH as the result of a cowswap market order',
            address=string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41'),
            counterparty=CPT_COWSWAP,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=256,
            timestamp=TimestampMS(1669210175000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('eip155:1/erc20:0xd9Fcd98c322942075A5C3860693e9f4f03AAE07b'),
            amount=FVal('0.426141931873249088'),
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
    tx_hash = deserialize_evm_tx_hash('0xaf8755f0ab8a0cfa8901fe2a9250a8727cca54825210061aab90f34b7a3ed9ba')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1641528717000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            amount=FVal('0.082968903798164815'),
            location_label=user_address,
            notes='Burn 0.082968903798164815 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1641528717000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('ETH'),
            amount=FVal('262'),
            location_label=user_address,
            notes='Swap 262 ETH via Uniswap V3 auto router',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1641528717000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            amount=FVal('841047.621362'),
            location_label=user_address,
            notes='Receive 841047.621362 USDC as the result of a swap via Uniswap V3 auto router',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x4bBa290826C253BD854121346c370a9886d1bC26']])
def test_swap_eth_to_tokens_refund(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x265c15c2b77090afb164f4c723b158f10d94853a705eda67410a340fc0113ece')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1669924223000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00142634334688392'),
            location_label=user_address,
            notes='Burn 0.00142634334688392 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1669924223000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('0.003918934703639028'),
            location_label=user_address,
            notes='Swap 0.003918934703639028 ETH via Uniswap V3 auto router',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1669924223000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USDT,
            amount=FVal('5'),
            location_label=user_address,
            notes='Receive 5 USDT as the result of a swap via Uniswap V3 auto router',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd6f2F8a2D6BD2f06234a95e61b55f41676CbE50d']])
def test_swap_tokens_to_eth(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x1b6c3fe84ed4f8f273a54c3e3f6ba80f843522c6a19220a05089104fc54b09ba')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1655541881000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            amount=FVal('0.03490929635453643'),
            location_label=user_address,
            notes='Burn 0.03490929635453643 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1655541881000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            amount=FVal('150000'),
            location_label=user_address,
            notes='Swap 150000 USDC via Uniswap V3 auto router',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1655541881000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('ETH'),
            amount=FVal('150.306972002256248665'),
            location_label=user_address,
            notes='Receive 150.306972002256248665 ETH as the result of a swap via Uniswap V3 auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xCDeBA740656640fCA1A7b573e925f8C3b92f76b6']])
def test_swap_tokens_to_tokens_single_receipt(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x3ae92fa63a9cf672906036beb18ece09592a8a471bd7f15e4385ca5011615e51')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1643060358000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.074007294410979132'),
            location_label=user_address,
            notes='Burn 0.074007294410979132 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1643060358000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0xa47c8bf37f92aBed4A126BDA807A7b7498661acD'),
            amount=FVal('3000000'),
            location_label=user_address,
            notes='Swap 3000000 UST via Uniswap V3 auto router',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1643060358000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            amount=FVal('2994089.109716'),
            location_label=user_address,
            notes='Receive 2994089.109716 USDC as the result of a swap via Uniswap V3 auto router',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x73264d8bE9EDDfCD25E4d54BF1b69828c9631A1C']])
def test_swap_tokens_to_tokens_multiple_receipts(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xa4e0dbf77bf7a9721e1ba4ecf44ed6ea8dcb1c16e9e784b6fefa30749f64e7c0')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1658331886000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.049823244141159502'),
            location_label=user_address,
            notes='Burn 0.049823244141159502 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1658331886000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'),
            amount=FVal('224.18247796'),
            location_label=user_address,
            notes='Swap 224.18247796 WBTC via Uniswap V3 auto router',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1658331886000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'),
            amount=FVal('5326023.631679255788142165'),
            location_label=user_address,
            notes='Receive 5326023.631679255788142165 DAI as the result of a swap via Uniswap V3 auto router',  # noqa: E501
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
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1672413263000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.004505819651212348'),
            location_label=ADDY_4,
            notes='Burn 0.004505819651212348 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1672413263000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            amount=FVal('1000.374356073654694973'),
            location_label=ADDY_4,
            notes='Remove 1000.374356073654694973 ETH from Uniswap V3 LP 389043',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1672413263000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_USDC,
            amount=FVal('198401.464386'),
            location_label=ADDY_4,
            notes='Remove 198401.464386 USDC from Uniswap V3 LP 389043',
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
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1672409279000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.005657780314871785'),
            location_label=ADDY_5,
            notes='Burn 0.005657780314871785 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1672409279000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_DAI,
            amount=FVal('11257.999999195502514358'),
            location_label=ADDY_5,
            notes='Deposit 11257.999999195502514358 DAI to Uniswap V3 LP 401357',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x5777d92f208679DB4b9778590Fa3CAB3aC9e2168'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1672409279000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_USDC,
            amount=FVal('13732.357062'),
            location_label=ADDY_5,
            notes='Deposit 13732.357062 USDC to Uniswap V3 LP 401357',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x5777d92f208679DB4b9778590Fa3CAB3aC9e2168'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=3,
            timestamp=TimestampMS(1672409279000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc721:0xC36442b4a4522E871399CD717aBDD847Ab11FE88/401357'),
            amount=ONE,
            location_label=ADDY_5,
            notes='Create Uniswap V3 LP with id 401357',
            counterparty=CPT_UNISWAP_V3,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events

    # Ensure the position token's name and symbol are set correctly
    position_token = get_evm_token(
        evm_address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC721,
        collectible_id=(collectible_id := '401357'),
    )
    assert position_token.name == f'Uniswap V3 Positions #{collectible_id}'
    assert position_token.symbol == f'UNI-V3-POS-{collectible_id}'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
def test_uniswap_v3_create_lp_position_with_native_refund(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test decoding of a lp creation with a native token deposit where a small amount of the
    deposited native token is returned (receive amount is subtracted from the deposit and the
    receive event is removed).
    """
    tx_hash = deserialize_evm_tx_hash('0x0ca4942007ea1e93a7b979da6066bb9b5ac25c14ebd8a8a4002bd03c339c0606')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1755714977000)),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000004389183915'),
        location_label=(user_address := arbitrum_one_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=4,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:42161/erc20:0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f'),
        amount=FVal(approve_amount := '1157920892373161954235709850086879078532699846656405640394575840079131.29623426'),  # noqa: E501
        location_label=user_address,
        address=(nft_manager := string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88')),  # noqa: E501
        notes=f'Set WBTC spending approval of {user_address} by {nft_manager} to {approve_amount}',  # type: ignore
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=5,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_ETH,
        amount=FVal(eth_amount := '0.004921550321882571'),
        location_label=user_address,
        notes=f'Deposit {eth_amount} ETH to Uniswap V3 LP 4818837',
        counterparty=CPT_UNISWAP_V3,
        address=nft_manager,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=6,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:42161/erc20:0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f'),
        amount=FVal(wbtc_amount := '0.00016509'),
        location_label=user_address,
        notes=f'Deposit {wbtc_amount} WBTC to Uniswap V3 LP 4818837',
        counterparty=CPT_UNISWAP_V3,
        address=string_to_evm_address('0x2f5e87C9312fa29aed5c179E456625D79015299c'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=7,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:42161/erc721:0xC36442b4a4522E871399CD717aBDD847Ab11FE88/4818837'),
        amount=ONE,
        location_label=user_address,
        notes='Create Uniswap V3 LP with id 4818837',
        counterparty=CPT_UNISWAP_V3,
        address=ZERO_ADDRESS,
    )]


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
        amount=FVal(0.007013719187732112),
        location_label=user_address,
        notes='Burn 0.007013719187732112 ETH for gas',
        tx_ref=tx_hash,
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_LUSD,
        amount=FVal('29998.270067672164822565'),
        location_label=user_address,
        notes='Swap 29998.270067672164822565 LUSD via Uniswap V3 auto router',
        tx_ref=tx_hash,
        counterparty=CPT_UNISWAP_V3,
        address='0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD',
    ), EvmSwapEvent(
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal('16.48341101375048316'),
        location_label=user_address,
        notes='Receive 16.48341101375048316 ETH as the result of a swap via Uniswap V3 auto router',  # noqa: E501
        tx_ref=tx_hash,
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
        sequence_index=102,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ZERO,
        location_label=string_to_evm_address('0x9e753054aedE94A2648d4D9d4Efa4f7e5aE82cb5'),
        notes=f'Successfully executed safe transaction 0xaae7b65fed168006d9d786c6f60f0f6c549e0189df7f6b101b185bbc538a8469 for multisig {user_address}',  # noqa: E501
        tx_ref=tx_hash,
        counterparty=CPT_SAFE_MULTISIG,
        address=user_address,
    ), EvmEvent(
        sequence_index=103,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:1/erc20:0x03ab458634910AaD20eF5f1C8ee96F1D6ac54919'),
        amount=FVal(rai_amount),
        location_label=user_address,
        notes=f'Deposit {rai_amount} RAI to Uniswap V3 LP {nft_id}',
        tx_ref=tx_hash,
        counterparty=CPT_UNISWAP_V3,
        address=(pool_address := string_to_evm_address('0x0dc9877F6024CCf16a470a74176C9260beb83AB6')),  # noqa: E501
    ), EvmEvent(
        sequence_index=104,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_WETH,
        amount=FVal(weth_amount),
        location_label=user_address,
        notes=f'Deposit {weth_amount} WETH to Uniswap V3 LP {nft_id}',
        tx_ref=tx_hash,
        counterparty=CPT_UNISWAP_V3,
        address=pool_address,
    ), EvmEvent(
        sequence_index=105,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset(f'eip155:1/erc721:0xC36442b4a4522E871399CD717aBDD847Ab11FE88/{nft_id}'),
        amount=ONE,
        location_label=string_to_evm_address('0xb26655EBEe9DFA2f8D20523FE7CaE45CBe0122A2'),
        notes=f'Create Uniswap V3 LP with id {nft_id}',
        tx_ref=tx_hash,
        counterparty=CPT_UNISWAP_V3,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xEEb775c27a0d476B145d2e3B4dCd10A0A5Bd064F']])
def test_swap_on_arbitrum(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x8fe6f4f80e34eebc8e61ad638d57fde3ec4a975817ee08ab209562d00a6aa217')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, swap_amount, receive_amount, gas_fees = TimestampMS(1710224315000), '0.21', '416.708088668961143612', '0.0001952302'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=arbitrum_one_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal(swap_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Swap {swap_amount} ETH via Uniswap V3 auto router',
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ARB,
            amount=FVal(receive_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Receive {receive_amount} ARB as the result of a swap via Uniswap V3 auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('base_accounts', [['0x3A4E1e525FaE9001037936164fC440df6E71f412']])
def test_swap_on_base(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2125ff35709009b9782f8351db3cb5a44a0bf088c3f38de08d92eb3906394635')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp, swap_amount, receive_amount, gas_fees = TimestampMS(1710230035000), '0.005', '10083924.460996717903453391', '0.000189731906791024'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=base_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal(swap_amount),
            location_label=base_accounts[0],
            notes=f'Swap {swap_amount} ETH via Uniswap V3 auto router',
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:8453/erc20:0x7299cD731d0712dB09E7dF43fD670D75Db3319Bc'),
            amount=FVal(receive_amount),
            location_label=base_accounts[0],
            notes=f'Receive {receive_amount} NESSY as the result of a swap via Uniswap V3 auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('optimism_accounts', [['0x8BAf1bBae7C3Cc1F9c5Bf20b3d13BBfe674B01B7']])
def test_swap_on_optimism(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0xfbaacab45a9d788c993f08a65652e7a363a82ee2343152ffa41d07c5456d1fe7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, swap_amount, receive_amount, gas_fees = TimestampMS(1710230523000), '23.093637251974648887', '23.084554', '0.000335793972468462'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=optimism_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:10/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1'),
            amount=FVal(swap_amount),
            location_label=optimism_accounts[0],
            notes=f'Swap {swap_amount} DAI via Uniswap V3 auto router',
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
            amount=FVal(receive_amount),
            location_label=optimism_accounts[0],
            notes=f'Receive {receive_amount} USDC.e as the result of a swap via Uniswap V3 auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x9d38bC769b4E88da3f4c31a06b626ef88a21065C']])
def test_swap_on_polygon_pos(polygon_pos_inquirer, polygon_pos_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2004f7b593d4ddf9372d78adb4b89852fa70eafa42418793b142a881b4171974')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, swap_amount, receive_amount, gas_fees = TimestampMS(1710231022000), '0.017521626565388156', '0.00097703', '0.025131590391178764'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POL,
            amount=FVal(gas_fees),
            location_label=polygon_pos_accounts[0],
            notes=f'Burn {gas_fees} POL for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_WETH_POLYGON,
            amount=FVal(swap_amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Swap {swap_amount} WETH via Uniswap V3 auto router',
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:137/erc20:0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6'),
            amount=FVal(receive_amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Receive {receive_amount} WBTC as the result of a swap via Uniswap V3 auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('optimism_accounts', [['0x9A539f692cDE873D6B882fc326c8d62D4cEA8048']])
def test_add_liquidity_on_optimism(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0x96bd0e37e1734b5e73f9abdf30b39c4e4a6879667c2d01a7be2d95a85cc0b0cc')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, approval, op_deposit, usdc_deposit, gas_fees = TimestampMS(1713269405000), '0.000129292741769402', '10975.908530657738737186', '32.212735', '0.000027353637451875'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=optimism_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=46,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_OP,
            amount=FVal(approval),
            location_label=optimism_accounts[0],
            notes=f'Set OP spending approval of 0x9A539f692cDE873D6B882fc326c8d62D4cEA8048 by 0xC36442b4a4522E871399CD717aBDD847Ab11FE88 to {approval}',  # noqa: E501
            address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=47,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:10/erc20:0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'),  # USDC
            amount=FVal(usdc_deposit),
            location_label=optimism_accounts[0],
            notes=f'Deposit {usdc_deposit} USDC to Uniswap V3 LP 550709',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0xB533c12fB4e7b53b5524EAb9b47d93fF6C7A456F'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=48,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_OP,
            amount=FVal(op_deposit),
            location_label=optimism_accounts[0],
            notes=f'Deposit {op_deposit} OP to Uniswap V3 LP 550709',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0xB533c12fB4e7b53b5524EAb9b47d93fF6C7A456F'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=49,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:10/erc721:0xC36442b4a4522E871399CD717aBDD847Ab11FE88/550709'),
            amount=ONE,
            location_label=optimism_accounts[0],
            notes='Create Uniswap V3 LP with id 550709',
            counterparty=CPT_UNISWAP_V3,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('binance_sc_accounts', [['0xEF575087F1e7BeC54046F98119c8C392a37c51dd']])
def test_swap_on_binance_sc(
        binance_sc_inquirer: 'BinanceSCInquirer',
        binance_sc_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x3cfb94c6c4a3ba05759cab565148fe5a0c1894479603c29c6c2201dbed943365')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=binance_sc_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_amount, swap_amount, receive_amount = binance_sc_accounts[0], TimestampMS(1736264377000), '0.000675955', '0.671147484158020414', '3.3'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BINANCE_SC,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_BSC_BNB,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} BNB for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BINANCE_SC,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:56/erc20:0x2170Ed0880ac9A755fd29B2688956BD959F933F8'),
            amount=FVal(swap_amount),
            location_label=user_address,
            notes=f'Swap {swap_amount} ETH via Uniswap V3 auto router',
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER_BINANCE_SC,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BINANCE_SC,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_BSC_BNB,
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} BNB as the result of a swap via Uniswap V3 auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER_BINANCE_SC,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
def test_receive_position_token_on_arbitrum(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that erc721 approval and transfer events work correctly.
    The approval event is on an untracked address, but is what creates the token initially.
    Regression test for https://github.com/rotki/rotki/pull/9286
    Since this transaction is interacting with the currently unsupported Krystal ALM protocol's
    V3Utils contract (https://alm-docs.krystal.app/resources/smart-contracts), these events are
    simply decoded as plain transfers and are not ordered correctly.
    """
    tx_hash = deserialize_evm_tx_hash('0xbdfe4bfba8932fafed46a0cae44a945088c2496e1ef3c643d315159f900c338b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_amount, spend_amount, receive_amount, v3utils_contract = arbitrum_one_accounts[0], TimestampMS(1718052436000), '0.00002126616', '100.768463', '0.000044879191744967', string_to_evm_address('0x3991bA795fb13a7646a8745F90b0F24Ed2443b03')  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
        amount=FVal(spend_amount),
        location_label=user_address,
        notes=f'Send {spend_amount} USDC from {user_address} to {v3utils_contract}',
        address=v3utils_contract,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=47,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=Asset('eip155:42161/erc721:0xC36442b4a4522E871399CD717aBDD847Ab11FE88/2985371'),
        amount=ONE,
        location_label=user_address,
        notes=f'Receive Uniswap V3 Positions NFT-V1 with id 2985371 from {v3utils_contract} to {user_address}',  # noqa: E501
        address=v3utils_contract,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=49,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=Asset('eip155:42161/erc20:0x8B0E6f19Ee57089F7649A455D89D7bC6314D04e8'),
        amount=FVal(receive_amount),
        location_label=user_address,
        notes=f'Receive {receive_amount} DMT from {v3utils_contract} to {user_address}',
        address=v3utils_contract,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd48101E479159Ef88668De1E19f055DA42e8Fb8D']])
def test_uniswap_v3_universal_router_2(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x8c1aab138325e03f5bc20e676b8a242d470922003c3be4a76c386a4e67ce7bce')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1677356075000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.003983465486960712'),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal(amount_out := '0.000184539583537197'),
            location_label=ethereum_accounts[0],
            notes=f'Swap {amount_out} ETH via Uniswap V3 auto router',
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER_V2,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=EvmToken('eip155:1/erc20:0x744d70FDBE2Ba4CF95131626614a1763DF805B9E'),  # SNT
            amount=FVal(amount_in := '10'),
            location_label=ethereum_accounts[0],
            notes=f'Receive {amount_in} SNT as the result of a swap via Uniswap V3 auto router',
            counterparty=CPT_UNISWAP_V3,
            address=UNISWAP_UNIVERSAL_ROUTER_V2,
        ),
    ]
    assert events == expected_events
