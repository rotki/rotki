import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.arbitrum_one.modules.odos.v1.constants import ODOS_V1_ROUTER as ARB_ROUTER
from rotkehlchen.chain.ethereum.modules.odos.v1.constants import ODOS_V1_ROUTER as ETH_ROUTER
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.odos.v1.constants import CPT_ODOS_V1
from rotkehlchen.chain.optimism.modules.odos.v1.constants import ODOS_V1_ROUTER as OPT_ROUTER
from rotkehlchen.chain.polygon_pos.modules.odos.v1.constants import ODOS_V1_ROUTER as POL_ROUTER
from rotkehlchen.constants.assets import A_ETH, A_LUSD, A_POLYGON_POS_MATIC, A_WETH, A_WETH_ARB
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x605572243c30Af7493707C9c8E8aA2Ee25537e9A']])
def test_swap_token_to_token_ethereum(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xce86cc4bb232af0ede2342b012270b1db4c61082ce2e32d8d274166cc9839143')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, approval_amount, swap_amount, received_amount, odos_fees_eth, gas_fees = TimestampMS(1691645135000), '115792089237316195423570985008687907853269984665640564035457.584007913129639935', '4000', '2.15484532751231104', '0.000151599541198592', '0.00403543'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=ethereum_accounts[0],
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=226,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_LUSD,
        balance=Balance(amount=FVal(approval_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Set LUSD spending approval of {ethereum_accounts[0]} by {ETH_ROUTER} to {approval_amount}',  # noqa: E501
        address=ETH_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=227,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_LUSD,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} LUSD in Odos v1',
        counterparty=CPT_ODOS_V1,
        address=ETH_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=228,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_WETH,
        balance=Balance(amount=FVal(received_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} WETH as the result of a swap in Odos v1',
        counterparty=CPT_ODOS_V1,
        address=ETH_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=229,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_WETH,
        balance=Balance(amount=FVal(odos_fees_eth)),
        location_label=ethereum_accounts[0],
        notes=f'Spend {odos_fees_eth} WETH as an Odos v1 fee',
        counterparty=CPT_ODOS_V1,
        address=ETH_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xcC91A1Fa81d7c4b10C4ECe01AbEb3EeE55e5373c']])
def test_swap_token_to_eth_arbitrum(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x98805f922be9de669ddbb7c398db3c1bfb692530ad32fa72b40ac5aba49b895e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, approval_amount, swap_amount, received_amount, odos_fees_eth, gas_fees = TimestampMS(1693606715000), '115792089237316195423570985008687907853269984665640564039457.580725740003253015', '0.00328217312638692', '0.003282173126386919', '0.000000000000000001', '0.0000798467'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_WETH_ARB,
        balance=Balance(amount=FVal(approval_amount)),
        location_label=arbitrum_one_accounts[0],
        notes=f'Set WETH spending approval of {arbitrum_one_accounts[0]} by {ARB_ROUTER} to {approval_amount}',  # noqa: E501
        address=ARB_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=4,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_WETH_ARB,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=arbitrum_one_accounts[0],
        notes=f'Swap {swap_amount} WETH in Odos v1',
        counterparty=CPT_ODOS_V1,
        address=ARB_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=5,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        balance=Balance(amount=FVal(received_amount)),
        location_label=arbitrum_one_accounts[0],
        notes=f'Receive {received_amount} ETH as the result of a swap in Odos v1',
        counterparty=CPT_ODOS_V1,
        address=ARB_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=6,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(odos_fees_eth)),
        location_label=arbitrum_one_accounts[0],
        notes=f'Spend {odos_fees_eth} ETH as an Odos v1 fee',
        counterparty=CPT_ODOS_V1,
        address=ARB_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x61c7953578576F56E369482cBbE545733798a3b7']])
def test_swap_eth_to_token_optimism(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0x82e41cedb2265288f4475d8c7137bcaa031e5969ecbfa21551a797f5a7a71e8f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, swap_amount, received_amount, gas_fees = TimestampMS(1691607223000), '1.347', '2494.738788', '0.000108989578875775'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=optimism_accounts[0],
        notes=f'Swap {swap_amount} ETH in Odos v1',
        counterparty=CPT_ODOS_V1,
        address=OPT_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
        balance=Balance(amount=FVal(received_amount)),
        location_label=optimism_accounts[0],
        notes=f'Receive {received_amount} USDC.e as the result of a swap in Odos v1',
        counterparty=CPT_ODOS_V1,
        address=OPT_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x0638df8ce244060e2ce2eEC04484334a99608Fa6']])
def test_swap_matic_to_token_polygon(polygon_pos_inquirer, polygon_pos_accounts):
    tx_hash = deserialize_evm_tx_hash('0x3802c36346914887b09d65d6ace796ba2549a8947aed9087475b78cef3b089e8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, swap_amount, received_amount, odos_fees_eth, gas_fees = TimestampMS(1700674099000), '5', '420.01909972952905', '66.153912047014979328', '0.022903685'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_POLYGON_POS_MATIC,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=polygon_pos_accounts[0],
        notes=f'Swap {swap_amount} MATIC in Odos v1',
        counterparty=CPT_ODOS_V1,
        address=POL_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:137/erc20:0x8b1f836491903743fE51ACd13f2CC8Ab95b270f6'),
        balance=Balance(amount=FVal(received_amount)),
        location_label=polygon_pos_accounts[0],
        notes=f'Receive {received_amount} ACY as the result of a swap in Odos v1',
        counterparty=CPT_ODOS_V1,
        address=POL_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=Asset('eip155:137/erc20:0x8b1f836491903743fE51ACd13f2CC8Ab95b270f6'),
        balance=Balance(amount=FVal(odos_fees_eth)),
        location_label=polygon_pos_accounts[0],
        notes=f'Spend {odos_fees_eth} ACY as an Odos v1 fee',
        counterparty=CPT_ODOS_V1,
        address=POL_ROUTER,
    )]
    assert expected_events == events
