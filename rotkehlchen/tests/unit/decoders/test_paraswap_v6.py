from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.decoding.paraswap.constants import CPT_PARASWAP
from rotkehlchen.chain.evm.decoding.paraswap.v6.constants import PARASWAP_AUGUSTUS_V6_ROUTER
from rotkehlchen.constants.assets import (
    A_BSC_BNB,
    A_DAI,
    A_ENS,
    A_ETH,
    A_OP,
    A_POLYGON_POS_MATIC,
    A_USDC,
    A_USDT,
    A_WETH_ARB,
    A_XDAI,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.unit.decoders.test_paraswap import A_POLYGON_POS_USDC, A_PSP
from rotkehlchen.tests.utils.constants import A_OPTIMISM_USDT
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_swap_amount_in(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x04df701a75c3dc3f1283c6a26e668bec4bd92cf7f02e9963c3c887f5376c590e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp = ethereum_accounts[0], TimestampMS(1734128975000)
    gas_amount, spend_amount, receive_amount, approve_amount, fee_amount = '0.006552891211821796', '1238.300219686159982592', '53167.300753584463143634', '999999999999999999999998760.699780313840017408', '1.041075685722072692'  # noqa: E501
    assert events == [EvmEvent(
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
        sequence_index=145,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_ENS,
        amount=FVal(approve_amount),
        location_label=user_address,
        notes=f'Set ENS spending approval of {user_address} by {PARASWAP_AUGUSTUS_V6_ROUTER} to {approve_amount}',  # noqa: E501
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=146,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ENS,
        amount=FVal(spend_amount),
        location_label=user_address,
        notes=f'Swap {spend_amount} ENS in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=147,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_DAI,
        amount=FVal(receive_amount),
        location_label=user_address,
        notes=f'Receive {receive_amount} DAI as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=148,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_DAI,
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} DAI as a paraswap fee',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xbF4EBEa7279DE8517f60BD5fdbe9AebE03De90ED']])
def test_gnosis_swap_amount_in(
        gnosis_inquirer: 'GnosisInquirer',
        gnosis_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x421c23d305703a57ea0b64cfc75e8f13b6db2ef30fba321ae19eecd1b91695bc')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    user_address, timestamp = gnosis_accounts[0], TimestampMS(1735672410000)
    gas_amount, spend_amount, receive_amount, fee_amount = '0.000422270393343876', '4867.05', '5023.5716702210346498', '0.0000000000000006'  # noqa: E501
    a_eure = Asset('eip155:100/erc20:0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430')
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_XDAI,
        amount=FVal(gas_amount),
        location_label=user_address,
        notes=f'Burn {gas_amount} XDAI for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_subtype=HistoryEventSubType.SPEND,
        asset=a_eure,
        amount=FVal(spend_amount),
        location_label=user_address,
        notes=f'Swap {spend_amount} EURe in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_XDAI,
        amount=FVal(receive_amount),
        location_label=user_address,
        notes=f'Receive {receive_amount} XDAI as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_XDAI,
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} XDAI as a paraswap fee',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('binance_sc_accounts', [['0xB26c469c17154911AF343E506ED8eFcd77EebdA0']])
def test_binance_sc_swap_amount_in(
        binance_sc_inquirer: 'BinanceSCInquirer',
        binance_sc_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x770bf2e71644a14e8132bb0694c6b97107b5b6084dbea5d907b3d0d307388785')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=binance_sc_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_amount, spend_amount, receive_amount = binance_sc_accounts[0], TimestampMS(1736536768000), '0.000173659', '0.0015', '1.03547122626033016'  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_BSC_BNB,
        amount=FVal(spend_amount),
        location_label=user_address,
        notes=f'Swap {spend_amount} BNB in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:56/erc20:0x55d398326f99059fF775485246999027B3197955'),
        amount=FVal(receive_amount),
        location_label=user_address,
        notes=f'Receive {receive_amount} BSC-USD as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xd0b97E7a82c45dEc8a8b1b30Dd46C95937725C71']])
