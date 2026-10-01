import json
import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.l2_with_l1_fees.types import (
    L1_ORIGINATED_TX_TYPE,
    L2_CHAINIDS_WITH_L1_FEES,
    L2ChainIdsWithL1FeesType,
    L2WithL1FeesTransaction,
)
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, TX_DECODED, HistoryMappingState
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.icons import NOT_FOUND_ICON_MARKER_SUFFIX
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import ChainID, EVMTxHash, Location, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import from_wei
from rotkehlchen.utils.progress import perform_userdb_migration_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log()
def data_migration_28(rotki: Rotkehlchen, progress_handler: MigrationProgressHandler) -> None:
    """Introduced at v1.44.1

    Legacy L1 fees of zero were stored both for resolved zero fees and for fees that could
    not be resolved, so their gas events may be missing the L1 portion. Mark them unresolved
    and reset the decoded events of those transactions so that redecoding repairs the fee.
    L1 originated transactions are skipped since their L1 fee is always zero. Transactions
    with customized or matched events stay decoded, as in reset_events_for_redecode(), since
    redecoding them on top of the preserved events would not repair the fee and could add
    duplicates. Instead their fee is resolved and their gas event amount updated in place,
    unless the gas event itself is customized or matched, in which case it is left as is.

    Also removes the API keys, query ranges and non syncing setting entries of BitMEX,
    whose API integration was removed after the exchange shut down.

    Also removes the empty files of the cached asset icons. Colibri used to mark an icon
    as not found with an empty .svg, which could hide an icon found later and was also
    written when the icon could not be queried due to rate limiting. Colibri now uses a
    .notfound marker instead. The removed icons are queried again when next shown. The
    icons directory is shared by all users while this runs once per user, so the .notfound
    markers written since another user ran it are kept.
    """
    customized_txs: list[tuple[EVMTxHash, L2ChainIdsWithL1FeesType]] = []  # filled by 1st step

    @progress_step(description='Resetting transactions with legacy zero L1 fees')
    def _reset_legacy_zero_l1_fees(rotki: Rotkehlchen) -> None:
        tx_ids: list[int] = []
        redecode_tx_ids: list[int] = []
        tx_hashes: defaultdict[L2ChainIdsWithL1FeesType, list[EVMTxHash]] = defaultdict(list)
        with rotki.data.db.conn.read_ctx() as cursor:
            for tx_id, tx_hash, chain_id, is_customized in cursor.execute(
                'SELECT txs.identifier, txs.tx_hash, txs.chain_id, EXISTS('
                'SELECT 1 FROM chain_events_info AS info INNER JOIN history_events_mappings '
                'AS mappings ON mappings.parent_identifier=info.identifier WHERE '
                'info.tx_ref=txs.tx_hash AND mappings.name=? AND mappings.value IN (?, ?)'
                ') FROM optimism_transactions AS fees INNER JOIN evm_transactions AS txs '
                'ON txs.identifier=fees.tx_id '
                'LEFT JOIN evmtx_receipts AS receipts ON receipts.tx_id=fees.tx_id '
                f"WHERE fees.l1_fee='0' AND txs.chain_id IN ({','.join('?' * len(L2_CHAINIDS_WITH_L1_FEES))}) "  # noqa: E501
                'AND (receipts.type IS NULL OR receipts.type!=?)',
                (
                    HISTORY_MAPPING_KEY_STATE,
                    HistoryMappingState.CUSTOMIZED.serialize_for_db(),
                    HistoryMappingState.MATCHED.serialize_for_db(),
                    *(x.serialize_for_db() for x in L2_CHAINIDS_WITH_L1_FEES),
                    L1_ORIGINATED_TX_TYPE,
                ),
            ):
                tx_ids.append(tx_id)
                chain: L2ChainIdsWithL1FeesType = ChainID.deserialize_from_db(chain_id)  # type: ignore[assignment]  # chain ids are filtered in the query
                if is_customized:
                    customized_txs.append((deserialize_evm_tx_hash(tx_hash), chain))
                    continue

                redecode_tx_ids.append(tx_id)
                tx_hashes[chain].append(EVMTxHash(tx_hash))

        if len(tx_ids) == 0:
            return

        dbevents = DBHistoryEvents(rotki.data.db)
        with rotki.data.db.user_write() as write_cursor:
            write_cursor.executemany(
                'UPDATE optimism_transactions SET l1_fee=NULL WHERE tx_id=?',
                [(tx_id,) for tx_id in tx_ids],
            )
            for chain_id, chain_tx_hashes in tx_hashes.items():
                dbevents.delete_events_by_tx_ref(
                    write_cursor=write_cursor,
                    tx_refs=chain_tx_hashes,
                    location=Location.from_chain_id(chain_id),
                    customized_handling='preserve_transactions',
                )
            write_cursor.executemany(
                'DELETE FROM evm_tx_mappings WHERE tx_id=? AND value=?',
                [(tx_id, TX_DECODED) for tx_id in redecode_tx_ids],
            )

    @progress_step(description='Repairing gas fees of customized transactions')
    def _repair_customized_legacy_zero_l1_fees(rotki: Rotkehlchen) -> None:
        """The customized transactions the previous step left decoded have an unresolved fee.
        Resolve it and correct their gas event, since no redecode would repair it."""
        dbevents = DBHistoryEvents(rotki.data.db)
        gas_event_where = (  # {} is IN for customized/matched gas events or NOT IN for the rest
            'FROM history_events AS events INNER JOIN chain_events_info AS info '
            'ON info.identifier=events.identifier WHERE info.tx_ref=? AND events.location=? '
            'AND info.counterparty=? AND events.type IN (?, ?) AND events.subtype=? AND '
            'events.identifier {} (SELECT parent_identifier FROM history_events_mappings '
            'WHERE name=? AND value IN (?, ?))'
        )
        for tx_hash, chain_id in customized_txs:
            try:
                with rotki.data.db.conn.read_ctx() as cursor:
                    tx, _ = rotki.chains_aggregator.get_evm_manager(chain_id).transactions.ensure_tx_data_exists(  # noqa: E501
                        cursor=cursor,
                        tx_hash=tx_hash,
                        relevant_address=None,
                    )
            except (RemoteError, InputError) as e:
                log.warning(
                    'Could not resolve the L1 fee of %s transaction %s due to %s. '
                    'Its gas event may be missing the L1 fee',
                    chain_id.to_name(),
                    tx_hash,
                    e,
                )
                continue

            if not isinstance(tx, L2WithL1FeesTransaction) or tx.l1_fee is None:
                continue  # ensure_tx_data_exists already logged the failure

            bindings = (
                tx_hash,
                Location.from_chain_id(chain_id).serialize_for_db(),
                CPT_GAS,
                HistoryEventType.SPEND.serialize(),
                HistoryEventType.FAIL.serialize(),  # gas of failed transactions
                HistoryEventSubType.FEE.serialize(),
                HISTORY_MAPPING_KEY_STATE,
                HistoryMappingState.CUSTOMIZED.serialize_for_db(),
                HistoryMappingState.MATCHED.serialize_for_db(),
            )
            with rotki.data.db.user_write() as write_cursor:
                if dbevents.mark_events_stale_by_query(
                    write_cursor=write_cursor,
                    query=f'SELECT events.timestamp {gas_event_where.format("NOT IN")}',
                    bindings=bindings,
                ) != 0:
                    write_cursor.execute(  # notes hold the amount: 'Burn X ETH for gas'
                        'UPDATE history_events SET amount=?, notes=REPLACE(notes, amount, ?) '
                        f'WHERE identifier IN (SELECT events.identifier {gas_event_where.format("NOT IN")})',  # noqa: E501
                        ((amount := str(from_wei(FVal(tx.gas_used * tx.gas_price + tx.l1_fee)))), amount, *bindings),  # noqa: E501
                    )
                elif write_cursor.execute(
                    f'SELECT COUNT(*) {gas_event_where.format("IN")}', bindings,
                ).fetchone()[0] != 0:
                    log.warning(
                        'Not updating the customized gas event of %s transaction %s. '
                        'It may be missing an L1 fee of %s wei',
                        chain_id.to_name(),
                        tx_hash,
                        tx.l1_fee,
                    )

    @progress_step(description='Removing BitMEX API data')
    def _remove_bitmex_data(rotki: Rotkehlchen) -> None:
        """BitMEX shut down and its API integration was removed. Its API keys can no longer
        be used, or removed through the API, so delete them along with their query ranges
        and non syncing setting. The BitMEX history events are kept."""
        with rotki.data.db.user_write() as write_cursor:
            write_cursor.execute(  # cascades to user_credentials_mappings
                'DELETE FROM user_credentials WHERE location=?',
                (Location.BITMEX.serialize_for_db(),),
            )
            write_cursor.execute(
                'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',
                (f'{Location.BITMEX!s}\\_%', '\\'),
            )
            if (non_syncing_exchanges := write_cursor.execute(
                "SELECT value FROM settings WHERE name='non_syncing_exchanges'",
            ).fetchone()) is None:
                return

            try:
                exchanges = json.loads(non_syncing_exchanges[0])
            except json.JSONDecodeError as e:
                log.error('Failed to read setting non_syncing_exchanges due to %s', e)
                return

            write_cursor.execute(
                "UPDATE settings SET value=? WHERE name='non_syncing_exchanges'",
                (json.dumps([x for x in exchanges if x['location'] != Location.BITMEX.serialize()]),),  # noqa: E501
            )

    @progress_step(description='Removing empty asset icon files')
    def _remove_empty_icons(rotki: Rotkehlchen) -> None:
        for entry in rotki.icon_manager.icons_dir.iterdir():
            try:
                if (
                    entry.suffix != NOT_FOUND_ICON_MARKER_SUFFIX and
                    entry.is_file() and
                    entry.stat().st_size == 0
                ):
                    entry.unlink()
            except OSError as e:
                log.error('Failed to remove empty icon file %s due to %s', entry, e)

    perform_userdb_migration_steps(rotki, progress_handler)
