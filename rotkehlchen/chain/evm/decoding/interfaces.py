import logging
from abc import ABCMeta, abstractmethod
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmProduct
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.optimism.modules.velodrome.velodrome_cache import VelodromePoolData
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.user_messages import MessagesAggregator

    from .base import BaseDecoderTools


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DecoderInterface(metaclass=ABCMeta):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        """This is the Decoder interface initialization signature"""
        self.base = base_tools
        self.msg_aggregator = msg_aggregator
        self.evm_inquirer = evm_inquirer

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        """Subclasses may implement this to return the mappings of addresses to decode functions"""
        return {}

    @staticmethod
    @abstractmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        """
        Subclasses implement this to specify which counterparty values are introduced by the module
        """

    def decoding_rules(self) -> list[Callable]:
        """
        Subclasses may implement this to add new generic decoding rules to be attempted
        by the decoding process
        """
        return []

    def decoding_by_input_data(self) -> dict[bytes, dict[bytes, Callable]]:
        """
        Subclasses may implement this to add decoding rules that are only triggered
        if input data match a specific pattern/value.

        For now only check against function signature and match it to specific event
        topics that need to be searched for if the given four bytes signature was in
        the input data.

        This is in essence a way to have a more constrained version of the general decoding_rules
        """
        return {}

    def enricher_rules(self) -> list[Callable]:
        """
        Subclasses may implement this to add new generic decoding rules to be attempted
        by the decoding process
        """
        return []

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        """
        Subclasses may implement this to add post processing of the decoded events.
        This will run after the normal decoding step and will only process decoded history events.

        This function should return a dict where values are tuples where the first element is the
        priority of a function and the second element is the function to run. The higher the
        priority number the later the function will be run.
        The keys of the dictionary are counterparties.
        """
        return {}

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        """
        Map addresses to counterparties so they can be filtered in the post
        decoding step.
        """
        return {}

    def notify_user(self, event: 'EvmEvent', counterparty: str) -> None:
        """
        Notify the user about a problem during the decoding of ethereum transactions. At the
        moment it doesn't take any error type but in the future it could be added if needed.
        Related issue: https://github.com/rotki/rotki/issues/4965
        """
        self.msg_aggregator.add_error(
            f'Could not identify asset {event.asset} decoding ethereum event in {counterparty}. '
            f'Make sure that it has all the required properties (name, symbol and decimals) and '
            f'try to decode the event again {event.tx_hash.hex()}.',
        )

    @staticmethod
    def possible_products() -> dict[str, list[EvmProduct]]:
        """Returns a mapping of counterparty to possible evmproducts associated with it
        for the decoder.
        """
        return {}


VOTE_CAST_WITH_PARAMS = b'\xe2\xba\xbf\xba\xc5\x88\x9ap\x9bc\xbb\x7fY\x8b2N\x08\xbcZO\xb9\xecd\x7f\xb3\xcb\xc9\xec\x07\xeb\x87\x12'  # noqa: E501
VOTE_CAST = b'\xb8\xe18\x88}\n\xa1;\xabD~\x82\xde\x9d\\\x17w\x04\x1e\xcd!\xca6\xba\x82O\xf1\xe6\xc0}\xdd\xa4'  # noqa: E501


class GovernableDecoderInterface(DecoderInterface, metaclass=ABCMeta):
    """Decoders of protocols that have voting in Governance

    Inheriting decoder classes should add the _decode_vote_cast() method
    and match it with the proper address to check for in addresses_to_decoders
    """
    def __init__(  # pylint: disable=super-init-not-called
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',  # pylint: disable=unused-argument
            protocol: str,
            proposals_url: str,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.protocol = protocol
        self.proposals_url = proposals_url

    def _decode_vote_cast(self, context: DecoderContext) -> DecodingOutput:
        """Decodes a vote cast event"""
        if context.tx_log.topics[0] not in (VOTE_CAST, VOTE_CAST_WITH_PARAMS):
            return DEFAULT_DECODING_OUTPUT  # for params event is same + params argument. Ignore it

        voter_address = hex_or_bytes_to_address(context.tx_log.topics[1])
        if not self.base.is_tracked(voter_address):
            return DEFAULT_DECODING_OUTPUT

        proposal_id = str(hex_or_bytes_to_int(context.tx_log.data[:32]))
        supports = bool(hex_or_bytes_to_int(context.tx_log.data[32:64]))
        notes = f'Voted {"FOR" if supports else "AGAINST"} {self.protocol} governance proposal {self.proposals_url}/{proposal_id}'  # noqa: E501
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_ETH,
            balance=Balance(),
            location_label=voter_address,
            notes=notes,
            address=context.tx_log.address,
            counterparty=self.protocol,
        )
        return DecodingOutput(event=event)