def test_swap_amount_in_on_balancer_v2(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x552ccefc137388007e6e6299f2c93f94852ca7bf838b2385b4f6f21cf1009bd3')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    user_address, timestamp = base_accounts[0], TimestampMS(1735294971000)
    gas_amount, spend_amount, receive_amount, fee_amount = '0.000006472538730227', '0.0007', '2.397762', '0.000189'  # noqa: E501
    a_usdbc = Asset('eip155:8453/erc20:0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA')
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount),
        location_label=user_address,
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BASE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(spend_amount),
        location_label=user_address,
        notes=f'Swap {spend_amount} ETH in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BASE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=a_usdbc,
        amount=FVal(receive_amount),
        location_label=user_address,
        notes=f'Receive {receive_amount} USDbC as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.BASE,
        event_subtype=HistoryEventSubType.FEE,
        asset=a_usdbc,
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} USDbC as a paraswap fee',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xcb3e623344178A91CA82777b51cDfC1155D5134a']])
def test_swap_amount_in_on_curve_v1(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0xf9a632e9cdf86b0af99d38b3bb83d8e73c115c181ca111b917f189851b7e0191')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp = arbitrum_one_accounts[0], TimestampMS(1735558953000)
    gas_amount, spend_amount, receive_amount, fee_amount = '0.00000448282', '1000', '1001.870050', '0.000294'  # noqa: E501
    a_bridged_usdc = Asset('eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8')
    a_usdt = Asset('eip155:42161/erc20:0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9')
    assert events == [EvmEvent(
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
        sequence_index=8,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=a_bridged_usdc,
        amount=ZERO,
        location_label=user_address,
        notes=f'Revoke USDC.e spending approval of {user_address} by {PARASWAP_AUGUSTUS_V6_ROUTER}',  # noqa: E501
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=9,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=a_bridged_usdc,
        amount=FVal(spend_amount),
        location_label=user_address,
        notes=f'Swap {spend_amount} USDC.e in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=10,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=a_usdt,
        amount=FVal(receive_amount),
        location_label=user_address,
        notes=f'Receive {receive_amount} USDT as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=11,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.FEE,
        asset=a_usdt,
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} USDT as a paraswap fee',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xA99f61aa6BA5665F62935F7d05Aa4A214a79E388']])
def test_swap_amount_in_on_curve_v2(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x6f3b9fae41f83f880f21e704962fb01de8f9b8be0e61fe6165c0bca3d8113492')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp = arbitrum_one_accounts[0], TimestampMS(1735343468000)
    gas_amount, spend_amount, receive_amount, approve_amount = '0.00000327561', '75752.06173519', '0.100234625527386499', '26602023.994064270347724293'  # noqa: E501
    a_gmac = Asset('eip155:42161/erc20:0xDc8B6B6bEab4d5034aE91B7A1cf7D05A41f0d239')
    assert events == [EvmEvent(
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
        asset=a_gmac,
        amount=FVal(approve_amount),
        location_label=user_address,
        notes=f'Set GMAC spending approval of {user_address} by {PARASWAP_AUGUSTUS_V6_ROUTER} to {approve_amount}',  # noqa: E501
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=a_gmac,
        amount=FVal(spend_amount),
        location_label=user_address,
        notes=f'Swap {spend_amount} GMAC in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=4,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_WETH_ARB,
        amount=FVal(receive_amount),
        location_label=user_address,
        notes=f'Receive {receive_amount} WETH as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x80A215BbA4Cb2eb51fb937140557EEFF5be4D552']])
def test_swap_amount_in_on_uniswap_v2(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x85ec582768ad89edd4541a73ff00b8f8cb51fdc0544f27f57b3452c9992f50d7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    user_address, timestamp = optimism_accounts[0], TimestampMS(1735562523000)
    gas_amount, spend_amount, receive_amount = '0.000007824286757602', '0.000002199165480099', '0.007498'  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount),
        location_label=user_address,
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(spend_amount),
        location_label=user_address,
        notes=f'Swap {spend_amount} ETH in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_OPTIMISM_USDT,
        amount=FVal(receive_amount),
        location_label=user_address,
        notes=f'Receive {receive_amount} USDT as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x4e6428489612D68e8fFe37e93eF147B413229d9D']])
