import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Optional, Union

from rotkehlchen.assets.asset import CryptoAsset, EvmToken
from rotkehlchen.assets.utils import get_evm_token, get_or_create_evm_token
from rotkehlchen.chain.decoding.tools import BaseDecoderTools as ChainBaseDecoderTools
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, token_normalized_value
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import OUTGOING_EVENT_TYPES
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.resolver import tokenid_to_collectible_id
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ChecksumEvmAddress,
    EvmTransaction,
    EVMTxHash,
    Location,
    Timestamp,
    TokenKind,
)
from rotkehlchen.utils.misc import bytes_to_address, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.assets.utils import TokenEncounterInfo
    from rotkehlchen.chain.evm.l2_with_l1_fees.node_inquirer import (
        DSProxyL2WithL1FeesInquirerWithCacheData,
    )
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer, EvmNodeInquirerWithProxies
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BaseDecoderTools(ChainBaseDecoderTools[EvmTxReceipt, ChecksumEvmAddress, EVMTxHash, EvmEvent, EvmProduct]):  # noqa: E501
    """A class that keeps a common state and offers some common decoding functionality
    TODO: rename `BaseDecoderTools` to `BaseEvmDecoderTools` in a follow-up pr.
    """

    def __init__(
            self,
            database: 'DBHandler',
            evm_inquirer: 'EvmNodeInquirer',
            is_non_conformant_erc721_fn: Callable[[ChecksumEvmAddress], bool],
            address_is_exchange_fn: Callable[[ChecksumEvmAddress], str | None],
            exceptions_mappings: dict[str, 'Asset'] | None = None,
    ) -> None:
        """
        `exceptions_mappings` is introduced to handle the monerium exceptions. It maps the v1
        tokens to the v2 tokens and it's later used during the decoding to change the asset in
        events from v1 tokens to v2 tokens."""
        super().__init__(
            database=database,
            blockchain=evm_inquirer.blockchain,
            address_is_exchange_fn=address_is_exchange_fn,
        )
        self.evm_inquirer = evm_inquirer
        self.is_non_conformant_erc721 = is_non_conformant_erc721_fn
        self.exceptions_mappings = exceptions_mappings or {}

    def reset_sequence_counter(self, tx_receipt: EvmTxReceipt) -> None:
        """Reset the sequence index counter before decoding a transaction.
        `sequence_offset` is set to one more than the highest tx log index, and is used in
        `get_next_sequence_index` to add new events whose sequence index will not collide with
        the sequence index of any events that have associated tx logs.
        """
        super().reset_sequence_counter(tx_receipt)
        self.sequence_offset = tx_receipt.logs[-1].log_index + 1 if len(tx_receipt.logs) else 0

    def get_sequence_index(self, tx_log: EvmTxReceiptLog) -> int:
        """Get the sequence index for an event associated with a specific tx log.
        Used for token transfers, approvals, and misc events created by the protocol decoders.
        Returns the current counter added to the log index, placing these events after those
        created using `get_next_sequence_index_pre_decoding`.
        """
        if __debug__:
            self.get_sequence_index_called = True

        return self.sequence_counter + tx_log.log_index

    def maybe_get_proxy_owner(self, address: ChecksumEvmAddress) -> ChecksumEvmAddress | None:  # pylint: disable=unused-argument
        """
        Checks whether given address is a proxy owned by any of the tracked accounts.
        If it is a proxy, it returns the owner of the proxy, otherwise `None`.
        """
        return None

    def get_address_or_proxy_owner(self, address: ChecksumEvmAddress) -> ChecksumEvmAddress | None:  # pylint: disable=unused-argument
        """If the address is a proxy return its owner, if not return address itself"""
        owner = self.maybe_get_proxy_owner(address)
        return owner or address

    def decode_erc20_721_transfer(
            self,
            token: EvmToken,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
    ) -> Optional['EvmEvent']:
        """
        Caller should know this is a transfer of either an ERC20 or an ERC721 token.
        Call this method to decode it.

        May raise:
        - DeserializationError
        - ConversionError
        """
        from_address = bytes_to_address(tx_log.topics[1])
        to_address = bytes_to_address(tx_log.topics[2])
        direction_result = self.decode_direction(
            from_address=from_address,
            to_address=to_address,
        )
        if direction_result is None:
            return None

        event_type, event_subtype, location_label, address, counterparty, verb = direction_result
        counterparty_or_address = counterparty or address
        amount_raw_or_token_id = int.from_bytes(tx_log.data)
        if token.token_kind == TokenKind.ERC20:
            amount = token_normalized_value(token_amount=amount_raw_or_token_id, token=token)
            if event_type in OUTGOING_EVENT_TYPES:
                notes = f'{verb} {amount} {token.symbol} from {location_label} to {counterparty_or_address}'  # noqa: E501
            else:
                notes = f'{verb} {amount} {token.symbol} from {counterparty_or_address} to {location_label}'  # noqa: E501
        else:  # erc721
            if (collectible_id := tokenid_to_collectible_id(identifier=token.identifier)) is None:
                log.debug(f'Failed to get token id from identifier when decoding token {token} as ERC721')  # noqa: E501
                return None

            amount = ONE
            name = 'ERC721 token' if token.name == '' else token.name
            if event_type in {HistoryEventType.SPEND, HistoryEventType.TRANSFER}:
                notes = f'{verb} {name} with id {collectible_id} from {location_label} to {counterparty_or_address}'  # noqa: E501
            else:
                notes = f'{verb} {name} with id {collectible_id} from {counterparty_or_address} to {location_label}'  # noqa: E501

        if amount == ZERO:
            return None  # Zero transfers are useless, so ignoring them

        return self.make_event_from_transaction(
            transaction=transaction,
            tx_log=tx_log,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=token,
            amount=amount,
            location_label=location_label,
            notes=notes,
            address=address,
            counterparty=counterparty,
        )

    def make_event(
            self,
            tx_hash: EVMTxHash,
            sequence_index: int,
            timestamp: Timestamp,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            asset: 'Asset',
            amount: FVal,
            location_label: str | None = None,
            notes: str | None = None,
            counterparty: str | None = None,
            product: EvmProduct | None = None,
            address: ChecksumEvmAddress | None = None,
            extra_data: dict[str, Any] | None = None,
    ) -> 'EvmEvent':
        """A convenience function to create an EvmEvent depending on the
        decoder's chain id"""
        return EvmEvent(
            tx_hash=tx_hash,
            sequence_index=sequence_index,
            timestamp=ts_sec_to_ms(timestamp),
            location=Location.from_chain_id(self.evm_inquirer.chain_id),
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            amount=amount,
            location_label=location_label,
            notes=notes,
            counterparty=counterparty,
            product=product,
            address=address,
            extra_data=extra_data,
        )

    def make_event_from_transaction(
            self,
            transaction: EvmTransaction,
            tx_log: EvmTxReceiptLog,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            asset: 'Asset',
            amount: FVal,
            location_label: str | None = None,
            notes: str | None = None,
            counterparty: str | None = None,
            product: EvmProduct | None = None,
            address: ChecksumEvmAddress | None = None,
            extra_data: dict[str, Any] | None = None,
    ) -> 'EvmEvent':
        """Convenience function on top of make_event to use the transaction and a given log.
        Must only be used once for a specific tx_log to prevent duplicate sequence indexes.
        """
        return self.make_event(
            tx_hash=transaction.tx_hash,
            sequence_index=self.get_sequence_index(tx_log),
            timestamp=transaction.timestamp,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            amount=amount,
            location_label=location_label,
            notes=notes,
            counterparty=counterparty,
            product=product,
            address=address,
            extra_data=extra_data,
        )

    def make_event_next_index(
            self,
            tx_hash: EVMTxHash,
            timestamp: Timestamp,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            asset: 'Asset',
            amount: FVal,
            location_label: str | None = None,
            notes: str | None = None,
            counterparty: str | None = None,
            product: EvmProduct | None = None,
            address: ChecksumEvmAddress | None = None,
            extra_data: dict[str, Any] | None = None,
    ) -> 'EvmEvent':
        """Convenience function on top of make_event to use next sequence index."""
        return self.make_event(
            tx_hash=tx_hash,
            sequence_index=self.get_next_sequence_index(),
            timestamp=timestamp,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            amount=amount,
            location_label=location_label,
            notes=notes,
            counterparty=counterparty,
            product=product,
            address=address,
            extra_data=extra_data,
        )

    def get_evm_token(self, address: ChecksumEvmAddress) -> EvmToken | None:
        """Query a token from the DB or cache. If it does not exist there return None"""
        return get_evm_token(evm_address=address, chain_id=self.evm_inquirer.chain_id)

    def get_or_create_evm_token(
            self,
            address: ChecksumEvmAddress,
            encounter: 'TokenEncounterInfo | None' = None,
    ) -> EvmToken:
        """A version of get_create_evm_token to be called from the decoders"""
        return get_or_create_evm_token(
            userdb=self.database,
            evm_address=address,
            chain_id=self.evm_inquirer.chain_id,
            evm_inquirer=self.evm_inquirer,
            encounter=encounter,
        )

    def get_or_create_evm_asset(self, address: ChecksumEvmAddress) -> CryptoAsset:
        """A version of get_create_evm_token to be called from the decoders

        Also checks for special cases like the special ETH (or MATIC etc)
        address used in some protocols
        """
        if address == ETH_SPECIAL_ADDRESS:
            return self.evm_inquirer.native_token
        return self.get_or_create_evm_token(address)

    def resolve_tokens_data(
            self,
            token_addresses: list['ChecksumEvmAddress'],
            token_amounts: list[int],
    ) -> dict[str, FVal]:
        """Returns the resolved evm tokens or native currency and their amounts"""
        resolved_result: dict[str, FVal] = {}
        for token_address, token_amount in zip(token_addresses, token_amounts, strict=True):
            if token_address == ZERO_ADDRESS:
                asset = self.evm_inquirer.native_token
            else:
                asset = get_or_create_evm_token(
                    userdb=self.database,
                    evm_inquirer=self.evm_inquirer,
                    evm_address=token_address,
                    chain_id=self.evm_inquirer.chain_id,
                    token_kind=TokenKind.ERC20,
                )

            resolved_result[asset.identifier] = asset_normalized_value(amount=token_amount, asset=asset)  # noqa: E501

        return resolved_result

    def get_token_or_native(
            self,
            address: ChecksumEvmAddress,
            encounter: 'TokenEncounterInfo | None' = None,
    ) -> CryptoAsset | EvmToken:
        """Return the native token if the address is special or zero; otherwise return the EVM token."""  # noqa: E501
        if address in (ZERO_ADDRESS, ETH_SPECIAL_ADDRESS):
            return self.evm_inquirer.native_token

        return self.get_or_create_evm_token(
            address=address,
            encounter=encounter,
        )


