import logging
from typing import Any, Final, TypedDict

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.history.events.structures.auto_notes import (
    APPROVE_TEMPLATE,
    DEPLOY_TEMPLATE,
    FAILED_GAS_TEMPLATE,
    GAS_TEMPLATE,
    NATIVE_ASSET_BY_LOCATION,
    NATIVE_TRANSFER_TEMPLATE,
    NO_VALUE_SELF_TX_TEMPLATE,
    OUTGOING_TRANSFER_TYPES,
    REVOKE_APPROVAL_TEMPLATE,
    SELF_TX_TEMPLATE,
    TOKEN_TRANSFER_IN_TEMPLATE,
    TOKEN_TRANSFER_OUT_TEMPLATE,
    TRANSFER_VERBS,
    is_plain_transfer,
)
from rotkehlchen.history.events.structures.base import (
    HistoryBaseEntryType,
)
from rotkehlchen.history.events.structures.onchain_event import OnchainEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
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

BRIDGE_EXTRA_DATA_KEY: Final = 'bridge'


class BridgeExtraData(TypedDict, total=False):
    """Structured cross-chain data written by bridge decoders under extra_data['bridge'].

    Chains are raw EVM chain ids (int) so that destinations rotki does not support can
    still be recorded, or a SupportedBlockchain serialized name (str) for non-EVM chains.
    to_asset is the raw target-chain token address. A zero address is preserved as a
    protocol-specific native-asset or default-routing sentinel.
    transfer_id is the protocol-native identifier of the transfer (deposit id, message
    nonce, transfer hash etc.) normalized to a string: decimal for numeric ids, 0x-hex
    for hash ids. It is unique for a protocol route and, when present on both sides of
    a bridge, allows exact matching even if an aggregator labels the source differently.
    """
    from_chain: int | str
    to_chain: int | str
    to_asset: str
    from_address: str
    to_address: str
    transfer_id: str


class EvmEvent(OnchainEvent[EVMTxHash, ChecksumEvmAddress]):  # hash in superclass

    @staticmethod
    def _calculate_group_identifier(tx_ref: EVMTxHash, location: Location) -> str:
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

    def auto_notes(self) -> str | None:
        """Notes of the events every EVM decoder produces before protocol specific decoding:
        gas, approvals, deploys, transactions to self and plain transfers. A protocol decoder
        that rewrites or extends one of those notes leaves them different from these, so they
        stay stored. ERC721 transfers name the token and stay stored too.
        """
        if self.counterparty == CPT_GAS:
            if self.event_subtype == HistoryEventSubType.FEE:
                if self.event_type == HistoryEventType.SPEND:
                    return GAS_TEMPLATE.format(amount=self.amount, symbol=self.asset.symbol_or_name())  # noqa: E501
                if self.event_type == HistoryEventType.FAIL:
                    return FAILED_GAS_TEMPLATE.format(amount=self.amount, symbol=self.asset.symbol_or_name())  # noqa: E501

        elif (
            self.event_type == HistoryEventType.INFORMATIONAL and
            self.event_subtype == HistoryEventSubType.APPROVE and
            self.counterparty is None
        ):
            template = REVOKE_APPROVAL_TEMPLATE if self.amount == ZERO else APPROVE_TEMPLATE
            return template.format(
                amount=self.amount,
                symbol=self.asset.symbol_or_name(),
                owner=self.location_label,
                spender=self.address,
            )

        elif self.event_type == HistoryEventType.DEPLOY:
            if self.address is not None:
                return DEPLOY_TEMPLATE.format(address=self.address)

        elif (
            self.event_type == HistoryEventType.TRANSACTION_TO_SELF and
            self.event_subtype == HistoryEventSubType.NONE
        ):
            if self.amount == ZERO:
                return NO_VALUE_SELF_TX_TEMPLATE.format()
            return SELF_TX_TEMPLATE.format(amount=self.amount, symbol=self.asset.symbol_or_name())

        elif (
            is_plain_transfer(self.event_type, self.event_subtype, self.counterparty) and
            (counterparty_or_address := self.counterparty or self.address) is not None
        ):
            fields = {
                'verb': TRANSFER_VERBS[self.event_type],
                'amount': self.amount,
                'symbol': self.asset.symbol_or_name(),
                'counterparty_or_address': counterparty_or_address,
            }
            if self.asset.identifier == NATIVE_ASSET_BY_LOCATION.get(self.location):
                return NATIVE_TRANSFER_TEMPLATE.format(
                    preposition='to' if self.event_type in OUTGOING_TRANSFER_TYPES else 'from',
                    **fields,
                )
            if '/erc721:' not in self.asset.identifier:
                template = TOKEN_TRANSFER_OUT_TEMPLATE if self.event_type in OUTGOING_TRANSFER_TYPES else TOKEN_TRANSFER_IN_TEMPLATE  # noqa: E501
                return template.format(location_label=self.location_label, **fields)

        return super().auto_notes()

    def has_details(self) -> bool:
        if self.extra_data is None:
            return False
        return len(self.extra_data.keys() & ALL_DETAILS_KEYS) > 0

    def get_details(self) -> dict[str, Any] | None:
        if self.extra_data is None:
            return None

        details = {k: v for k, v in self.extra_data.items() if k in ALL_DETAILS_KEYS}
        return details if len(details) > 0 else None
