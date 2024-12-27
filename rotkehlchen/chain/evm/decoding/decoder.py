import importlib
import logging
import operator
import pkgutil
import traceback
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from types import ModuleType
from typing import TYPE_CHECKING, Any, Optional, Protocol

import gevent
from gevent.lock import Semaphore
from more_itertools import peekable
from web3.exceptions import Web3Exception

from rotkehlchen.api.websockets.typedefs import ProgressUpdateSubType, WSMessageType
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token, get_token
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.beefy_finance.decoder import BeefyFinanceCommonDecoder
from rotkehlchen.chain.evm.decoding.interfaces import ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.oneinch.v5.decoder import Oneinchv5Decoder
from rotkehlchen.chain.evm.decoding.oneinch.v6.decoder import Oneinchv6Decoder
from rotkehlchen.chain.evm.decoding.open_ocean.decoder import OpenOceanDecoder
from rotkehlchen.chain.evm.decoding.pendle.constants import (
    PENDLE_SUPPORTED_CHAINS_WITHOUT_ETHEREUM,
)
from rotkehlchen.chain.evm.decoding.pendle.decoder import PendleCommonDecoder
from rotkehlchen.chain.evm.decoding.rainbow.constants import RAINBOW_SUPPORTED_CHAINS
from rotkehlchen.chain.evm.decoding.rainbow.decoder import RainbowDecoder
from rotkehlchen.chain.evm.decoding.safe.decoder import SafemultisigDecoder
from rotkehlchen.chain.evm.decoding.socket_bridge.decoder import SocketBridgeDecoder
from rotkehlchen.chain.evm.decoding.stakedao.constants import (
    STAKEDAO_SUPPORTED_CHAINS_WITHOUT_CLAIMS,
)
from rotkehlchen.chain.evm.decoding.stakedao.decoder import StakedaoCommonDecoder
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.weth.constants import (
    CHAINS_WITH_SPECIAL_WETH,
    CHAINS_WITHOUT_NATIVE_ETH,
)
from rotkehlchen.chain.evm.decoding.weth.decoder import WethDecoder
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.constants import ZERO
from rotkehlchen.db.constants import EVMTX_DECODED, EVMTX_SPAM
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import (
    InputError,
    ModuleLoadingError,
    NotERC20Conformant,
    NotERC721Conformant,
    RemoteError,
)
from rotkehlchen.errors.serialization import ConversionError, DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tasks.assets import maybe_detect_new_tokens
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmTokenKind,
    EvmTransaction,
    EVMTxHash,
    Location,
)
from rotkehlchen.utils.misc import bytes_to_address, from_wei
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

from .base import BaseDecoderTools, BaseDecoderToolsWithDSProxy
from .constants import (
    CPT_ACCOUNT_DELEGATION,
    CPT_GAS,
    ERC20_OR_ERC721_APPROVE,
    ERC20_OR_ERC721_TRANSFER,
    OUTGOING_EVENT_TYPES,
)
from .structures import (
    DEFAULT_DECODING_OUTPUT,
    FAILED_ENRICHMENT_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
    EnricherContext,
    TransferEnrichmentOutput,
)
from .utils import maybe_reshuffle_events

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import AssetWithOracles, EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer, EvmNodeInquirerWithDSProxy
    from rotkehlchen.chain.evm.transactions import EvmTransactions
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.client import DBCursor
    from rotkehlchen.externalapis.beaconchain.service import BeaconChain
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

    from .interfaces import DecoderInterface

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
MIN_LOGS_PROCESSED_TO_SLEEP = 1000


def decode_safely(
        msg_aggregator: 'MessagesAggregator',
        tx_hash: EVMTxHash,
        chain_id: ChainID,
        func: Callable,
        *args: tuple[Any],
        **kwargs: Any,
) -> tuple[Any, bool]:
    """
    Wrapper for methods that execute logic from decoders. It handles all known errors
    by logging them and optionally sending them to the user.

    It returns a tuple where the first argument is the output of func and the second is a boolean
    set to True if an error was raised from func.
    """
    try:
        return func(*args, **kwargs), False
    except (
        UnknownAsset,
        WrongAssetType,
        DeserializationError,
        IndexError,
        ValueError,
        ConversionError,
        Web3Exception,
        NotERC20Conformant,
    ) as e:
        log.error(traceback.format_exc())
        error_prefix = f'Decoding of transaction {tx_hash.hex()} in {chain_id.to_name()}'
        log.error(
            f'{error_prefix} failed due to {e} '
            f'when calling {func.__name__} with {args=} {kwargs=}',
        )
        msg_aggregator.add_error(f'{error_prefix} failed. Check logs for more details')

    return None, True


class EventDecoderFunction(Protocol):

    def __call__(
            self,
            token: 'EvmToken | None',
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            action_items: list[ActionItem],
            all_logs: list[EvmTxReceiptLog],
    ) -> DecodingOutput:
        ...


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class DecodingRules:
    address_mappings: dict[ChecksumEvmAddress, tuple[Any, ...]]
    event_rules: list[EventDecoderFunction]
    input_data_rules: dict[bytes, dict[bytes, Callable]]
    token_enricher_rules: list[Callable]  # enrichers to run for token transfers
    # rules to run after the main decoding loop. post_decoding_rules is a mapping of
    # counterparties to tuples of the rules that need to be executed.
    post_decoding_rules: dict[str, list[tuple[int, Callable]]]
    all_counterparties: set['CounterpartyDetails']
    addresses_to_counterparties: dict[ChecksumEvmAddress, str]

    def __add__(self, other: 'DecodingRules') -> 'DecodingRules':
        if not isinstance(other, DecodingRules):
            raise TypeError(
                f'Can only add DecodingRules to DecodingRules. Got {type(other)}',
            )

        intersection = set(other.input_data_rules).intersection(set(self.input_data_rules))
        if len(intersection) != 0:
            raise ValueError(f'Input data duplicates found in decoding rules for {intersection}')

        return DecodingRules(
            address_mappings=self.address_mappings | other.address_mappings,
            event_rules=self.event_rules + other.event_rules,
            input_data_rules=self.input_data_rules | other.input_data_rules,
            token_enricher_rules=self.token_enricher_rules + other.token_enricher_rules,
            post_decoding_rules=self.post_decoding_rules | other.post_decoding_rules,
            all_counterparties=self.all_counterparties | other.all_counterparties,
            addresses_to_counterparties=self.addresses_to_counterparties | other.addresses_to_counterparties,  # noqa: E501
        )


