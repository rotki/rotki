from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.polygon_pos_bridge.decoder import (
    BRIDGE_ADDRESS,
    ERC20_BRIDGE_ADDRESS,
    ETH_BRIDGE_ADDRESS,
    PLASMA_BRIDGE_ADDRESS,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.polygon.constants import CPT_POLYGON
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.polygon_pos.modules.polygon_pos_bridge.decoder import (
    PLASMA_BRIDGE_CHILD_CHAIN,
)
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH, A_POL, A_POLYGON_POS_MATIC, A_USDT, Asset
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x2195a238350A51C077A9C499E18Ce720048fbbD2']])
def test_polygon_pos_bridge_l2_deposit(
        polygon_pos_inquirer: 'PolygonPOSInquirer',
        polygon_pos_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xa97396d6b61f213ebf194807553c06768fb9d1ca04ba30bfafb1a788357f3c36')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user_address, gas_amount, deposit_amount = TimestampMS(1729861499000), polygon_pos_accounts[0], '0.0016145640090944', '80.675001498474753918'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
            sequence_index=163,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:137/erc20:0x61299774020dA444Af134c82fa83E3810b309991'),
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Bridge {deposit_amount} RNDR from Polygon POS to Ethereum via Polygon bridge',
            counterparty=CPT_POLYGON,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x76a5217E52fd01F468743f62a874e2Ec9bbB3e1c']])
def test_polygon_pos_bridge_l2_plasma_deposit(
        polygon_pos_inquirer: 'PolygonPOSInquirer',
        polygon_pos_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x8b86c3f67ce0497075fd4d7ffa0c57a0b4c752bace3e0764f6e7a8b8f6a720a9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user_address, gas_amount, deposit_amount = TimestampMS(1729875073000), polygon_pos_accounts[0], '0.00456586488143955', '57008.16996625583804992'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_POLYGON_POS_MATIC,
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Bridge {deposit_amount} POL from Polygon POS to Ethereum via Polygon bridge',
            counterparty=CPT_POLYGON,
            address=string_to_evm_address('0x0000000000000000000000000000000000001010'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x07aE8551Be970cB1cCa11Dd7a11F47Ae82e70E67']])
def test_polygon_pos_bridge_l2_withdraw(
        polygon_pos_inquirer: 'PolygonPOSInquirer',
        polygon_pos_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x74b36dd98fb9e3a6bf9fa4cd6ba2066cd3fa86797b206bd709cfb097bb0c85a4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user_address, bridge_amount = TimestampMS(1729879355000), polygon_pos_accounts[0], '892014.616138'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=293,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:137/erc20:0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'),
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} USDC from Ethereum to Polygon POS via Polygon bridge',
            counterparty=CPT_POLYGON,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0xBa95718a52b5a3DBa749a7641712Dc05a3550d4f']])
def test_polygon_pos_bridge_l2_plasma_withdraw(
        polygon_pos_inquirer: 'PolygonPOSInquirer',
        polygon_pos_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x962b5ec3701a4441ceca761c77879ae112e5052d53e80b3a2948fc52abdf8aee')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, bridge_amount = polygon_pos_accounts[0], TimestampMS(1729779147000), '29948.586147495793690333'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=611,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_POLYGON_POS_MATIC,
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} POL from Ethereum to Polygon POS via Polygon bridge',
            counterparty=CPT_POLYGON,
            address=PLASMA_BRIDGE_CHILD_CHAIN,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5CbE388d4C1Bc89C772cc14B1cBC58f4fAeBC4E3']])
def test_polygon_pos_bridge_deposit_token(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x6d3e7d69b34a9f6454de29f7b0f3fcebac17360a07918fc73dc3f6cf1baf3305')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, bridge_amount = ethereum_accounts[0], TimestampMS(1730122691000), '0.001221458186810547', '9.8867467185941'  # noqa: E501
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            tx_ref=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=590,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:1/erc20:0x0F5D2fB29fb7d3CFeE444a200298f468908cC942'),
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} MANA from Ethereum to Polygon POS via Polygon bridge',
            tx_ref=tx_hash,
            counterparty=CPT_POLYGON,
            address=ERC20_BRIDGE_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x2247C97f32A1A29a1359580CA3dA7cd51990CB04']])
def test_polygon_pos_bridge_deposit_eth(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x418f03068bdfcd64693f133908a40a6e87acba416a88fe4436939079a1853e26')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, bridge_amount = ethereum_accounts[0], TimestampMS(1730123615000), '0.001059375034920494', '7.624084200852464793'  # noqa: E501
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            tx_ref=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} ETH from Ethereum to Polygon POS via Polygon bridge',
            tx_ref=tx_hash,
            counterparty=CPT_POLYGON,
            address=BRIDGE_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xE34396C7D34280Af3959D47826bF4f4346fab2A7']])
def test_polygon_pos_bridge_deposit_plasma(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x9ad56dd8369a184c2a56931e496691bb78ae604c375b29c5f8971a50a39cfee7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, bridge_amount = ethereum_accounts[0], TimestampMS(1730121767000), '0.001529439860389197', '2000'  # noqa: E501
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            tx_ref=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=484,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_POL,
            amount=ZERO,
            location_label=user_address,
            notes=f'Revoke POL spending approval of {user_address} by {PLASMA_BRIDGE_ADDRESS}',
            tx_ref=tx_hash,
            address=PLASMA_BRIDGE_ADDRESS,
        ), EvmEvent(
            sequence_index=485,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_POL,
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} POL from Ethereum to Polygon POS via Polygon bridge',
            tx_ref=tx_hash,
            counterparty=CPT_POLYGON,
            address=PLASMA_BRIDGE_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0CDa93172497f319a85c8f83132B61bd92D51cCE']])
def test_polygon_pos_bridge_withdraw_token(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x0bc7401a1b8a1ae7182f16f9e26db50ac114a7a4d1543f13651fdb0d9ea5d95a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, bridge_amount = ethereum_accounts[0], TimestampMS(1730122559000), '0.002847157008173436', '445.962192'  # noqa: E501
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            tx_ref=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=309,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_USDT,
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} USDT from Polygon POS to Ethereum via Polygon bridge',
            tx_ref=tx_hash,
            counterparty=CPT_POLYGON,
            address=ERC20_BRIDGE_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xF04c50634CCc5746720f679e8689e3198208636B']])
def test_polygon_pos_bridge_withdraw_eth(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x8b097020083573f2121564048947746eda00ea3d9111a52a47f4d1d7e40739a0')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, bridge_amount = ethereum_accounts[0], TimestampMS(1730127155000), '0.003165818745737182', '1.2925'  # noqa: E501
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            tx_ref=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} ETH from Polygon POS to Ethereum via Polygon bridge',
            tx_ref=tx_hash,
            counterparty=CPT_POLYGON,
            address=ETH_BRIDGE_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xddeB04d7Dab85BD6AdfaC8851F9cdB3a06Be77aD']])
def test_polygon_pos_bridge_plasma_start_exit(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x42e58d6bde4d59aba15cd37c16a693f583a5d477b8c3f8d9ca5b4c2fefc55cfe')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount = ethereum_accounts[0], TimestampMS(1730059739000), '0.00251101180596609'  # noqa: E501
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            tx_ref=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=205,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:1/erc721:0xDF74156420Bd57ab387B195ed81EcA36F9fABAca/588708823241823398655445372856552995073191575662'),
            amount=ONE,
            location_label=user_address,
            notes='Receive Exit NFT from Polygon Bridge',
            tx_ref=tx_hash,
            counterparty=CPT_POLYGON,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xddeB04d7Dab85BD6AdfaC8851F9cdB3a06Be77aD']])
def test_polygon_pos_bridge_plasma_process_exit(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x772c7c665a24954b11aa66226a4602537e970df114b0d7875572975b641ba47f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, bridge_amount = ethereum_accounts[0], TimestampMS(1730059799000), '0.000750908659746456', '2004.054999809184671214'  # noqa: E501
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            tx_ref=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=335,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:1/erc721:0xDF74156420Bd57ab387B195ed81EcA36F9fABAca/588708823241823398655445372856552995073191575662'),
            amount=ONE,
            location_label=user_address,
            notes='Return Exit NFT to Polygon Bridge',
            tx_ref=tx_hash,
            counterparty=CPT_POLYGON,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            sequence_index=336,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_POL,
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} POL from Polygon POS to Ethereum via Polygon bridge',
            tx_ref=tx_hash,
            counterparty=CPT_POLYGON,
            address=PLASMA_BRIDGE_ADDRESS,
        ),
    ]