def test_swap_amount_in_on_uniswap_v3(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0xd3cbe70512bcc026a29aa2baaa5d8466b44589b2ec212e46504312b15ec1aa58')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    user_address, timestamp = optimism_accounts[0], TimestampMS(1735645113000)
    gas_amount, spend_amount, receive_amount = '0.000000490133458226', '250', '138.185435850061640894'  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.OPTIMISM,
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
        location=Location.OPTIMISM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_OPTIMISM_USDT,
        amount=ZERO,
        location_label=user_address,
        notes=f'Revoke USDT spending approval of {user_address} by {PARASWAP_AUGUSTUS_V6_ROUTER}',
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_OPTIMISM_USDT,
        amount=FVal(spend_amount),
        location_label=user_address,
        notes=f'Swap {spend_amount} USDT in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_OP,
        amount=FVal(receive_amount),
        location_label=user_address,
        notes=f'Receive {receive_amount} OP as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd7E5cF676A0Baa36a4Ae9FB921dEB8c8EFC1D873']])
def test_swap_amount_out(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x50cf628b1214b6c2a2bdd044c9b8c406e556d0772146b367b9a05cace0eb63ee')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp = ethereum_accounts[0], TimestampMS(1735636607000)
    gas_amount, spend_amount, receive_amount, fee_amount = '0.006876240225525588', '12834.982319', '100000', '130.256893'  # noqa: E501
    assert events == [EvmEvent(
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
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDC,
        amount=FVal(spend_amount),
        location_label=user_address,
        notes=f'Swap {spend_amount} USDC in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc20:0x26E550AC11B26f78A04489d5F20f24E3559f7Dd9'),
        amount=FVal(receive_amount),
        location_label=user_address,
        notes=f'Receive {receive_amount} KEKIUS as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USDC,
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} USDC as a paraswap fee',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xAA3279F1e2f9D53ED621E84137b48882caF7fA0A']])
def test_swap_amount_out_on_balancer_v2(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x46b617b4b4ac2cc4955f5da9542ed7da98559d12effef704dc86dc4986330693')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp = ethereum_accounts[0], TimestampMS(1735560491000)
    gas_amount, spend_amount, receive_amount, fee_amount = '0.000681291880210914', '0.074748826042431161', '10000', '0.00011195530610449'  # noqa: E501
    assert events == [EvmEvent(
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
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(spend_amount),
        location_label=user_address,
        notes=f'Swap {spend_amount} ETH in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_PSP,
        amount=FVal(receive_amount),
        location_label=user_address,
        notes=f'Receive {receive_amount} PSP as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} ETH as a paraswap fee',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0xf3c25Eff97D5C7f8C3E741fd4698d407112691aF']])
def test_swap_amount_out_on_uniswap_v2(
        polygon_pos_inquirer: 'PolygonPOSInquirer',
        polygon_pos_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x730cb91f140a8574978f76dd22b1b84318cc73b762f22ec2db1c5673bfb976ad')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp = polygon_pos_accounts[0], TimestampMS(1734927359000)
    gas_amount, spend_amount, receive_amount = '0.0215667022013292', '0.020592381778840645', '0.01'
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POLYGON_POS_MATIC,
        amount=FVal(gas_amount),
        location_label=user_address,
        notes=f'Burn {gas_amount} POL for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_POLYGON_POS_MATIC,
        amount=FVal(spend_amount),
        location_label=user_address,
        notes=f'Swap {spend_amount} POL in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_POLYGON_POS_USDC,
        amount=FVal(receive_amount),
        location_label=user_address,
        notes=f'Receive {receive_amount} USDC as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0xf14B9E45d0426c4508b5340A57390E79bACAf396']])
def test_swap_amount_out_on_uniswap_v3(
        polygon_pos_inquirer: 'PolygonPOSInquirer',
        polygon_pos_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0xae411965ab6c572be23f62438e9d57e04be369d37a661a58e5d1cce9545c0ac9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp = polygon_pos_accounts[0], TimestampMS(1735668540000)
    gas_amount, spend_amount, receive_amount, approve_amount = '0.009231833980057221', '67.14398', '55152.6107', '0.67144'  # noqa: E501
    a_usdc = Asset('eip155:137/erc20:0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174')
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POLYGON_POS_MATIC,
        amount=FVal(gas_amount),
        location_label=user_address,
        notes=f'Burn {gas_amount} POL for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=a_usdc,
        amount=FVal(approve_amount),
        location_label=user_address,
        notes=f'Set USDC spending approval of {user_address} by {PARASWAP_AUGUSTUS_V6_ROUTER} to {approve_amount}',  # noqa: E501
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_subtype=HistoryEventSubType.SPEND,
        asset=a_usdc,
        amount=FVal(spend_amount),
        location_label=user_address,
        notes=f'Swap {spend_amount} USDC in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:137/erc20:0xE9c21De62C5C5d0cEAcCe2762bF655AfDcEB7ab3'),
        amount=FVal(receive_amount),
        location_label=user_address,
        notes=f'Receive {receive_amount} AKRE as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9809b45121669A3Fee0aD2A8B3d8147AF0305a8b']])