class EVMTransactionDecoder(ABC):

    def __init__(
            self,
            database: 'DBHandler',
            evm_inquirer: 'EvmNodeInquirer',
            transactions: 'EvmTransactions',
            value_asset: 'AssetWithOracles',
            event_rules: list[EventDecoderFunction],
            misc_counterparties: list[CounterpartyDetails],
            base_tools: BaseDecoderTools,
            dbevmtx_class: type[DBEvmTx] = DBEvmTx,
            addresses_exceptions: dict[ChecksumEvmAddress, int] | None = None,
            beacon_chain: 'BeaconChain | None' = None,
    ):
        """
        Initialize an evm chain transaction decoder module for a particular chain.

        `value_asset` is the asset that is normally transferred at value transfers
        and the one that is spent for gas in this chain

        `event_rules` is a list of callables to act as decoding rules for all tx
        receipt logs decoding for the particular chain

        `misc_counterparties` is a list of counterparties not associated with any specific
        decoder that should be included for this decoder modules.

        `addresses_exceptions` is a dict of address to the block number at which we should start
        ignoring transfers for that address. It was introduced to ignore events for monerium
        legacy tokens.
        """
        self.database = database
        self.misc_counterparties = [CounterpartyDetails(identifier=CPT_GAS, label='gas', icon='lu-flame')] + misc_counterparties  # noqa: E501
        self.evm_inquirer = evm_inquirer
        self.transactions = transactions
        self.beacon_chain = beacon_chain
        self.msg_aggregator = database.msg_aggregator
        self.chain_modules_root = f'rotkehlchen.chain.{self.evm_inquirer.chain_name}.modules'
        self.chain_modules_prefix_length = len(self.chain_modules_root)
        self.dbevmtx = dbevmtx_class(self.database)
        self.dbevents = DBHistoryEvents(self.database)
        self.base = base_tools
        self.rules = DecodingRules(
            address_mappings={},
            event_rules=[
                self._maybe_decode_erc20_approve,
                self._maybe_decode_erc20_721_transfer,
            ],
            input_data_rules={},
            token_enricher_rules=[],
            post_decoding_rules={},
            all_counterparties=set(self.misc_counterparties),
            addresses_to_counterparties={},
        )
        self.rules.event_rules.extend(event_rules)
        self.value_asset = value_asset
        self.decoders: dict[str, DecoderInterface] = {}
        self.addresses_exceptions = addresses_exceptions or {}

        # Add the built-in decoders
        self._add_builtin_decoders(self.rules)
        # Recursively check all submodules to get all decoder address mappings and rules
        self.rules += self._recursively_initialize_decoders(self.chain_modules_root)
        self.undecoded_tx_query_lock = Semaphore()

    def _add_builtin_decoders(self, rules: DecodingRules) -> None:
        """Adds decoders that should be built-in for every EVM decoding run

        Think: Perhaps we can move them under a specific directory and use the
        normal loading?
        """
        self._add_single_decoder(class_name='Safemultisig', decoder_class=SafemultisigDecoder, rules=rules)  # noqa: E501
        self._add_single_decoder(class_name='Oneinchv5', decoder_class=Oneinchv5Decoder, rules=rules)  # noqa: E501
        self._add_single_decoder(class_name='Oneinchv6', decoder_class=Oneinchv6Decoder, rules=rules)  # noqa: E501
        self._add_single_decoder(class_name='SocketBridgeDecoder', decoder_class=SocketBridgeDecoder, rules=rules)  # noqa: E501
        self._add_single_decoder(class_name='OpenOcean', decoder_class=OpenOceanDecoder, rules=rules)  # noqa: E501
        self._add_single_decoder(class_name='BeefyFinance', decoder_class=BeefyFinanceCommonDecoder, rules=rules)  # noqa: E501

        # Excluding Gnosis and Polygon PoS because they dont have ETH as native token
        # Also arb and scroll because they don't follow the weth9 design
        if self.evm_inquirer.chain_id not in CHAINS_WITHOUT_NATIVE_ETH | CHAINS_WITH_SPECIAL_WETH:
            self._add_single_decoder(
                class_name='Weth',
                decoder_class=WethDecoder,
                rules=rules,
            )

        # Add the Rainbow decoder if the chain is supported
        if self.evm_inquirer.chain_id in RAINBOW_SUPPORTED_CHAINS:
            self._add_single_decoder(
                class_name='RainbowDecoder',
                decoder_class=RainbowDecoder,
                rules=rules,
            )

        if self.evm_inquirer.chain_id in PENDLE_SUPPORTED_CHAINS_WITHOUT_ETHEREUM:
            self._add_single_decoder(
                class_name='Pendle',
                decoder_class=PendleCommonDecoder,
                rules=rules,
            )

        if self.evm_inquirer.chain_id in STAKEDAO_SUPPORTED_CHAINS_WITHOUT_CLAIMS:
            self._add_single_decoder(
                class_name='Stakedao',
                decoder_class=StakedaoCommonDecoder,
                rules=rules,
            )

    def _add_single_decoder(
            self,
            class_name: str,
            decoder_class: type['DecoderInterface'],
            rules: DecodingRules,
    ) -> None:
        """Initialize a single decoder, add it to the set of decoders to use
        and append its rules to the passed rules
        """
        if class_name in self.decoders:
            raise ModuleLoadingError(f'{self.evm_inquirer.chain_name} decoder with name {class_name} already loaded')  # noqa: E501

        extra_args = []
        if class_name == 'Eth2':
            extra_args.append(self.beacon_chain)

        try:  # not giving kwargs since, kwargs name can differ
            self.decoders[class_name] = decoder_class(
                self.evm_inquirer,  # evm_inquirer
                self.base,  # base_tools
                self.msg_aggregator,  # msg_aggregator
                *extra_args,
            )
        except (UnknownAsset, WrongAssetType) as e:
            self.msg_aggregator.add_error(
                f'Failed at initialization of {self.evm_inquirer.chain_name} '
                f'{class_name} decoder due to asset mismatch: {e!s}',
            )
            return
        except (NotERC721Conformant, NotERC20Conformant):
            self.msg_aggregator.add_error(
                f'Failed at initialization of {self.evm_inquirer.chain_name} '
                f'{class_name} decoder due to non conformant token',
            )
            return

        new_input_data_rules = self.decoders[class_name].decoding_by_input_data()
        new_address_to_decoders = self.decoders[class_name].addresses_to_decoders()
        new_address_to_counterparties = self.decoders[class_name].addresses_to_counterparties()

        if __debug__:  # sanity checks for now only in debug as decoders are constant
            for new_struct, main_struct, type_name in (
                    (new_input_data_rules, rules.input_data_rules, 'input_data_rules'),
                    (new_address_to_decoders, rules.address_mappings, 'address_mappings'),
                    (new_address_to_counterparties, rules.addresses_to_counterparties, 'address_to_counterparties'),  # noqa: E501
            ):
                self.assert_keys_are_unique(new_struct=new_struct, main_struct=main_struct, class_name=class_name, type_name=type_name)  # noqa: E501

        rules.address_mappings.update(new_address_to_decoders)
        rules.event_rules.extend(self.decoders[class_name].decoding_rules())
        rules.input_data_rules.update(new_input_data_rules)
        rules.token_enricher_rules.extend(self.decoders[class_name].enricher_rules())
        rules.post_decoding_rules.update(self.decoders[class_name].post_decoding_rules())
        rules.all_counterparties.update(self.decoders[class_name].counterparties())
        rules.addresses_to_counterparties.update(new_address_to_counterparties)
        self._chain_specific_decoder_initialization(self.decoders[class_name])

    def _recursively_initialize_decoders(
            self,
            package: str | ModuleType,
    ) -> DecodingRules:
        if isinstance(package, str):
            package = importlib.import_module(package)

        rules = DecodingRules(
            address_mappings={},
            event_rules=[],
            input_data_rules={},
            token_enricher_rules=[],
            post_decoding_rules={},
            all_counterparties=set(),
            addresses_to_counterparties={},
        )

        for _, name, is_pkg in pkgutil.walk_packages(package.__path__):
            full_name = package.__name__ + '.' + name
            if full_name == __name__ or is_pkg is False:
                continue  # skip

            submodule = None
            with suppress(ModuleNotFoundError):
                submodule = importlib.import_module(full_name + '.decoder')

            if submodule is not None:
                # take module name, transform it and find decoder if exists
                class_name = full_name[self.chain_modules_prefix_length:].translate({ord('.'): None})  # noqa: E501
                parts = class_name.split('_')
                class_name = ''.join([x.capitalize() for x in parts])
                submodule_decoder = getattr(submodule, f'{class_name}Decoder', None)

                if submodule_decoder:
                    self._add_single_decoder(class_name=class_name, decoder_class=submodule_decoder, rules=rules)  # noqa: E501

            if is_pkg:
                recursive_results = self._recursively_initialize_decoders(full_name)
                rules += recursive_results

        return rules

    def get_decoders_products(self) -> dict[str, list[EvmProduct]]:
        """Get the list of possible products"""
        possible_products: dict[str, list[EvmProduct]] = {}
        for decoder in self.decoders.values():
            possible_products |= decoder.possible_products()

        return possible_products

    def _reload_single_decoder(self, cursor: 'DBCursor', decoder: 'DecoderInterface') -> None:
        """Reload data for a single decoder"""
        if isinstance(decoder, CustomizableDateMixin):
            decoder.reload_settings(cursor)
        if isinstance(decoder, ReloadableDecoderMixin):
            try:
                new_mappings = decoder.reload_data()
            except RemoteError as e:
                counterparty = decoder.counterparties()[0].label
                log.error(f'Failed to query remote information for {counterparty} due to {e}')
                self.msg_aggregator.add_error(
                    f'Failed to update cache for {counterparty} due to a '
                    'network error. A re-decoding might be required if information '
                    'was not up to date.',
                )
                return

            if new_mappings is not None:
                self.rules.address_mappings.update(new_mappings)
                self.rules.addresses_to_counterparties.update(decoder.addresses_to_counterparties())

    def reload_data(self, cursor: 'DBCursor') -> None:
        """Reload all related settings from DB and data that any decoder may require from the chain
        so that decoding happens with latest data
        """
        self.base.refresh_tracked_accounts(cursor)
        for decoder in self.decoders.values():
            self._reload_single_decoder(cursor, decoder)

    def reload_specific_decoders(self, cursor: 'DBCursor', decoders: set[str]) -> None:
        """Reload DB data for the given decoders. Decoders are identified by the class name
        (without the Decoder suffix)
        """
        self.base.refresh_tracked_accounts(cursor)
        for decoder_name in decoders:
            if (decoder := self.decoders.get(decoder_name)) is None:
                log.error(f'Requested reloading of data for unknown {self.evm_inquirer.chain_name} decoder {decoder_name}')  # noqa: E501
                continue

            self._reload_single_decoder(cursor, decoder)

    def try_all_rules(
            self,
            token: 'EvmToken | None',
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            action_items: list[ActionItem],
            all_logs: list[EvmTxReceiptLog],
    ) -> DecodingOutput | None:
        """
        Execute event rules for the current tx log. Returns None when no
        new event or actions need to be propagated.
        """
        for rule in self.rules.event_rules:
            if len(tx_log.topics) == 0:
                continue  # ignore anonymous events

            decoding_output, err = decode_safely(
                msg_aggregator=self.msg_aggregator,
                tx_hash=transaction.tx_hash,
                chain_id=transaction.chain_id,
                func=rule,
                token=token,
                tx_log=tx_log,
                transaction=transaction,
                decoded_events=decoded_events,
                action_items=action_items,
                all_logs=all_logs,
            )
            if err:
                continue

            if (
                decoding_output.event is not None or
                len(decoding_output.action_items) > 0 or
                decoding_output.process_swaps
            ):
                return decoding_output

        return None

    def decode_by_address_rules(self, context: DecoderContext) -> DecodingOutput:
        """
        Sees if the log is on an address for which we have specific decoders and calls it

        Should catch all underlying errors these decoders will raise. So far known are:
        - DeserializationError
        - ConversionError
        - UnknownAsset
        """
        mapping_result = self.rules.address_mappings.get(context.tx_log.address)
        if mapping_result is None:
            return DEFAULT_DECODING_OUTPUT

        method, *args = mapping_result
        result, err = decode_safely(  # can't used named arguments with *args
            self.msg_aggregator,
            context.transaction.tx_hash,
            context.transaction.chain_id,
            method,
            *(context, *args),
        )
        if err:
            return DEFAULT_DECODING_OUTPUT

        return result

    def run_all_post_decoding_rules(
            self,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            all_logs: list[EvmTxReceiptLog],
            counterparties: set[str],
    ) -> tuple[list['EvmEvent'], bool]:
        """
        The post-decoding rules list consists of tuples (priority, rule) and must be
        sorted by priority in ascending order. The higher the priority number the later
        the rule is run.
        Matches post decoding rules to all matched counterparties propagated for decoding
        from the decoding/enriching rules and also the counterparties associated with the
        transaction to_address field.
        Returns a tuple containing the list of decoded events and a boolean flag indicating
        whether any post-decoding rules ran successfully and may have modified the events.
        """
        maybe_modified = False
        if transaction.to_address is not None:
            address_counterparty = self.rules.addresses_to_counterparties.get(transaction.to_address)  # noqa: E501
            if address_counterparty is not None:
                counterparties.add(address_counterparty)

        rules = self._chain_specific_post_decoding_rules(transaction)
        # get the rules that need to be applied by counterparty
        for counterparty in counterparties:
            new_rules = self.rules.post_decoding_rules.get(counterparty)
            if new_rules is not None:
                rules.extend(new_rules)

        # Sort post decoding rules by priority (which is the first element of the tuple)
        rules.sort(key=operator.itemgetter(0))
        for _, rule in rules:
            result_events, is_err = decode_safely(
                msg_aggregator=self.msg_aggregator,
                tx_hash=transaction.tx_hash,
                chain_id=transaction.chain_id,
                func=rule,
                transaction=transaction,
                decoded_events=decoded_events,
                all_logs=all_logs,
            )
            if not is_err:  # post decoding appends and returns to decoded events if successful
                maybe_modified = True
                decoded_events = result_events
                if len(result_events) > len(decoded_events):
                    break  # an event was added, so let's break out of post decoding

        return decoded_events, maybe_modified

    @staticmethod
    def _process_swaps(
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
    ) -> list['EvmEvent']:
        """Convert EvmEvents with event_type of TRADE into EvmSwapEvents.

        Assumes that the decoding logic has already ordered the sequence indexes of trade events
        in the correct spend/receive/fee order with no other events between them (although the
        indexes do not need to be consecutive). If an incomplete or unordered group of Trade events
        is encountered an error will be logged and the original EvmEvents saved to the db.

        If a swap has multiple spend receive or fee events, then the event_type will be set to
        MULTI_TRADE for all the events in the swap.

        Returns the list of decoded events ordered by sequence index with any complete groups
        of trade events replaced with EvmSwapEvents.
        """
        processed_events = []
        trade_subtypes = (HistoryEventSubType.SPEND, HistoryEventSubType.RECEIVE, HistoryEventSubType.FEE)  # noqa: E501
        events_iterator = peekable(iter(decoded_events))
        while (next_event := events_iterator.peek(None)) is not None:
            if (
                next_event.event_type != HistoryEventType.TRADE or
                next_event.event_subtype not in trade_subtypes
            ):  # event is not part of a swap - save it and continue
                processed_events.append(next(events_iterator))
                continue

            trade_events: list[EvmEvent] = []
            event_type = HistoryEventType.TRADE
            for subtype in trade_subtypes:
                subtype_events = []
                while (
                    (next_event := events_iterator.peek(None)) is not None and
                    next_event.event_type == HistoryEventType.TRADE and
                    next_event.event_subtype == subtype
                ):  # match events in the order defined in trade_subtypes
                    subtype_events.append(next(events_iterator))

                if len(subtype_events) > 1:
                    event_type = HistoryEventType.MULTI_TRADE
                elif len(subtype_events) == 0 and subtype != HistoryEventSubType.FEE:  # if no spend or receive was found then the group is incomplete or out of order.  # noqa: E501
                    # If no events yet (failed on SPEND), save next(events_iterator), so that
                    # we move on to the event after in the next while loop iteration.
                    # If some events (failed on RECEIVE), save only the already matched
                    # trade_events so the next event (could be the SPEND of another group) will be
                    # reprocessed in the next iteration of the main while loop.
                    processed_events.extend(trade_events if len(trade_events) > 0 else [next(events_iterator)])  # noqa: E501
                    log.error(
                        'Encountered incomplete or unordered swap event group '
                        f'{trade_events + [next_event]} in transaction {transaction!s}',
                    )
                    trade_events = []
                    break

                trade_events.extend(subtype_events)

            if len(trade_events) == 0:
                continue  # swap group was incomplete or unordered.

            spend_event = trade_events[0]
            for idx, trade_event in enumerate(trade_events):
                swap_event = EvmSwapEvent(
                    tx_hash=trade_event.tx_hash,
                    sequence_index=spend_event.sequence_index + idx,  # Make indexes consecutive (required for retrieving the receive and fee events when editing a swap event group via the api).  # noqa: E501
                    timestamp=trade_event.timestamp,
                    location=trade_event.location,
                    event_type=event_type,  # type: ignore[arg-type]  # will be TRADE or MULTI_TRADE
                    event_subtype=trade_event.event_subtype,  # type: ignore[arg-type]  # will be SPEND, RECEIVE, or FEE
                    asset=trade_event.asset,
                    amount=trade_event.amount,
                    notes=trade_event.notes,
                    extra_data=trade_event.extra_data,
                    # location label can be different on the spend versus the receive, but if its
                    # missing, fall back to setting it from the spend event.
                    location_label=trade_event.location_label if trade_event.location_label is not None else spend_event.location_label,  # noqa: E501
                    # the rest should be the same for the whole group, so set from the spend event.
                    counterparty=spend_event.counterparty,
                    product=spend_event.product,
                    address=spend_event.address,
                )
                processed_events.append(swap_event)

        return processed_events

    def _decode_transaction(
            self,
            transaction: EvmTransaction,
            tx_receipt: EvmTxReceipt,
    ) -> tuple[list['EvmEvent'], bool, set[str] | None]:
        """
        Decodes an evm transaction and its receipt and saves result in the DB.

        Returns
        - the list of decoded events
        - a flag which is True if balances refresh is needed
        - A list of decoders to reload or None if no need
        """
        log.debug(f'Starting decoding of transaction {transaction.tx_hash.hex()} logs at {self.evm_inquirer.chain_name}')  # noqa: E501
        with self.database.conn.read_ctx() as read_cursor:
            tx_id = transaction.get_or_query_db_id(read_cursor)

        self.base.reset_sequence_counter(tx_receipt)
        # check if any eth transfer happened in the transaction, including in internal transactions
        events = self._maybe_decode_simple_transactions(transaction, tx_receipt)
        action_items: list[ActionItem] = []
        counterparties = set()
        refresh_balances = False
        reload_decoders = None
        process_swaps = False

        # Check if any rules should run due to the 4bytes signature of the input data
        fourbytes = transaction.input_data[:4]
        input_data_rules = self.rules.input_data_rules.get(fourbytes)
        monerium_special_handling_event = False
        # decode transaction logs from the receipt
        for idx, tx_log in enumerate(tx_receipt.logs):
            if (
                monerium_special_handling_event is False and
                self.evm_inquirer.chain_id in {ChainID.GNOSIS, ChainID.POLYGON_POS} and
                (block_number := self.addresses_exceptions.get(tx_log.address)) is not None and
                block_number < transaction.block_number
            ):
                # for the special case of monerium tokens detect while iterating over the log
                # events if we have in the transaction a legacy transfer and set the flag.
                # We use this flag to avoid iterating twice over the events searching
                # for legacy transfers.
                monerium_special_handling_event = True

            if (idx + 1) % MIN_LOGS_PROCESSED_TO_SLEEP == 0:
                log.debug(f'Context switching out of the log event nr. {idx + 1} of {self.evm_inquirer.chain_name} {transaction}')  # noqa: E501
                gevent.sleep(0)

            context = DecoderContext(
                tx_log=tx_log,
                transaction=transaction,
                decoded_events=events,
                all_logs=tx_receipt.logs,
                action_items=action_items,
            )
            if input_data_rules and len(tx_log.topics) != 0 and (input_rule := input_data_rules.get(tx_log.topics[0])) is not None:  # noqa: E501
                result, is_err = decode_safely(
                    msg_aggregator=self.msg_aggregator,
                    tx_hash=context.transaction.tx_hash,
                    chain_id=context.transaction.chain_id,
                    func=input_rule,
                    context=context,
                )
                if not is_err and result.event:
                    events.append(result.event)
                    continue  # since the input data rule found an event for this log

            decoding_output = self.decode_by_address_rules(context)
            if decoding_output.refresh_balances is True:
                refresh_balances = True
            if decoding_output.reload_decoders is not None:
                reload_decoders = decoding_output.reload_decoders
            if decoding_output.process_swaps:
                process_swaps = True

            action_items.extend(decoding_output.action_items)
            if decoding_output.matched_counterparty is not None:
                counterparties.add(decoding_output.matched_counterparty)
            if decoding_output.event:
                events.append(decoding_output.event)
                continue

            rules_decoding_output = self.try_all_rules(
                token=get_token(evm_address=tx_log.address, chain_id=self.evm_inquirer.chain_id),
                tx_log=tx_log,
                transaction=transaction,
                decoded_events=events,
                action_items=action_items,
                all_logs=tx_receipt.logs,
            )
            if rules_decoding_output is not None:
                if rules_decoding_output.refresh_balances is True:
                    refresh_balances = True
                action_items.extend(rules_decoding_output.action_items)
                if rules_decoding_output.matched_counterparty is not None:
                    counterparties.add(rules_decoding_output.matched_counterparty)
                if rules_decoding_output.event is not None:
                    events.append(rules_decoding_output.event)
                if rules_decoding_output.process_swaps:
                    process_swaps = True

        if monerium_special_handling_event is True:
            # When events that need special handling exist iterate over the decoded events and
            # exchange the legacy assets by the v2 assets. Also delete v2 events to
            # avoid duplications. In the case of this exception handling, v2 events exist only
            # for the case of interacting with the v1 tokens since interacting
            # with v2 doesn't emit v1 transfers.
            replacement_assets = self.base.exceptions_mappings.values()
            potential_duplicates_map = defaultdict(list)
            for event in events:
                if (replacement := self.base.exceptions_mappings.get(event.asset.identifier)) is not None:  # noqa: E501
                    event.asset = replacement  # otherwise change the asset
                    potential_duplicates_map[replacement, event.amount, event.maybe_get_direction()].append(event)  # noqa: E501

                elif event.asset.identifier in replacement_assets:
                    potential_duplicates_map[event.asset, event.amount, event.maybe_get_direction()].append(event)  # noqa: E501

            eventids_to_remove = set()
            for potential_duplicates in potential_duplicates_map.values():
                if len(potential_duplicates) != 2:
                    continue

                if (
                        potential_duplicates[0].asset == potential_duplicates[1].asset and
                        potential_duplicates[0].amount == potential_duplicates[1].amount and
                        potential_duplicates[0].event_type == potential_duplicates[1].event_type and  # noqa: E501
                        potential_duplicates[0].event_subtype == potential_duplicates[1].event_subtype and  # noqa: E501
                        potential_duplicates[0].counterparty == potential_duplicates[1].counterparty  # noqa: E501
                ):
                    eventids_to_remove.add(potential_duplicates[0].sequence_index)
                    continue

                # else just choose the one that has not been decoded
                for duplicate in potential_duplicates:
                    if duplicate.counterparty is not None:
                        continue  # keep events that have been decoded properly

                    eventids_to_remove.add(duplicate.sequence_index)  # using sequence index since identifier does not exist here  # noqa: E501
                    break

            new_events = [x for x in events if x.sequence_index not in eventids_to_remove]
            events = new_events

        # should run after monerium special handling as in paraswap decoder, during post-decoding,
        # the extra EURe event receive is seen as a receival
        events, maybe_modified = self.run_all_post_decoding_rules(
            transaction=transaction,
            decoded_events=events,
            all_logs=tx_receipt.logs,
            counterparties=counterparties,
        )
        if maybe_modified:
            process_swaps = True  # a swap may have been created in post decoding

        if len(events) == 0 and (eth_event := self._get_eth_transfer_event(transaction)) is not None:  # noqa: E501
            events = [eth_event]

        # Process swaps after the monerium handling to avoid interpreting duplicate
        # transfers as part of a multi swap.
        events = sorted(events, key=lambda x: x.sequence_index, reverse=False)
        if process_swaps:
            events = self._process_swaps(transaction=transaction, decoded_events=events)

        if (
                tx_receipt.tx_type == 4 and
                transaction.from_address == transaction.to_address and
                transaction.authorization_list is not None
        ):  # if the event is an eip-7702 transaction, we need to add an informational event.
            if (delegated_address := transaction.authorization_list[-1].delegated_address) == ZERO_ADDRESS:  # noqa: E501
                notes = f'Revoke account delegation for {transaction.from_address}'
            else:
                notes = f'Execute account delegation to {delegated_address}'

            events.append(self.base.make_event(
                tx_hash=transaction.tx_hash,
                sequence_index=self.base.get_next_sequence_index(),
                timestamp=transaction.timestamp,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.DELEGATE,
                asset=self.value_asset,
                amount=ZERO,
                location_label=transaction.from_address,
                address=delegated_address,
                notes=notes,
                counterparty=CPT_ACCOUNT_DELEGATION,
            ))

        with self.database.user_write() as write_cursor:
            if len(events) > 0:
                self.dbevents.add_history_events(
                    write_cursor=write_cursor,
                    history=events,
                )
            else:
                # This is probably a phishing zero value token transfer tx.
                # Details here: https://github.com/rotki/rotki/issues/5749
                with suppress(InputError):  # We don't care if it's already in the DB
                    self.database.add_to_ignored_action_ids(
                        write_cursor=write_cursor,
                        identifiers=[transaction.identifier],
                    )

            write_cursor.execute(
                'INSERT OR IGNORE INTO evm_tx_mappings(tx_id, value) VALUES(?, ?)',
                (tx_id, EVMTX_DECODED),
            )

        return events, refresh_balances, reload_decoders  # Propagate for post processing in the caller  # noqa: E501

    def get_and_decode_undecoded_transactions(
            self,
            limit: int | None = None,
            send_ws_notifications: bool = False,
    ) -> None:
        """Checks the DB for up to `limit` undecoded transactions and decodes them.
        If a list of addresses is provided then only the transactions involving those
        addresses are decoded.

        This is protected by concurrent access from a lock"""
        with self.undecoded_tx_query_lock:
            log.debug(f'Starting task to process undecoded transactions for {self.evm_inquirer.chain_name} with {limit=}')  # noqa: E501
            hashes = self.dbevmtx.get_transaction_hashes_not_decoded(
                chain_id=self.evm_inquirer.chain_id,
                limit=limit,
            )
            if len(hashes) != 0:
                log.debug(f'Will decode {len(hashes)} transactions for {self.evm_inquirer.chain_name}')  # noqa: E501
                self.decode_transaction_hashes(
                    ignore_cache=False,
                    tx_hashes=hashes,
                    send_ws_notifications=send_ws_notifications,
                )
            log.debug(f'Finished task to process undecoded transactions for {self.evm_inquirer.chain_name} with {limit=}')  # noqa: E501

    def decode_and_get_transaction_hashes(
            self,
            ignore_cache: bool,
            tx_hashes: list[EVMTxHash],
            send_ws_notifications: bool = False,
            delete_customized: bool = False,
    ) -> list['EvmEvent']:
        """
        Thin wrapper around _decode_transaction_hashes that returns the decoded events.

        May raise:
        - DeserializationError if there is a problem with contacting a remote to get receipts
        - RemoteError if there is a problem with contacting a remote to get receipts
        - InputError if the transaction hash is not found in the DB
        """
        events: list[EvmEvent] = []
        self._decode_transaction_hashes(
            ignore_cache=ignore_cache,
            tx_hashes=tx_hashes,
            events=events,
            send_ws_notifications=send_ws_notifications,
            delete_customized=delete_customized,
        )
        return events

    def decode_transaction_hashes(
            self,
            ignore_cache: bool,
            tx_hashes: list[EVMTxHash],
            send_ws_notifications: bool = False,
            delete_customized: bool = False,
    ) -> None:
        """
        Thin wrapper around _decode_transaction_hashes that ignores decoded events

        May raise:
        - DeserializationError if there is a problem with contacting a remote to get receipts
        - RemoteError if there is a problem with contacting a remote to get receipts
        - InputError if the transaction hash is not found in the DB
        """
        self._decode_transaction_hashes(
            ignore_cache=ignore_cache,
            tx_hashes=tx_hashes,
            events=None,
            send_ws_notifications=send_ws_notifications,
            delete_customized=delete_customized,
        )

    def _decode_transaction_hashes(
            self,
            ignore_cache: bool,
            tx_hashes: list[EVMTxHash],
            events: list['EvmEvent'] | None = None,
            send_ws_notifications: bool = False,
            delete_customized: bool = False,
    ) -> None:
        """Make sure that receipts are pulled + events decoded for the given transaction hashes.
        If delete_customized is True then also customized events are deleted before redecoding.

        The transaction hashes must exist in the DB at the time of the call.
        This logic modifies the `events` argument if it isn't none.

        May raise:
        - DeserializationError if there is a problem with contacting a remote to get receipts
        - RemoteError if there is a problem with contacting a remote to get receipts
        - InputError if the transaction hash is not found in the DB
        """
        with self.database.conn.read_ctx() as cursor:
            self.reload_data(cursor)

        refresh_balances = False
        total_transactions = len(tx_hashes)
        log.debug(f'Started logic to decode {total_transactions} transactions from {self.evm_inquirer.chain_id}')  # noqa: E501
        for tx_index, tx_hash in enumerate(tx_hashes):
            log.debug(f'Decoding logic started for {tx_hash.hex()} ({self.evm_inquirer.chain_name})')  # noqa: E501
            if send_ws_notifications and tx_index % 10 == 0:
                log.debug(f'Processed {tx_index} out of {total_transactions} transactions from {self.evm_inquirer.chain_id}')  # noqa: E501
                self.msg_aggregator.add_message(
                    message_type=WSMessageType.PROGRESS_UPDATES,
                    data={
                        'chain': self.evm_inquirer.chain_name,
                        'subtype': str(ProgressUpdateSubType.EVM_UNDECODED_TRANSACTIONS),
                        'total': total_transactions,
                        'processed': tx_index,
                    },
                )

            # TODO: Change this if transaction filter query can accept multiple hashes
            with self.database.conn.read_ctx() as cursor:
                try:
                    tx, receipt = self.transactions.get_or_create_transaction(
                        cursor=cursor,
                        tx_hash=tx_hash,
                        relevant_address=None,
                    )
                except RemoteError as e:
                    raise InputError(f'{self.evm_inquirer.chain_name} hash {tx_hash.hex()} does not correspond to a transaction. {e}') from e  # noqa: E501

            new_events, new_refresh_balances, reload_decoders = self._get_or_decode_transaction_events(  # noqa: E501
                transaction=tx,
                tx_receipt=receipt,
                ignore_cache=ignore_cache,
                delete_customized=delete_customized,
            )

            if events is not None:
                events.extend(new_events)

            if new_refresh_balances is True:
                refresh_balances = True

            if reload_decoders is not None:
                with self.database.conn.read_ctx() as cursor:
                    self.reload_specific_decoders(cursor, decoders=reload_decoders)

        if send_ws_notifications:
            self.msg_aggregator.add_message(
                message_type=WSMessageType.PROGRESS_UPDATES,
                data={
                    'chain': self.evm_inquirer.chain_name,
                    'subtype': str(ProgressUpdateSubType.EVM_UNDECODED_TRANSACTIONS),
                    'total': total_transactions,
                    'processed': total_transactions,
                },
            )

        self._post_process(refresh_balances=refresh_balances)
        maybe_detect_new_tokens(self.database)

    def _get_or_decode_transaction_events(
            self,
            transaction: EvmTransaction,
            tx_receipt: EvmTxReceipt,
            ignore_cache: bool,
            delete_customized: bool = False,
    ) -> tuple[list['EvmEvent'], bool, set[str] | None]:
        """
        Get a transaction's events if existing in the DB or decode them.
        Returns:
        - the list of decoded events
        - a flag which is True if balances refresh is needed
        - A list of decoders to reload or None if no need
        """
        with self.database.conn.read_ctx() as cursor:
            tx_id = transaction.get_or_query_db_id(cursor)

        if ignore_cache is True:  # delete all decoded events
            with self.database.user_write() as write_cursor:
                self.dbevents.delete_events_by_tx_hash(
                    write_cursor=write_cursor,
                    tx_hashes=[transaction.tx_hash],
                    location=Location.from_chain_id(self.evm_inquirer.chain_id),
                    delete_customized=delete_customized,
                )
                write_cursor.execute(
                    'DELETE from evm_tx_mappings WHERE tx_id=? AND value IN (?, ?)',
                    (tx_id, EVMTX_DECODED, EVMTX_SPAM),
                )
        else:  # see if events are already decoded and return them
            with self.database.conn.read_ctx() as cursor:
                cursor.execute(
                    'SELECT COUNT(*) from evm_tx_mappings WHERE tx_id=? AND value=?',
                    (tx_id, EVMTX_DECODED),
                )
                if cursor.fetchone()[0] != 0:  # already decoded and in the DB
                    events = self.dbevents.get_history_events(
                        cursor=cursor,
                        filter_query=EvmEventFilterQuery.make(
                            tx_hashes=[transaction.tx_hash],
                        ),
                        has_premium=True,  # for this function we don't limit anything
                    )
                    return events, False, None

        # else we should decode now
        return self._decode_transaction(transaction=transaction, tx_receipt=tx_receipt)

    def _maybe_decode_internal_transactions(
            self,
            tx: EvmTransaction,
            tx_receipt: EvmTxReceipt,
            events: list['EvmEvent'],
    ) -> None:
        """
        check for internal transactions if the transaction is not canceled. This function mutates
        the events argument.
        """
        if tx_receipt.status is False:
            return

        internal_txs = self.dbevmtx.get_evm_internal_transactions(
            parent_tx_hash=tx.tx_hash,
            blockchain=self.evm_inquirer.blockchain,
        )
        for internal_tx in internal_txs:
            if internal_tx.to_address is None:
                continue  # can that happen? Internal transaction deploying a contract?
            direction_result = self.base.decode_direction(
                from_address=internal_tx.from_address,
                to_address=internal_tx.to_address,
            )
            if direction_result is None:
                continue

            amount = ZERO if internal_tx.value == 0 else from_wei(FVal(internal_tx.value))
            if amount == ZERO:
                continue

            event_type, event_subtype, location_label, address, counterparty, verb = direction_result  # noqa: E501
            counterparty_or_address = counterparty or address
            preposition = 'to' if event_type in OUTGOING_EVENT_TYPES else 'from'
            events.append(self.base.make_event(
                tx_hash=tx.tx_hash,
                sequence_index=self.base.get_next_sequence_index_pre_decoding(),
                timestamp=tx.timestamp,
                event_type=event_type,
                event_subtype=event_subtype,
                asset=self.value_asset,
                amount=amount,
                location_label=location_label,
                notes=f'{verb} {amount} {self.value_asset.symbol} {preposition} {counterparty_or_address}',  # noqa: E501
                address=address,
                counterparty=counterparty,
            ))

    def _get_eth_transfer_event(self, tx: EvmTransaction) -> Optional['EvmEvent']:
        direction_result = self.base.decode_direction(
            from_address=tx.from_address,
            to_address=tx.to_address,
        )
        if direction_result is None:
            return None
        event_type, event_subtype, location_label, address, counterparty, verb = direction_result
        counterparty_or_address = counterparty or address
        amount = ZERO if tx.value == 0 else from_wei(FVal(tx.value))
        preposition = 'to' if event_type in OUTGOING_EVENT_TYPES else 'from'
        return self.base.make_event(
            tx_hash=tx.tx_hash,
            sequence_index=self.base.get_next_sequence_index_pre_decoding(),
            timestamp=tx.timestamp,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=self.value_asset,
            amount=amount,
            location_label=location_label,
            notes=f'{verb} {amount} {self.value_asset.symbol} {preposition} {counterparty_or_address}',  # noqa: E501
            address=address,
            counterparty=counterparty,
        )

    def _get_transfer_or_approval_token_kind_and_id(
            self,
            tx_log: EvmTxReceiptLog,
    ) -> tuple[EvmTokenKind, str | None] | None:
        """Determine if a transfer or approval event is for an erc20 or erc721 token.
        Returns the token kind and id (or None for erc20) in a tuple, or None on error."""
        if self._is_non_conformant_erc721(tx_log.address):
            return EvmTokenKind.ERC721, str(int.from_bytes(tx_log.data[0:32]))  # token_id is in data  # noqa: E501
        elif len(tx_log.topics) == 3:  # typical ERC20 has 2 indexed args
            return EvmTokenKind.ERC20, None  # no token_id for erc20
        elif len(tx_log.topics) == 4:  # typical ERC721 has 3 indexed args
            return EvmTokenKind.ERC721, str(int.from_bytes(tx_log.topics[3]))  # token_id is in topics  # noqa: E501
        else:
            log.debug(f'Failed to decode token with address {tx_log.address} due to inability to match token type')  # noqa: E501
            return None

    def _maybe_decode_erc20_approve(
            self,
            token: 'EvmToken | None',
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],  # pylint: disable=unused-argument
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> DecodingOutput:
        if (
            tx_log.topics[0] != ERC20_OR_ERC721_APPROVE or
            (token_kind_and_id := self._get_transfer_or_approval_token_kind_and_id(tx_log=tx_log)) is None  # noqa: E501
        ):
            return DEFAULT_DECODING_OUTPUT

        token_kind, collectible_id = token_kind_and_id
        if len(tx_log.topics) in (3, 4):
            owner_address = bytes_to_address(tx_log.topics[1])
            spender_address = bytes_to_address(tx_log.topics[2])
            amount_raw = int.from_bytes(tx_log.data)
        elif len(tx_log.topics) == 1 and len(tx_log.data) == 96:  # malformed erc20 approve (finance.vote)  # noqa: E501
            owner_address = bytes_to_address(tx_log.data[:32])
            spender_address = bytes_to_address(tx_log.data[32:64])
            amount_raw = int.from_bytes(tx_log.data[64:])
        else:
            log.debug(
                f'Got an ERC20 approve event with unknown structure '
                f'in transaction {transaction.tx_hash.hex()}',
            )
            return DEFAULT_DECODING_OUTPUT

        if token is None:
            try:
                token = get_or_create_evm_token(
                    userdb=self.database,
                    evm_address=tx_log.address,
                    chain_id=self.evm_inquirer.chain_id,
                    token_kind=token_kind,
                    collectible_id=collectible_id,
                    evm_inquirer=self.evm_inquirer,
                    encounter=TokenEncounterInfo(tx_hash=transaction.tx_hash),
                )
            except (NotERC20Conformant, NotERC721Conformant):
                return DEFAULT_DECODING_OUTPUT  # ignore non token transfers for now

        if not self.base.any_tracked([owner_address, spender_address]):
            return DEFAULT_DECODING_OUTPUT

        amount = token_normalized_value(token_amount=amount_raw, token=token)
        if amount == ZERO:
            notes = f'Revoke {token.symbol} spending approval of {owner_address} by {spender_address}'  # noqa: E501
        else:
            notes = f'Set {token.symbol} spending approval of {owner_address} by {spender_address} to {amount}'  # noqa: E501
        event = self.base.make_event_from_transaction(
            transaction=transaction,
            tx_log=tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=token,
            amount=amount,
            location_label=owner_address,
            notes=notes,
            address=spender_address,
        )
        return DecodingOutput(event=event)

    def _maybe_decode_simple_transactions(
            self,
            tx: EvmTransaction,
            tx_receipt: EvmTxReceipt,
    ) -> list['EvmEvent']:
        """Decodes normal ETH transfers, internal transactions and gas cost payments"""
        events: list[EvmEvent] = []
        # check for gas spent
        direction_result = self.base.decode_direction(tx.from_address, tx.to_address)
        if direction_result is not None:
            event_type, _, location_label, _, _, _ = direction_result
            if event_type in OUTGOING_EVENT_TYPES:
                eth_burned_as_gas = self._calculate_gas_burned(tx)
                notes = f'Burn {eth_burned_as_gas} {self.value_asset.symbol} for gas'
                event_type = HistoryEventType.SPEND

                if tx_receipt.status is False:
                    notes += ' of a failed transaction'
                    event_type = HistoryEventType.FAIL

                events.append(self.base.make_event(
                    tx_hash=tx.tx_hash,
                    sequence_index=self.base.get_next_sequence_index_pre_decoding(),
                    timestamp=tx.timestamp,
                    event_type=event_type,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=self.value_asset,
                    amount=eth_burned_as_gas,
                    location_label=location_label,
                    notes=notes,
                    counterparty=CPT_GAS,
                ))

        # Decode internal transactions after gas so gas is always 0 indexed
        self._maybe_decode_internal_transactions(
            tx=tx,
            tx_receipt=tx_receipt,
            events=events,
        )

        if tx_receipt.status is False or direction_result is None:
            # Not any other action to do for failed transactions or transaction where
            # any tracked address is not involved
            return events

        # now decode the actual transaction eth transfer itself
        amount = ZERO if tx.value == 0 else from_wei(FVal(tx.value))
        if tx.to_address is None:
            if not self.base.is_tracked(tx.from_address):
                return events

            event_subtype = HistoryEventSubType.NONE
            if amount != ZERO:
                event_subtype = HistoryEventSubType.SPEND

            events.append(self.base.make_event(  # contract deployment
                tx_hash=tx.tx_hash,
                sequence_index=self.base.get_next_sequence_index_pre_decoding(),
                timestamp=tx.timestamp,
                event_type=HistoryEventType.DEPLOY,
                event_subtype=event_subtype,
                asset=self.value_asset,
                amount=amount,
                location_label=tx.from_address,
                notes='Contract deployment',
                address=None,  # TODO: Find out contract address
            ))
            return events

        if amount == ZERO:
            return events

        if (eth_event := self._get_eth_transfer_event(tx)) is not None:
            events.append(eth_event)
        return events

    def _maybe_decode_erc20_721_transfer(
            self,
            token: 'EvmToken | None',
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],  # pylint: disable=unused-argument
            action_items: list[ActionItem],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> DecodingOutput:
        if (
            tx_log.topics[0] != ERC20_OR_ERC721_TRANSFER or
            (token_kind_and_id := self._get_transfer_or_approval_token_kind_and_id(tx_log=tx_log)) is None  # noqa: E501
        ):
            return DEFAULT_DECODING_OUTPUT

        token_kind, collectible_id = token_kind_and_id
        if token is None:
            try:
                found_token = get_or_create_evm_token(
                    userdb=self.database,
                    evm_address=tx_log.address,
                    chain_id=self.evm_inquirer.chain_id,
                    token_kind=token_kind,
                    collectible_id=collectible_id,
                    evm_inquirer=self.evm_inquirer,
                    encounter=TokenEncounterInfo(tx_hash=transaction.tx_hash),
                )
            except (NotERC20Conformant, NotERC721Conformant):
                return DEFAULT_DECODING_OUTPUT  # ignore non token transfers for now
        else:
            found_token = token

        transfer = self.base.decode_erc20_721_transfer(
            token=found_token,
            tx_log=tx_log,
            transaction=transaction,
        )
        if transfer is None:
            return DEFAULT_DECODING_OUTPUT

        for idx, action_item in enumerate(action_items):
            if (
                    (action_item.asset is None or action_item.asset == found_token) and
                    action_item.from_event_type == transfer.event_type and
                    action_item.from_event_subtype == transfer.event_subtype and
                    (
                        (action_item.amount is None or action_item.amount == transfer.amount) or
                        (
                            action_item.amount_error_tolerance is not None and
                            action_item.amount is not None and
                            abs(action_item.amount - transfer.amount) < action_item.amount_error_tolerance  # noqa: E501
                        )
                    ) and
                    (action_item.location_label is None or action_item.location_label == transfer.location_label)  # noqa: E501
            ):
                if action_item.action == 'skip':
                    action_items.pop(idx)
                    return DEFAULT_DECODING_OUTPUT
                if action_item.action == 'skip & keep':
                    # the action item is skipped but kept in the list of action items. Is used
                    # to propagate information between event decoders and enrichers
                    continue

                # else atm only transform
                if action_item.to_event_type is not None:
                    transfer.event_type = action_item.to_event_type
                if action_item.to_event_subtype is not None:
                    transfer.event_subtype = action_item.to_event_subtype
                if action_item.to_notes is not None:
                    format_kwargs = {}
                    if '{amount}' in action_item.to_notes:
                        format_kwargs['amount'] = str(transfer.amount)
                    if '{symbol}' in action_item.to_notes:
                        format_kwargs['symbol'] = found_token.symbol

                    if len(format_kwargs) != 0:
                        transfer.notes = action_item.to_notes.format(**format_kwargs)
                    else:  # needed since notes may contain {} and not need formatting (eg. Safe{Pass})  # noqa: E501
                        transfer.notes = action_item.to_notes

                if action_item.to_counterparty is not None:
                    transfer.counterparty = action_item.to_counterparty
                if action_item.to_product is not None:
                    transfer.product = action_item.to_product
                if action_item.extra_data is not None:
                    transfer.extra_data = action_item.extra_data
                if action_item.to_address is not None:
                    transfer.address = action_item.to_address
                if action_item.to_location_label is not None:
                    transfer.location_label = action_item.to_location_label

                if action_item.pair_with_next_action_item:
                    if len(action_items) <= idx + 1:
                        log.error(f'At {transaction=} asked for pair with next action item for {action_item=} while there is no more items')  # noqa: E501
                        break

                    action_items[idx + 1].paired_events_data = ([transfer], True)

                if action_item.paired_events_data is not None:
                    # If there is a paired event to this, take care of the order
                    out_events: Sequence[EvmEvent] = [transfer]
                    in_events = action_item.paired_events_data[0]
                    if action_item.paired_events_data[1] is True:
                        out_events = action_item.paired_events_data[0]
                        in_events = [transfer]
                    maybe_reshuffle_events(
                        ordered_events=[*out_events, *in_events],
                        events_list=decoded_events + [transfer],
                    )

                action_items.pop(idx)
                break  # found an action item and acted on it

        # Add additional information to transfers for different protocols
        enrichment_output = self._enrich_protocol_transfers(
            context=EnricherContext(
                tx_log=tx_log,
                transaction=transaction,
                action_items=action_items,
                all_logs=all_logs,
                token=found_token,
                event=transfer,
            ),
        )
        return DecodingOutput(
            event=transfer,
            matched_counterparty=enrichment_output.matched_counterparty,
            refresh_balances=enrichment_output.refresh_balances,
            process_swaps=enrichment_output.process_swaps,
        )

    def _post_process(self, refresh_balances: bool) -> None:
        """
        Method that handles actions that have to be taken after a batch of transactions gets
        decoded. Currently may only send a websocket message to the frontend to refresh balances.
        The caller of decode_transactions should call this method after a batch of transactions
        has been decoded.
        """
        if refresh_balances is True:
            log.debug(f'Sending ws to refresh balances for {self.evm_inquirer.chain_name}')
            self.msg_aggregator.add_message(
                message_type=WSMessageType.REFRESH_BALANCES,
                data={
                    'type': 'blockchain_balances',
                    'blockchain': self.evm_inquirer.chain_id.to_blockchain().serialize(),
                },
            )

    def _chain_specific_decoder_initialization(
            self,
            decoder: 'DecoderInterface',  # pylint: disable=unused-argument
    ) -> None:
        """Custom initialization for each decoder, based on the type of EVM chain.

        This is a no-op by default
        """
        return None

    def _chain_specific_post_decoding_rules(
            self,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
    ) -> list[tuple[int, Callable]]:
        """Custom post-decoding rules for specific chains. This is a no-op by default."""
        return []

    def _calculate_gas_burned(self, tx: EvmTransaction) -> FVal:
        """Calculates gas burn based on relevant chain's formula."""
        return from_wei(FVal(tx.gas_used * tx.gas_price))

    if __debug__:  # for now only debug as decoders are constant

        def assert_keys_are_unique(self, new_struct: dict, main_struct: dict, class_name: str, type_name: str) -> None:  # noqa: E501
            """Asserts that some decoders keys of new rules are unique"""
            intersection = set(new_struct).intersection(set(main_struct))
            if len(intersection) != 0:
                raise AssertionError(f'{type_name} duplicates found in decoding rules of {self.evm_inquirer.chain_name} {class_name}: {intersection}')  # noqa: E501

    def _enrich_protocol_transfers(self, context: EnricherContext) -> TransferEnrichmentOutput:
        """Decode special transfers made by contract execution for example at the moment
        of depositing assets or withdrawing.
        It assumes that the event being decoded has been already filtered and is a transfer.
        Can be overridden by child classes for chain-specific logic."""
        transfer_enrich: TransferEnrichmentOutput
        for enrich_call in self.rules.token_enricher_rules:
            transfer_enrich, err = decode_safely(
                msg_aggregator=self.msg_aggregator,
                tx_hash=context.transaction.tx_hash,
                chain_id=context.transaction.chain_id,
                func=enrich_call,
                context=context,
            )
            if err:
                return FAILED_ENRICHMENT_OUTPUT

            if transfer_enrich != FAILED_ENRICHMENT_OUTPUT:
                return transfer_enrich

        return FAILED_ENRICHMENT_OUTPUT

    # -- methods to be implemented by child classes --

    @staticmethod
    @abstractmethod
    def _is_non_conformant_erc721(address: ChecksumEvmAddress) -> bool:
        """Determine whether the address is a non-conformant erc721 for the chain"""

    @staticmethod
    @abstractmethod
    def _address_is_exchange(address: ChecksumEvmAddress) -> str | None:
        """Takes an address and returns if it's an exchange in the given chain
        and the counterparty to use if it is."""


class EVMTransactionDecoderWithDSProxy(EVMTransactionDecoder, ABC):
    def __init__(
            self,
            database: 'DBHandler',
            evm_inquirer: 'EvmNodeInquirerWithDSProxy',
            transactions: 'EvmTransactions',
            value_asset: 'AssetWithOracles',
            event_rules: list[EventDecoderFunction],
            misc_counterparties: list[CounterpartyDetails],
            base_tools: BaseDecoderToolsWithDSProxy,
            beacon_chain: 'BeaconChain | None' = None,
    ):
        super().__init__(
            database=database,
            evm_inquirer=evm_inquirer,
            transactions=transactions,
            value_asset=value_asset,
            event_rules=event_rules,
            misc_counterparties=misc_counterparties,
            base_tools=base_tools,
            beacon_chain=beacon_chain,
        )
        self.evm_inquirer: EvmNodeInquirerWithDSProxy  # Set explicit type
        self.base: BaseDecoderToolsWithDSProxy  # Set explicit type
