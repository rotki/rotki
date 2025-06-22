import logging
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any, Final, Literal, overload

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi_str
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.utils import (
    asset_normalized_value,
    token_normalized_value_decimals,
)
from rotkehlchen.chain.evm.constants import MERKLE_CLAIM
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChainID, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.velodrome.velodrome_cache import VelodromePoolData
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

    from .base import BaseDecoderTools


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
CACHE_QUERY_METHOD_TYPE = (
    Callable[
        [
            'OptimismInquirer | BaseInquirer',
            Literal[CacheType.VELODROME_POOL_ADDRESS, CacheType.AERODROME_POOL_ADDRESS],
            'MessagesAggregator',
            bool,
        ],
        list['VelodromePoolData'] | None] |
    Callable[
        [
            'EvmNodeInquirer',
            Literal[CacheType.BALANCER_V1_POOLS, CacheType.BALANCER_V2_POOLS],
            'MessagesAggregator',
            bool,
        ],
        tuple[set['ChecksumEvmAddress'], set['ChecksumEvmAddress']] | None] |
    Callable[
        ['EthereumInquirer', Literal[CacheType.CURVE_LP_TOKENS], 'MessagesAggregator', bool],
        list | None,
    ] |
    Callable[
        ['EthereumInquirer', Literal[CacheType.EXTRAFI_NEXT_RESERVE_ID], 'MessagesAggregator', bool],  # noqa: E501
        list | None,
    ] |
    Callable[
        ['EthereumInquirer', Literal[CacheType.CONVEX_POOL_ADDRESS], 'MessagesAggregator', bool],
        dict | None,
    ] |
    Callable[
        ['EthereumInquirer', Literal[CacheType.GEARBOX_POOL_ADDRESS], 'MessagesAggregator', bool],
        list | None,
    ]
)


class DecoderInterface(ABC):

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


VOTE_CAST_WITH_PARAMS: Final = b'\xe2\xba\xbf\xba\xc5\x88\x9ap\x9bc\xbb\x7fY\x8b2N\x08\xbcZO\xb9\xecd\x7f\xb3\xcb\xc9\xec\x07\xeb\x87\x12'  # noqa: E501
VOTE_CAST: Final = b'\xb8\xe18\x88}\n\xa1;\xabD~\x82\xde\x9d\\\x17w\x04\x1e\xcd!\xca6\xba\x82O\xf1\xe6\xc0}\xdd\xa4'  # noqa: E501
VOTE_CAST_UNINDEXED: Final = b'\x87xV3\x8e\x13\xf6=\x0c6\x82/\xf0\xefsk\x80\x93L\xd9\x05t\xa3\xa5\xbc\x92b\xc3\x9d!|F'  # noqa: E501


VOTE_CAST_COMMON_ABI: Final = '{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"voter","type":"address"},{"indexed":false,"internalType":"uint256","name":"proposalId","type":"uint256"},{"indexed":false,"internalType":"uint8","name":"support","type":"uint8"},{"indexed":false,"internalType":"uint256","name":"weight","type":"uint256"},{"indexed":false,"internalType":"string","name":"reason","type":"string"}'  # noqa: E501
VOTE_CAST_ABI: Final = VOTE_CAST_COMMON_ABI + '],"name":"VoteCast","type":"event"}'
VOTE_CAST_WITH_PARAMS_ABI: Final = VOTE_CAST_COMMON_ABI + ',{"indexed":false,"internalType":"bytes","name":"params","type":"bytes"}],"name":"VoteCastWithParams","type":"event"}'  # noqa: E501
GOVERNORALPHA_PROPOSE: Final = b"}\x84\xa6&:\xe0\xd9\x8d3)\xbd{F\xbbN\x8do\x98\xcd5\xa7\xad\xb4\\'L\x8b\x7f\xd5\xeb\xd5\xe0"  # noqa: E501
GOVERNORALPHA_PROPOSE_ABI: Final = '{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"id","type":"uint256"},{"indexed":false,"internalType":"address","name":"proposer","type":"address"},{"indexed":false,"internalType":"address[]","name":"targets","type":"address[]"},{"indexed":false,"internalType":"uint256[]","name":"values","type":"uint256[]"},{"indexed":false,"internalType":"string[]","name":"signatures","type":"string[]"},{"indexed":false,"internalType":"bytes[]","name":"calldatas","type":"bytes[]"},{"indexed":false,"internalType":"uint256","name":"startBlock","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"endBlock","type":"uint256"},{"indexed":false,"internalType":"string","name":"description","type":"string"}],"name":"ProposalCreated","type":"event"}'  # noqa: E501


