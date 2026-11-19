from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from eth_utils import to_checksum_address

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.arbitrum_one.types import ArbitrumOneTransaction
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.connext.constants import (
    CONNEXT_CPT_DETAILS,
    CONNEXT_NXTP_MANAGERS,
    CPT_CONNEXT,
    DEFAULT_NXTP_MANAGER,
    LEGACY_TRANSACTION_CANCELLED_TOPIC,
    LEGACY_TRANSACTION_FULFILLED_TOPIC,
    LEGACY_TRANSACTION_PREPARED_TOPIC,
    TRANSACTION_CANCELLED_TOPIC,
    TRANSACTION_FULFILLED_TOPIC,
    TRANSACTION_PREPARED_TOPIC,
)
from rotkehlchen.chain.evm.decoding.constants import (
    ERC20_OR_ERC721_APPROVE,
    ERC20_OR_ERC721_TRANSFER,
)
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_POL
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import (
    LOCATION_ARBITRUM_ONE,
    LOCATION_ETHEREUM,
    LOCATION_POLYGON_POS,
)
from rotkehlchen.tasks.bridges import (
    MATCHED_BRIDGE_KEY,
    get_unmatched_bridge_events,
    match_bridge_transactions,
)
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmInternalTransaction,
    EvmTransaction,
    EVMTxHash,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import address_to_bytes32

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.decoding.decoder import ArbitrumOneTransactionDecoder
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.polygon_pos.manager import PolygonPOSManager
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.db.dbhandler import DBHandler

USER_ADDRESS = string_to_evm_address('0xc37b40ABdB939635068d3c5f13E7faF686F03B65')
ROUTER_ADDRESS = string_to_evm_address('0x95829c9aCFECaEC0ee594a377311b0937C4a2882')
RELAYER_ADDRESS = string_to_evm_address('0x0aE392879a228B2484d9B1F80A5d0B7080fe79c2')
POLYGON_MANAGER = string_to_evm_address('0x6090De2EC76eb1Dc3B5d632734415c93c44Fd113')
ARBITRUM_MANAGER = string_to_evm_address('0xcF4d2994088a8CDE52FB584fE29608b63Ec063B2')
ARBITRUM_LEGACY_MANAGER = string_to_evm_address('0xF293D5d599c046681AB28c1Bc7927Fff859c67A7')
POLYGON_DAI_ADDRESS = string_to_evm_address('0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063')
ARBITRUM_DAI_ADDRESS = string_to_evm_address('0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1')
A_POLYGON_DAI = Asset(f'eip155:137/erc20:{POLYGON_DAI_ADDRESS}')
A_ARBITRUM_DAI = Asset(f'eip155:42161/erc20:{ARBITRUM_DAI_ADDRESS}')
SAMPLE_TX_ID = bytes.fromhex('71e69d0e855f52d5e3ec99d26ec9ec9c0d3abe62bd84759386248984262130cd')
EMPTY_CALLDATA_HASH = bytes.fromhex(
    'c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470',
)


def _make_receipt(
        tx_hash: EVMTxHash,
        chain_id: ChainID,
        logs: list[EvmTxReceiptLog],
) -> EvmTxReceipt:
    return EvmTxReceipt(
        tx_hash=tx_hash,
        chain_id=chain_id,
        status=True,
        contract_address=None,
        tx_type=0,
        logs=logs,
    )


def _decode_offline_tx(
        database: DBHandler,
        decoder: EVMTransactionDecoder,
        transaction: EvmTransaction,
        receipt: EvmTxReceipt,
        internal_transactions: list[EvmInternalTransaction] | None = None,
) -> list[EvmEvent]:
    dbevmtx = DBEvmTx(database)
    with database.user_write() as write_cursor:
        dbevmtx.add_transactions(write_cursor, [transaction], relevant_address=None)
        if internal_transactions:
            dbevmtx.add_evm_internal_transactions(
                write_cursor,
                internal_transactions,
                relevant_address=USER_ADDRESS,
            )
        decoder.reload_data(write_cursor)

    events, _, _ = decoder._decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    return events


def _encode_tx_data(
        receiving_manager: ChecksumEvmAddress,
        user: ChecksumEvmAddress,
        router: ChecksumEvmAddress,
        sending_asset: ChecksumEvmAddress,
        receiving_asset: ChecksumEvmAddress,
        fallback: ChecksumEvmAddress,
        receiving_address: ChecksumEvmAddress,
        sending_chain_id: int,
        receiving_chain_id: int,
        amount: int,
        transaction_id: bytes = SAMPLE_TX_ID,
        initiator: ChecksumEvmAddress | None = None,
        has_initiator: bool = True,
        expiry: int = 1664998533,
        prepared_block: int = 33849292,
) -> bytes:
    words = [
        address_to_bytes32(receiving_manager),
        address_to_bytes32(user),
        address_to_bytes32(router),
    ]
    if has_initiator:
        words.append(address_to_bytes32(initiator or user))
    words.extend([
        address_to_bytes32(sending_asset),
        address_to_bytes32(receiving_asset),
        address_to_bytes32(fallback),
        address_to_bytes32(receiving_address),
        address_to_bytes32(ZERO_ADDRESS),
        EMPTY_CALLDATA_HASH,
        transaction_id,
        sending_chain_id.to_bytes(32, 'big'),
        receiving_chain_id.to_bytes(32, 'big'),
        amount.to_bytes(32, 'big'),
        expiry.to_bytes(32, 'big'),
        prepared_block.to_bytes(32, 'big'),
    ])
    return b''.join(words)


