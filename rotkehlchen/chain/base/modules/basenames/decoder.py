import logging
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final

import requests

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi_str
from rotkehlchen.chain.evm.decoding.ens.decoder import EnsCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import tokenid_belongs_to_collection
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    BASENAMES_BASE_REGISTRAR,
    BASENAMES_CPT_DETAILS,
    BASENAMES_L2_RESOLVER,
    BASENAMES_REGISTRAR_CONTROLLER,
    BASENAMES_REGISTRY,
    CPT_BASENAMES,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BASE_ETH_NODE: Final = b'\xff\x1e<\x0e\xb0\x0e\xc7\x14\xe3Ka\x14\x12_\xbd\xe1\xde\xa2\xf2Jr\xfb\xf6r\xe7\xb7\xfdV\x902\x8e\x10'  # noqa: E501
BASE_REVERSE_NODE: Final = b'\x08\xd9\xb0\x99>\xb8\xc4\xdaW\xc3zK\x84\xa6\xe3\x84\xc2b1\x14\xffN\x93p\xedQ\xc9\xb8\x93Q\t\xba'  # noqa: E501
NAME_REGISTERED_TOPIC: Final = b'\x06g\x08m\x08As3\xcec\xf4\r[\xc2\xefo\xd30\xe2Z\xaa\xf3\x17\xb7\xc4\x89T\x1f\x8f\xe6\x00\xfa'  # noqa: E501
NAME_REGISTERED_ABI: Final = '{"anonymous":false,"inputs":[{"indexed":false,"internalType":"string","name":"name","type":"string"},{"indexed":true,"internalType":"bytes32","name":"label","type":"bytes32"},{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":false,"internalType":"uint256","name":"expires","type":"uint256"}],"name":"NameRegistered","type":"event"}'  # noqa: E501


