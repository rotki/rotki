import logging
from typing import TYPE_CHECKING, Any

from eth_abi import decode as decode_abi
from eth_utils import keccak

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.ens.constants import (
    ADDR_CHANGED,
    CONTENT_HASH_CHANGED,
    TEXT_CHANGED_KEY_ONLY,
)
from rotkehlchen.chain.evm.decoding.ens.decoder import EnsCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress, Timestamp, TokenKind
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    COMMITTED,
    CPT_GNS,
    GET_FULL_NAME_ABI,
    GNS_CPT_DETAILS,
    GWEI_NAMES_ADDRESS,
    NAME_REGISTERED,
    NAME_RENEWED,
    PRIMARY_NAME_SET,
    SET_TEXT_METHOD,
    SUBDOMAIN_REGISTERED,
    TEXT_KEY_HASHES,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GweiNamesDecoder(EnsCommonDecoder):
    """Decoder for the Gwei Name Service (https://github.com/lucadonnoh/gwei-names)

    An ownerless ENS fork where registration fees are burned in the contract.
    Registration happens with a commit/reveal scheme and all functionality
    (registrar, resolver, reverse resolution and the ERC721 name NFTs) lives in a
    single contract. The token id of a name equals the uint256 of its namehash, so
    names can always be recovered on-chain via getFullName(tokenId).
    """

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            reverse_resolver=GWEI_NAMES_ADDRESS,
            counterparty=CPT_GNS,
            suffix='gwei',
            display_name='GNS',
        )

    def _get_name_to_show(self, node: bytes, context: DecoderContext) -> str | None:
        """Get the full name for the given namehash/node from the DB cache or the contract.

        The namehash -> name mapping is deterministic so caching it is always safe.
        Returns the full name with the .gwei suffix or None if it can't be found.
        """
        with GlobalDBHandler().conn.read_ctx() as cursor:
            if (name := globaldb_get_unique_cache_value(
                    cursor=cursor,
                    key_parts=(CacheType.ENS_NAMEHASH, node.hex()),
            )) is not None:
                return name

        try:
            name = self.node_inquirer.call_contract(
                contract_address=GWEI_NAMES_ADDRESS,
                abi=GET_FULL_NAME_ABI,
                method_name='getFullName',
                arguments=[int.from_bytes(node)],
            )
        except RemoteError as e:
            log.error('Failed to query gwei name for node %s due to %s', node.hex(), e)
            return None

        if not name:
            return None

        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=(CacheType.ENS_NAMEHASH, node.hex()),
                value=name,
            )
        return name

    def _maybe_get_labelhash_name(
            self,
            context: DecoderContext,
            label_hash: str,
            node: bytes | None = None,
    ) -> str | None:
        """In gwei-names the token id used as label hash by the common name transfer
        decoding equals the namehash of the full name, so delegate to the node lookup.
        """
        return self._get_name_to_show(
            node=bytes.fromhex(label_hash.removeprefix('0x')),
            context=context,
        )

    def _get_name(self, token_id: int, context: DecoderContext) -> str | None:
        return self._get_name_to_show(node=token_id.to_bytes(32), context=context)

    def _get_new_contenthash(self, context: DecoderContext) -> str | None:
        """The GNS contract is not in the contracts DB, so decode the log data directly"""
        return decode_abi(['bytes'], context.tx_log.data)[0].hex()

    def _token_identifier(self, token_id: int) -> str:
        return evm_address_to_identifier(
            address=GWEI_NAMES_ADDRESS,
            chain_id=self.node_inquirer.chain_id,
            token_type=TokenKind.ERC721,
            collectible_id=str(token_id),
        )

    def _decode_committed(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode the commitment event of the commit/reveal registration scheme"""
        if not self.base.is_tracked(committer := bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_EVM_DECODING_OUTPUT

        context.decoded_events.append(self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=committer,
            notes='Commit to registering a GNS name',
            counterparty=CPT_GNS,
            address=context.tx_log.address,
        ))
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_name_registered(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode the registration (reveal) of a top level gwei name.

        Pairs the burned ETH registration fee with the received name NFT, netting out
        any refund of overpaid ETH. Subdomain registrations emit this event too but
        with a zero expiry and are handled by the SubdomainRegistered event instead.
        """
        label, expires = decode_abi(['string', 'uint256'], context.tx_log.data)
        if expires == 0:
            return DEFAULT_EVM_DECODING_OUTPUT  # subdomain. Handled in _decode_subdomain_registered  # noqa: E501

        fullname = f'{label}.gwei'
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_set_unique_cache_value(  # cache namehash -> name for resolver events
                write_cursor=write_cursor,
                key_parts=(CacheType.ENS_NAMEHASH, context.tx_log.topics[1].hex()),
                value=fullname,
            )

        token_identifier = self._token_identifier(int.from_bytes(context.tx_log.topics[1]))
        refund_amount, to_remove_indices = ZERO, []
        spend_event = receive_event = None
        for event_idx, event in enumerate(context.decoded_events):
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.asset == A_ETH and
                event.address == GWEI_NAMES_ADDRESS
            ):  # net out the refund of overpaid ETH from the registration spend event
                refund_amount += event.amount
                to_remove_indices.append(event_idx)
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.asset.identifier == token_identifier
            ):
                receive_event = event
            elif (
                event.event_type == HistoryEventType.SPEND and
                event.asset == A_ETH and
                event.address == GWEI_NAMES_ADDRESS
            ):
                spend_event = event

        if spend_event is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        spend_event.amount -= refund_amount
        spend_event.counterparty = CPT_GNS
        spend_event.notes = f'Register GNS name {fullname} for {spend_event.amount} ETH until {self.timestamp_to_date(expires)}'  # noqa: E501
        spend_event.extra_data = {'name': fullname, 'expires': expires}
        for index in reversed(to_remove_indices):
            del context.decoded_events[index]

        if receive_event is None:
            spend_event.event_subtype = HistoryEventSubType.NONE
            return DEFAULT_EVM_DECODING_OUTPUT

        spend_event.event_type = HistoryEventType.TRADE
        spend_event.event_subtype = HistoryEventSubType.SPEND
        receive_event.event_type = HistoryEventType.TRADE
        receive_event.event_subtype = HistoryEventSubType.RECEIVE
        maybe_reshuffle_events(
            ordered_events=[spend_event, receive_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(process_swaps=True)

    def _decode_subdomain_registered(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode the free registration of a subdomain by the parent name owner"""
        token_id = int.from_bytes(context.tx_log.topics[1])
        name = self._get_name(token_id=token_id, context=context) or f"{decode_abi(['string'], context.tx_log.data)[0]}.gwei"  # noqa: E501
        token_identifier = self._token_identifier(token_id)
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.asset.identifier == token_identifier
            ):
                event.counterparty = CPT_GNS
                event.notes = f'Register GNS subdomain {name}'
                return DEFAULT_EVM_DECODING_OUTPUT

        if self.base.is_tracked(context.transaction.from_address):
            # registerSubdomainFor can mint the subdomain to an untracked address
            context.decoded_events.append(self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ZERO,
                location_label=context.transaction.from_address,
                notes=f'Register GNS subdomain {name}',
                counterparty=CPT_GNS,
                address=context.tx_log.address,
            ))
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_name_renewed(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode the renewal of a top level gwei name, netting out any refund"""
        token_id = int.from_bytes(context.tx_log.topics[1])
        new_expires = Timestamp(int.from_bytes(context.tx_log.data[:32]))
        name = self._get_name(token_id=token_id, context=context) or f'name with nodehash 0x{token_id:064x}'  # noqa: E501
        refund_amount, to_remove_indices = ZERO, []
        spend_event = None
        for event_idx, event in enumerate(context.decoded_events):
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.asset == A_ETH and
                event.address == GWEI_NAMES_ADDRESS
            ):
                refund_amount += event.amount
                to_remove_indices.append(event_idx)
            elif (
                event.event_type == HistoryEventType.SPEND and
                event.asset == A_ETH and
                event.address == GWEI_NAMES_ADDRESS
            ):
                spend_event = event

        if spend_event is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        spend_event.amount -= refund_amount
        spend_event.event_type = HistoryEventType.RENEW
        spend_event.event_subtype = HistoryEventSubType.NONE
        spend_event.counterparty = CPT_GNS
        spend_event.notes = f'Renew GNS name {name} for {spend_event.amount} ETH until {self.timestamp_to_date(new_expires)}'  # noqa: E501
        spend_event.extra_data = {'name': name, 'expires': new_expires}
        for index in reversed(to_remove_indices):
            del context.decoded_events[index]

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_primary_name_set(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode setting/unsetting the primary name used for reverse resolution"""
        if self.base.is_tracked(address := bytes_to_address(context.tx_log.topics[1])):
            associated_address = address
        elif self.base.is_tracked(context.transaction.from_address):
            associated_address = context.transaction.from_address
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        if (token_id := int.from_bytes(context.tx_log.topics[2])) == 0:
            notes = 'Unset GNS primary name'
        else:
            name = self._get_name(token_id=token_id, context=context) or f'name with nodehash 0x{token_id:064x}'  # noqa: E501
            notes = f'Set {name} as GNS primary name'

        context.decoded_events.append(self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=associated_address,
            notes=notes,
            counterparty=CPT_GNS,
            address=context.tx_log.address,
        ))
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_text_changed(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode setting a text record (avatar, url, com.twitter, etc.) of a gwei name.

        Unlike the ENS resolvers, the key of the event is an indexed string so only its
        hash is logged. It is recovered from the hashes of the common ENSIP-5 keys and
        as a fallback from the transaction input data.
        """
        if not self.base.is_tracked(context.transaction.from_address):
            return DEFAULT_EVM_DECODING_OUTPUT

        if (
                (key := TEXT_KEY_HASHES.get(context.tx_log.topics[2])) is None and
                context.transaction.to_address == GWEI_NAMES_ADDRESS and
                context.transaction.input_data[:4] == SET_TEXT_METHOD
        ):
            _, input_key, _ = decode_abi(
                ['uint256', 'string', 'string'],
                context.transaction.input_data[4:],
            )
            if keccak(text=input_key) == context.tx_log.topics[2]:
                key = input_key

        token_id = int.from_bytes(context.tx_log.topics[1])
        name = self._get_name(token_id=token_id, context=context) or f'name with nodehash 0x{token_id:064x}'  # noqa: E501
        value = decode_abi(['string'], context.tx_log.data)[0]
        key_str = key if key is not None else 'text'
        notes = f'Set GNS {key_str} {f"to {value} " if value else ""}attribute for {name}'
        context.decoded_events.append(self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=context.transaction.from_address,
            notes=notes,
            counterparty=CPT_GNS,
            address=context.tx_log.address,
        ))
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_gns_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER:
            return self._decode_name_transfer(context)
        if context.tx_log.topics[0] == COMMITTED:
            return self._decode_committed(context)
        if context.tx_log.topics[0] == NAME_REGISTERED:
            return self._decode_name_registered(context)
        if context.tx_log.topics[0] == SUBDOMAIN_REGISTERED:
            return self._decode_subdomain_registered(context)
        if context.tx_log.topics[0] == NAME_RENEWED:
            return self._decode_name_renewed(context)
        if context.tx_log.topics[0] == PRIMARY_NAME_SET:
            return self._decode_primary_name_set(context)
        if context.tx_log.topics[0] == ADDR_CHANGED:
            return self._decode_addr_changed(context)
        if context.tx_log.topics[0] == TEXT_CHANGED_KEY_ONLY:
            return self._decode_text_changed(context)
        if context.tx_log.topics[0] == CONTENT_HASH_CHANGED:
            return self._decode_ens_public_resolver_content_hash(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {GWEI_NAMES_ADDRESS: (self._decode_gns_events,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (GNS_CPT_DETAILS,)