def _encode_v01_fulfilled_data(tx_data: bytes, relayer_fee: int) -> bytes:
    # Top-level dynamic args offset (0xa0 = 160), success, isContract, returnData offset, caller
    header = (
        (160).to_bytes(32, 'big') +
        (0).to_bytes(32, 'big') +
        (0).to_bytes(32, 'big') +
        (992).to_bytes(32, 'big') +
        address_to_bytes32(RELAYER_ADDRESS)
    )
    return header + tx_data + relayer_fee.to_bytes(32, 'big')


def _encode_v01_cancelled_data(tx_data: bytes) -> bytes:
    # Top-level dynamic args offset (0x40 = 64), caller
    header = (64).to_bytes(32, 'big') + address_to_bytes32(ROUTER_ADDRESS)
    return header + tx_data


def test_connext_configuration() -> None:
    assert CONNEXT_CPT_DETAILS.identifier == CPT_CONNEXT
    assert CONNEXT_CPT_DETAILS.label == 'Connext'
    assert CONNEXT_CPT_DETAILS.image == 'connext.svg'
    icon_path = (
        Path(__file__).resolve().parents[4] /
        'frontend/app/public/assets/images/protocols' /
        CONNEXT_CPT_DETAILS.image
    )
    assert icon_path.is_file()
    assert set(CONNEXT_NXTP_MANAGERS) == {
        ChainID.ETHEREUM,
        ChainID.OPTIMISM,
        ChainID.CRONOS,
        ChainID.BINANCE_SC,
        ChainID.GNOSIS,
        ChainID.POLYGON_POS,
        ChainID.FANTOM,
        ChainID.BOBA,
        ChainID.EVMOS,
        ChainID.ARBITRUM_ONE,
        ChainID.ARBITRUM_NOVA,
        ChainID.AVALANCHE,
    }
    for managers in CONNEXT_NXTP_MANAGERS.values():
        assert len(managers) > 0
        for address in managers:
            assert address == to_checksum_address(address)


