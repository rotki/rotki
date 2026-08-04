import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import globaldb_set_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType

from .constants import CRVUSD_MINTER, CRVUSD_MINTER_ABI

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def query_crvusd_controllers(evm_inquirer: EvmNodeInquirer) -> None:
    """Query crvUSD controller contract addresses from the minter contract and cache them"""
    try:
        number_of_markets = (minter := EvmContract(
            address=CRVUSD_MINTER,
            abi=CRVUSD_MINTER_ABI,
            deployed_block=0,
        )).call(node_inquirer=evm_inquirer, method_name='n_collaterals')

        controllers_result = evm_inquirer.multicall(calls=[
            (minter.address, minter.encode(method_name='controllers', arguments=[idx]))
            for idx in range(number_of_markets)
        ])
    except RemoteError as e:
        log.error(f'Failed to query crvUSD controllers from the minter contract due to {e!s}')
        return

    controllers = []
    for idx, result in enumerate(controllers_result):
        try:
            controller_address = minter.decode(
                result=result,
                method_name='controllers',
                arguments=[idx],
            )[0]
        except DeserializationError as e:
            log.error('Failed to read the crvUSD controller with index %s due to %s', idx, e)
            continue

        if controller_address == ZERO_ADDRESS:
            log.error(
                'Curve minter contract returned zero address for the controller '
                'with index %s. Skipping.',
                idx,
            )
            continue

        controllers.append(controller_address)

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(
                CacheType.CURVE_CRVUSD_CONTROLLERS,
                str(evm_inquirer.chain_id.serialize_for_db()),
            ),
            values=controllers,
        )
