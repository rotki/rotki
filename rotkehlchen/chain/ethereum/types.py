from typing import TYPE_CHECKING, Any, Literal, Protocol

if TYPE_CHECKING:
    # This is a list of all ethereum abi that are guaranteed to be returned
    # by EthereumContracts as they are stored in the file/DB
    ETHEREUM_KNOWN_ABI = Literal[
        'ATOKEN',
        'ATOKEN_V2',
        'CONVEX_LP_TOKEN',
        'CTOKEN',
        'CURVE_METAPOOL_FACTORY',
        'CURVE_POOL',
        'CURVE_REGISTRY',
        'ERC20_TOKEN',
        'ERC721_TOKEN',
        'FARM_ASSET',
        'UNISWAP_V2_LP',
        'UNISWAP_V3_POOL',
        'UNIV1_LP',
        'YEARN_VAULT_V2',
        'ZERION_ADAPTER',
        'ILK_REGISTRY',  # added in 1.27.1 data migration
        'CVX_REWARD_POOL',  # added in 1.28.0 packaged globaldb
        'CVX_LOCKER_V2',
        'COMPOUND_V3_TOKEN',
        'COMPOUND_V3_REWARDS',
        'GEARBOX_FARMING_POOL',
        'GEARBOX_STAKING',
        'HOP_POOL',
        'EXTRAFI_LOCK',
        'EXTRAFI_LENDING',
        'EXTRAFI_FARM',
    ]


class LogIterationCallback(Protocol):
    """Callback executed when querying onchain log events after finishing a range
    of blocks
    """
    def __call__(self, last_block_queried: int, filters: dict[str, Any]) -> None:
        ...
