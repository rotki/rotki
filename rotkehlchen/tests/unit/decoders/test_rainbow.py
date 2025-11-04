from typing import Final
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.rainbow.constants import (
    CPT_RAINBOW_SWAPS,
    RAINBOW_ROUTER_CONTRACT,
)
from rotkehlchen.chain.evm.transactions import EvmTransactions
from rotkehlchen.constants.assets import A_BSC_BNB, A_ETH, A_OP, A_POL
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    EvmInternalTransaction,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)

A_AIT: Final = Asset('eip155:1/erc20:0x89d584A1EDB3A70B3B07963F9A3eA5399E38b136')
A_BUOY: Final = Asset('eip155:1/erc20:0x289Ff00235D2b98b0145ff5D4435d3e92f9540a6')
A_AXGT: Final = Asset('eip155:1/erc20:0xDd66781D0E9a08D4FBb5eC7BAc80B691BE27F21D')
A_ZIG: Final = Asset('eip155:1/erc20:0xb2617246d0c6c0087f18703d576831899ca94f01')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xfe25d6300D33e19E15AeeFEFD0Aafb319Dd61ae1']])
def test_rainbow_swap_eth_to_token(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xcd6afacf1efce38186b6cf9164792c4034d33d3f071c5e28c0b79ce5ab0223a9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    swap_amount, received_amount, gas_fees, fee_amount, timestamp, user_address = '0.1983', '28827.267041421686554081', '0.000114360530468618', '0.0017', TimestampMS(1741808351000), ethereum_accounts[0]  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} ETH in Rainbow',
        address=RAINBOW_ROUTER_CONTRACT,
        counterparty=CPT_RAINBOW_SWAPS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_AIT,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} AIT as the result of a swap in Rainbow',
        counterparty=CPT_RAINBOW_SWAPS,
        address=RAINBOW_ROUTER_CONTRACT,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} ETH as Rainbow fee',
        counterparty=CPT_RAINBOW_SWAPS,
        address=RAINBOW_ROUTER_CONTRACT,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0a471798F7f609A0B7fAC97051E57Be1c434FdeF']])
def test_rainbow_swap_token_to_eth(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xd34d7393151a3c0f2d23d0df4d8f0b4a000be7613277e831ef0860191e68f855')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    swap_amount, received_amount, gas_fees, fee_amount, timestamp, user_address = '1010.887928111872496631', '0.089068967427375408', '0.000147805218572058', '0.000763576624440434', TimestampMS(1741892171000), ethereum_accounts[0]  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_BUOY,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} BOOE in Rainbow',
        address=RAINBOW_ROUTER_CONTRACT,
        counterparty=CPT_RAINBOW_SWAPS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} ETH as the result of a swap in Rainbow',
        address=RAINBOW_ROUTER_CONTRACT,
        counterparty=CPT_RAINBOW_SWAPS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} ETH as Rainbow fee',
        counterparty=CPT_RAINBOW_SWAPS,
        address=RAINBOW_ROUTER_CONTRACT,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xB80177697e160eFC91d4B1ec295ABE6Ce0c0Fe1f']])
def test_rainbow_swap_token_to_token(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x4f85ee11bbc401240755b083106e0811e6b60ef7972063a51596934cbb6ed43f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    gas_fees, swap_amount, received_amount, approve_amount, fee_amount, timestamp, user_address = '0.000364910690805408', '77248.794187730822813278', '45110.517197738477939043', '115792089237316195423570985008687907853269984665640563961546.545997090312884234', '662.243823091993942423', TimestampMS(1741889531000), ethereum_accounts[0]  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=281,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_ZIG,
        amount=FVal(approve_amount),
        location_label=user_address,
        notes=f'Set ZIG spending approval of {user_address} by {RAINBOW_ROUTER_CONTRACT} to {approve_amount}',  # noqa: E501
        address=RAINBOW_ROUTER_CONTRACT,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=282,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ZIG,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} ZIG in Rainbow',
        address=RAINBOW_ROUTER_CONTRACT,
        counterparty=CPT_RAINBOW_SWAPS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=283,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_AXGT,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} AXGT as the result of a swap in Rainbow',
        counterparty=CPT_RAINBOW_SWAPS,
        address=RAINBOW_ROUTER_CONTRACT,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=284,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ZIG,
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} ZIG as Rainbow fee',
        counterparty=CPT_RAINBOW_SWAPS,
        address=RAINBOW_ROUTER_CONTRACT,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xD918F8179e915e523c0d14B98dDD45aD6AE82076']])
