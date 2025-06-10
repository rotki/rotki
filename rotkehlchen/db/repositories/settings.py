"""Repository for managing database settings."""
import json
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.db.settings import (
    DEFAULT_ASK_USER_UPON_SIZE_DISCREPANCY,
    DEFAULT_LAST_DATA_MIGRATION,
    DEFAULT_PREMIUM_SHOULD_SYNC,
    ROTKEHLCHEN_DB_VERSION,
    CachedSettings,
    DBSettings,
    ModifiableDBSettings,
    db_settings_from_dict,
)
from rotkehlchen.db.utils import str_to_bool
from rotkehlchen.types import ExchangeLocationID, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


class SettingsRepository:
    """Repository for handling all settings-related database operations."""

    def __init__(self) -> None:
        """Initialize the settings repository."""
        self.setting_to_default_type: dict[str, tuple[Any, Any]] = {
            'version': (int, ROTKEHLCHEN_DB_VERSION),
            'last_write_ts': (int, Timestamp(0)),
            'premium_should_sync': (str_to_bool, DEFAULT_PREMIUM_SHOULD_SYNC),
            'main_currency': (lambda x: Asset(x).resolve(), A_USD.resolve_to_fiat_asset()),
            'ongoing_upgrade_from_version': (int, None),
            'last_data_migration': (int, DEFAULT_LAST_DATA_MIGRATION),
            'non_syncing_exchanges': (lambda data: [ExchangeLocationID.deserialize(x) for x in json.loads(data)], []),  # noqa: E501
            'beacon_rpc_endpoint': (str, None),
            'ask_user_upon_size_discrepancy': (str_to_bool, DEFAULT_ASK_USER_UPON_SIZE_DISCREPANCY),  # noqa: E501
        }

    def get(
            self,
            cursor: 'DBCursor',
            name: Literal[
                'version',
                'last_write_ts',
                'premium_should_sync',
                'main_currency',
                'ongoing_upgrade_from_version',
                'last_data_migration',
                'non_syncing_exchanges',
                'beacon_rpc_endpoint',
                'ask_user_upon_size_discrepancy',
            ],
    ) -> int | Timestamp | bool | AssetWithOracles | list[ExchangeLocationID] | str | None:
        """Get a setting value from the database."""
        deserializer, default_value = self.setting_to_default_type[name]
        cursor.execute(
            'SELECT value FROM settings WHERE name=?;', (name,),
        )
        result = cursor.fetchone()
        if result is not None:
            return deserializer(result[0])  # type: ignore

        return default_value  # type: ignore

    def set(
            self,
            write_cursor: 'DBCursor',
            name: Literal[
                'version',
                'last_write_ts',
                'premium_should_sync',
                'ongoing_upgrade_from_version',
                'main_currency',
                'non_syncing_exchanges',
                'ask_user_upon_size_discrepancy',
            ],
            value: int | Timestamp | Asset | str | bool,
    ) -> None:
        """Set a setting value in the database."""
        write_cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            (name, str(value)),
        )
        CachedSettings().update_entry(name, value)

    def get_all_settings(
            self, cursor: 'DBCursor', msg_aggregator: Any, have_premium: bool = False,
    ) -> DBSettings:
        """Get all settings from the database."""
        cursor.execute('SELECT name, value FROM settings;')
        settings_dict = {}
        for q in cursor:
            settings_dict[q[0]] = q[1]

        # Also add the non-DB saved settings
        settings_dict['have_premium'] = have_premium
        return db_settings_from_dict(settings_dict, msg_aggregator)

    def set_all_settings(self, write_cursor: 'DBCursor', settings: ModifiableDBSettings) -> None:
        """Set multiple settings at once."""
        settings_dict = settings.serialize()
        write_cursor.executemany(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            list(settings_dict.items()),
        )
        CachedSettings().update_entries(settings)