@pytest.mark.parametrize('polygon_pos_accounts', [[USER_ADDRESS]])
@pytest.mark.parametrize('arbitrum_one_accounts', [[USER_ADDRESS]])
def test_connext_polygon_send_arbitrum_receive_and_bridge_match(
        polygon_pos_accounts: list[ChecksumEvmAddress],
        arbitrum_one_accounts: list[ChecksumEvmAddress],
        polygon_pos_manager: PolygonPOSManager,
        arbitrum_one_transaction_decoder: ArbitrumOneTransactionDecoder,
        database: DBHandler,
) -> None:
    """Decode the Polygon prepare and Arbitrum fulfill transactions and verify exact bridge match.

    Polygon tx:  0x7d672c0d7e376408f1bfe4f0dff83900239cd87ed91510b47ac36d1c12f94b2c
    Arbitrum tx: 0x8ef5f4ff4136f90c1e7428dea480aa10b13e936fb955962888a35cb2e690167e
    """
    poly_tx_hash = deserialize_evm_tx_hash(
        '0x7d672c0d7e376408f1bfe4f0dff83900239cd87ed91510b47ac36d1c12f94b2c',
    )
    send_raw = 558_063_689_000_000_000_000
    poly_tx = EvmTransaction(
        tx_hash=poly_tx_hash,
        chain_id=ChainID.POLYGON_POS,
        timestamp=Timestamp(1664739397),
        block_number=33849292,
        from_address=USER_ADDRESS,
        to_address=POLYGON_MANAGER,
        value=0,
        gas=200000,
        gas_price=30469839137,
        gas_used=124708,
        input_data=b'\xd9\x45\x93\x72',
        nonce=1,
    )
    poly_tx_data = _encode_tx_data(
        receiving_manager=ARBITRUM_MANAGER,
        user=USER_ADDRESS,
        router=ROUTER_ADDRESS,
        sending_asset=POLYGON_DAI_ADDRESS,
        receiving_asset=ARBITRUM_DAI_ADDRESS,
        fallback=USER_ADDRESS,
        receiving_address=USER_ADDRESS,
        sending_chain_id=ChainID.POLYGON_POS.value,
        receiving_chain_id=ChainID.ARBITRUM_ONE.value,
        amount=send_raw,
    )
    poly_receipt = _make_receipt(
        tx_hash=poly_tx_hash,
        chain_id=ChainID.POLYGON_POS,
        logs=[
            EvmTxReceiptLog(
                log_index=225,
                address=POLYGON_DAI_ADDRESS,
                data=send_raw.to_bytes(32, 'big'),
                topics=[
                    ERC20_OR_ERC721_TRANSFER,
                    address_to_bytes32(USER_ADDRESS),
                    address_to_bytes32(POLYGON_MANAGER),
                ],
            ),
            EvmTxReceiptLog(
                log_index=226,
                address=POLYGON_DAI_ADDRESS,
                data=(0).to_bytes(32, 'big'),
                topics=[
                    ERC20_OR_ERC721_APPROVE,
                    address_to_bytes32(USER_ADDRESS),
                    address_to_bytes32(POLYGON_MANAGER),
                ],
            ),
            EvmTxReceiptLog(
                log_index=227,
                address=POLYGON_MANAGER,
                data=poly_tx_data + address_to_bytes32(USER_ADDRESS),
                topics=[
                    TRANSACTION_PREPARED_TOPIC,
                    address_to_bytes32(USER_ADDRESS),
                    address_to_bytes32(ROUTER_ADDRESS),
                    SAMPLE_TX_ID,
                ],
            ),
        ],
    )

    poly_events = _decode_offline_tx(
        database=database,
        decoder=polygon_pos_manager.transactions_decoder,
        transaction=poly_tx,
        receipt=poly_receipt,
    )
    assert poly_events == [
        EvmEvent(
            tx_ref=poly_tx_hash,
            sequence_index=0,
            timestamp=(poly_ts := TimestampMS(1664739397000)),
            location=LOCATION_POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POL,
            amount=FVal('0.003799832699096996'),
            location_label=USER_ADDRESS,
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=poly_tx_hash,
            sequence_index=226,
            timestamp=poly_ts,
            location=LOCATION_POLYGON_POS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_POLYGON_DAI,
            amount=FVal('558.063689'),
            location_label=USER_ADDRESS,
            notes='Bridge 558.063689 DAI from Polygon POS to Arbitrum One via Connext',
            counterparty=CPT_CONNEXT,
            address=POLYGON_MANAGER,
            extra_data={'bridge': {
                'from_chain': 137,
                'to_chain': 42161,
                'from_address': USER_ADDRESS,
                'to_address': USER_ADDRESS,
                'to_asset': ARBITRUM_DAI_ADDRESS,
                'transfer_id': SAMPLE_TX_ID.hex(),
            }},
        ),
        EvmEvent(
            tx_ref=poly_tx_hash,
            sequence_index=227,
            timestamp=poly_ts,
            location=LOCATION_POLYGON_POS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_POLYGON_DAI,
            amount=FVal('0'),
            location_label=USER_ADDRESS,
            address=POLYGON_MANAGER,
        ),
    ]

    arb_tx_hash = deserialize_evm_tx_hash(
        '0x8ef5f4ff4136f90c1e7428dea480aa10b13e936fb955962888a35cb2e690167e',
    )
    gross_recv_raw = 557_518_972_505_620_559_533
    relayer_fee_raw = 234_988_249_067_872_227
    net_recv_raw = gross_recv_raw - relayer_fee_raw
    arb_tx = ArbitrumOneTransaction(
        tx_hash=arb_tx_hash,
        chain_id=ChainID.ARBITRUM_ONE,
        timestamp=Timestamp(1664739556),
        block_number=28049002,
        from_address=string_to_evm_address('0x160694F252B907cDf3862922950142A5F1Fd161a'),
        to_address=string_to_evm_address('0x4775aF8FeF4809fE10bf05867D2b038A4B5b2146'),
        value=0,
        gas=500000,
        gas_price=100000000,
        gas_used=419348,
        input_data=b'\xb8\x7b\x0b\x4c',
        nonce=1,
        tx_type=0,
    )
    arb_tx_data = _encode_tx_data(
        receiving_manager=ARBITRUM_MANAGER,
        user=USER_ADDRESS,
        router=ROUTER_ADDRESS,
        sending_asset=POLYGON_DAI_ADDRESS,
        receiving_asset=ARBITRUM_DAI_ADDRESS,
        fallback=USER_ADDRESS,
        receiving_address=USER_ADDRESS,
        sending_chain_id=ChainID.POLYGON_POS.value,
        receiving_chain_id=ChainID.ARBITRUM_ONE.value,
        amount=gross_recv_raw,
        expiry=1664912133,
        prepared_block=15662607,
    )
    arb_receipt = _make_receipt(
        tx_hash=arb_tx_hash,
        chain_id=ChainID.ARBITRUM_ONE,
        logs=[
            EvmTxReceiptLog(
                log_index=0,
                address=ARBITRUM_DAI_ADDRESS,
                data=relayer_fee_raw.to_bytes(32, 'big'),
                topics=[
                    ERC20_OR_ERC721_TRANSFER,
                    address_to_bytes32(ARBITRUM_MANAGER),
                    address_to_bytes32(RELAYER_ADDRESS),
                ],
            ),
            EvmTxReceiptLog(
                log_index=1,
                address=ARBITRUM_DAI_ADDRESS,
                data=net_recv_raw.to_bytes(32, 'big'),
                topics=[
                    ERC20_OR_ERC721_TRANSFER,
                    address_to_bytes32(ARBITRUM_MANAGER),
                    address_to_bytes32(USER_ADDRESS),
                ],
            ),
            EvmTxReceiptLog(
                log_index=2,
                address=ARBITRUM_MANAGER,
                data=_encode_v01_fulfilled_data(arb_tx_data, relayer_fee_raw),
                topics=[
                    TRANSACTION_FULFILLED_TOPIC,
                    address_to_bytes32(USER_ADDRESS),
                    address_to_bytes32(ROUTER_ADDRESS),
                    SAMPLE_TX_ID,
                ],
            ),
        ],
    )

    arb_events = _decode_offline_tx(
        database=database,
        decoder=arbitrum_one_transaction_decoder,
        transaction=arb_tx,
        receipt=arb_receipt,
    )
    assert arb_events == [
        EvmEvent(
            tx_ref=arb_tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1664739556000),
            location=LOCATION_ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ARBITRUM_DAI,
            amount=FVal('557.283984256552687306'),
            location_label=USER_ADDRESS,
            notes=(
                'Bridge 557.283984256552687306 DAI from Polygon POS to Arbitrum One via Connext'
            ),
            counterparty=CPT_CONNEXT,
            address=ARBITRUM_MANAGER,
            extra_data={'bridge': {
                'from_chain': 137,
                'to_chain': 42161,
                'from_address': USER_ADDRESS,
                'to_address': USER_ADDRESS,
                'transfer_id': SAMPLE_TX_ID.hex(),
            }},
        ),
    ]

    # Verify automatic Tier-1 exact bridge matching links the two legs
    dbevents = DBHistoryEvents(database)
    match_bridge_transactions(database=database)
    unmatched_deposits, unmatched_withdrawals = get_unmatched_bridge_events(database=database)
    assert unmatched_deposits == []
    assert unmatched_withdrawals == []
    with database.conn.read_ctx() as cursor:
        stored_events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                type_and_subtype_combinations=[
                    (HistoryEventType.DEPOSIT, HistoryEventSubType.BRIDGE),
                    (HistoryEventType.WITHDRAWAL, HistoryEventSubType.BRIDGE),
                ],
            ),
        )
    assert len(stored_events) == 2
    for stored_event in stored_events:
        assert stored_event.extra_data is not None
        assert MATCHED_BRIDGE_KEY in stored_event.extra_data