def test_rainbow_swap_on_arbitrum_one(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0xeb91cb1f850ebf1ac028b9c23c2445e8d050df6eca58f9aff6a2f77e5d156fcc')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    gas_fees, swap_amount, received_amount, fee_amount, timestamp, user_address = '0.0000046705', '0.0305382', '57.839494', '0.0002618', TimestampMS(1742300433000), arbitrum_one_accounts[0]  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
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
        location_label=user_address,
        notes=f'Swap {swap_amount} ETH in Rainbow',
        address=RAINBOW_ROUTER_CONTRACT,
        counterparty=CPT_RAINBOW_SWAPS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:42161/erc20:0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9'),
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} USDT as the result of a swap in Rainbow',
        address=RAINBOW_ROUTER_CONTRACT,
        counterparty=CPT_RAINBOW_SWAPS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} ETH as Rainbow fee',
        counterparty=CPT_RAINBOW_SWAPS,
        address=RAINBOW_ROUTER_CONTRACT,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x4C855204c4EeD411a03D20acE673d08837A8F5ee']])
def test_rainbow_swap_on_base(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0xa8ba1828b24608d3c3405a211bca5fcb57c5f4cdfde93d6a55b7f3b16f8f78f1')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    gas_fees, swap_amount, received_amount, fee_amount, timestamp, user_address = '0.000000503840420226', '0.00007932', '2.062496993416307892', '0.00000068', TimestampMS(1742302681000), base_accounts[0]  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
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
        location_label=user_address,
        notes=f'Swap {swap_amount} ETH in Rainbow',
        address=RAINBOW_ROUTER_CONTRACT,
        counterparty=CPT_RAINBOW_SWAPS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BASE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:8453/erc20:0x46777C76dBbE40fABB2AAB99E33CE20058e76C59'),
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} L3 as the result of a swap in Rainbow',
        address=RAINBOW_ROUTER_CONTRACT,
        counterparty=CPT_RAINBOW_SWAPS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.BASE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} ETH as Rainbow fee',
        counterparty=CPT_RAINBOW_SWAPS,
        address=RAINBOW_ROUTER_CONTRACT,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('binance_sc_accounts', [['0xe733D0155F460DC8574855293Fbd4E6b44699374']])