class MerkleClaimDecoderInterface(DecoderInterface, ABC):
    """Decoders of protocols containing a merkle airdrop claim"""

    def _maybe_enrich_claim_transfer(
            self,
            context: DecoderContext,
            counterparty: str,
            token_id: str,
            notes_suffix: str,
            claiming_address: ChecksumEvmAddress,
            claimed_amount: FVal,
            airdrop_identifiers: str,
    ) -> DecodingOutput:
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.location_label == claiming_address and
                event.asset.identifier == token_id and
                event.amount == claimed_amount
            ):
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.AIRDROP
                event.counterparty = counterparty
                event.notes = f'Claim {claimed_amount} {notes_suffix}'
                event.address = context.tx_log.address
                event.extra_data = {AIRDROP_IDENTIFIER_KEY: airdrop_identifiers}
                break
        else:
            log.error(f'Could not find transfer event for {counterparty} airdrop claim {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_indexed_merkle_claim(
            self,
            context: DecoderContext,
            counterparty: str,
            token_id: str,
            token_decimals: int,
            notes_suffix: str,
            airdrop_identifier: str,
    ) -> DecodingOutput:
        """This decodes all merkledrop claims but with indexed topic arguments"""
        if context.tx_log.topics[0] != MERKLE_CLAIM:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(claiming_address := bytes_to_address(context.tx_log.topics[2])):  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        claimed_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.topics[3]),
            token_decimals=token_decimals,
        )
        return self._maybe_enrich_claim_transfer(context, counterparty, token_id, notes_suffix, claiming_address, claimed_amount, airdrop_identifier)  # noqa: E501

    def _decode_merkle_claim(
            self,
            context: DecoderContext,
            counterparty: str,
            token_id: str,
            token_decimals: int,
            notes_suffix: str,
            airdrop_identifier: str,
    ) -> DecodingOutput:
        """This decodes all merkledrop claims that fit the same event log format"""
        if context.tx_log.topics[0] != MERKLE_CLAIM:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(claiming_address := bytes_to_address(context.tx_log.data[32:64])):  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        claimed_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[64:96]),
            token_decimals=token_decimals,
        )
        return self._maybe_enrich_claim_transfer(context, counterparty, token_id, notes_suffix, claiming_address, claimed_amount, airdrop_identifier)  # noqa: E501


class VoteChoice(StrEnum):
    FOR = auto()
    AGAINST = auto()
    ABSTAIN = auto()