@pytest.mark.parametrize('arbitrum_one_accounts', [[USER_ADDRESS]])
@pytest.mark.parametrize('polygon_pos_accounts', [[USER_ADDRESS]])
def test_connext_ignores_router_side_prepare_and_fulfill(
        arbitrum_one_accounts: list[ChecksumEvmAddress],
        polygon_pos_accounts: list[ChecksumEvmAddress],
        arbitrum_one_transaction_decoder: ArbitrumOneTransactionDecoder,
        polygon_pos_manager: PolygonPOSManager,
        database: DBHandler,
) -> None:
    """Receiving-chain prepare and sending-chain fulfill are router-only and should be ignored."""
    tx_data = _encode_tx_data(
        receiving_manager=ARBITRUM_MANAGER,
        user=USER_ADDRESS,
        router=ROUTER_ADDRESS,
        sending_asset=POLYGON_DAI_ADDRESS,
        receiving_asset=ARBITRUM_DAI_ADDRESS,
        fallback=USER_ADDRESS,
        receiving_address=USER_ADDRESS,
        sending_chain_id=ChainID.POLYGON_POS.value,
        receiving_chain_id=ChainID.ARBITRUM_ONE.value,
        amount=100 * 10**18,
    )
    arb_tx_hash = deserialize_evm_tx_hash('0x' + '11' * 32)
    arb_tx = ArbitrumOneTransaction(
        tx_hash=arb_tx_hash,
        chain_id=ChainID.ARBITRUM_ONE,
        timestamp=Timestamp(1664739500),
        block_number=28048999,
        from_address=ROUTER_ADDRESS,
        to_address=ARBITRUM_MANAGER,
        value=0,
        gas=200000,
        gas_price=100000000,
        gas_used=100000,
        input_data=b'',
        nonce=1,
        tx_type=0,
    )
    arb_receipt = _make_receipt(
        tx_hash=arb_tx_hash,
        chain_id=ChainID.ARBITRUM_ONE,
        logs=[EvmTxReceiptLog(
            log_index=0,
            address=ARBITRUM_MANAGER,
            data=tx_data + address_to_bytes32(ROUTER_ADDRESS),
            topics=[
                TRANSACTION_PREPARED_TOPIC,
                address_to_bytes32(USER_ADDRESS),
                address_to_bytes32(ROUTER_ADDRESS),
                SAMPLE_TX_ID,
            ],
        )],
    )
    arb_events = _decode_offline_tx(
        database=database,
        decoder=arbitrum_one_transaction_decoder,
        transaction=arb_tx,
        receipt=arb_receipt,
    )
    assert arb_events == []

    poly_tx_hash = deserialize_evm_tx_hash('0x' + '22' * 32)
    poly_tx = EvmTransaction(
        tx_hash=poly_tx_hash,
        chain_id=ChainID.POLYGON_POS,
        timestamp=Timestamp(1664739600),
        block_number=33849300,
        from_address=ROUTER_ADDRESS,
        to_address=POLYGON_MANAGER,
        value=0,
        gas=200000,
        gas_price=30000000000,
        gas_used=100000,
        input_data=b'',
        nonce=1,
    )
    poly_receipt = _make_receipt(
        tx_hash=poly_tx_hash,
        chain_id=ChainID.POLYGON_POS,
        logs=[EvmTxReceiptLog(
            log_index=0,
            address=POLYGON_MANAGER,
            data=_encode_v01_fulfilled_data(tx_data, 0),
            topics=[
                TRANSACTION_FULFILLED_TOPIC,
                address_to_bytes32(USER_ADDRESS),
                address_to_bytes32(ROUTER_ADDRESS),
                SAMPLE_TX_ID,
            ],
        )],
    )
    poly_events = _decode_offline_tx(
        database=database,
        decoder=polygon_pos_manager.transactions_decoder,
        transaction=poly_tx,
        receipt=poly_receipt,
    )
    assert poly_events == []