class BasenamesDecoder(EnsCommonDecoder):

    def __init__(  # pylint: disable=super-init-not-called
            self,
            base_inquirer: 'BaseInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',  # pylint: disable=unused-argument
    ) -> None:
        super().__init__(
            evm_inquirer=base_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            reverse_resolver=BASENAMES_L2_RESOLVER,
            counterparty=CPT_BASENAMES,
            suffix='base.eth',
            display_name='Basenames',
        )

    def _get_name_to_show(self, node: bytes, context: DecoderContext) -> str | None:
        """Get the full name associated with the specified node.
        Returns the full name, or None if unable to retrieve a name.
        """
        # Check if it's a node with a hardcoded value
        # See https://github.com/base-org/basenames/blob/main/src/util/Constants.sol
        if node == BASE_ETH_NODE:
            return 'base.eth'
        elif node == BASE_REVERSE_NODE:
            return 'reverse'

        # Try to retrieve it from the cache
        with GlobalDBHandler().conn.read_ctx() as cursor:
            if (name_to_show := globaldb_get_unique_cache_value(
                    cursor=cursor,
                    key_parts=(CacheType.ENS_NAMEHASH, node.hex()),
            )) is not None:
                return name_to_show

        # Call the L2 Resolver contract's name method.
        try:
            if not (name_to_show := self.evm_inquirer.contracts.contract(BASENAMES_L2_RESOLVER).call(  # noqa: E501
                node_inquirer=self.evm_inquirer,
                method_name='name',
                arguments=[node],
            )):
                log.error(f'Blank name returned from resolver contract for node {node.hex()}.')
                return None
        except RemoteError as e:
            log.error(f'Failed to find full Basename for node {node.hex()} due to {e!s}')
            return None

        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=(CacheType.ENS_NAMEHASH, node.hex()),
                value=name_to_show,
            )
        return name_to_show

    def _maybe_get_labelhash_name(
            self,
            context: DecoderContext,
            label_hash: str,
            node: bytes | None = None,
    ) -> str | None:
        """Try to get the name corresponding to a labelhash.
        Checks the cache first and then queries the base.org api.
        Returns the name or None if unable to retrieve a name.
        """
        label_hash = label_hash.removeprefix('0x')
        with GlobalDBHandler().conn.read_ctx() as cursor:
            if (found_name := globaldb_get_unique_cache_value(
                cursor=cursor,
                key_parts=(CacheType.ENS_LABELHASH, label_hash),
            )):
                return found_name

        try:
            response_data = requests.get(
                url=f'https://www.base.org/api/basenames/metadata/{int(label_hash, 16)}',
                timeout=CachedSettings().get_timeout_tuple(),
            ).json()
        except (requests.exceptions.RequestException, JSONDecodeError, ValueError) as e:
            log.error(
                f'Failed to retrieve name for labelhash {label_hash} '
                f'from Basenames api due to {e!s}',
            )
            return None

        if not isinstance(response_data, dict):
            log.error(
                f'Failed to retrieve name for labelhash {label_hash}. '
                f'Basenames api response should be a dict, instead got {response_data}',
            )
            return None

        try:
            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                globaldb_set_unique_cache_value(
                    write_cursor=write_cursor,
                    key_parts=(CacheType.ENS_LABELHASH, label_hash),
                    value=(name := response_data['name']),
                )
        except KeyError:
            log.error(
                f'Failed to retrieve name for labelhash {label_hash}. '
                f'Basenames api response is missing the name attribute.',
            )
            return None

        return name

    def _decode_registrar_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != NAME_REGISTERED_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        try:
            _, decoded_data = decode_event_data_abi_str(
                tx_log=context.tx_log,
                abi_json=NAME_REGISTERED_ABI,
            )
        except DeserializationError as e:
            log.error(f'Failed to decode Basenames registered event due to {e!s}')
            return DEFAULT_DECODING_OUTPUT

        fullname = f'{decoded_data[0]}.base.eth'
        expires = decoded_data[1]
        spend_event = receive_event = None
        for event in context.decoded_events:
            if event.event_type == HistoryEventType.SPEND and event.asset == A_ETH and event.address == context.tx_log.address:  # noqa: E501
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = CPT_BASENAMES
                event.notes = f'Register {self.display_name} name {fullname} for {event.amount} ETH until {self.timestamp_to_date(expires)}'  # noqa: E501
                event.extra_data = {'name': fullname, 'expires': expires}
                spend_event = event
            elif event.event_type == HistoryEventType.RECEIVE and tokenid_belongs_to_collection(
                token_identifier=event.asset.identifier,
                collection_identifier='eip155:8453/erc721:0x03c4738Ee98aE44591e1A4A4F3CaB6641d95DD9a',  # Basenames NFTs  # noqa: E501
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                # Update the note using the tx_log address (registrar controller) as the from address instead of the zero address  # noqa: E501
                event.notes = f'Receive {self.display_name} name {fullname} from {context.tx_log.address} to {event.location_label}'  # noqa: E501
                receive_event = event

        if receive_event is not None and spend_event is None:
            # Create spend event with zero balance for discounted registrations
            spend_event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                asset=A_ETH,
                amount=ZERO,
                location_label=bytes_to_address(context.tx_log.topics[2]),
                notes=f'Register {self.display_name} name {fullname} until {self.timestamp_to_date(expires)}',  # noqa: E501
                counterparty=CPT_BASENAMES,
                address=context.tx_log.address,
                extra_data={'name': fullname, 'expires': expires},
            )
            context.decoded_events.append(spend_event)

        if spend_event is not None and receive_event is not None:
            maybe_reshuffle_events(
                ordered_events=[spend_event, receive_event],
                events_list=context.decoded_events,
            )

        return DecodingOutput(process_swaps=True)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            BASENAMES_REGISTRAR_CONTROLLER: (self._decode_registrar_events,),
            BASENAMES_L2_RESOLVER: (self._decode_ens_public_resolver_events,),
            BASENAMES_REGISTRY: (self._decode_ens_registry_with_fallback_event,),
            BASENAMES_BASE_REGISTRAR: (self._decode_name_transfer,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (BASENAMES_CPT_DETAILS,)
