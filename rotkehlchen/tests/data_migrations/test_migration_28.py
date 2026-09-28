from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.l2_with_l1_fees.types import (
    L1_ORIGINATED_TX_TYPE,
    L2WithL1FeesTransaction,
)
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, TX_DECODED, HistoryMappingState
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.l2withl1feestx import DBL2WithL1FeesTx
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.data_migrations import run_single_migration
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import ChainID, Location, Timestamp, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


@pytest.mark.parametrize('data_migration_version', [27])
def test_migration_28_resets_legacy_zero_fees(database: DBHandler) -> None:
    """Decoded transactions with a legacy zero L1 fee get their fee marked unresolved and
    their decoded events reset so they are redecoded. Resolved nonzero fees and L1
    originated transactions, whose fee is always zero, are left decoded. Transactions with
    customized events get their fee marked unresolved but keep their events and stay
    decoded, since redecoding them on top of the preserved events would not repair them."""
    transactions = [
        L2WithL1FeesTransaction(
            tx_hash=make_evm_tx_hash(),
            chain_id=chain_id,
            timestamp=Timestamp(1),
            block_number=1,
            from_address=make_evm_address(),
            to_address=None,
            value=0,
            gas=21000,
            gas_price=1,
            gas_used=21000,
            input_data=b'',
            nonce=0,
            l1_fee=fee,
        ) for chain_id, fee in (
            (ChainID.OPTIMISM, 0),  # legacy zero, reset
            (ChainID.BASE, 0),  # legacy zero, reset
            (ChainID.OPTIMISM, 123),  # resolved, kept
            (ChainID.SCROLL, 0),  # L1 originated, kept
            (ChainID.OPTIMISM, None),  # unresolved and not decoded, untouched
            (ChainID.OPTIMISM, 0),  # legacy zero with a customized event, stays decoded
        )
    ]
    dbevents = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        DBL2WithL1FeesTx(database).add_transactions(
            write_cursor=write_cursor,
            evm_transactions=transactions,
            relevant_address=None,
        )
        tx_ids = [write_cursor.execute(
            'SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
            (tx.tx_hash, tx.chain_id.serialize_for_db()),
        ).fetchone()[0] for tx in transactions]
        write_cursor.executemany(
            'INSERT INTO evmtx_receipts(tx_id, contract_address, status, type) VALUES(?, ?, ?, ?)',
            [(tx_id, None, 1, L1_ORIGINATED_TX_TYPE if idx == 3 else 2) for idx, tx_id in enumerate(tx_ids)],  # noqa: E501
        )
        for tx, tx_id, location in zip(
                transactions[:4] + transactions[5:],
                tx_ids[:4] + tx_ids[5:],
                (Location.OPTIMISM, Location.BASE, Location.OPTIMISM, Location.SCROLL, Location.OPTIMISM),  # noqa: E501
                strict=True,
        ):
            dbevents.add_history_event(
                write_cursor=write_cursor,
                event=EvmEvent(
                    tx_ref=tx.tx_hash,
                    sequence_index=0,
                    timestamp=TimestampMS(1000),
                    location=location,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=Asset('ETH'),
                    amount=FVal('0.000021'),
                    location_label=tx.from_address,
                ),
                mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED} if tx_id == tx_ids[5] else None,  # noqa: E501
            )
            write_cursor.execute(
                'INSERT INTO evm_tx_mappings(tx_id, value) VALUES(?, ?)',
                (tx_id, TX_DECODED),
            )

    run_single_migration(database=database, migration=28)

    with database.conn.read_ctx() as cursor:
        for tx, tx_id, (expected_fee, decoded) in zip(transactions, tx_ids, (
            (None, False),
            (None, False),
            ('123', True),
            ('0', True),
            (None, False),
            (None, True),
        ), strict=True):
            assert cursor.execute(
                'SELECT l1_fee FROM optimism_transactions WHERE tx_id=?', (tx_id,),
            ).fetchone() == (expected_fee,)
            assert cursor.execute(
                'SELECT COUNT(*) FROM evm_tx_mappings WHERE tx_id=? AND value=?',
                (tx_id, TX_DECODED),
            ).fetchone()[0] == int(decoded)
            assert cursor.execute(
                'SELECT COUNT(*) FROM chain_events_info WHERE tx_ref=?',
                (tx.tx_hash,),
            ).fetchone()[0] == int(decoded)
