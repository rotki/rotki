from typing import TYPE_CHECKING, Literal

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
    ]
