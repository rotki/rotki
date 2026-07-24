from enum import IntEnum
from typing import Final

from rotkehlchen.types import SolanaAddress

CPT_SOLANA_STAKE: Final = 'solana-stake'
STAKE_PROGRAM: Final = SolanaAddress('Stake11111111111111111111111111111111111111')


class StakeInstructionTag(IntEnum):
    """Stake program instruction enum tags, serialized as 4-byte little-endian values.
    https://github.com/solana-program/stake/blob/main/interface/src/instruction.rs
    """
    INITIALIZE = 0
    AUTHORIZE = 1
    DELEGATE_STAKE = 2
    SPLIT = 3
    WITHDRAW = 4
    DEACTIVATE = 5
    SET_LOCKUP = 6
    MERGE = 7
    AUTHORIZE_WITH_SEED = 8
    INITIALIZE_CHECKED = 9
    AUTHORIZE_CHECKED = 10
    AUTHORIZE_CHECKED_WITH_SEED = 11
    SET_LOCKUP_CHECKED = 12
    GET_MINIMUM_DELEGATION = 13
    DEACTIVATE_DELINQUENT = 14
    REDELEGATE = 15
    MOVE_STAKE = 16
    MOVE_LAMPORTS = 17


# System program instruction discriminators (4-byte little-endian enum tags) used to
# fund new stake accounts.
# https://github.com/solana-program/system/blob/main/interface/src/instruction.rs
SYSTEM_CREATE_ACCOUNT_DISCRIMINATOR: Final = b'\x00\x00\x00\x00'
SYSTEM_CREATE_ACCOUNT_WITH_SEED_DISCRIMINATOR: Final = b'\x03\x00\x00\x00'
