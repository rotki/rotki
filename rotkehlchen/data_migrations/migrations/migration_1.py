from typing import TYPE_CHECKING

from rotkehlchen.typing import Location

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen


def data_migration_1(rotki: 'Rotkehlchen') -> None:
    """
    Purge data for exchanges where there is more than one instance. Also purge information
    from kraken as requested for https://github.com/rotki/rotki/pull/3755
    """
    db = rotki.data.db
    cursor = db.conn.cursor()
    for exchange_location, exchanges in rotki.exchange_manager.connected_exchanges.items():
        if len(exchanges) > 1 or exchange_location == Location.KRAKEN:
            db.purge_exchange_data(exchange_location)
            db.delete_used_query_range_for_exchange(exchange_location)
        elif len(exchanges) == 1:
            cursor.executemany(
                'UPDATE used_query_ranges SET name=? WHERE name=?',
                [
                    (
                        f'{exchange_location}_trades_{exchanges[0].name}',
                        f'{exchange_location}_trades',
                    ),
                    (
                        f'{exchange_location}_margins_{exchanges[0].name}',
                        f'{exchange_location}_margins',
                    ),
                    (
                        f'{exchange_location}_asset_movements_{exchanges[0].name}',
                        f'{exchange_location}_asset_movements',
                    ),
                    (
                        f'{exchange_location}_ledger_actions_{exchanges[0].name}',
                        f'{exchange_location}_ledger_actions',
                    ),
                ],
            )
        db.conn.commit()
