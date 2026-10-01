from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.l2_with_l1_fees.types import (
    L1_ORIGINATED_TX_TYPE,
    L2WithL1FeesTransaction,
)
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, TX_DECODED, HistoryMappingState
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.l2withl1feestx import DBL2WithL1FeesTx
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.data_migrations.test_migrations import MockRotkiForMigrations
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
    customized events keep their events and stay decoded, since redecoding them on top of
    the preserved events would not repair them. Their fee is resolved instead and their gas
    event corrected, unless the gas event itself is customized or the fee cannot be resolved.
    """
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
            (ChainID.OPTIMISM, 0),  # legacy zero with a customized gas event, stays decoded
            (ChainID.OPTIMISM, 0),  # legacy zero with a customized sibling, gas event corrected
            (ChainID.BASE, 0),  # legacy zero with a customized sibling, fee resolution fails
            (ChainID.OPTIMISM, 0),  # failed legacy zero with a customized sibling, gas corrected
            (ChainID.OPTIMISM, None),  # L1 originated with a customized sibling, untouched
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
            [(tx_id, None, 1, L1_ORIGINATED_TX_TYPE if idx in {3, 9} else 2) for idx, tx_id in enumerate(tx_ids)],  # noqa: E501
        )
        for tx, tx_id, location in zip(
                transactions[:4] + transactions[5:],
                tx_ids[:4] + tx_ids[5:],
                (Location.OPTIMISM, Location.BASE, Location.OPTIMISM, Location.SCROLL, Location.OPTIMISM, Location.OPTIMISM, Location.BASE, Location.OPTIMISM, Location.OPTIMISM),  # noqa: E501
                strict=True,
        ):
            dbevents.add_history_event(
                write_cursor=write_cursor,
                event=EvmEvent(
                    tx_ref=tx.tx_hash,
                    sequence_index=0,
                    timestamp=TimestampMS(1000),
                    location=location,
                    event_type=HistoryEventType.FAIL if (failed := tx_id == tx_ids[8]) else HistoryEventType.SPEND,  # noqa: E501
                    event_subtype=HistoryEventSubType.FEE,
                    asset=Asset('ETH'),
                    amount=FVal('0.000021'),
                    location_label=tx.from_address,
                    notes=f"Burn 0.000021 ETH for gas{' of a failed transaction' if failed else ''}",  # noqa: E501
                    counterparty=CPT_GAS,
                ),
                mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED} if tx_id == tx_ids[5] else None,  # noqa: E501
            )
            if tx_id in tx_ids[6:]:
                dbevents.add_history_event(
                    write_cursor=write_cursor,
                    event=EvmEvent(
                        tx_ref=tx.tx_hash,
                        sequence_index=1,
                        timestamp=TimestampMS(1000),
                        location=location,
                        event_type=HistoryEventType.RECEIVE,
                        event_subtype=HistoryEventSubType.REWARD,
                        asset=Asset('ETH'),
                        amount=FVal('1'),
                        location_label=tx.from_address,
                    ),
                    mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.MATCHED},
                )
            write_cursor.execute(
                'INSERT INTO evm_tx_mappings(tx_id, value) VALUES(?, ?)',
                (tx_id, TX_DECODED),
            )

    def mock_ensure_tx_data_exists(cursor, tx_hash, relevant_address):  # pylint: disable=unused-argument
        """Resolve the fee like the real repair does, failing for the last transaction"""
        if tx_hash == transactions[7].tx_hash:
            raise RemoteError('all indexers failed')

        idx = next(idx for idx, tx in enumerate(transactions) if tx.tx_hash == tx_hash)
        (tx := transactions[idx]).l1_fee = 500000
        with database.user_write() as write_cursor:
            DBL2WithL1FeesTx.set_l1_fee(
                write_cursor=write_cursor,
                tx_id=tx_ids[idx],
                l1_fee=tx.l1_fee,
            )
        return tx, None

    (chains_aggregator := MagicMock()).get_evm_manager.return_value.transactions.ensure_tx_data_exists.side_effect = mock_ensure_tx_data_exists  # noqa: E501
    with patch.object(MockRotkiForMigrations, 'chains_aggregator', new=chains_aggregator, create=True):  # noqa: E501
        run_single_migration(database=database, migration=28)

    with database.conn.read_ctx() as cursor:
        for tx, tx_id, (expected_fee, decoded, events_num, gas_amount, failed) in zip(transactions, tx_ids, (  # noqa: E501
            (None, False, 0, None, False),
            (None, False, 0, None, False),
            ('123', True, 1, '0.000021', False),
            ('0', True, 1, '0.000021', False),
            (None, False, 0, None, False),
            ('500000', True, 1, '0.000021', False),  # customized gas event left as is
            ('500000', True, 2, '0.000000000000521', False),  # 21000 * 1 + 500000 wei
            (None, True, 2, '0.000021', False),
            ('500000', True, 2, '0.000000000000521', True),
            (None, True, 2, '0.000021', False),
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
            ).fetchone()[0] == events_num
            assert cursor.execute(
                'SELECT amount, notes FROM history_events AS events INNER JOIN chain_events_info '
                'AS info ON info.identifier=events.identifier WHERE info.tx_ref=? AND '
                'events.sequence_index=0',
                (tx.tx_hash,),
            ).fetchone() == (None if gas_amount is None else (
                gas_amount,
                f"Burn {gas_amount} ETH for gas{' of a failed transaction' if failed else ''}",
            ))
