import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import content_hash

from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi_str
from rotkehlchen.chain.ethereum.modules.ens.constants import CPT_ENS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.ens.constants import (
    ADDR_CHANGED,
    CONTENT_HASH_CHANGED,
    NEW_OWNER,
    NEW_RESOLVER,
    TEXT_CHANGED_KEY_AND_VALUE,
    TEXT_CHANGED_KEY_AND_VALUE_ABI,
    TEXT_CHANGED_KEY_ONLY,
    TEXT_CHANGED_KEY_ONLY_ABI,
)
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, TokenKind
from rotkehlchen.utils.misc import bytes_to_address
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EnsCommonDecoder(EvmDecoderInterface, CustomizableDateMixin, ABC):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            reverse_resolver: 'ChecksumEvmAddress',
            counterparty: str,
            suffix: str,
            display_name: str,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        CustomizableDateMixin.__init__(self, base_tools.database)
        self.reverse_resolver = reverse_resolver
        self.counterparty = counterparty
        self.suffix = suffix
        self.display_name = display_name

    def _decode_name_transfer(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != ERC20_OR_ERC721_TRANSFER:
            return DEFAULT_EVM_DECODING_OUTPUT

        # The ENS contract doesn't implement the `symbol` and `name` methods so we must hardcode them here  # noqa: E501
        symbol, name = ('ENS', 'Ethereum Name Service') if self.counterparty == CPT_ENS else (None, None)  # noqa: E501
        to_address = bytes_to_address(context.tx_log.topics[2])
        token = get_or_create_evm_token(
            userdb=self.database,
            evm_address=context.tx_log.address,
            chain_id=self.node_inquirer.chain_id,
            token_kind=TokenKind.ERC721,
            symbol=symbol,
            name=name,
            collectible_id=str(collectible_id := int.from_bytes(context.tx_log.topics[3])),
            evm_inquirer=self.node_inquirer,
            encounter=TokenEncounterInfo(tx_hash=context.transaction.tx_hash),
        )
        transfer_event = self.base.decode_erc20_721_transfer(
            token=token,
            tx_log=context.tx_log,
            transaction=context.transaction,
        )
        if transfer_event is None:  # Can happen if neither from/to is tracked
            return DEFAULT_EVM_DECODING_OUTPUT

        label_hash = f'0x{collectible_id:064x}'  # Transform the int token id to a 32 bytes hex label hash  # noqa: E501
        found_name = self._maybe_get_labelhash_name(context=context, label_hash=label_hash)
        if found_name is None:
            name_to_show = ''
        else:
            name_to_show = f'{found_name}.{self.suffix} ' if not found_name.endswith(f'.{self.suffix}') else f'{found_name} '  # noqa: E501

        from_text = to_text = ''
        if transfer_event.event_type == HistoryEventType.SPEND:
            verb = 'Send'
            if transfer_event.location_label != context.transaction.from_address:
                from_text = f'from {transfer_event.location_label} '
            to_text = f'to {to_address}'
        elif transfer_event.event_type == HistoryEventType.RECEIVE:
            verb = 'Receive'
            from_text = f'from {transfer_event.address} '
            to_text = f'to {transfer_event.location_label}'
        else:  # can only be ...
            verb = 'Transfer'
            if transfer_event.location_label != context.transaction.from_address:
                from_text = f'from {transfer_event.location_label} '
            to_text = f'to {to_address}'

        transfer_event.counterparty = self.counterparty
        transfer_event.notes = f'{verb} {self.display_name} name {name_to_show}{from_text}{to_text}'  # noqa: E501
        return EvmDecodingOutput(events=[transfer_event], refresh_balances=False)

    def _decode_new_resolver(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode event where address is set for an ENS name."""
        ens_name = self._get_name_to_show(node=context.tx_log.topics[1], context=context)
        suffix = ens_name if ens_name is not None else 'an ENS name'

        # Not able to give more info to the user such as address that was set since
        # we don't have historical info and event doesn't provide it
        notes = f'Set {self.display_name} address for {suffix}'
        context.decoded_events.append(self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=context.transaction.from_address,
            notes=notes,
            counterparty=self.counterparty,
            address=context.transaction.to_address,
        ))
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_new_owner(self, context: DecoderContext) -> EvmDecodingOutput:
        if self.base.is_tracked(new_owner := bytes_to_address(context.tx_log.data[:32])):
            associated_address = new_owner
        elif self.base.is_tracked(context.transaction.from_address):
            associated_address = context.transaction.from_address
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        node_name = self._get_name_to_show(node=(node := context.tx_log.topics[1]), context=context)  # noqa: E501
        label_hash = '0x' + context.tx_log.topics[2].hex()
        label_name = self._maybe_get_labelhash_name(context=context, label_hash=label_hash, node=node)  # noqa: E501

        node_str = f'{node_name} node' if node_name else f'node with nodehash {context.tx_log.topics[1].hex()}'  # noqa: E501
        if label_name:
            subnode_str = f'{label_name}.eth' if (not label_name.endswith('.eth') and node_name == 'eth') else label_name  # noqa: E501
        else:
            subnode_str = f'with label hash {label_hash}'

        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=associated_address,
            notes=f'Transfer {node_str} ownership of subnode {subnode_str} to {new_owner}',
            address=context.tx_log.address,
            counterparty=self.counterparty,
        )
        return EvmDecodingOutput(events=[event])

    def _decode_ens_registry_with_fallback_event(self, context: DecoderContext) -> EvmDecodingOutput:  # noqa: E501
        """Decode event where address is set for an ENS name."""
        if context.tx_log.topics[0] == NEW_RESOLVER:
            return self._decode_new_resolver(context)
        elif context.tx_log.topics[0] == NEW_OWNER:
            return self._decode_new_owner(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_ens_public_resolver_content_hash(self, context: DecoderContext) -> EvmDecodingOutput:  # noqa: E501
        """Decode an event that modifies a content hash for the public ENS resolver"""
        node = context.tx_log.topics[1]  # node is a hash of the name used by ens internals
        contract = self.node_inquirer.contracts.contract_by_address(address=context.tx_log.address)
        if contract is None:
            self.msg_aggregator.add_error(
                f'Failed to find {self.display_name} public resolver contract with address '
                f'{context.tx_log.address} for {context.transaction}. '
                f'This should never happen. Please, '
                f"open an issue in rotki's github repository.",
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        result = contract.decode_event(context.tx_log, 'ContenthashChanged', argument_names=None)
        new_hash = result[1][0].hex()
        name_to_show = self._get_name_to_show(node=node, context=context)

        try:
            codec = content_hash.get_codec(new_hash)
            value_hash = content_hash.decode(new_hash)
            value = f'{codec}://{value_hash}'
        except (TypeError, KeyError, ValueError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Inability to find key {msg}'
            log.error(f'Failed to decode content hash {new_hash} in {context.transaction} due to {msg}')  # noqa: E501
            value = f'unknown type hash {new_hash}'

        notes = f'Change {self.display_name} content hash to {value}'
        if name_to_show is not None:
            notes += f' for {name_to_show}'
        context.decoded_events.append(self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=context.transaction.from_address,
            notes=notes,
            counterparty=self.counterparty,
            address=context.transaction.to_address,
        ))
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_addr_changed(self, context: DecoderContext) -> EvmDecodingOutput:

        if self.base.is_tracked(new_address := bytes_to_address(context.tx_log.data[:32])):
            associated_address = new_address
        elif self.base.is_tracked(context.transaction.from_address):
            associated_address = context.transaction.from_address
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        node = context.tx_log.topics[1]  # node is a hash of the name used by ens internals
        name = self._get_name_to_show(node=node, context=context)
        name_str = name or f'name with nodehash {node.hex()}'
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=associated_address,
            notes=f'Address for {name_str} changed to {new_address}',
            address=context.tx_log.address,
            counterparty=self.counterparty,
        )
        return EvmDecodingOutput(events=[event])

    def _decode_ens_public_resolver_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode events that modify the ENS resolver.

        For example, where a text property (discord, telegram, etc.) is set for an ENS name.
        Also forward to different functions that do non-text modifications
        """
        if context.tx_log.topics[0] == CONTENT_HASH_CHANGED:
            return self._decode_ens_public_resolver_content_hash(context)

        if context.tx_log.topics[0] == ADDR_CHANGED:
            return self._decode_addr_changed(context)

        # else by now it should only be text attribute changes
        if context.tx_log.topics[0] not in (TEXT_CHANGED_KEY_ONLY, TEXT_CHANGED_KEY_AND_VALUE):
            return DEFAULT_EVM_DECODING_OUTPUT

        try:
            _, decoded_data = decode_event_data_abi_str(
                context.tx_log,
                TEXT_CHANGED_KEY_ONLY_ABI if context.tx_log.topics[0] == TEXT_CHANGED_KEY_ONLY else TEXT_CHANGED_KEY_AND_VALUE_ABI,  # noqa: E501
            )
        except DeserializationError as e:
            log.error(f'Failed to decode {self.display_name} set-text event in {context.transaction} due to {e!s}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        changed_key = decoded_data[0]
        new_value = decoded_data[1] if context.tx_log.topics[0] == TEXT_CHANGED_KEY_AND_VALUE else None  # noqa: E501
        node = context.tx_log.topics[1]  # node is a hash of the name used by ens internals

        name_to_show = self._get_name_to_show(node=node, context=context)
        notes = f'Set {self.display_name} {changed_key} {f"to {new_value} " if new_value else ""}attribute'  # noqa: E501
        if name_to_show is not None:
            notes += f' for {name_to_show}'
        context.decoded_events.append(self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=context.transaction.from_address,
            notes=notes,
            counterparty=self.counterparty,
            address=context.transaction.to_address,
        ))
        return DEFAULT_EVM_DECODING_OUTPUT

    @abstractmethod
    def _maybe_get_labelhash_name(
            self,
            context: DecoderContext,
            label_hash: str,
            node: bytes | None = None,
    ) -> str | None:
        """
        Subclasses implement this to retrieve the name for a labelhash
        """

    @abstractmethod
    def _get_name_to_show(self, node: bytes, context: DecoderContext) -> str | None:
        """
        Subclasses implement this to retrieve the full name for a node
        """
