import json
import logging
import urllib.parse
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ALLASSETIMAGESDIR_NAME, ASSETIMAGESDIR_NAME, IMAGESDIR_NAME
from rotkehlchen.constants.assets import A_COW, A_GNOSIS_COW, A_LQTY
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
    create_asset_movement_with_fee,
)
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import Location
from rotkehlchen.utils.misc import ts_sec_to_ms
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='UserDB v45->v46 upgrade')
def upgrade_v45_to_v46(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v45 to v46. This was in v1.37 release.

    - Remove balancer module from settings
    - Refresh icons
    """
    @progress_step(description='Removing balancer module from user settings.')
    def _remove_balancer_module(write_cursor: 'DBCursor') -> None:
        if (active_modules_result := write_cursor.execute("SELECT value FROM settings where name='active_modules'").fetchone()) is None:  # noqa: E501
            return None

        try:
            active_modules = json.loads(active_modules_result[0])
        except json.JSONDecodeError:
            log.error(f'During v45->v46 DB upgrade a non-json active_modules entry was found: {active_modules_result[0]}.')  # noqa: E501
            return None

        write_cursor.execute(
            "UPDATE OR IGNORE settings SET value=? WHERE name='active_modules'",
            (json.dumps([module for module in active_modules if module != 'balancer']),),
        )

    @progress_step(description='Refreshing icons.')
    def _refresh_icons(write_cursor: 'DBCursor') -> None:
        identifiers_to_delete = [
            A_COW.identifier,
            A_LQTY.identifier,
            A_GNOSIS_COW.identifier,
            'eip155:42161/erc20:0xcb8b5CD20BdCaea9a010aC1F8d835824F5C87A04',  # Cowswap on Arbitrum
        ]
        icons_dir = db.user_data_dir.parent.parent / IMAGESDIR_NAME / ASSETIMAGESDIR_NAME / ALLASSETIMAGESDIR_NAME  # noqa: E501
        for identifier in identifiers_to_delete:
            icon_path = icons_dir / f'{urllib.parse.quote_plus(identifier)}_small.png'
            icon_path.unlink(missing_ok=True)

    @progress_step(description='Moving EVM event extra data to the history_events table.')
    def _move_extra_data(write_cursor: 'DBCursor') -> None:
        write_cursor.execute('ALTER TABLE history_events ADD COLUMN extra_data TEXT;')
        write_cursor.execute(
            'UPDATE history_events SET extra_data = '
            '(SELECT extra_data FROM evm_events_info '
            'WHERE evm_events_info.identifier = history_events.identifier);',
        )
        write_cursor.execute('ALTER TABLE evm_events_info DROP COLUMN extra_data;')

    @progress_step(description='Converting asset movements to history events')
    def move_asset_movements(write_cursor: 'DBCursor') -> None:
        new_events: list[AssetMovement] = []
        write_cursor.execute(
            'SELECT id, location, category, address, transaction_id, timestamp, asset, '
            'amount, fee_asset, fee, link FROM asset_movements',
        )

        for row in write_cursor:
            try:
                new_events.extend(create_asset_movement_with_fee(
                    timestamp=ts_sec_to_ms(row[5]),
                    location=Location.deserialize_from_db(row[1]),
                    event_type=HistoryEventType.DEPOSIT if row[2] == 'A' else HistoryEventType.WITHDRAWAL,  # noqa: E501
                    asset=Asset(row[6]),
                    amount=FVal(row[7]),
                    fee_asset=Asset(row[8]),
                    fee=FVal(row[9]),
                    extra_data=maybe_set_transaction_extra_data(
                        address=row[3],
                        transaction_id=row[4],
                        extra_data={'reference': row[10]} if row[10] is not None and row[10] not in ('', 'None') else None,  # in coinbase we were storing 'None' as string.  # noqa: E501
                    ),
                ))
            except (DeserializationError, UnknownAsset) as e:
                log.error(f'Failed to deserialize row {row} due to {e}. Skipping.')

        binding_tuples = ((
            event.entry_type.value,
            event.event_identifier,
            event.sequence_index,
            event.timestamp,
            event.location.serialize_for_db(),
            event.location_label,
            event.asset.identifier,
            str(event.balance.amount),
            str(event.balance.usd_value),
            event.notes,
            event.event_type.serialize(),
            event.event_subtype.serialize(),
            json.dumps(event.extra_data) if event.extra_data else None,
        ) for event in new_events)
        write_cursor.executemany(
            (
                'INSERT OR IGNORE INTO history_events(entry_type, event_identifier, '
                'sequence_index, timestamp, location, location_label, asset, amount, usd_value, '
                'notes, type, subtype, extra_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
            ),
            binding_tuples,
        )

        write_cursor.execute('DROP TABLE asset_movements')
        write_cursor.execute('DROP TABLE asset_movement_category')

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
