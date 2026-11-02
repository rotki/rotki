import logging
from typing import TYPE_CHECKING, Any, Final

import ens
from eth_utils import keccak

from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi_str
from rotkehlchen.chain.evm.decoding.ens.constants import NEW_OWNER, NEW_RESOLVER
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
from rotkehlchen.utils.misc import bytes_to_address, from_wei

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
    ENS_V2_ETH_REGISTRY,
    ENS_V2_HCA_FACTORY,
    ENS_V2_LOCKED_MIGRATION_CONTROLLER,
    ENS_V2_UNLOCKED_MIGRATION_CONTROLLER,
    ETH_NODE,
    HCA_DEPLOYED,
    LABEL_REGISTERED,
    LABEL_REGISTERED_ABI,
    NAME_REGISTERED_BASE_COST_AND_PREMIUM,
    NAME_REGISTERED_BASE_COST_AND_PREMIUM_ABI,
    NAME_REGISTERED_SINGLE_COST,
    NAME_REGISTERED_SINGLE_COST_ABI,
    NAME_RENEWED,
    NAME_RENEWED_ABI,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MIGRATION_CONTROLLERS: Final = {
    ENS_V2_UNLOCKED_MIGRATION_CONTROLLER,
    ENS_V2_LOCKED_MIGRATION_CONTROLLER,
}


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
            ethereum_inquirer: EthereumInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,  # pylint: disable=unused-argument
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

        refund_from_registrar = ZERO
        to_remove_indices = []
        spend_event = receive_event = None
        for event_idx, event in enumerate(context.decoded_events):
            if event.event_type == HistoryEventType.RECEIVE and event.asset == A_ETH and event.address in {ENS_REGISTRAR_CONTROLLER_1, ENS_REGISTRAR_CONTROLLER_2}:  # noqa: E501
                # remove ETH refund event and net it out from the registration spend event.
                refund_from_registrar += event.amount
                to_remove_indices.append(event_idx)

        expected_amounts = {amount}
        if refund_from_registrar != ZERO:
            expected_amounts.add(amount + refund_from_registrar)

        for event in context.decoded_events:
            # Find the ETH transfer event that pays for registration.
            if (
                event.event_type == HistoryEventType.SPEND and
                event.asset == A_ETH and
                event.address == context.tx_log.address and
                event.amount in expected_amounts
            ):
                event.amount = amount
                event.counterparty = CPT_ENS
                event.notes = f'Register ENS name {fullname} for {amount} ETH until {self.timestamp_to_date(expires)}'  # noqa: E501
                event.extra_data = {'name': fullname, 'expires': expires}
                spend_event = event
                break

        if spend_event is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        for event in context.decoded_events:
            # Find the ENS ERC721 receive event which should be before the registered event
            if event.event_type == HistoryEventType.RECEIVE and tokenid_belongs_to_collection(
                token_identifier=event.asset.identifier,
                collection_identifier='eip155:1/erc721:0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85',
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                receive_event = event

        for index in reversed(to_remove_indices):
            del context.decoded_events[index]

        if receive_event is not None:
            spend_event.event_type = HistoryEventType.TRADE
            spend_event.event_subtype = HistoryEventSubType.SPEND
            maybe_reshuffle_events(
                ordered_events=[spend_event, receive_event],
                events_list=context.decoded_events,
            )
            return EvmDecodingOutput(process_swaps=True)

        spend_event.event_subtype = HistoryEventSubType.NONE
        return DEFAULT_EVM_DECODING_OUTPUT

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
        renewal_event_found = False
        for idx, event in enumerate(context.decoded_events):
            if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.asset == A_ETH and event.address in {context.tx_log.address, context.transaction.to_address}:  # noqa: E501
                refund_event_idx = idx
                refund_amount = event.amount

                if context.tx_log.address == ENS_REGISTRAR_CONTROLLER_1:  # old controller
                    # old controller logs actual cost after refund
                    checked_cost = logged_cost + refund_amount
                # else new controller logs the msg.value, which is the brutto value

            # Find the transfer event which should be before the name renewed event.
            # Some extensions go through a wrapper contract that forwards the payment to the
            # registrar controller emitting this event, so also match the transaction recipient.
            if event.event_type == HistoryEventType.SPEND and event.asset == A_ETH and event.amount == checked_cost and event.address in {context.tx_log.address, context.transaction.to_address}:  # noqa: E501
                event.amount -= refund_amount  # get correct amount spent
                event.event_type = HistoryEventType.RENEW
                event.event_subtype = HistoryEventSubType.NONE
                event.counterparty = CPT_ENS
                event.notes = f'Renew ENS name {fullname} for {event.amount} ETH until {self.timestamp_to_date(expires)}'  # noqa: E501
                event.extra_data = {'name': fullname, 'expires': expires}
                renewal_event_found = True

        if renewal_event_found is False and self.base.is_tracked(context.transaction.from_address):
            context.decoded_events.append(self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.RENEW,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=logged_cost - refund_amount,
                location_label=context.transaction.from_address,
                notes=f'Renew ENS name {fullname} for {logged_cost - refund_amount} ETH until {self.timestamp_to_date(expires)}',  # noqa: E501
                counterparty=CPT_ENS,
                address=context.transaction.to_address,
                extra_data={'name': fullname, 'expires': expires},
            ))

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

    def _migrated_labelhashes(self, context: DecoderContext) -> set[bytes]:
        """Labelhashes of the names that the transaction migrates from ENS v1 to v2"""
        return {
            log_entry.topics[2] for log_entry in context.all_logs
            if (
                log_entry.address == ENS_V2_ETH_REGISTRY and
                log_entry.topics[0] == LABEL_REGISTERED and
                bytes_to_address(log_entry.topics[3]) in MIGRATION_CONTROLLERS
            )
        }

    def _decode_ens_registry_with_fallback_event(self, context: DecoderContext) -> EvmDecodingOutput:  # noqa: E501
        """The v1 registry logs emitted when a name is migrated to v2 only describe moving the
        name to the migration controller and clearing its resolver. They are covered by the
        migration event so don't decode them separately."""
        if context.tx_log.topics[0] in (NEW_OWNER, NEW_RESOLVER) and len(
            labelhashes := self._migrated_labelhashes(context),
        ) != 0:
            if context.tx_log.topics[0] == NEW_OWNER:
                is_migration_log = (
                    context.tx_log.topics[1] == ETH_NODE and
                    context.tx_log.topics[2] in labelhashes
                )
            else:
                is_migration_log = context.tx_log.topics[1] in {
                    keccak(ETH_NODE + labelhash) for labelhash in labelhashes
                }

            if is_migration_log:
                return DEFAULT_EVM_DECODING_OUTPUT

        return super()._decode_ens_registry_with_fallback_event(context)

    def _decode_v2_registry_event(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode the migration of a name from ENS v1 to ENS v2. The v2 registry logs a
        LabelRegistered with the migration controller as sender when that happens.

        The v2 token is an ERC-1155 that is not decoded, so the migration is represented by
        the v1 ERC-721 that leaves the user.
        """
        if (
            context.tx_log.topics[0] != LABEL_REGISTERED or
            bytes_to_address(context.tx_log.topics[3]) not in MIGRATION_CONTROLLERS
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        try:
            _, decoded_data = decode_event_data_abi_str(context.tx_log, LABEL_REGISTERED_ABI)
        except DeserializationError as e:
            log.error('Failed to decode ENS v2 label registered event', tx_hash=str(context.transaction.tx_hash), error=str(e))  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        fullname = _save_hash_mappings_get_fullname(name=decoded_data[0], tx_hash=context.transaction.tx_hash)  # noqa: E501
        new_owner, expires = decoded_data[1], decoded_data[2]
        v1_asset_id = f'eip155:1/erc721:{ENS_BASE_REGISTRAR_IMPLEMENTATION}/{int.from_bytes(context.tx_log.topics[2])}'  # noqa: E501
        for event in context.decoded_events:
            if event.event_type == HistoryEventType.SPEND and event.asset.identifier == v1_asset_id:  # noqa: E501
                event.event_type = HistoryEventType.MIGRATE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = CPT_ENS
                event.notes = f'Migrate ENS name {fullname} to ENS v2'
                if new_owner != event.location_label:
                    event.notes += f' with new owner {new_owner}'
                event.extra_data = {'name': fullname, 'expires': expires}
                return DEFAULT_EVM_DECODING_OUTPUT

        # Not a v1 ERC-721 (e.g. wrapped name) or not decoded. Still note the migration
        if self.base.is_tracked(new_owner):
            location_label = new_owner
        elif self.base.is_tracked(context.transaction.from_address):
            location_label = context.transaction.from_address
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=location_label,
            notes=f'Migrate ENS name {fullname} to ENS v2',
            counterparty=CPT_ENS,
            address=context.tx_log.address,
            extra_data={'name': fullname, 'expires': expires},
        )])

    def _decode_hca_factory_event(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode the deployment of the user's ENS v2 account contract"""
        if (
            context.tx_log.topics[0] != HCA_DEPLOYED or
            not self.base.is_tracked(owner := bytes_to_address(context.tx_log.topics[2]))
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=owner,
            notes=f'Create ENS v2 account contract {bytes_to_address(context.tx_log.topics[1])}',
            counterparty=CPT_ENS,
            address=context.tx_log.address,
        )])

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            ENS_GOVERNOR: (self._decode_governance,),
            ENS_REGISTRAR_CONTROLLER_1: (self._decode_ens_registrar_event,),
            ENS_REGISTRAR_CONTROLLER_2: (self._decode_ens_registrar_event,),
            ENS_BASE_REGISTRAR_IMPLEMENTATION: (self._decode_name_transfer,),
            ENS_REGISTRY_WITH_FALLBACK: (self._decode_ens_registry_with_fallback_event,),
            ENS_V2_ETH_REGISTRY: (self._decode_v2_registry_event,),
            ENS_V2_HCA_FACTORY: (self._decode_hca_factory_event,),
            ENS_PUBLIC_RESOLVER_2_ADDRESS: (self._decode_ens_public_resolver_events,),
            ENS_PUBLIC_RESOLVER_3_ADDRESS: (self._decode_ens_public_resolver_events,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (ENS_CPT_DETAILS,)