def test_swap_on_augustus_rfq(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0xa86ff8176bce4b6a392b6a325a0d642f4514741f1ee7dedd6a0119289238ce55')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp = ethereum_accounts[0], TimestampMS(1735677155000)
    gas_amount, spend_amount, receive_amount = '0.000848030323614944', '5122.952074', '1286.103459892685175335'  # noqa: E501
    assert events == [EvmEvent(
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
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal(spend_amount),
        location_label=user_address,
        notes=f'Swap {spend_amount} USDT in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc20:0x44ff8620b8cA30902395A7bD3F2407e1A091BF73'),
        amount=FVal(receive_amount),
        location_label=user_address,
        notes=f'Receive {receive_amount} VIRTUAL as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x70F256DC42E7f6eC5c59466A4Eb3e888d4A4dceE']])
def test_eure_receive_swap(
        gnosis_inquirer: 'GnosisInquirer',
        gnosis_accounts: list['ChecksumEvmAddress'],
):
    """Regression test for a bug where swaps in Gnosis receiving EURe were not decoded properly"""
    tx_hash = deserialize_evm_tx_hash('0x81130d4e9695b1e03c5960e51864740a7d6a3c3cab7b708f717dc5f18caad079')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, spend_amount, receive_amount = gnosis_accounts[0], TimestampMS(1749200310000), '0.000105481', '2497.622499', '2185.911263467705546005'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_XDAI,
        amount=FVal(gas_amount),
        location_label=user_address,
        notes=f'Burn {gas_amount} XDAI for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:100/erc20:0x2a22f9c3b484c3629090FeED35F17Ff8F88f76F0'),  # USDC.e
        amount=FVal(spend_amount),
        location_label=user_address,
        notes=f'Swap {spend_amount} USDC.e in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:100/erc20:0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430'),  # EURe
        amount=FVal(receive_amount),
        location_label=user_address,
        notes=f'Receive {receive_amount} EURe as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('gnosis_accounts', [['0x522ff17C6Ab585047174e6d1817B046D38F7C5f9']])
def test_swap_with_unrelated_curve_deposit(
        gnosis_inquirer: 'GnosisInquirer',
        gnosis_accounts: list['ChecksumEvmAddress'],
        load_global_caches,
) -> None:
    """Regression test for a bug where an unrelated curve deposit was causing the spend half of the
    swap to be incorrectly decoded."""
    tx_hash = deserialize_evm_tx_hash('0xb65c9b6566bf9d7f6e6313523560e0683f63bfadcadd9e4e8444819f96803401')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1751459205000)),
        location=Location.GNOSIS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_XDAI,
        amount=FVal(gas_amount := '0.000211096'),
        location_label=(user_address := gnosis_accounts[0]),
        notes=f'Burn {gas_amount} XDAI for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=11,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=(a_usdc := Asset('eip155:100/erc20:0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83')),
        amount=ZERO,
        location_label=user_address,
        notes=f'Revoke USDC spending approval of {user_address} by {PARASWAP_AUGUSTUS_V6_ROUTER}',
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=12,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_subtype=HistoryEventSubType.SPEND,
        asset=a_usdc,
        amount=FVal(spend_amount := '1147.097024'),
        location_label=user_address,
        notes=f'Swap {spend_amount} USDC in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=13,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:100/erc20:0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430'),
        amount=FVal(receive_amount := '973.320900476562704102'),
        location_label=user_address,
        notes=f'Receive {receive_amount} EURe as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_V6_ROUTER,
    )]