@pytest.mark.parametrize('polygon_pos_accounts', [[USER_ADDRESS]])
def test_connext_v01_cancel_refund(
        polygon_pos_accounts: list[ChecksumEvmAddress],
        polygon_pos_manager: PolygonPOSManager,
        database: DBHandler,
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x' + '33' * 32)
    refund_raw = 250 * 10**18
    tx = EvmTransaction(
        tx_hash=tx_hash,
        chain_id=ChainID.POLYGON_POS,
        timestamp=Timestamp(1665000000),
        block_number=33900000,
        from_address=ROUTER_ADDRESS,
        to_address=POLYGON_MANAGER,
        value=0,
        gas=200000,
        gas_price=30000000000,
        gas_used=100000,
        input_data=b'',
        nonce=1,
    )
    tx_data = _encode_tx_data(
        receiving_manager=ARBITRUM_MANAGER,
        user=USER_ADDRESS,
        router=ROUTER_ADDRESS,
        sending_asset=POLYGON_DAI_ADDRESS,
        receiving_asset=ARBITRUM_DAI_ADDRESS,
        fallback=USER_ADDRESS,
        receiving_address=USER_ADDRESS,
        sending_chain_id=ChainID.POLYGON_POS.value,
        receiving_chain_id=ChainID.ARBITRUM_ONE.value,
        amount=refund_raw,
    )
    receipt = _make_receipt(
        tx_hash=tx_hash,
        chain_id=ChainID.POLYGON_POS,
        logs=[
            EvmTxReceiptLog(
                log_index=0,
                address=POLYGON_DAI_ADDRESS,
                data=refund_raw.to_bytes(32, 'big'),
                topics=[
                    ERC20_OR_ERC721_TRANSFER,
                    address_to_bytes32(POLYGON_MANAGER),
                    address_to_bytes32(USER_ADDRESS),
                ],
            ),
            EvmTxReceiptLog(
                log_index=1,
                address=POLYGON_MANAGER,
                data=_encode_v01_cancelled_data(tx_data),
                topics=[
                    TRANSACTION_CANCELLED_TOPIC,
                    address_to_bytes32(USER_ADDRESS),
                    address_to_bytes32(ROUTER_ADDRESS),
                    SAMPLE_TX_ID,
                ],
            ),
        ],
    )
    events = _decode_offline_tx(
        database=database,
        decoder=polygon_pos_manager.transactions_decoder,
        transaction=tx,
        receipt=receipt,
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1665000000000),
            location=LOCATION_POLYGON_POS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REFUND,
            asset=A_POLYGON_DAI,
            amount=FVal('250'),
            location_label=USER_ADDRESS,
            notes='Receive 250 DAI as refund from Connext',
            counterparty=CPT_CONNEXT,
            address=POLYGON_MANAGER,
        ),
    ]


