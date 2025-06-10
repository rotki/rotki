"""Repository for managing module data in the database."""
import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.types import PurgeableModuleName

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor

log = logging.getLogger(__name__)


class ModuleDataRepository:
    """Repository for handling all module data operations."""

    def get_module_data(
            self,
            cursor: 'DBCursor',
            module_name: PurgeableModuleName,
    ) -> dict[str, Any]:
        """Get module data from the database."""
        cursor.execute(
            'SELECT data FROM module_data WHERE module_name=?',
            (module_name,),
        )
        result = cursor.fetchone()
        if result is None:
            return {}

        # Module data is stored as JSON
        import json
        return json.loads(result[0])

    def set_module_data(
            self,
            write_cursor: 'DBCursor',
            module_name: PurgeableModuleName,
            data: dict[str, Any],
    ) -> None:
        """Set or update module data in the database."""
        import json
        serialized_data = json.dumps(data)

        write_cursor.execute(
            'INSERT OR REPLACE INTO module_data(module_name, data) VALUES(?, ?)',
            (module_name, serialized_data),
        )

    def delete_module_data(
            self,
            write_cursor: 'DBCursor',
            module_name: PurgeableModuleName,
    ) -> None:
        """Delete module data from the database."""
        write_cursor.execute(
            'DELETE FROM module_data WHERE module_name=?',
            (module_name,),
        )

    def delete_eth2_daily_stats(self, write_cursor: 'DBCursor') -> None:
        """Delete all historical ETH2 eth2_daily_staking_details data"""
        write_cursor.execute('DELETE FROM eth2_daily_staking_details;')

    def delete_cowswap_trade_data(self, write_cursor: 'DBCursor') -> None:
        """Delete all cowswap trade/orders data from the DB"""
        write_cursor.execute('DELETE FROM cowswap_orders;')

    def delete_gnosispay_data(self, write_cursor: 'DBCursor') -> None:
        """Delete all saved gnosispay merchant data from the DB"""
        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name=?;',
            (DBCacheStatic.LAST_GNOSISPAY_QUERY_TS.value,),
        )
        write_cursor.execute('DELETE FROM gnosispay_data;')

    def delete_loopring_data(self, write_cursor: 'DBCursor') -> None:
        """Delete all loopring related data"""
        write_cursor.execute(
            'DELETE FROM multisettings WHERE name LIKE ? ESCAPE ?',
            ('loopring\\_%', '\\'),
        )

    def purge_module_data(
            self,
            write_cursor: 'DBCursor',
            module_name: PurgeableModuleName | None,
    ) -> None:
        """Purge all data for a specific module or all modules if None."""
        if module_name is None:
            self.delete_loopring_data(write_cursor)
            self.delete_eth2_daily_stats(write_cursor)
            self.delete_cowswap_trade_data(write_cursor)
            self.delete_gnosispay_data(write_cursor)
            log.debug('Purged all module data from the DB')
            return
        elif module_name == 'loopring':
            self.delete_loopring_data(write_cursor)
        elif module_name == 'eth2':
            self.delete_eth2_daily_stats(write_cursor)
        elif module_name == 'cowswap':
            self.delete_cowswap_trade_data(write_cursor)
        elif module_name == 'gnosis_pay':
            self.delete_gnosispay_data(write_cursor)
        else:
            log.debug(f'Requested to purge {module_name} data from the DB but nothing to do')
            return

        log.debug(f'Purged {module_name} data from the DB')
