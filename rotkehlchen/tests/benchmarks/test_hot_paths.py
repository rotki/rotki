"""Micro-benchmarks for hot pure-python paths (measurement framework §4.4).

Excluded from normal test runs via the global `-m "not benchmark"` addopts.
Run explicitly with:

    uv run python pytestgeventwrapper.py -m benchmark --benchmark-only rotkehlchen/tests/benchmarks

Kept pytest-codspeed compatible: only the plain `benchmark` fixture API is
used, so switching/adding `pytest-codspeed` later is a drop-in.
"""
from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH, A_USDC
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import deserialize_evm_tx_hash
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmTransaction,
    Location,
    Timestamp,
    TimestampMS,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.db.dbhandler import DBHandler

N_EVENTS = 1_000
N_CUSTOMIZED_TXS = 1_000
N_DECODE_TXS = 50
USDT_ADDRESS = string_to_evm_address('0xdAC17F958D2ee523a2206206994597C13D831ec7')


def _address_topic(address: ChecksumEvmAddress) -> bytes:
    """Left-pad a 20-byte address into a 32-byte log topic."""
    return bytes(12) + bytes.fromhex(address[2:])


def _make_decodable_transactions(
        from_address: ChecksumEvmAddress,
        to_address: ChecksumEvmAddress,
) -> list[tuple[EvmTransaction, EvmTxReceipt]]:
    """Build representative ERC20-transfer transactions decoded fully offline.

    Each transaction carries a gas fee plus three USDT Transfer logs between two tracked
    accounts, the most common shape the decoder processes. Both endpoints are tracked so the
    transfer-decoding path actually emits events instead of bailing out early.
    """
    from_topic, to_topic = _address_topic(from_address), _address_topic(to_address)
    transactions = []
    for idx in range(N_DECODE_TXS):
        tx_hash = deserialize_evm_tx_hash(idx.to_bytes(32, 'big'))
        transactions.append((
            EvmTransaction(
                tx_hash=tx_hash,
                chain_id=ChainID.ETHEREUM,
                timestamp=Timestamp(1700000000 + idx),
                block_number=18000000 + idx,
                from_address=from_address,
                to_address=USDT_ADDRESS,
                value=0,
                gas=45000,
                gas_price=10000000000,
                gas_used=45000,
                input_data=b'',
                nonce=idx,
            ),
            EvmTxReceipt(
                tx_hash=tx_hash,
                chain_id=ChainID.ETHEREUM,
                contract_address=None,
                status=True,
                tx_type=0,
                logs=[
                    EvmTxReceiptLog(
                        log_index=log_idx,
                        data=((idx + log_idx + 1) * 1000000).to_bytes(32, 'big'),
                        address=USDT_ADDRESS,
                        topics=[ERC20_OR_ERC721_TRANSFER, from_topic, to_topic],
                    )
                    for log_idx in range(3)
                ],
            ),
        ))

    return transactions