def test_rainbow_swap_on_binance_sc(binance_sc_inquirer, binance_sc_accounts):
    """Test that a rainbow swap on binance_sc works correctly.
    Also a regression test for https://github.com/orgs/rotki/projects/11/views/2?pane=issue&itemId=109177215
    Rainbow swap fees are calculated from the internal transactions, but the app only queries
    transactions linked to user addresses, which omits the transactions needed here. The tests
    overlooked this since `get_decoded_events_of_transaction` queries all internal transactions
    for a given tx_hash. To verify that the fix for this works, mock the initial internal
    transaction query, and rely on the Rainbow decoder to query the needed internal transactions.
    """
    tx_hash = deserialize_evm_tx_hash('0x68b7935786f6281c2774c6e4f7c0146cd9e4a0e40f0a2f49368e92fc5d2844c5')  # noqa: E501
    call_count = 0
    original_query_and_save = EvmTransactions(
        evm_inquirer=binance_sc_inquirer,
        database=binance_sc_inquirer.database,
    )._query_and_save_internal_transactions_for_range_or_parent_hash

    def mock_query_and_save_internal_txs(*args, **kwargs):
        """On the initial attempt to query, add an unrelated internal tx to ensure all needed
        transactions get queried later even when some are already present for this tx_hash.
        On any subsequent attempts to query simply call the original query function.
        """
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            with binance_sc_inquirer.database.conn.write_ctx() as write_cursor:
                DBEvmTx(binance_sc_inquirer.database).add_evm_internal_transactions(
                    write_cursor=write_cursor,
                    transactions=[EvmInternalTransaction(
                        parent_tx_hash=tx_hash,
                        chain_id=binance_sc_inquirer.chain_id,
                        trace_id=0,
                        from_address=ZERO_ADDRESS,
                        to_address=ZERO_ADDRESS,
                        value=10000,
                        gas=0,
                        gas_used=0,
                    )],
                    relevant_address=binance_sc_accounts[0],
                )
        elif call_count > 1:
            original_query_and_save(*args, **kwargs)

    with patch(
        'rotkehlchen.chain.evm.transactions.EvmTransactions._query_and_save_internal_transactions_for_range_or_parent_hash',
        side_effect=mock_query_and_save_internal_txs,
    ):
        events, _ = get_decoded_events_of_transaction(evm_inquirer=binance_sc_inquirer, tx_hash=tx_hash)  # noqa: E501

    gas_fees, swap_amount, received_amount, fee_amount, timestamp, user_address = '0.000561831', '0.0579036', '15021.487938841009576268', '0.0004964', TimestampMS(1742292986000), binance_sc_accounts[0]  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BSC_BNB,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} BNB for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_BSC_BNB,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} BNB in Rainbow',
        address=RAINBOW_ROUTER_CONTRACT,
        counterparty=CPT_RAINBOW_SWAPS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:56/erc20:0x8051A61319B7FF7010a200E39b30b9a084dbCB5f'),
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} camel as the result of a swap in Rainbow',
        address=RAINBOW_ROUTER_CONTRACT,
        counterparty=CPT_RAINBOW_SWAPS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BSC_BNB,
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} BNB as Rainbow fee',
        counterparty=CPT_RAINBOW_SWAPS,
        address=RAINBOW_ROUTER_CONTRACT,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x158E5aE870c64C0B48Dd062c62D160aBF13391b6']])
def test_rainbow_swap_on_optimism(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc670f3c5efbeaf47e1c14349be3dc0f6df136b69d651b26e3a2cf371b6a63f6f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    gas_fees, swap_amount, received_amount, fee_amount, timestamp, user_address = '0.000000048317451417', '0.01060905', '23.332130274980295506', '0.00009095', TimestampMS(1742305889000), optimism_accounts[0]  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} ETH in Rainbow',
        address=RAINBOW_ROUTER_CONTRACT,
        counterparty=CPT_RAINBOW_SWAPS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_OP,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} OP as the result of a swap in Rainbow',
        address=RAINBOW_ROUTER_CONTRACT,
        counterparty=CPT_RAINBOW_SWAPS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} ETH as Rainbow fee',
        counterparty=CPT_RAINBOW_SWAPS,
        address=RAINBOW_ROUTER_CONTRACT,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x383d65320c9f1F4109DeB828d29FC7573122E9a7']])
def test_rainbow_swap_on_polygon_pos(polygon_pos_inquirer, polygon_pos_accounts):
    tx_hash = deserialize_evm_tx_hash('0x240ab184f97590310a32b77ebbcaa80f898a01c29592f41442391c67f7e20360')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    gas_fees, swap_amount, received_amount, fee_amount, timestamp, user_address = '0.0138519465', '9.915', '7.29700878889547439', '0.085', TimestampMS(1742309278000), polygon_pos_accounts[0]  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POL,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} POL for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_POL,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} POL in Rainbow',
        address=RAINBOW_ROUTER_CONTRACT,
        counterparty=CPT_RAINBOW_SWAPS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:137/erc20:0xBbba073C31bF03b8ACf7c28EF0738DeCF3695683'),
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} SAND as the result of a swap in Rainbow',
        address=RAINBOW_ROUTER_CONTRACT,
        counterparty=CPT_RAINBOW_SWAPS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POL,
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} POL as Rainbow fee',
        counterparty=CPT_RAINBOW_SWAPS,
        address=RAINBOW_ROUTER_CONTRACT,
    )]
