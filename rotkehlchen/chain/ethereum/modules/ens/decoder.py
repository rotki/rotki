import logging
from typing import TYPE_CHECKING, Any

import ens

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi_str
from rotkehlchen.chain.evm.decoding.ens.decoder import EnsCommonDecoder
from rotkehlchen.chain.evm.decoding.interfaces import GovernableDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import tokenid_belongs_to_collection
from rotkehlchen.errors.api import APIKeyNotConfigured
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.graph import Graph
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress, EVMTxHash
from rotkehlchen.utils.misc import from_wei

from .constants import (
    CPT_ENS,
    ENS_BASE_REGISTRAR_IMPLEMENTATION,
    ENS_CPT_DETAILS,
    ENS_GOVERNOR,
    ENS_PUBLIC_RESOLVER_2_ADDRESS,
    ENS_PUBLIC_RESOLVER_3_ADDRESS,
    ENS_REGISTRAR_CONTROLLER_1,
    ENS_REGISTRAR_CONTROLLER_2,
    ENS_REGISTRY_WITH_FALLBACK,
    ENS_REVERSE_RESOLVER,
    NAME_REGISTERED_BASE_COST_AND_PREMIUM,
    NAME_REGISTERED_BASE_COST_AND_PREMIUM_ABI,
    NAME_REGISTERED_SINGLE_COST,
    NAME_REGISTERED_SINGLE_COST_ABI,
    NAME_RENEWED,
    NAME_RENEWED_ABI,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _save_hash_mappings_get_fullname(name: str, tx_hash: EVMTxHash) -> str:
    """
    Saves the namehash -> name and labelhash -> name mappings to the global DB
    cache and gets name with.eth suffix.

    The given name has to be without the .eth suffix and is returned with it. In the case that
    the registered name is invalid we return the name but we don't store it in the database cache.
    """
    full_name = f'{name}.eth'
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        try:
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=(CacheType.ENS_NAMEHASH, ens.ENS.namehash(full_name).hex()),
                value=full_name,
            )
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=(CacheType.ENS_LABELHASH, ens.ENS.labelhash(name).hex()),
                value=name,
            )
        except ens.exceptions.InvalidName as e:
            log.error(
                f'Got an invalid ENS name {name} during decoding {tx_hash!s}.'
                f'namehash and labelhash not stored in the globaldb cache. {e=}',
            )
    return full_name


