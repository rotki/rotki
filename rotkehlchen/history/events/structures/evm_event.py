import logging
from typing import Any, Final

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.history.events.structures.base import (
    HistoryBaseEntryType,
)
from rotkehlchen.history.events.structures.onchain_event import OnchainEvent
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ChecksumEvmAddress,
    EVMTxHash,
    Location,
    deserialize_evm_tx_hash,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


SUB_SWAPS_DETAILS: Final = 'sub_swaps'
LIQUITY_STAKING_DETAILS: Final = 'liquity_staking'

ALL_DETAILS_KEYS = {
    SUB_SWAPS_DETAILS,
    LIQUITY_STAKING_DETAILS,
}


class EvmEvent(OnchainEvent[EVMTxHash, ChecksumEvmAddress]):  # hash in superclass

    @staticmethod
    def _calculate_event_identifier(tx_ref: EVMTxHash, location: Location) -> str:
        return f'{location.to_chain_id()}{tx_ref!s}'

    @staticmethod
    def _serialize_tx_ref_for_db(tx_ref: EVMTxHash) -> bytes:
        return bytes(tx_ref)

    @staticmethod
    def _deserialize_tx_ref(tx_ref_data: bytes) -> EVMTxHash:
        return deserialize_evm_tx_hash(tx_ref_data)

    @staticmethod
    def deserialize_address(address_data: Any) -> ChecksumEvmAddress:
        return string_to_evm_address(address_data)

    @property
    def entry_type(self) -> HistoryBaseEntryType:
        return HistoryBaseEntryType.EVM_EVENT

    def has_details(self) -> bool:
        if self.extra_data is None:
            return False
        return len(self.extra_data.keys() & ALL_DETAILS_KEYS) > 0

    def get_details(self) -> dict[str, Any] | None:
        if self.extra_data is None:
            return None

        details = {k: v for k, v in self.extra_data.items() if k in ALL_DETAILS_KEYS}
        return details if len(details) > 0 else None