@pytest.mark.parametrize('polygon_pos_accounts', [[USER_ADDRESS]])
@pytest.mark.parametrize('arbitrum_one_accounts', [[USER_ADDRESS]])
def test_connext_legacy_v0050_prepare_fulfill_and_cancel(
        polygon_pos_accounts: list[ChecksumEvmAddress],
        arbitrum_one_accounts: list[ChecksumEvmAddress],
        polygon_pos_manager: PolygonPOSManager,
        arbitrum_one_transaction_decoder: ArbitrumOneTransactionDecoder,
        database: DBHandler,
) -> None:
    """Verify legacy NXTP v0.0.50 deployments (15-word TransactionData without initiator)."""
    amount_raw = 100 * 10**18
    relayer_fee_raw = 1 * 10**18
    net_raw = amount_raw - relayer_fee_raw
    legacy_tx_data = _encode_tx_data(
        receiving_manager=ARBITRUM_LEGACY_MANAGER,
        user=USER_ADDRESS,
        router=ROUTER_ADDRESS,
        sending_asset=POLYGON_DAI_ADDRESS,
        receiving_asset=ARBITRUM_DAI_ADDRESS,
        fallback=USER_ADDRESS,
        receiving_address=USER_ADDRESS,
        sending_chain_id=ChainID.POLYGON_POS.value,
        receiving_chain_id=ChainID.ARBITRUM_ONE.value,
        amount=amount_raw,
        has_initiator=False,
    )

    # Legacy prepare on Polygon (DEFAULT_NXTP_MANAGER)
    prep_hash = deserialize_evm_tx_hash('0x' + '44' * 32)
    prep_tx = EvmTransaction(
        tx_hash=prep_hash,
        chain_id=ChainID.POLYGON_POS,
        timestamp=Timestamp(1632000000),
        block_number=19000000,
        from_address=USER_ADDRESS,
        to_address=DEFAULT_NXTP_MANAGER,
        value=0,
        gas=200000,
        gas_price=1,
        gas_used=100000,
        input_data=b'',
        nonce=1,
    )
    prep_receipt = _make_receipt(
        tx_hash=prep_hash,
        chain_id=ChainID.POLYGON_POS,
        logs=[
            EvmTxReceiptLog(
                log_index=0,
                address=POLYGON_DAI_ADDRESS,
                data=amount_raw.to_bytes(32, 'big'),
                topics=[
                    ERC20_OR_ERC721_TRANSFER,
                    address_to_bytes32(USER_ADDRESS),
                    address_to_bytes32(DEFAULT_NXTP_MANAGER),
                ],
            ),
            EvmTxReceiptLog(
                log_index=1,
                address=DEFAULT_NXTP_MANAGER,
                data=legacy_tx_data + address_to_bytes32(USER_ADDRESS),
                topics=[
                    LEGACY_TRANSACTION_PREPARED_TOPIC,
                    address_to_bytes32(USER_ADDRESS),
                    address_to_bytes32(ROUTER_ADDRESS),
                    SAMPLE_TX_ID,
                ],
            ),
        ],
    )
    prep_events = _decode_offline_tx(
        database=database,
        decoder=polygon_pos_manager.transactions_decoder,
        transaction=prep_tx,
        receipt=prep_receipt,
    )
    bridge_prep = [e for e in prep_events if e.counterparty == CPT_CONNEXT]
    assert len(bridge_prep) == 1
    assert bridge_prep[0].event_type == HistoryEventType.DEPOSIT
    assert bridge_prep[0].event_subtype == HistoryEventSubType.BRIDGE
    assert bridge_prep[0].amount == FVal('100')
    assert bridge_prep[0].extra_data == {'bridge': {
        'from_chain': 137,
        'to_chain': 42161,
        'from_address': USER_ADDRESS,
        'to_address': USER_ADDRESS,
        'to_asset': ARBITRUM_DAI_ADDRESS,
        'transfer_id': SAMPLE_TX_ID.hex(),
    }}

    # Legacy fulfill on Arbitrum (ARBITRUM_LEGACY_MANAGER)
    fulfill_hash = deserialize_evm_tx_hash('0x' + '55' * 32)
    fulfill_tx = ArbitrumOneTransaction(
        tx_hash=fulfill_hash,
        chain_id=ChainID.ARBITRUM_ONE,
        timestamp=Timestamp(1632000100),
        block_number=1000000,
        from_address=RELAYER_ADDRESS,
        to_address=ARBITRUM_LEGACY_MANAGER,
        value=0,
        gas=200000,
        gas_price=1,
        gas_used=100000,
        input_data=b'',
        nonce=1,
        tx_type=0,
    )
    fulfill_receipt = _make_receipt(
        tx_hash=fulfill_hash,
        chain_id=ChainID.ARBITRUM_ONE,
        logs=[
            EvmTxReceiptLog(
                log_index=0,
                address=ARBITRUM_DAI_ADDRESS,
                data=net_raw.to_bytes(32, 'big'),
                topics=[
                    ERC20_OR_ERC721_TRANSFER,
                    address_to_bytes32(ARBITRUM_LEGACY_MANAGER),
                    address_to_bytes32(USER_ADDRESS),
                ],
            ),
            EvmTxReceiptLog(
                log_index=1,
                address=ARBITRUM_LEGACY_MANAGER,
                data=legacy_tx_data + relayer_fee_raw.to_bytes(32, 'big'),
                topics=[
                    LEGACY_TRANSACTION_FULFILLED_TOPIC,
                    address_to_bytes32(USER_ADDRESS),
                    address_to_bytes32(ROUTER_ADDRESS),
                    SAMPLE_TX_ID,
                ],
            ),
        ],
    )
    fulfill_events = _decode_offline_tx(
        database=database,
        decoder=arbitrum_one_transaction_decoder,
        transaction=fulfill_tx,
        receipt=fulfill_receipt,
    )
    assert len(fulfill_events) == 1
    assert fulfill_events[0].event_type == HistoryEventType.WITHDRAWAL
    assert fulfill_events[0].event_subtype == HistoryEventSubType.BRIDGE
    assert fulfill_events[0].counterparty == CPT_CONNEXT
    assert fulfill_events[0].amount == FVal('99')

    # Legacy cancel on Polygon
    cancel_hash = deserialize_evm_tx_hash('0x' + '66' * 32)
    cancel_tx = EvmTransaction(
        tx_hash=cancel_hash,
        chain_id=ChainID.POLYGON_POS,
        timestamp=Timestamp(1632100000),
        block_number=19010000,
        from_address=ROUTER_ADDRESS,
        to_address=DEFAULT_NXTP_MANAGER,
        value=0,
        gas=200000,
        gas_price=1,
        gas_used=100000,
        input_data=b'',
        nonce=1,
    )
    cancel_receipt = _make_receipt(
        tx_hash=cancel_hash,
        chain_id=ChainID.POLYGON_POS,
        logs=[
            EvmTxReceiptLog(
                log_index=0,
                address=POLYGON_DAI_ADDRESS,
                data=amount_raw.to_bytes(32, 'big'),
                topics=[
                    ERC20_OR_ERC721_TRANSFER,
                    address_to_bytes32(DEFAULT_NXTP_MANAGER),
                    address_to_bytes32(USER_ADDRESS),
                ],
            ),
            EvmTxReceiptLog(
                log_index=1,
                address=DEFAULT_NXTP_MANAGER,
                data=legacy_tx_data + address_to_bytes32(ROUTER_ADDRESS),
                topics=[
                    LEGACY_TRANSACTION_CANCELLED_TOPIC,
                    address_to_bytes32(USER_ADDRESS),
                    address_to_bytes32(ROUTER_ADDRESS),
                    SAMPLE_TX_ID,
                ],
            ),
        ],
    )
    cancel_events = _decode_offline_tx(
        database=database,
        decoder=polygon_pos_manager.transactions_decoder,
        transaction=cancel_tx,
        receipt=cancel_receipt,
    )
    assert len(cancel_events) == 1
    assert cancel_events[0].event_type == HistoryEventType.WITHDRAWAL
    assert cancel_events[0].event_subtype == HistoryEventSubType.REFUND
    assert cancel_events[0].counterparty == CPT_CONNEXT
    assert cancel_events[0].amount == FVal('100')