class EnsDecoder(GovernableDecoderInterface, EnsCommonDecoder):
    def __init__(  # pylint: disable=super-init-not-called
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',  # pylint: disable=unused-argument
    ) -> None:
        EnsCommonDecoder.__init__(
            self,
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            reverse_resolver=ENS_REVERSE_RESOLVER,
            counterparty=CPT_ENS,
            suffix='eth',
            display_name='ENS',
        )
        GovernableDecoderInterface.__init__(
            self,
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            protocol=CPT_ENS,
            proposals_url='https://www.tally.xyz/gov/ens/proposal',
        )
        self.ethereum = ethereum_inquirer
        self.graph = Graph(
            subgraph_id='5XqPmWe6gjyrJtFn9cLy237i4cWw2j9HcUJEXsP5qGtH',
            database=self.database,
            label=CPT_ENS,
        )

    def _maybe_get_labelhash_name(
            self,
            context: DecoderContext,
            label_hash: str,
            node: bytes | None = None,
    ) -> str | None:
        """Try to get the labelhash full name either from DB cache or the graph"""
        if not label_hash.startswith('0x'):
            label_hash = f'0x{label_hash}'
        found_name = None
        with GlobalDBHandler().conn.read_ctx() as cursor:
            found_name = globaldb_get_unique_cache_value(cursor=cursor, key_parts=(CacheType.ENS_LABELHASH, label_hash))  # noqa: E501

        if found_name:
            return found_name

        try:
            result = self.graph.query(
                querystr=f'query{{domains(first:1, where:{{labelhash:"{label_hash}"}}){{name}}}}')
            found_name = result['domains'][0]['name']
        except (RemoteError, KeyError, IndexError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key {msg}'
            log.error(
                f'Failed to query graph for token ID to ENS name '
                f'in {context.transaction.tx_hash!s} due to {msg} '
                f'during decoding events. Not adding name to event',
            )
        except APIKeyNotConfigured as e:
            log.warning(
                f'Not adding name to ENS event in {context.transaction.tx_hash!s} since '
                f'The Graph cannot be queried. {e}',
            )
        else:  # successfully queried the graph. Save in the cache
            assert found_name is not None, 'should not be None here'
            if '].addr.reverse' in found_name and node:  # then this node is not a namehash
                try:  # this kind of result can be returned by the graph query and means we need to do reverse resolution  # noqa: E501
                    found_name = self.ethereum.contracts.contract(ENS_REVERSE_RESOLVER).call(
                        node_inquirer=self.ethereum,
                        method_name='name',
                        arguments=[node],
                    )
                except RemoteError as e:
                    log.debug(f'Failed to reverse resolve ENS name: {e!s}')
                    return None

            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                globaldb_set_unique_cache_value(
                    write_cursor=write_cursor,
                    key_parts=(CacheType.ENS_LABELHASH, label_hash),
                    value=found_name,
                )

        return found_name

    def _decode_ens_registrar_event(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] in (
            NAME_REGISTERED_SINGLE_COST,
            NAME_REGISTERED_BASE_COST_AND_PREMIUM,
        ):
            return self._decode_name_registered(context=context)

        if context.tx_log.topics[0] == NAME_RENEWED:
            return self._decode_name_renewed(context=context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_name_registered(self, context: DecoderContext) -> EvmDecodingOutput:
        try:
            _, decoded_data = decode_event_data_abi_str(
                context.tx_log,
                NAME_REGISTERED_SINGLE_COST_ABI if context.tx_log.topics[0] == NAME_REGISTERED_SINGLE_COST else NAME_REGISTERED_BASE_COST_AND_PREMIUM_ABI,  # noqa: E501
            )
        except DeserializationError as e:
            log.debug(f'Failed to decode ENS name registered event due to {e!s}')
            return DEFAULT_EVM_DECODING_OUTPUT

        fullname = _save_hash_mappings_get_fullname(name=decoded_data[0], tx_hash=context.transaction.tx_hash)  # noqa: E501
        if context.tx_log.topics[0] == NAME_REGISTERED_SINGLE_COST:
            amount = from_wei(decoded_data[1])
            expires = decoded_data[2]
        else:
            amount = from_wei(decoded_data[1] + decoded_data[2])  # In the new version the amount is baseCost + premium  # noqa: E501
            expires = decoded_data[3]

        refund_from_registrar = None
        to_remove_indices = []
        spend_event = receive_event = None
        for event_idx, event in enumerate(context.decoded_events):
            if event.event_type == HistoryEventType.RECEIVE and event.asset == A_ETH and event.address in {ENS_REGISTRAR_CONTROLLER_1, ENS_REGISTRAR_CONTROLLER_2}:  # noqa: E501
                # remove ETH refund event
                refund_from_registrar = event.amount
                to_remove_indices.append(event_idx)

            # Find the ETH transfer event which should be before the registered event
            if event.event_type == HistoryEventType.SPEND and event.asset == A_ETH and event.address == context.tx_log.address:  # noqa: E501
                expected_amount = amount
                if refund_from_registrar:
                    expected_amount = amount + refund_from_registrar
                if event.amount != expected_amount:
                    return DEFAULT_EVM_DECODING_OUTPUT  # registration amount did not match

                event.amount = amount  # adjust the spent amount too, after refund
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = CPT_ENS
                event.notes = f'Register ENS name {fullname} for {amount} ETH until {self.timestamp_to_date(expires)}'  # noqa: E501
                event.extra_data = {'name': fullname, 'expires': expires}
                spend_event = event

            # Find the ENS ERC721 receive event which should be before the registered event
            if event.event_type == HistoryEventType.RECEIVE and tokenid_belongs_to_collection(
                token_identifier=event.asset.identifier,
                collection_identifier='eip155:1/erc721:0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85',
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                receive_event = event

        for index in to_remove_indices:
            del context.decoded_events[index]

        if spend_event is not None and receive_event is not None:
            maybe_reshuffle_events(
                ordered_events=[spend_event, receive_event],
                events_list=context.decoded_events,
            )

        return EvmDecodingOutput(process_swaps=True)

    def _decode_name_renewed(self, context: DecoderContext) -> EvmDecodingOutput:
        try:
            _, decoded_data = decode_event_data_abi_str(context.tx_log, NAME_RENEWED_ABI)
        except DeserializationError as e:
            log.error(f'Failed to decode ENS name renewed event in {context.transaction.tx_hash!s} due to {e!s}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        fullname = _save_hash_mappings_get_fullname(name=decoded_data[0], tx_hash=context.transaction.tx_hash)  # noqa: E501
        logged_cost = from_wei(decoded_data[1])  # logs msg.value for new controller and actual cost for old  # noqa: E501
        expires = decoded_data[2]

        refund_event_idx, refund_amount, checked_cost = None, ZERO, logged_cost
        for idx, event in enumerate(context.decoded_events):
            if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.asset == A_ETH and event.address == context.tx_log.address:  # noqa: E501
                refund_event_idx = idx
                refund_amount = event.amount

                if context.tx_log.address == ENS_REGISTRAR_CONTROLLER_1:  # old controller
                    # old controller logs actual cost after refund
                    checked_cost = logged_cost + refund_amount
                # else new controller logs the msg.value, which is the brutto value

            # Find the transfer event which should be before the name renewed event
            if event.event_type == HistoryEventType.SPEND and event.asset == A_ETH and event.amount == checked_cost and event.address == context.tx_log.address:  # noqa: E501
                event.amount -= refund_amount  # get correct amount spent
                event.event_type = HistoryEventType.RENEW
                event.event_subtype = HistoryEventSubType.NONE
                event.counterparty = CPT_ENS
                event.notes = f'Renew ENS name {fullname} for {event.amount} ETH until {self.timestamp_to_date(expires)}'  # noqa: E501
                event.extra_data = {'name': fullname, 'expires': expires}

        if refund_event_idx is not None:
            del context.decoded_events[refund_event_idx]
        return DEFAULT_EVM_DECODING_OUTPUT

    def _get_name_to_show(self, node: bytes, context: DecoderContext) -> str | None:
        """Try to find the name associated with the ENS namehash/node that is being modified

        Returns the fullname
        """
        namehash = '0x' + node.hex()
        queried_graph = False
        with GlobalDBHandler().conn.read_ctx() as cursor:
            name_to_show = globaldb_get_unique_cache_value(cursor=cursor, key_parts=(CacheType.ENS_NAMEHASH, namehash))  # noqa: E501

        if name_to_show is None:  # ask the graph
            try:
                result = self.graph.query(
                    querystr=f'query{{domains(first:1, where:{{id:"{namehash}"}}){{name}}}}')
                name_to_show = result['domains'][0]['name']
                queried_graph = True
            except (RemoteError, KeyError, IndexError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key {msg}'
                log.error(
                    f'Failed to query graph for namehash to ENS name in '
                    f'{context.transaction} due to {msg} '
                    f'during decoding events. Not adding name to event',
                )
            except APIKeyNotConfigured as e:
                log.warning(
                    f'Not adding name to ENS event in {context.transaction} since '
                    f'The Graph cannot be queried. {e}',
                )
            else:
                if '].addr.reverse' in name_to_show:  # then this node is not a namehash
                    try:  # this kind of result can be returned by the graph query and means we need to do reverse resolution  # noqa: E501
                        name_to_show = self.ethereum.contracts.contract(ENS_REVERSE_RESOLVER).call(
                            node_inquirer=self.ethereum,
                            method_name='name',
                            arguments=[node],
                        )
                    except RemoteError as e:
                        log.debug(f'Failed to reverse resolve ENS name: {e!s}')
                        return None

        elif queried_graph:  # if we successfully asked the graph, save the mapping
            _save_hash_mappings_get_fullname(name=name_to_show[:-4], tx_hash=context.transaction.tx_hash)  # noqa: E501

        return name_to_show or None  # Return None if name_to_show is blank

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            ENS_GOVERNOR: (self._decode_governance,),
            ENS_REGISTRAR_CONTROLLER_1: (self._decode_ens_registrar_event,),
            ENS_REGISTRAR_CONTROLLER_2: (self._decode_ens_registrar_event,),
            ENS_BASE_REGISTRAR_IMPLEMENTATION: (self._decode_name_transfer,),
            ENS_REGISTRY_WITH_FALLBACK: (self._decode_ens_registry_with_fallback_event,),
            ENS_PUBLIC_RESOLVER_2_ADDRESS: (self._decode_ens_public_resolver_events,),
            ENS_PUBLIC_RESOLVER_3_ADDRESS: (self._decode_ens_public_resolver_events,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (ENS_CPT_DETAILS,)
