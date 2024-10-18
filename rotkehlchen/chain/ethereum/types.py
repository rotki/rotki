from typing import TYPE_CHECKING, Any, Literal, Protocol, TypeVar

if TYPE_CHECKING:
    from rotkehlchen.chain.gnosis.transactions import GnosisWithdrawalsQueryParameters

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
        'YEARN_VAULT_V3',
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


T_contra = TypeVar('T_contra', bound='GnosisWithdrawalsQueryParameters | None', contravariant=True)


class LogIterationCallback(Protocol[T_contra]):
    """Callback executed when querying onchain log events after finishing a range
    of blocks
    """
    def __call__(
            self,
            last_block_queried: int,
            filters: dict[str, Any],
            new_events: list[dict[str, Any]],
            cb_arguments: T_contra,
    ) -> None:
        """
        - last_block_queried: number of the last block queried
        - filters: filters used when querying log events
        - new_events: New events found in the current iteration of the log search
        - cb_arguments: An instance of a dataclass containing additional context and mutable state
        for the callback. This object facilitates bidirectional communication, allowing the
        callback to both receive and update query-related information. For example, in
        GnosisWithdrawalsQueryParameters, it can be used to track and update the last queried block
        across multiple callback invocations.
        """