def _make_events() -> list[EvmEvent]:
    address = string_to_evm_address('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    return [
        EvmEvent(
            tx_ref=deserialize_evm_tx_hash(idx.to_bytes(32, 'big')),
            sequence_index=idx % 16,
            timestamp=TimestampMS(1700000000000 + idx * 13_000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_USDC if idx % 3 == 0 else A_ETH,
            amount=FVal(f'{idx + 1}.{idx % 100:02d}'),
            location_label=address,
            counterparty='uniswap-v3' if idx % 5 == 0 else None,
            address=address,
            notes=f'Receive {idx + 1} tokens from somewhere interesting {idx}',
        )
        for idx in range(N_EVENTS)
    ]


@pytest.mark.benchmark
def test_history_event_db_serialization(benchmark: 'Callable') -> None:
    """Write-path serialization of history events, exercised on every
    transaction decode and event edit"""
    events = _make_events()
    benchmark(lambda: [event.serialize_for_db() for event in events])


@pytest.mark.benchmark
def test_history_event_api_serialization(benchmark: 'Callable') -> None:
    """API serialization of history events, exercised on every events page"""
    events = _make_events()
    benchmark(lambda: [event.serialize() for event in events])


@pytest.mark.benchmark
def test_fval_arithmetic(benchmark: 'Callable') -> None:
    """FVal math as done in balance aggregation loops"""
    values = [FVal(f'{idx}.{idx % 1000:03d}') for idx in range(1, N_EVENTS + 1)]
    price = FVal('1234.5678')

    def aggregate() -> FVal:
        total = FVal(0)
        for value in values:
            total += value * price
        return total

    benchmark(aggregate)


@pytest.mark.benchmark
def test_redecode_delete_customized_lookup(benchmark: 'Callable', database: 'DBHandler') -> None:
    """Per-transaction redecode delete path.

    When redecoding, rotki calls `delete_events_by_tx_ref` once per transaction (see
    `decoder._maybe_load_or_purge_events_from_db`). The customized-event exclusion lookup
    used to scan the whole `history_events_mappings` table on every call, so its cost grew
    with the user's total customized events rather than with the few txs being redecoded.

    This seeds a heavy customized-events table and measures a single delete on a fully
    customized tx. Such a tx is preserved by `preserve_transactions`, so the call deletes
    nothing and stays repeatable across benchmark rounds while still exercising the lookup.
    """
    db = DBHistoryEvents(database)
    tx_hashes = [make_evm_tx_hash() for _ in range(N_CUSTOMIZED_TXS)]
    with database.user_write() as write_cursor:
        for tx_hash in tx_hashes:
            for seq_idx in range(2):
                db.add_history_event(
                    write_cursor=write_cursor,
                    event=EvmEvent(
                        tx_ref=tx_hash,
                        sequence_index=seq_idx,
                        timestamp=TimestampMS(1700000000000),
                        location=Location.ETHEREUM,
                        event_type=HistoryEventType.RECEIVE,
                        event_subtype=HistoryEventSubType.NONE,
                        asset=A_ETH,
                        amount=ONE,
                    ),
                    mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED},
                )

    def run() -> None:
        with database.user_write() as write_cursor:
            db.delete_events_by_tx_ref(
                write_cursor=write_cursor,
                tx_refs=[tx_hashes[0]],
                location=Location.ETHEREUM,
                customized_handling='preserve_transactions',
            )

    benchmark(run)


@pytest.mark.benchmark
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x4bBa290826C253BD854121346c370a9886d1bC26',
    '0x38C3f1Ab36BdCa29133d8AF7A19811D10B6CA3FC',
]])
def test_transaction_decoding(
        benchmark: 'Callable',
        database: 'DBHandler',
        ethereum_accounts: list[ChecksumEvmAddress],
        ethereum_transaction_decoder: 'EthereumTransactionDecoder',
) -> None:
    """Generic transaction-decoding hot path.

    Measures `_decode_transaction` (gas event + per-log decoder dispatch + ERC20 transfer
    decoding + post-decoding rules + event ordering), the backbone every redecode runs per
    transaction. It is read-only (the event DB write is deferred to the caller), so decoding
    the same batch each round is repeatable, deterministic and needs no network.
    """
    tx_data = _make_decodable_transactions(ethereum_accounts[0], ethereum_accounts[1])
    with database.user_write() as write_cursor:
        DBEvmTx(database).add_transactions(
            write_cursor,
            [tx for tx, _ in tx_data],
            relevant_address=None,
        )

    # guard that the data actually exercises the decode path (1 gas + 3 transfer events)
    # so the benchmark cannot silently degrade into decoding nothing
    sample_events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=tx_data[0][0],
        tx_receipt=tx_data[0][1],
    )
    assert len(sample_events) == 4

    def run() -> None:
        for transaction, receipt in tx_data:
            ethereum_transaction_decoder._decode_transaction(
                transaction=transaction,
                tx_receipt=receipt,
            )

    benchmark(run)


@pytest.mark.benchmark
def test_events_filter_query_construction(benchmark: 'Callable') -> None:
    """Filter-query construction + SQL preparation, done per events API call"""
    def build() -> tuple:
        filter_query = EvmEventFilterQuery.make(
            from_ts=Timestamp(1600000000),
            to_ts=Timestamp(1800000000),
            assets=(A_ETH, A_USDC),
            counterparties=['uniswap-v3', 'gas'],
            location_labels=['0x9531C059098e3d194fF87FebB587aB07B30B1306'],
            limit=50,
            offset=0,
        )
        return filter_query.prepare()

    benchmark(build)
