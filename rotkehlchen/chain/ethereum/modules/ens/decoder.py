import logging
from typing import TYPE_CHECKING, Any

import content_hash
import ens

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi_str
from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import GovernableDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.api import APIKeyNotConfigured
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress, EvmTokenKind, EVMTxHash
from rotkehlchen.utils.misc import from_wei, hex_or_bytes_to_address, hex_or_bytes_to_str
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

from .constants import (
    ADDR_CHANGED,
    CONTENT_HASH_CHANGED,
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
    NEW_OWNER,
    NEW_RESOLVER,
    TEXT_CHANGED_KEY_AND_VALUE,
    TEXT_CHANGED_KEY_AND_VALUE_ABI,
    TEXT_CHANGED_KEY_ONLY,
    TEXT_CHANGED_KEY_ONLY_ABI,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
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
                f'Got an invalid ENS name {name} during decoding {tx_hash.hex()}.'
                f'namehash and labelhash not stored in the globaldb cache. {e=}',
            )
    return full_name


class EnsDecoder(GovernableDecoderInterface, CustomizableDateMixin):
    def __init__(  # pylint: disable=super-init-not-called
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',  # pylint: disable=unused-argument
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            protocol=CPT_ENS,
            proposals_url='https://www.tally.xyz/gov/ens/proposal',
        )
        self.base = base_tools
        self.ethereum = ethereum_inquirer
        CustomizableDateMixin.__init__(self, base_tools.database)
        self.eth = A_ETH.resolve_to_crypto_asset()
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
                f'in {context.transaction.tx_hash.hex()} due to {msg} '
                f'during decoding events. Not adding name to event',
            )
        except APIKeyNotConfigured as e:
            log.warning(
                f'Not adding name to ENS event in {context.transaction.tx_hash.hex()} since '
                f'The Graph cannot be queried. {e}',
            )
        else:  # succesfully queried the graph. Save in the cache
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
                    value=found_name,  # type: ignore  # should not be None here
                )

        return found_name

    def _decode_ens_registrar_event(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] in (
            NAME_REGISTERED_SINGLE_COST,
            NAME_REGISTERED_BASE_COST_AND_PREMIUM,
        ):
            return self._decode_name_registered(context=context)

        if context.tx_log.topics[0] == NAME_RENEWED:
            return self._decode_name_renewed(context=context)

        return DEFAULT_DECODING_OUTPUT

    def _decode_name_registered(self, context: DecoderContext) -> DecodingOutput:
        try:
            _, decoded_data = decode_event_data_abi_str(
                context.tx_log,
                NAME_REGISTERED_SINGLE_COST_ABI if context.tx_log.topics[0] == NAME_REGISTERED_SINGLE_COST else NAME_REGISTERED_BASE_COST_AND_PREMIUM_ABI,  # noqa: E501
            )
        except DeserializationError as e:
            log.debug(f'Failed to decode ENS name registered event due to {e!s}')
            return DEFAULT_DECODING_OUTPUT

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
            if event.event_type == HistoryEventType.RECEIVE and event.asset == A_ETH and event.address == ENS_REGISTRAR_CONTROLLER_1:  # noqa: E501
                # remove ETH refund event
                refund_from_registrar = event.balance.amount
                to_remove_indices.append(event_idx)

            # Find the ETH transfer event which should be before the registered event
            if event.event_type == HistoryEventType.SPEND and event.asset == A_ETH and event.address == context.tx_log.address:  # noqa: E501
                expected_amount = amount
                if refund_from_registrar:
                    expected_amount = amount + refund_from_registrar
                if event.balance.amount != expected_amount:
                    return DEFAULT_DECODING_OUTPUT  # registration amount did not match

                event.balance.amount = amount  # adjust the spent amount too, after refund
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = CPT_ENS
                event.notes = f'Register ENS name {fullname} for {amount} ETH until {self.timestamp_to_date(expires)}'  # noqa: E501
                event.extra_data = {'name': fullname, 'expires': expires}
                spend_event = event

            # Find the ENS ERC721 receive event which should be before the registered event
            if event.event_type == HistoryEventType.RECEIVE and event.asset.identifier == 'eip155:1/erc721:0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85':  # noqa: E501
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

        return DEFAULT_DECODING_OUTPUT

    def _decode_name_renewed(self, context: DecoderContext) -> DecodingOutput:
        try:
            _, decoded_data = decode_event_data_abi_str(context.tx_log, NAME_RENEWED_ABI)
        except DeserializationError as e:
            log.error(f'Failed to decode ENS name renewed event in {context.transaction.tx_hash.hex()} due to {e!s}')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        fullname = _save_hash_mappings_get_fullname(name=decoded_data[0], tx_hash=context.transaction.tx_hash)  # noqa: E501
        logged_cost = from_wei(decoded_data[1])  # logs msg.value for new controller and actual cost for old  # noqa: E501
        expires = decoded_data[2]

        refund_event_idx, refund_amount, checked_cost = None, ZERO, logged_cost
        for idx, event in enumerate(context.decoded_events):
            if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.asset == A_ETH and event.address == context.tx_log.address:  # noqa: E501
                refund_event_idx = idx
                refund_amount = event.balance.amount

                if context.tx_log.address == ENS_REGISTRAR_CONTROLLER_1:  # old controller
                    # old controller logs actual cost after refund
                    checked_cost = logged_cost + refund_amount
                # else new controller logs the msg.value, which is the brutto value

            # Find the transfer event which should be before the name renewed event
            if event.event_type == HistoryEventType.SPEND and event.asset == A_ETH and event.balance.amount == checked_cost and event.address == context.tx_log.address:  # noqa: E501
                event.balance.amount -= refund_amount  # get correct amount spent
                event.event_type = HistoryEventType.RENEW
                event.event_subtype = HistoryEventSubType.NONE
                event.counterparty = CPT_ENS
                event.notes = f'Renew ENS name {fullname} for {event.balance.amount} ETH until {self.timestamp_to_date(expires)}'  # noqa: E501
                event.extra_data = {'name': fullname, 'expires': expires}

        if refund_event_idx is not None:
            del context.decoded_events[refund_event_idx]
        return DEFAULT_DECODING_OUTPUT

    def _decode_name_transfer(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != ERC20_OR_ERC721_TRANSFER:
            return DEFAULT_DECODING_OUTPUT

        to_address = hex_or_bytes_to_address(context.tx_log.topics[2])
        token = get_or_create_evm_token(
            userdb=self.database,
            evm_address=context.tx_log.address,
            chain_id=self.evm_inquirer.chain_id,
            token_kind=EvmTokenKind.ERC721,
            evm_inquirer=self.evm_inquirer,
            encounter=TokenEncounterInfo(tx_hash=context.transaction.tx_hash),
        )
        transfer_event = self.base.decode_erc20_721_transfer(
            token=token,
            tx_log=context.tx_log,
            transaction=context.transaction,
        )
        if transfer_event is None:  # Can happen if neither from/to is tracked
            return DEFAULT_DECODING_OUTPUT

        label_hash = '0x{:064x}'.format(transfer_event.extra_data['token_id'])  # type: ignore[index]  # ERC721 transfer always has extra data. This code is to transform the int token id to a 32 bytes hex label hash
        found_name = self._maybe_get_labelhash_name(context=context, label_hash=label_hash)
        if found_name is None:
            name_to_show = ''
        else:
            name_to_show = f'{found_name}.eth ' if not found_name.endswith('.eth') else f'{found_name} '  # noqa: E501

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

        transfer_event.counterparty = CPT_ENS
        transfer_event.notes = f'{verb} ENS name {name_to_show}{from_text}{to_text}'
        return DecodingOutput(event=transfer_event, refresh_balances=False)

    def _decode_new_resolver(self, context: DecoderContext) -> DecodingOutput:
        """Decode event where address is set for an ENS name."""
        ens_name = self._get_name_to_show(node=context.tx_log.topics[1], tx_hash=context.transaction.tx_hash)  # noqa: E501
        suffix = ens_name if ens_name is not None else 'an ENS name'

        # Not able to give more info to the user such as address that was set since
        # we don't have historical info and event doesn't provide it
        notes = f'Set ENS address for {suffix}'
        context.decoded_events.append(self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=context.transaction.from_address,
            notes=notes,
            counterparty=CPT_ENS,
            address=context.transaction.to_address,
        ))
        return DEFAULT_DECODING_OUTPUT

    def _decode_new_owner(self, context: DecoderContext) -> DecodingOutput:
        if self.base.is_tracked(new_owner := hex_or_bytes_to_address(context.tx_log.data[:32])):
            associated_address = new_owner
        elif self.base.is_tracked(context.transaction.from_address):
            associated_address = context.transaction.from_address
        else:
            return DEFAULT_DECODING_OUTPUT

        node_name = self._get_name_to_show(node=(node := context.tx_log.topics[1]), tx_hash=context.transaction.tx_hash)  # noqa: E501
        label_hash = '0x' + hex_or_bytes_to_str(context.tx_log.topics[2])
        label_name = self._maybe_get_labelhash_name(context=context, label_hash=label_hash, node=node)  # noqa: E501

        node_str = f'{node_name} node' if node_name else f'node witn nodehash {context.tx_log.topics[1].hex()}'  # noqa: E501
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
            balance=Balance(),
            location_label=associated_address,
            notes=f'Transfer {node_str} ownership of subnode {subnode_str} to {new_owner}',
            address=context.tx_log.address,
            counterparty=CPT_ENS,
        )
        return DecodingOutput(event=event)

    def _decode_ens_registry_with_fallback_event(self, context: DecoderContext) -> DecodingOutput:
        """Decode event where address is set for an ENS name."""
        if context.tx_log.topics[0] == NEW_RESOLVER:
            return self._decode_new_resolver(context)
        elif context.tx_log.topics[0] == NEW_OWNER:
            return self._decode_new_owner(context)

        return DEFAULT_DECODING_OUTPUT

    def _get_name_to_show(self, node: bytes, tx_hash: EVMTxHash) -> str | None:
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
                    f'{tx_hash.hex()} due to {msg} '
                    f'during decoding events. Not adding name to event',
                )
            except APIKeyNotConfigured as e:
                log.warning(
                    f'Not adding name to ENS event in {tx_hash.hex()} since '
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
            _save_hash_mappings_get_fullname(name=name_to_show[:-4], tx_hash=tx_hash)

        return name_to_show

    def _decode_ens_public_resolver_content_hash(self, context: DecoderContext) -> DecodingOutput:
        """Decode an event that modifies a content hash for the public ENS resolver"""
        node = context.tx_log.topics[1]  # node is a hash of the name used by ens internals
        contract = self.ethereum.contracts.contract_by_address(address=context.tx_log.address)
        if contract is None:
            self.msg_aggregator.add_error(
                f'Failed to find ENS public resolver contract with address '
                f'{context.tx_log.address} for {context.transaction.tx_hash.hex()}. '
                f'This should never happen. Please, '
                f"open an issue in rotki's github repository.",
            )
            return DEFAULT_DECODING_OUTPUT

        result = contract.decode_event(context.tx_log, 'ContenthashChanged', argument_names=None)
        new_hash = result[1][0].hex()
        name_to_show = self._get_name_to_show(node=node, tx_hash=context.transaction.tx_hash)

        try:
            codec = content_hash.get_codec(new_hash)
            value_hash = content_hash.decode(new_hash)
            value = f'{codec}://{value_hash}'
        except (TypeError, KeyError, ValueError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Inability to find key {msg}'
            log.error(f'Failed to decode content hash {new_hash} in {context.transaction.tx_hash.hex()} due to {msg}')  # noqa: E501
            value = f'unknown type hash {new_hash}'

        notes = f'Change ENS content hash to {value}'
        if name_to_show is not None:
            notes += f' for {name_to_show}'
        context.decoded_events.append(self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=context.transaction.from_address,
            notes=notes,
            counterparty=CPT_ENS,
            address=context.transaction.to_address,
        ))
        return DEFAULT_DECODING_OUTPUT

    def _decode_addr_changed(self, context: DecoderContext) -> DecodingOutput:

        if self.base.is_tracked(new_address := hex_or_bytes_to_address(context.tx_log.data[:32])):
            associated_address = new_address
        elif self.base.is_tracked(context.transaction.from_address):
            associated_address = context.transaction.from_address
        else:
            return DEFAULT_DECODING_OUTPUT

        node = context.tx_log.topics[1]  # node is a hash of the name used by ens internals
        name = self._get_name_to_show(node=node, tx_hash=context.transaction.tx_hash)
        name_str = name or f'name with nodehash {node.hex()}'
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=associated_address,
            notes=f'Address for {name_str} changed to {new_address}',
            address=context.tx_log.address,
            counterparty=CPT_ENS,
        )
        return DecodingOutput(event=event)

    def _decode_ens_public_resolver_events(self, context: DecoderContext) -> DecodingOutput:
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
            return DEFAULT_DECODING_OUTPUT

        try:
            _, decoded_data = decode_event_data_abi_str(
                context.tx_log,
                TEXT_CHANGED_KEY_ONLY_ABI if context.tx_log.topics[0] == TEXT_CHANGED_KEY_ONLY else TEXT_CHANGED_KEY_AND_VALUE_ABI,  # noqa: E501
            )
        except DeserializationError as e:
            log.error(f'Failed to decode ENS set-text event in {context.transaction.tx_hash.hex()} due to {e!s}')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        changed_key = decoded_data[0]
        new_value = decoded_data[1] if context.tx_log.topics[0] == TEXT_CHANGED_KEY_AND_VALUE else None  # noqa: E501
        node = context.tx_log.topics[1]  # node is a hash of the name used by ens internals

        name_to_show = self._get_name_to_show(node=node, tx_hash=context.transaction.tx_hash)
        notes = f'Set ENS {changed_key} {f"to {new_value} " if new_value else ""}attribute'
        if name_to_show is not None:
            notes += f' for {name_to_show}'
        context.decoded_events.append(self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=context.transaction.from_address,
            notes=notes,
            counterparty=CPT_ENS,
            address=context.transaction.to_address,
        ))
        return DEFAULT_DECODING_OUTPUT

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