class BaseDecoderToolsWithProxy(BaseDecoderTools):
    """Like BaseDecoderTools but with Proxy evm inquirers"""

    def __init__(
            self,
            database: 'DBHandler',
            evm_inquirer: Union['EvmNodeInquirerWithProxies', 'DSProxyL2WithL1FeesInquirerWithCacheData'],  # noqa: E501
            is_non_conformant_erc721_fn: Callable[[ChecksumEvmAddress], bool],
            address_is_exchange_fn: Callable[[ChecksumEvmAddress], str | None],
            exceptions_mappings: dict[str, 'Asset'] | None = None,
    ) -> None:
        super().__init__(
            database=database,
            evm_inquirer=evm_inquirer,
            is_non_conformant_erc721_fn=is_non_conformant_erc721_fn,
            address_is_exchange_fn=address_is_exchange_fn,
            exceptions_mappings=exceptions_mappings,
        )
        self.evm_inquirer: EvmNodeInquirerWithProxies  # to specify the type

    def maybe_get_proxy_owner(self, address: ChecksumEvmAddress) -> ChecksumEvmAddress | None:
        """
        Checks whether given address is a proxy owned by any of the tracked accounts.
        If it is a proxy, it returns the owner of the proxy, otherwise `None`.
        """
        return self.evm_inquirer.proxies_inquirer.maybe_get_proxy_owner(address)