@pytest.mark.parametrize('ethereum_accounts', [[USER_ADDRESS]])
def test_connext_native_asset_bridge(
        ethereum_accounts: list[ChecksumEvmAddress],
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        database: DBHandler,
) -> None:
    """Verify native ETH (ZERO_ADDRESS) bridge prepare and internal-tx fulfill."""
    amount_raw = 2 * 10**18
    relayer_fee_raw = 10**16
    net_raw = amount_raw - relayer_fee_raw

    # Native prepare on Ethereum -> Arbitrum
    send_hash = deserialize_evm_tx_hash('0x' + '77' * 32)
    send_tx = EvmTransaction(
        tx_hash=send_hash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1664739000),
        block_number=15660000,
        from_address=USER_ADDRESS,
        to_address=DEFAULT_NXTP_MANAGER,
        value=amount_raw,
        gas=200000,
        gas_price=10**9,
        gas_used=100000,
        input_data=b'',
        nonce=1,
    )
    send_tx_data = _encode_tx_data(
        receiving_manager=ARBITRUM_MANAGER,
        user=USER_ADDRESS,
        router=ROUTER_ADDRESS,
        sending_asset=ZERO_ADDRESS,
        receiving_asset=ZERO_ADDRESS,
        fallback=USER_ADDRESS,
        receiving_address=USER_ADDRESS,
        sending_chain_id=ChainID.ETHEREUM.value,
        receiving_chain_id=ChainID.ARBITRUM_ONE.value,
        amount=amount_raw,
    )
    send_receipt = _make_receipt(
        tx_hash=send_hash,
        chain_id=ChainID.ETHEREUM,
        logs=[EvmTxReceiptLog(
            log_index=0,
            address=DEFAULT_NXTP_MANAGER,
            data=send_tx_data + address_to_bytes32(USER_ADDRESS),
            topics=[
                TRANSACTION_PREPARED_TOPIC,
                address_to_bytes32(USER_ADDRESS),
                address_to_bytes32(ROUTER_ADDRESS),
                SAMPLE_TX_ID,
            ],
        )],
    )
    send_events = _decode_offline_tx(
        database=database,
        decoder=ethereum_transaction_decoder,
        transaction=send_tx,
        receipt=send_receipt,
    )
    bridge_send = [e for e in send_events if e.counterparty == CPT_CONNEXT]
    assert bridge_send == [EvmEvent(
        tx_ref=send_hash,
        sequence_index=1,
        timestamp=TimestampMS(1664739000000),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=A_ETH,
        amount=FVal('2'),
        location_label=USER_ADDRESS,
        notes='Bridge 2 ETH from Ethereum to Arbitrum One via Connext',
        counterparty=CPT_CONNEXT,
        address=DEFAULT_NXTP_MANAGER,
        extra_data={'bridge': {
            'from_chain': 1,
            'to_chain': 42161,
            'from_address': USER_ADDRESS,
            'to_address': USER_ADDRESS,
            'to_asset': ZERO_ADDRESS,
            'transfer_id': SAMPLE_TX_ID.hex(),
        }},
    )]

    # Native fulfill on Ethereum (from Arbitrum) via internal tx
    recv_hash = deserialize_evm_tx_hash('0x' + '88' * 32)
    recv_tx = EvmTransaction(
        tx_hash=recv_hash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1664739100),
        block_number=15660010,
        from_address=RELAYER_ADDRESS,
        to_address=DEFAULT_NXTP_MANAGER,
        value=0,
        gas=200000,
        gas_price=10**9,
        gas_used=100000,
        input_data=b'',
        nonce=1,
    )
    recv_tx_data = _encode_tx_data(
        receiving_manager=DEFAULT_NXTP_MANAGER,
        user=USER_ADDRESS,
        router=ROUTER_ADDRESS,
        sending_asset=ZERO_ADDRESS,
        receiving_asset=ZERO_ADDRESS,
        fallback=USER_ADDRESS,
        receiving_address=USER_ADDRESS,
        sending_chain_id=ChainID.ARBITRUM_ONE.value,
        receiving_chain_id=ChainID.ETHEREUM.value,
        amount=amount_raw,
    )
    recv_receipt = _make_receipt(
        tx_hash=recv_hash,
        chain_id=ChainID.ETHEREUM,
        logs=[EvmTxReceiptLog(
            log_index=0,
            address=DEFAULT_NXTP_MANAGER,
            data=_encode_v01_fulfilled_data(recv_tx_data, relayer_fee_raw),
            topics=[
                TRANSACTION_FULFILLED_TOPIC,
                address_to_bytes32(USER_ADDRESS),
                address_to_bytes32(ROUTER_ADDRESS),
                SAMPLE_TX_ID,
            ],
        )],
    )
    recv_events = _decode_offline_tx(
        database=database,
        decoder=ethereum_transaction_decoder,
        transaction=recv_tx,
        receipt=recv_receipt,
        internal_transactions=[EvmInternalTransaction(
            parent_tx_hash=recv_hash,
            chain_id=ChainID.ETHEREUM,
            trace_id=1,
            from_address=DEFAULT_NXTP_MANAGER,
            to_address=USER_ADDRESS,
            value=net_raw,
            gas=0,
            gas_used=0,
        )],
    )
    assert recv_events == [EvmEvent(
        tx_ref=recv_hash,
        sequence_index=0,
        timestamp=TimestampMS(1664739100000),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=A_ETH,
        amount=FVal('1.99'),
        location_label=USER_ADDRESS,
        notes='Bridge 1.99 ETH from Arbitrum One to Ethereum via Connext',
        counterparty=CPT_CONNEXT,
        address=DEFAULT_NXTP_MANAGER,
        extra_data={'bridge': {
            'from_chain': 42161,
            'to_chain': 1,
            'from_address': USER_ADDRESS,
            'to_address': USER_ADDRESS,
            'transfer_id': SAMPLE_TX_ID.hex(),
        }},
    )]


