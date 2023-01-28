import logging
from typing import TYPE_CHECKING

from rotkehlchen.globaldb.upgrades.v3_v4 import _add_eth_abis_json, _add_eth_contracts_json
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def migrate_to_v5(connection: 'DBConnection') -> None:
    """Upgrades globalDB to v5 by updating the contract data + abi tables."""
    log.debug('Entered globaldb v4->v5 upgrade')

    with connection.write_ctx() as cursor:
        _add_eth_contracts_json(cursor)
        _add_eth_abis_json(cursor)

    log.debug('Finished globaldb v4->v5 upgrade')