class ReloadableDecoderMixin(metaclass=ABCMeta):
    """Used by decoders of protocols that use data that can be reloaded from the db or from a
    remote data source, to the decoder's memory."""

    @abstractmethod
    def reload_data(self) -> Mapping[ChecksumEvmAddress, tuple[Any, ...]] | None:
        """Subclasses may implement this to be able to reload some of the decoder's properties
        Returns only new mappings of addresses to decode functions"""


class ReloadableCacheDecoderMixin(ReloadableDecoderMixin, metaclass=ABCMeta):
    """Used by decoders of protocols that have data stored in the globaldb cache
    tables. It can reload them to the decoder's memory.
    """

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            cache_type_to_check_for_freshness: CacheType,
            query_data_method: Callable[['OptimismInquirer'], list['VelodromePoolData'] | None] | Callable[['EthereumInquirer'], list | None],  # noqa: E501
            save_data_to_cache_method: Callable[['DBCursor', 'DBHandler', list], None],
            read_data_from_cache_method: Callable[[], tuple[dict[ChecksumEvmAddress, Any] | set[ChecksumEvmAddress], ...]],  # noqa: E501
    ) -> None:
        """
        :param evm_inquirer: The evm inquirer used to query the remote data source.
        :param cache_type_to_check_for_freshness: The cache type that is checked for freshness.
        :param query_data_method: The method that queries the remote source for data.
        :param save_data_to_cache_method: The method that saves the data to the cache tables.
        :param read_data_from_cache_method: The method that reads the data from the
        cache tables. This function returns a tuple of values, because subclasses may return
        more than a set of caches (example: different set of pools).
        """
        self.evm_inquirer = evm_inquirer
        self.cache_type_to_check_for_freshness = cache_type_to_check_for_freshness
        self.query_data_method = query_data_method
        self.save_data_to_cache_method = save_data_to_cache_method
        self.read_data_from_cache_method = read_data_from_cache_method
        self.cache_data = self.read_data_from_cache_method()

    @abstractmethod
    def _cache_mapping_methods(self) -> tuple[Callable, ...]:
        """Methods used to decode cache data"""

    def reload_data(self) -> Mapping[ChecksumEvmAddress, tuple[Any, ...]] | None:
        """Make sure cache_data is recently queried from the remote source,
        saved in the DB and loaded to the decoder's memory.

        If a query happens and any new mappings are generated they are returned,
        otherwise `None` is returned.
        """
        self.evm_inquirer.ensure_cache_data_is_updated(  # type:ignore  # evm_inquirer has the required method here
            cache_type=self.cache_type_to_check_for_freshness,
            query_method=self.query_data_method,
            save_method=self.save_data_to_cache_method,
        )

        new_cache_data = self.read_data_from_cache_method()
        cache_diff = [  # get the new items for the different information stored in the cache
            (new_data.keys() if isinstance(new_data, dict) else new_data) -
            (data.keys() if isinstance(data, dict) else data)
            for data, new_data in zip(self.cache_data, new_cache_data, strict=True)
        ]  # strict=True guaranteed due to number of caches always the same
        if sum(len(x) for x in cache_diff) == 0:
            return None

        self.cache_data = new_cache_data
        new_decoding_mapping: dict[ChecksumEvmAddress, tuple[Any, ...]] = {}
        # pair each new address in each cache container to the method decoding its logic
        for data_diff, method in zip(cache_diff, self._cache_mapping_methods(), strict=True):  # size should be correct if inheriting decoder is implemented properly  # noqa: E501
            new_decoding_mapping |= {address: (method,) for address in data_diff}

        return new_decoding_mapping


class ReloadablePoolsAndGaugesDecoderMixin(ReloadableCacheDecoderMixin, metaclass=ABCMeta):
    """Used by decoders of protocols that have pools and gauges stored in the globaldb cache
    tables. It can reload them to the decoder's memory.
    """
    @property
    @abstractmethod
    def pools(self) -> dict[ChecksumEvmAddress, Any] | set[ChecksumEvmAddress]:
        """abstractmethod to get pools from `cache_data`"""

    @property
    def gauges(self) -> set[ChecksumEvmAddress]:
        """method to get gauges from `cache_data`.
        The structure is common in the decoders using this logic"""
        assert isinstance(self.cache_data[1], set), 'Decoder cache_data[1] is not a set'
        return self.cache_data[1]

    @abstractmethod
    def _decode_pool_events(self, context: DecoderContext) -> DecodingOutput:
        """Decodes events related to protocol pools."""

    @abstractmethod
    def _decode_gauge_events(self, context: DecoderContext) -> DecodingOutput:
        """Decodes events related to protocol gauges."""

    def _cache_mapping_methods(self) -> tuple[Callable, ...]:
        return (self._decode_pool_events, self._decode_gauge_events)