@pytest.mark.parametrize('polygon_pos_accounts', [[USER_ADDRESS]])
def test_connext_malformed_log_data(
        polygon_pos_accounts: list[ChecksumEvmAddress],
        polygon_pos_manager: PolygonPOSManager,
        database: DBHandler,
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x' + '99' * 32)
    tx = EvmTransaction(
        tx_hash=tx_hash,
        chain_id=ChainID.POLYGON_POS,
        timestamp=Timestamp(1664739397),
        block_number=33849292,
        from_address=ROUTER_ADDRESS,
        to_address=POLYGON_MANAGER,
        value=0,
        gas=200000,
        gas_price=1,
        gas_used=100000,
        input_data=b'',
        nonce=1,
    )
    receipt = _make_receipt(
        tx_hash=tx_hash,
        chain_id=ChainID.POLYGON_POS,
        logs=[
            EvmTxReceiptLog(
                log_index=0,
                address=POLYGON_MANAGER,
                data=b'\x00' * 16,
                topics=[
                    TRANSACTION_PREPARED_TOPIC,
                    address_to_bytes32(USER_ADDRESS),
                    address_to_bytes32(ROUTER_ADDRESS),
                    SAMPLE_TX_ID,
                ],
            ),
            EvmTxReceiptLog(
                log_index=1,
                address=POLYGON_MANAGER,
                data=b'\x00' * 16,
                topics=[
                    TRANSACTION_FULFILLED_TOPIC,
                    address_to_bytes32(USER_ADDRESS),
                    address_to_bytes32(ROUTER_ADDRESS),
                    SAMPLE_TX_ID,
                ],
            ),
            EvmTxReceiptLog(
                log_index=2,
                address=POLYGON_MANAGER,
                data=b'\x00' * 16,
                topics=[
                    TRANSACTION_CANCELLED_TOPIC,
                    address_to_bytes32(USER_ADDRESS),
                    address_to_bytes32(ROUTER_ADDRESS),
                    SAMPLE_TX_ID,
                ],
            ),
        ],
    )
    events = _decode_offline_tx(
        database=database,
        decoder=polygon_pos_manager.transactions_decoder,
        transaction=tx,
        receipt=receipt,
    )
    assert events == []


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_manager_connect_at_start', [(
    WeightedNode(
        node_info=NodeName(
            name='polygon-drpc',
            endpoint='https://polygon.drpc.org',
            owned=False,
            blockchain=SupportedBlockchain.POLYGON_POS,
        ),
        active=True,
        weight=ONE,
    ),
)])
@pytest.mark.parametrize('polygon_pos_accounts', [[USER_ADDRESS]])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_connext_bridge_send_on_polygon(
        polygon_pos_inquirer: PolygonPOSInquirer,
        polygon_pos_accounts: list[ChecksumEvmAddress],
) -> None:
    with patch(
        'rotkehlchen.chain.evm.transactions.'
        'EvmTransactions._query_and_save_internal_transactions_for_parent_hash',
        return_value=[],
    ):
        events, _ = get_decoded_events_of_transaction(
            evm_inquirer=polygon_pos_inquirer,
            tx_hash=(tx_hash := deserialize_evm_tx_hash(
                '0x7d672c0d7e376408f1bfe4f0dff83900239cd87ed91510b47ac36d1c12f94b2c',
            )),
        )
    user_address = polygon_pos_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1664739397000)),
            location=LOCATION_POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POL,
            amount=FVal('0.003799832699096996'),
            location_label=user_address,
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=226,
            timestamp=timestamp,
            location=LOCATION_POLYGON_POS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_POLYGON_DAI,
            amount=FVal('558.063689'),
            location_label=user_address,
            notes='Bridge 558.063689 DAI from Polygon POS to Arbitrum One via Connext',
            counterparty=CPT_CONNEXT,
            address=POLYGON_MANAGER,
            extra_data={'bridge': {
                'from_chain': 137,
                'to_chain': 42161,
                'from_address': user_address,
                'to_address': user_address,
                'to_asset': ARBITRUM_DAI_ADDRESS,
                'transfer_id': SAMPLE_TX_ID.hex(),
            }},
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=227,
            timestamp=timestamp,
            location=LOCATION_POLYGON_POS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_POLYGON_DAI,
            amount=FVal('0'),
            location_label=user_address,
            address=POLYGON_MANAGER,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_manager_connect_at_start', [(
    WeightedNode(
        node_info=NodeName(
            name='arbitrum-rpc',
            endpoint='https://arb1.arbitrum.io/rpc',
            owned=False,
            blockchain=SupportedBlockchain.ARBITRUM_ONE,
        ),
        active=True,
        weight=ONE,
    ),
)])
@pytest.mark.parametrize('arbitrum_one_accounts', [[USER_ADDRESS]])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_connext_bridge_receive_on_arbitrum(
        arbitrum_one_inquirer: ArbitrumOneInquirer,
        arbitrum_one_accounts: list[ChecksumEvmAddress],
) -> None:
    with patch(
        'rotkehlchen.chain.evm.transactions.'
        'EvmTransactions._query_and_save_internal_transactions_for_parent_hash',
        return_value=[],
    ):
        events, _ = get_decoded_events_of_transaction(
            evm_inquirer=arbitrum_one_inquirer,
            tx_hash=(tx_hash := deserialize_evm_tx_hash(
                '0x8ef5f4ff4136f90c1e7428dea480aa10b13e936fb955962888a35cb2e690167e',
            )),
        )
    user_address = arbitrum_one_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1664739556000),
            location=LOCATION_ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ARBITRUM_DAI,
            amount=FVal('557.283984256552687306'),
            location_label=user_address,
            notes=(
                'Bridge 557.283984256552687306 DAI from Polygon POS to Arbitrum One via Connext'
            ),
            counterparty=CPT_CONNEXT,
            address=ARBITRUM_MANAGER,
            extra_data={'bridge': {
                'from_chain': 137,
                'to_chain': 42161,
                'from_address': user_address,
                'to_address': user_address,
                'transfer_id': SAMPLE_TX_ID.hex(),
            }},
        ),
    ]