class GovernableDecoderInterface(DecoderInterface, ABC):
    """Decoders of protocols that have voting in Governance

    Inheriting decoder classes should add the _decode_governance() method
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
        DecoderInterface.__init__(
            self,
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.protocol = protocol
        self.proposals_url = proposals_url

    def _decode_vote_cast_common(
            self,
            context: DecoderContext,
            voter_address: ChecksumEvmAddress,
            vote_choice: VoteChoice,
            proposal_id: int,
            notes_reason: str = '',
    ) -> DecodingOutput:
        notes = f'Vote {vote_choice.upper()} {"in " if vote_choice == VoteChoice.ABSTAIN else ""}{self.protocol} governance proposal {self.proposals_url}/{proposal_id}{notes_reason}'  # noqa: E501
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_ETH,
            amount=ZERO,
            location_label=voter_address,
            notes=notes,
            address=context.tx_log.address,
            counterparty=self.protocol,
        )
        return DecodingOutput(events=[event])

    @staticmethod
    def _decode_raw_vote(vote_raw: int) -> VoteChoice:
        if vote_raw == 0:
            return VoteChoice.AGAINST
        elif vote_raw == 1:
            return VoteChoice.FOR
        else:
            return VoteChoice.ABSTAIN

    def _decode_vote_cast(self, context: DecoderContext, abi: str) -> DecodingOutput:
        if not self.base.is_tracked(voter_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

        try:  # we use decode_event_data_abi_str due to "reason" string being hard to
            # decode directly. Perhaps if we learn how to and abstract in our own
            # function manually we can use here and other places
            _, decoded_data = decode_event_data_abi_str(context.tx_log, abi)
        except DeserializationError as e:
            log.error(
                f'Failed to decode vote_cast event ABI at '
                f'{context.transaction.tx_hash.hex()} due to {e}',
            )
            return DEFAULT_DECODING_OUTPUT

        proposal_id, vote_raw, notes_reason = decoded_data[0], decoded_data[1], ''
        if len(decoded_data[3]) != 0:
            notes_reason = f' with reasoning: {decoded_data[3]}'

        return self._decode_vote_cast_common(
            context=context,
            voter_address=voter_address,
            vote_choice=self._decode_raw_vote(vote_raw),
            proposal_id=proposal_id,
            notes_reason=notes_reason,
        )

    def _decode_vote_cast_unindexed(self, context: DecoderContext) -> DecodingOutput:
        if not self.base.is_tracked(voter_address := bytes_to_address(context.tx_log.data[:32])):
            return DEFAULT_DECODING_OUTPUT

        return self._decode_vote_cast_common(
            context=context,
            voter_address=voter_address,
            vote_choice=self._decode_raw_vote(int.from_bytes(context.tx_log.data[64:96])),
            proposal_id=int.from_bytes(context.tx_log.data[32:64]),
        )

    def _decode_propose(self, context: DecoderContext, abi: str) -> DecodingOutput:
        try:  # using decode_event_data_abi_str for same reason as in vote cast
            _, decoded_data = decode_event_data_abi_str(context.tx_log, abi)
        except DeserializationError as e:
            log.error(f'Failed to decode governor alpha event due to {e!s} for {context.transaction.tx_hash.hex()}')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        proposal_id = decoded_data[0]
        proposal_text = decoded_data[8]
        notes = f'Create {self.protocol} proposal {proposal_id}. {proposal_text}'
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_ETH,
            amount=ZERO,
            location_label=context.transaction.from_address,
            notes=notes,
            address=context.tx_log.address,
            counterparty=self.protocol,
        )
        return DecodingOutput(events=[event])

    def _decode_governance(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == VOTE_CAST:
            event_abi = VOTE_CAST_ABI
            method = self._decode_vote_cast
        elif context.tx_log.topics[0] == VOTE_CAST_WITH_PARAMS:
            event_abi = VOTE_CAST_WITH_PARAMS_ABI
            method = self._decode_vote_cast
        elif context.tx_log.topics[0] == VOTE_CAST_UNINDEXED:
            return self._decode_vote_cast_unindexed(context)
        elif context.tx_log.topics[0] == GOVERNORALPHA_PROPOSE:
            method = self._decode_propose
            event_abi = GOVERNORALPHA_PROPOSE_ABI
        else:
            return DEFAULT_DECODING_OUTPUT

        return method(context, event_abi)


class ReloadableDecoderMixin(ABC):
    """Used by decoders of protocols that use data that can be reloaded from the db or from a
    remote data source, to the decoder's memory."""

    @abstractmethod
    def reload_data(self) -> Mapping[ChecksumEvmAddress, tuple[Any, ...]] | None:
        """Subclasses may implement this to be able to reload some of the decoder's properties
        Returns only new mappings of addresses to decode functions"""


