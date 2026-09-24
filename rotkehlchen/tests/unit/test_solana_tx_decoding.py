from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.chain.solana.types import SolanaTransaction
from rotkehlchen.concurrency import TaskCancelledError
from rotkehlchen.constants.assets import A_SOL
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.constants import TX_DECODED
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.factories import make_solana_signature
from rotkehlchen.types import Timestamp, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.chain.solana.manager import SolanaManager


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('failure_stage', ['decode', 'write'])
def test_cancelled_redecode_preserves_solana_history(
        solana_manager: SolanaManager,
        failure_stage: str,
) -> None:
    decoder = solana_manager.transactions_decoder
    database = solana_manager.database
    transaction = SolanaTransaction(
        fee=0, slot=1, success=True, signature=make_solana_signature(),
        block_time=Timestamp(1), account_keys=[], instructions=[],
    )
    with database.user_write() as cursor:
        decoder.dbtx.add_transactions(cursor, [transaction], relevant_address=None)
        tx_id = transaction.get_or_query_db_id(cursor)
        event_id = DBHistoryEvents(database).add_history_event(cursor, SolanaEvent(
            tx_ref=transaction.signature, sequence_index=0, timestamp=TimestampMS(1000),
            event_type=HistoryEventType.RECEIVE, event_subtype=HistoryEventSubType.NONE,
            asset=A_SOL, amount=ONE,
        ))
        cursor.execute(
            'INSERT INTO solana_tx_mappings(tx_id, value) VALUES (?, ?)', (tx_id, TX_DECODED),
        )

    with (
        patch.object(
            decoder,
            '_decode_transaction' if failure_stage == 'decode' else '_write_tx_events',
            side_effect=TaskCancelledError('cancelled during redecoding'),
        ),
        pytest.raises(TaskCancelledError),
    ):
        decoder._decode_transaction_from_context(
            transaction, ignore_cache=True, delete_customized=False,
        )

    with database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT identifier FROM history_events').fetchall() == [(event_id,)]
        assert cursor.execute('SELECT tx_id, value FROM solana_tx_mappings').fetchall() == [
            (tx_id, TX_DECODED),
        ]

    decoder._decode_transaction_from_context(
        transaction, ignore_cache=True, delete_customized=False,
    )
    with database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT identifier FROM history_events').fetchall() == []
        assert cursor.execute('SELECT tx_id, value FROM solana_tx_mappings').fetchall() == [
            (tx_id, TX_DECODED),
        ]
