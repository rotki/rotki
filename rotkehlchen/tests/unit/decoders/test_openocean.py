from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.arbitrum_one.modules.open_ocean.decoder import DISTRIBUTOR_ADDR
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.open_ocean.constants import (
    CPT_OPENOCEAN,
    OPENOCEAN_EXCHANGE_ADDRESS,
    OPENOCEAN_LABEL,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import (
    A_ARB,
    A_BSC_BNB,
    A_ETH,
    A_POLYGON_POS_MATIC,
    A_WETH,
    A_XDAI,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
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
@pytest.mark.parametrize('polygon_pos_accounts', [['0x9b3Df1109CD696f08eEDa860C6D5dA56D3DA2daF']])
def test_openocean_swap_token_to_token(
        polygon_pos_inquirer: 'PolygonPOSInquirer',
        polygon_pos_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x4c335999c657e3d6f4dfe875d50911a844580c42a667d6952211459c0eae587d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_amount, spend_amount, receive_amount, approve_amount = polygon_pos_accounts[0], TimestampMS(1735222115000), '0.245916524062468656', '10000', '433.966123379781075037', '115792089237316195423570985008687907853269984665640564039457584007893003.638699'  # noqa: E501
    pos_usdt = Asset('eip155:137/erc20:0xc2132D05D31c914a87C6611C10748AEb04B58e8F')
    assert events == [
        EvmEvent(
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
            sequence_index=14,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=pos_usdt,
            amount=FVal(approve_amount),
            location_label=user_address,
            notes=f'Set USDT spending approval of {user_address} by 0x000000000022D473030F116dDEE9F6B43aC78BA3 to {approve_amount}',  # noqa: E501
            address=string_to_evm_address('0x000000000022D473030F116dDEE9F6B43aC78BA3'),
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=15,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_subtype=HistoryEventSubType.SPEND,
            asset=pos_usdt,
            amount=FVal(spend_amount),
            location_label=user_address,
            notes=f'Swap {spend_amount} USDT in {OPENOCEAN_LABEL}',
            counterparty=CPT_OPENOCEAN,
            address=string_to_evm_address('0x1E82AD8A12068A85fCb96368463B434e77b21201'),
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=16,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:137/erc20:0x53E0bca35eC356BD5ddDFebbD1Fc0fD03FaBad39'),
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} LINK from {OPENOCEAN_LABEL} swap',
            counterparty=CPT_OPENOCEAN,
            address=string_to_evm_address('0x1E82AD8A12068A85fCb96368463B434e77b21201'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x9fC0784d90bcac115129366AcD2acB1EFa575009']])
def test_openocean_swap_eth_to_token(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0xe45c138f3086f821c6598b24999c9cc0ca9ed95ecccc08b57f751d7146fd01ca')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, spend_amount, receive_amount = base_accounts[0], TimestampMS(1735074071000), '0.000005051509746809', '0.0031', '1013.977585253488605008'  # noqa: E501
    assert events == [
        EvmEvent(
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
            notes=f'Swap {spend_amount} ETH in {OPENOCEAN_LABEL}',
            counterparty=CPT_OPENOCEAN,
            address=OPENOCEAN_EXCHANGE_ADDRESS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:8453/erc20:0x9430A7e6283Fb704Fd1D9302868Bc39d16FE82Ba'),
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} cbDXN from {OPENOCEAN_LABEL} swap',
            counterparty=CPT_OPENOCEAN,
            address=OPENOCEAN_EXCHANGE_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xB3cbefF0336BaA4863Cb51238bD6C35BDAaB3D84']])
def test_openocean_swap_token_to_eth(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x076fdb84e51d17d2f9727c34f4b73cc1ffcd3671165764a0a287fe09a0cab36e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, spend_amount, receive_amount, approve_amount = optimism_accounts[0], TimestampMS(1735203855000), '0.000002907634681445', '5', '0.001484145603280848', '115792089237316195423570985008687907853269984665640564039457584007913121.115067'  # noqa: E501
    op_usdce = Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607')
    assert events == [
        EvmEvent(
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
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=op_usdce,
            amount=FVal(approve_amount),
            location_label=user_address,
            notes=f'Set USDC.e spending approval of {user_address} by 0x000000000022D473030F116dDEE9F6B43aC78BA3 to {approve_amount}',  # noqa: E501
            address=string_to_evm_address('0x000000000022D473030F116dDEE9F6B43aC78BA3'),
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=op_usdce,
            amount=FVal(spend_amount),
            location_label=user_address,
            notes=f'Swap {spend_amount} USDC.e in {OPENOCEAN_LABEL}',
            counterparty=CPT_OPENOCEAN,
            address=OPENOCEAN_EXCHANGE_ADDRESS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=4,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} ETH from {OPENOCEAN_LABEL} swap',
            counterparty=CPT_OPENOCEAN,
            address=OPENOCEAN_EXCHANGE_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_openocean_swap_uniswap_with_swapped_log(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0xf882a6a323bdc7ac05e78e2c346fddb489249afc04e68f09b1858ab357c8ede0')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_amount, spend_amount, receive_amount, approve_amount = arbitrum_one_accounts[0], TimestampMS(1702485949000), '0.0005537799', '3000', '3412.773848', '99999999999999999999996999'  # noqa: E501
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
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_ARB,
            amount=FVal(approve_amount),
            location_label=user_address,
            notes=f'Set ARB spending approval of {user_address} by {OPENOCEAN_EXCHANGE_ADDRESS} to {approve_amount}',  # noqa: E501
            address=OPENOCEAN_EXCHANGE_ADDRESS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ARB,
            amount=FVal(spend_amount),
            location_label=user_address,
            notes=f'Swap {spend_amount} ARB in {OPENOCEAN_LABEL}',
            counterparty=CPT_OPENOCEAN,
            address=string_to_evm_address('0xE07f9293ADe766Bffdf5e8548aD50425D49D5b25'),
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} USDC from {OPENOCEAN_LABEL} swap',
            counterparty=CPT_OPENOCEAN,
            address=string_to_evm_address('0xE07f9293ADe766Bffdf5e8548aD50425D49D5b25'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xfACcCDaC14056e2Cb7E95ddd1E8E9924bE8CAdBe']])
def test_openocean_swap_uniswapv2(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x497acb2385e7d7bc39160097348bd6423ecfe50f616dd2841cecd25a6561fae2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, spend_amount, receive_amount = ethereum_accounts[0], TimestampMS(1735206827000), '0.00072231082663302', '7500', '0.02494511741519721'  # noqa: E501
    assert events == [
        EvmEvent(
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
            asset=Asset('eip155:1/erc20:0xC5bA042BF8832999b17c9036E8212f49DCE0501A'),
            amount=FVal(spend_amount),
            location_label=user_address,
            notes=f'Swap {spend_amount} YOURAI in {OPENOCEAN_LABEL}',
            counterparty=CPT_OPENOCEAN,
            address=string_to_evm_address('0xAd4010bD5579f62fB40730cEf5cdE27d620c0383'),
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_WETH,
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} WETH from {OPENOCEAN_LABEL} swap',
            counterparty=CPT_OPENOCEAN,
            address=string_to_evm_address('0xAd4010bD5579f62fB40730cEf5cdE27d620c0383'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd79A19c88D34538dC56926021D07B1F719BBbF3c']])
def test_openocean_swap_uniswapv3(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0xb8caa647073e36ea91c2c22e57b49ddd1721c6c8b18ef51c3043adaa2950251b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, spend_amount, receive_amount = ethereum_accounts[0], TimestampMS(1735071359000), '0.0006813857721462', '0.02515', '800.247565502385530038'  # noqa: E501
    assert events == [
        EvmEvent(
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
            notes=f'Swap {spend_amount} ETH in {OPENOCEAN_LABEL}',
            counterparty=CPT_OPENOCEAN,
            address=OPENOCEAN_EXCHANGE_ADDRESS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0x157a6df6B74F4E5E45af4E4615FDe7B49225a662'),
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} ISLAND from {OPENOCEAN_LABEL} swap',
            counterparty=CPT_OPENOCEAN,
            address=OPENOCEAN_EXCHANGE_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('binance_sc_accounts', [['0xbF10AEcf9b1D6EbBF3d23237BA90d74600a7Cb3e']])
def test_openocean_swap_on_binance_sc(
        binance_sc_inquirer: 'BinanceSCInquirer',
        binance_sc_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x401b2209ef972bf9f3e77b743df65b9a0057e21e3a325b790811902d6faa6f2f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=binance_sc_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_amount, spend_amount, receive_amount, approve_amount = binance_sc_accounts[0], TimestampMS(1736523190000), '0.000261305', '0.006797769273691619', '0.031725949469604878', '115792089237316195423570985008687907853269984665640564039457.577210143855948316'  # noqa: E501
    a_bsc_eth = Asset('eip155:56/erc20:0x2170Ed0880ac9A755fd29B2688956BD959F933F8')
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
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=338,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=a_bsc_eth,
        amount=FVal(approve_amount),
        location_label=user_address,
        notes=f'Set ETH spending approval of {user_address} by 0x000000000022D473030F116dDEE9F6B43aC78BA3 to {approve_amount}',  # noqa: E501
        address=string_to_evm_address('0x000000000022D473030F116dDEE9F6B43aC78BA3'),
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=339,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.SPEND,
        asset=a_bsc_eth,
        amount=FVal(spend_amount),
        location_label=user_address,
        notes=f'Swap {spend_amount} ETH in {OPENOCEAN_LABEL}',
        counterparty=CPT_OPENOCEAN,
        address=string_to_evm_address('0x55877bD7F2EE37BDe55cA4B271A3631f3A7ef121'),
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=340,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BSC_BNB,
        amount=FVal(receive_amount),
        location_label=user_address,
        notes=f'Receive {receive_amount} BNB from {OPENOCEAN_LABEL} swap',
        counterparty=CPT_OPENOCEAN,
        address=string_to_evm_address('0x55877bD7F2EE37BDe55cA4B271A3631f3A7ef121'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x1Bc91Ad00C40ddE565a055bbe39069b84868738e']])
def test_openocean_swap_xdai_to_token(
        gnosis_inquirer: 'GnosisInquirer',
        gnosis_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x806a840fd2c7ed43eefb2069a3a1d1921b668f3762a3ec6928549055d5b65453')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, spend_amount, receive_amount = gnosis_accounts[0], TimestampMS(1741275975000), '0.000389004', '18.7', '18.651429'  # noqa: E501
    assert events == [
        EvmEvent(
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
            asset=A_XDAI,
            amount=FVal(spend_amount),
            location_label=user_address,
            notes=f'Swap {spend_amount} XDAI in {OPENOCEAN_LABEL}',
            counterparty=CPT_OPENOCEAN,
            address=OPENOCEAN_EXCHANGE_ADDRESS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:100/erc20:0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83'),
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} USDC from {OPENOCEAN_LABEL} swap',
            counterparty=CPT_OPENOCEAN,
            address=OPENOCEAN_EXCHANGE_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xc992007929b1841eA94eCFE52a600CcF8A594668']])
def test_openocean_distribution(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0xaaa23c4ce149a1c72159816e4fa4cd820143a9e0a933b10fd4c78c78884370ff')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1711763457000),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ARB,
            amount=FVal('2'),
            location_label=arbitrum_one_accounts[0],
            address=DISTRIBUTOR_ADDR,
            notes='Receive 2 ARB from OpenOcean as part of activity incentives',
            counterparty=CPT_OPENOCEAN,
        ),
    ]
