from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    # This is a list of all optimism abis that are guaranteed to be returned
    # by EthereumContracts as they are stored in the file/DB
    OPTIMISM_KNOWN_ABI = Literal['VELO_V2_LP', 'HOP_STAKING', 'GEARBOX_LP']
