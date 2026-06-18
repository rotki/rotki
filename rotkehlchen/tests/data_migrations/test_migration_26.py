"""Test for data migration 26 - cleanup of orphaned manual balance tag mappings."""
import pytest

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.gnosis.modules.gnosis_pay.constants import (
    CPT_GNOSIS_PAY,
    GNOSIS_PAY_SPENDING_COLLECTOR,
)
from rotkehlchen.constants.assets import Asset
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.data_migrations import run_single_migration
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash, Location, TimestampMS

A_EURE = Asset('eip155:100/erc20:0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430')
# An unrelated EURe recipient used to check that only transfers to the spending collector match.
OTHER_ADDRESS = string_to_evm_address('0x9E0D8c9ff04F58e8D4053b78d33e582D8aCc8c44')


@pytest.mark.parametrize('data_migration_version', [25])
def test_migration_26_orphaned_manual_balance_tags(database: DBHandler) -> None:
    """Orphaned manual-balance tag mappings (left by the v51->v52 id renumbering) are removed,
    while valid manual-balance tags and non-numeric references (blockchain accounts, xpubs) stay.
    """
    address = '0x742d35Cc6634C0532925a3b844Bc454e4438f44e'
    xpub_ref = 'xpub6CUGRUonZSQ4TWtTMmzXdrXDtypWKiKrhko4egpiMZbpiaQL2jkwSB1icqYh2cfDfVxdx4df189oLKnC5fSwqPfgyP3hooxujYzAu3fDVmz/m'  # noqa: E501
    with database.user_write() as write_cursor:
        # two manual balances with an id gap (id 4 missing), as left behind by a deletion
        write_cursor.executemany(
            'INSERT INTO manually_tracked_balances(id, asset, label, amount, location, category) '
            'VALUES(?, ?, ?, ?, ?, ?)',
            [
                (3, 'BTC', 'kept wallet', '1', 'A', 'A'),
                (5, 'ETH', 'tagged wallet', '2', 'A', 'A'),
            ],
        )
        write_cursor.execute(
            'INSERT OR IGNORE INTO tags(name, description, background_color, foreground_color) '
            'VALUES(?, ?, ?, ?)', ('public', '', 'ffffff', '000000'),
        )
        write_cursor.executemany(
            'INSERT INTO tag_mappings(object_reference, tag_name) VALUES(?, ?)',
            [
                ('5', 'public'),  # valid: points at an existing manual balance
                ('7', 'public'),  # orphan: no manual balance with id 7
                (address, 'public'),  # blockchain account tag, must be untouched
                (xpub_ref, 'public'),  # xpub tag, must be untouched
            ],
        )

    run_single_migration(database=database, migration=26)

    with database.conn.read_ctx() as cursor:
        assert set(cursor.execute(
            'SELECT object_reference FROM tag_mappings WHERE tag_name=?', ('public',),
        ).fetchall()) == {('5',), (address,), (xpub_ref,)}  # orphan '7' removed, rest kept


@pytest.mark.parametrize('data_migration_version', [25])
def test_migration_26_retag_gnosis_pay_new_spender_payments(database: DBHandler) -> None:
    """A Gnosis Pay payment decoded as a plain spend (no counterparty) before the new spender
    was supported is retagged as a gnosis_pay payment, so a refresh and the merchant backfill
    can pick it up. Already-tagged payments and spends to other addresses are left untouched.
    """
    dbevents = DBHistoryEvents(database)

    def make_spend(
            tx_ref: EVMTxHash,
            amount: str,
            address: ChecksumEvmAddress,
            subtype: HistoryEventSubType,
            counterparty: str | None,
            notes: str | None,
    ) -> EvmEvent:
        return EvmEvent(
            tx_ref=tx_ref,
            sequence_index=0,
            timestamp=TimestampMS(1780902380000),
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=subtype,
            asset=A_EURE,
            amount=FVal(amount),
            location_label=OTHER_ADDRESS,
            notes=notes,
            counterparty=counterparty,
            address=address,
        )

    # the v2 payment decoded as a plain spend - should be retagged
    target_event = make_spend(
        tx_ref=(target_tx := make_evm_tx_hash()),
        amount='2.1',
        address=GNOSIS_PAY_SPENDING_COLLECTOR,
        subtype=HistoryEventSubType.NONE,
        counterparty=None,
        notes='Send 2.1 EURe from gnosis address to gnosis address',
    )
    # an already correctly decoded payment - must not be touched
    tagged_event = make_spend(
        tx_ref=make_evm_tx_hash(),
        amount='5',
        address=GNOSIS_PAY_SPENDING_COLLECTOR,
        subtype=HistoryEventSubType.PAYMENT,
        counterparty=CPT_GNOSIS_PAY,
        notes='Spend 5 EURe via Gnosis Pay',
    )
    # a plain spend to a different address - must not be touched
    other_event = make_spend(
        tx_ref=make_evm_tx_hash(),
        amount='3',
        address=OTHER_ADDRESS,
        subtype=HistoryEventSubType.NONE,
        counterparty=None,
        notes='Send 3 EURe from gnosis address to gnosis address',
    )
    with database.user_write() as write_cursor:
        target_id = dbevents.add_history_event(write_cursor, target_event)
        tagged_id = dbevents.add_history_event(write_cursor, tagged_event)
        other_id = dbevents.add_history_event(write_cursor, other_event)

    assert target_id is not None and tagged_id is not None and other_id is not None

    backfill_query = (
        'SELECT EI.tx_ref FROM history_events H '
        'INNER JOIN chain_events_info EI ON EI.identifier = H.identifier '
        'WHERE H.location = ? AND EI.counterparty = ? AND H.notes LIKE ?'
    )
    backfill_bindings = (
        Location.GNOSIS.serialize_for_db(),
        CPT_GNOSIS_PAY,
        'Spend% via Gnosis Pay',
    )
    with database.conn.read_ctx() as cursor:  # before migration the merchant backfill misses it
        assert (bytes(target_tx),) not in cursor.execute(backfill_query, backfill_bindings).fetchall()  # noqa: E501

    run_single_migration(database=database, migration=26)

    with database.conn.read_ctx() as cursor:
        assert set(cursor.execute(
            'SELECT H.identifier, H.type, H.subtype, H.notes, EI.counterparty '
            'FROM history_events H '
            'INNER JOIN chain_events_info EI ON EI.identifier = H.identifier '
            'WHERE H.identifier IN (?, ?, ?)',
            (target_id, tagged_id, other_id),
        ).fetchall()) == {
            # the v2 payment got retagged as a gnosis pay payment
            (target_id, HistoryEventType.SPEND.serialize(), HistoryEventSubType.PAYMENT.serialize(), 'Spend 2.1 EURe via Gnosis Pay', CPT_GNOSIS_PAY),  # noqa: E501
            # the already tagged and the unrelated spend stay exactly as they were
            (tagged_id, HistoryEventType.SPEND.serialize(), HistoryEventSubType.PAYMENT.serialize(), 'Spend 5 EURe via Gnosis Pay', CPT_GNOSIS_PAY),  # noqa: E501
            (other_id, HistoryEventType.SPEND.serialize(), HistoryEventSubType.NONE.serialize(), 'Send 3 EURe from gnosis address to gnosis address', None),  # noqa: E501
        }
        # the merchant backfill now finds the retagged event
        assert (bytes(target_tx),) in cursor.execute(backfill_query, backfill_bindings).fetchall()
