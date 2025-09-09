import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.quickswap.utils import get_quickswap_algebra_position_price
from rotkehlchen.chain.evm.decoding.quickswap.v3.constants import (
    QUICKSWAP_V3_NFT_MANAGER_ABI,
    QUICKSWAP_V3_POOL_ABI,
    QUICKSWAP_V3_POOL_INIT_CODE_HASH,
)
from rotkehlchen.chain.polygon_pos.modules.quickswap.v3.constants import (
    QUICKSWAP_V3_NFT_MANAGER,
    QUICKSWAP_V3_POOL_DEPLOYER,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.inquirer import Inquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def get_quickswap_v3_position_price(inquirer: 'Inquirer', token: 'EvmToken') -> Price:
    """Get the price of a Quickswap V3 LP position."""
    return get_quickswap_algebra_position_price(
        inquirer=inquirer,
        token=token,
        nft_manager=QUICKSWAP_V3_NFT_MANAGER,
        nft_manager_abi=QUICKSWAP_V3_NFT_MANAGER_ABI,
        pool_deployer=QUICKSWAP_V3_POOL_DEPLOYER,
        pool_abi=QUICKSWAP_V3_POOL_ABI,
        pool_init_code_hash=QUICKSWAP_V3_POOL_INIT_CODE_HASH,
    )
