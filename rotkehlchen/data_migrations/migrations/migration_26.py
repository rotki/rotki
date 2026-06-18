import logging
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.gnosis.modules.gnosis_pay.constants import (
    CPT_GNOSIS_PAY,
    GNOSIS_PAY_SPENDING_COLLECTOR,
)
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import Location
from rotkehlchen.utils.progress import perform_userdb_migration_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log()
def data_migration_26(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """Introduced at v1.43.2

    - Clean up manually tracked balance tag mappings that were orphaned by the v51->v52 DB
    upgrade. That upgrade rebuilt manually_tracked_balances without preserving the id column,
    so rows above a deleted-id gap were renumbered and their tag_mappings (keyed by the old id)
    no longer point at any balance. Worse, since ids are now dense, a stale mapping can later
    re-attach to a newly added balance that happens to reuse the old id, showing a phantom tag.

    The original association is unrecoverable, so we delete the orphaned mappings. Manual balance
    tags use a pure-integer object_reference (blockchain accounts use addresses and xpubs use the
    xpub string), so all-digit references that match no current balance id are the orphans.

    - Retag Gnosis Pay card payments made through the new post-hack spender contract that were
    decoded as plain token spends before the decoder learned the new spender address.
    """
    @progress_step(description='Removing orphaned manual balance tag mappings')
    def _remove_orphaned_manual_balance_tags(rotki: 'Rotkehlchen') -> None:
        with rotki.data.db.conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'DELETE FROM tag_mappings WHERE '
                "object_reference GLOB '[0-9]*' AND NOT object_reference GLOB '*[^0-9]*' AND "
                'CAST(object_reference AS INTEGER) NOT IN (SELECT id FROM manually_tracked_balances)',  # noqa: E501
            )

    @progress_step(description='Tagging Gnosis Pay payments from the new spender contract')
    def _retag_gnosis_pay_new_spender_payments(rotki: 'Rotkehlchen') -> None:
        """Gnosis Pay payments made through the new post-hack spender contract were decoded as
        plain token spends before the decoder learned the new spender address. They are missing
        the gnosis_pay counterparty, so the Gnosis Pay refresh (which only enriches events that
        already carry the counterparty) can never attach merchant data to them.

        All Gnosis Pay card payments (old and new spender alike) send the spent token to the
        spending collector, so we match outgoing transfers to it that are not yet attributed to
        any counterparty and turn them into proper payment events. This lets a refresh pick them
        up without a full redecode. Reproducing the decoder's notes is what makes the automatic
        merchant backfill (which looks for 'Spend% via Gnosis Pay' notes) find them too.
        """
        updates: list[tuple[str, int]] = []
        with rotki.data.db.conn.read_ctx() as cursor:
            for identifier, amount, asset_id in cursor.execute(
                'SELECT H.identifier, H.amount, H.asset FROM history_events H '
                'INNER JOIN chain_events_info EI ON EI.identifier = H.identifier '
                'WHERE H.location = ? AND H.type = ? AND H.subtype = ? AND '
                'EI.address = ? AND EI.counterparty IS NULL',
                (
                    Location.GNOSIS.serialize_for_db(),
                    HistoryEventType.SPEND.serialize(),
                    HistoryEventSubType.NONE.serialize(),
                    GNOSIS_PAY_SPENDING_COLLECTOR,
                ),
            ):
                try:
                    symbol = Asset(asset_id).resolve_to_asset_with_symbol().symbol
                except (UnknownAsset, WrongAssetType) as e:
                    log.error(
                        'Could not resolve symbol for %s while tagging Gnosis Pay '
                        'payment event %s due to %s. Skipping it',
                        asset_id, identifier, e,
                    )
                    continue

                updates.append((f'Spend {FVal(amount)} {symbol} via Gnosis Pay', identifier))

        if len(updates) == 0:
            return

        with rotki.data.db.conn.write_ctx() as write_cursor:
            write_cursor.executemany(
                'UPDATE history_events SET subtype = ?, notes = ? WHERE identifier = ?',
                [
                    (HistoryEventSubType.PAYMENT.serialize(), notes, identifier)
                    for notes, identifier in updates
                ],
            )
            write_cursor.executemany(
                'UPDATE chain_events_info SET counterparty = ? WHERE identifier = ?',
                [(CPT_GNOSIS_PAY, identifier) for _, identifier in updates],
            )

    perform_userdb_migration_steps(rotki, progress_handler, should_vacuum=False)