class ReloadableCacheDecoderMixin(ReloadableDecoderMixin, ABC):
    """Used by decoders of protocols that have data stored in the globaldb cache
    tables. It can reload them to the decoder's memory.
    """

    @overload  # without chain_id
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            cache_type_to_check_for_freshness: CacheType,
            query_data_method: CACHE_QUERY_METHOD_TYPE,
            read_data_from_cache_method: Callable[[], tuple[dict[ChecksumEvmAddress, Any] | set[ChecksumEvmAddress], ...]],  # noqa: E501
    ) -> None:
        ...

    @overload  # with chain_id
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            cache_type_to_check_for_freshness: CacheType,
            query_data_method: CACHE_QUERY_METHOD_TYPE,
            read_data_from_cache_method: Callable[[ChainID], tuple[dict[ChecksumEvmAddress, Any] | set[ChecksumEvmAddress], ...]],  # noqa: E501
            chain_id: ChainID,
    ) -> None:
        ...

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            cache_type_to_check_for_freshness: CacheType,
            query_data_method: CACHE_QUERY_METHOD_TYPE,
            read_data_from_cache_method: Callable[..., tuple[dict[ChecksumEvmAddress, Any] | set[ChecksumEvmAddress], ...]],  # noqa: E501
            chain_id: ChainID | None = None,
    ) -> None:
        """
        :param evm_inquirer: The evm inquirer used to query the remote data source.
        :param cache_type_to_check_for_freshness: The cache type that is checked for freshness.
        :param query_data_method: The method that queries the remote source
        for data and saves the new information.
        :param read_data_from_cache_method: The method that reads the data from the local cache.
        :param chain_id: The optional chain id of the data to read from the cache tables.
        cache tables.
        """
        self.evm_inquirer = evm_inquirer
        self.cache_type_to_check_for_freshness = cache_type_to_check_for_freshness
        self.query_data_method = query_data_method
        self.read_data_from_cache_method = read_data_from_cache_method
        self.chain_id = chain_id
        self.cache_data: tuple[dict[ChecksumEvmAddress, Any] | set[ChecksumEvmAddress], ...] = ()

    @abstractmethod
    def _cache_mapping_methods(self) -> tuple[Callable, ...]:
        """Methods used to decode cache data"""

    def post_cache_update_callback(self) -> None:
        """Called whenever the cache is updated. Can be overwritten by subclasses to trigger a
        logic whenever the cache is updated."""

    def reload_data(self) -> Mapping[ChecksumEvmAddress, tuple[Any, ...]] | None:
        """Make sure cache_data is recently queried from the remote source,
        saved in the DB and loaded to the decoder's memory.

        If a query happens and any new mappings are generated they are returned,
        otherwise `None` is returned.
        """
        self.evm_inquirer.ensure_cache_data_is_updated(
            cache_type=self.cache_type_to_check_for_freshness,
            query_method=self.query_data_method,
            chain_id=self.chain_id,
            cache_key_parts=(str(self.chain_id.serialize_for_db()),) if self.chain_id else None,
        )

        if self.chain_id is None:
            new_cache_data = self.read_data_from_cache_method()
        else:
            new_cache_data = self.read_data_from_cache_method(self.chain_id)

        cache_diff = [  # get the new items for the different information stored in the cache
            (new_data.keys() if isinstance(new_data, dict) else new_data) -
            (data.keys() if isinstance(data, dict) else data)
            for data, new_data in zip(self.cache_data, new_cache_data, strict=True)  # strict=True guaranteed due to number of caches always the same  # noqa: E501
        ] if len(self.cache_data) > 0 else [  # if self.cache_data is empty, the diff is only from new_cache_data  # noqa: E501
            (set(new_data.keys()) if isinstance(new_data, dict) else new_data)
            for new_data in new_cache_data
        ]

        self.cache_data = new_cache_data
        self.post_cache_update_callback()
        if sum(len(x) for x in cache_diff) == 0:
            return None

        new_decoding_mapping: dict[ChecksumEvmAddress, tuple[Any, ...]] = {}
        # pair each new address in each cache container to the method decoding its logic
        for data_diff, method in zip(cache_diff, self._cache_mapping_methods(), strict=True):  # size should be correct if inheriting decoder is implemented properly  # noqa: E501
            new_decoding_mapping |= dict.fromkeys(data_diff, (method,))

        return new_decoding_mapping


class ReloadablePoolsAndGaugesDecoderMixin(ReloadableCacheDecoderMixin, ABC):
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


class CommonGrantsDecoderMixin(DecoderInterface, ABC):
    """Abstracting some common functionality of grants decoders. Specifically
    gitcoin cgrants and CLRfund"""

    def _decode_matching_claim_common(
            self,
            context: DecoderContext,
            name: str,
            asset: Asset,
            claimee_raw: bytes,
            amount_raw: bytes,
            counterparty: str,
    ) -> DecodingOutput:
        """Decode the matching funds claim based on the given name and asset. We need
        to provide the name and the asset as this is based per contract and does not change.

        For the token we could query it but the name we can't. Still since it's hard
        coded per contract and we have a hard coded list it's best to not ask the chain
        and do an extra network query since this is immutable.

        The caller should confirm that the topic[0] matces the required topic hash.
        """
        if not self.base.any_tracked([claimee := bytes_to_address(claimee_raw), context.transaction.from_address]):  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        asset = asset.resolve_to_crypto_asset()
        amount = asset_normalized_value(
            amount=int.from_bytes(amount_raw),
            asset=asset,
        )
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == asset and
                    event.amount == amount and
                    event.location_label == claimee
            ):
                event.event_subtype = HistoryEventSubType.DONATE
                event.counterparty = counterparty
                event.notes = f'Claim {amount} {asset.symbol} as matching funds payout of {counterparty} {name}'  # noqa: E501
                if context.transaction.from_address != claimee:
                    event.notes += f' for {claimee}'
                break

        else:
            log.error(
                f'Failed to find the {counterparty} matching receive transfer for {self.evm_inquirer.chain_name} transaction {context.transaction.tx_hash.hex()}.',  # noqa: E501
            )

        return DEFAULT_DECODING_OUTPUT
