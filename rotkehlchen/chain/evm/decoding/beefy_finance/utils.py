import logging

from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import globaldb_set_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import CacheType, ChainID
from rotkehlchen.utils.network import request_get

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def query_beefy_vaults(chain: ChainID) -> None:
    """Fetches Beefy Finance vault addresses for the given chain and caches them locally.

    It pulls all vaults from the Beefy API, filters for the specified chain,
    and stores the vault contract addresses in the global database for later use.
    """
    vaults = []
    try:
        result = request_get(url=f'https://api.beefy.finance/vaults/all/{chain.value}')
        for entry in result:
            try:
                vaults.append(deserialize_evm_address(entry['earnContractAddress']))
            except (DeserializationError, KeyError) as e:
                msg = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
                log.warning(f'Skipping beefy vault entry {entry} for {chain} due to {msg}')
                continue

    except (RemoteError, UnableToDecryptRemoteData) as e:
        log.error(f'Failed to retrieve Beefy vaults for {chain} due to {e!s}')
        return

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.BEEFY_VAULTS, str(chain.serialize())),
            values=vaults,
        )
