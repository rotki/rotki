from typing import Final

from rotkehlchen.history.events.structures.base import HistoryBaseEntryType

STAKING_ENTRY_TYPES: Final = {  # types that need the extra staking columns
    HistoryBaseEntryType.ETH_DEPOSIT_EVENT,
    HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT,
    HistoryBaseEntryType.ETH_BLOCK_EVENT,
}
CHAIN_ENTRY_TYPES: Final = {  # types that need the chain event columns
    HistoryBaseEntryType.EVM_EVENT,
    HistoryBaseEntryType.EVM_SWAP_EVENT,
    HistoryBaseEntryType.SOLANA_EVENT,
    HistoryBaseEntryType.SOLANA_SWAP_EVENT,
    HistoryBaseEntryType.ETH_DEPOSIT_EVENT,
}
