import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.asset import EvmToken, UnderlyingToken
from rotkehlchen.assets.utils import (
    asset_normalized_value,
    get_or_create_evm_token,
    get_single_underlying_token,
    token_normalized_value,
)
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.utils import should_update_protocol_cache
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface, ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.superfluid.constants import (
    CFA_V1_ADDRESSES,
    CPT_SUPERFLUID,
    FLOW_UPDATED_TOPIC,
    TOKEN_DOWNGRADED_TOPIC,
    TOKEN_UPGRADED_TOPIC,
)
from rotkehlchen.chain.evm.decoding.superfluid.utils import query_superfluid_tokens
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import globaldb_get_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress, TokenKind
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# The calculation for converting between the per second and monthly rates is defined as
# amount of supertoken / ((365/12) * 24 * 60 * 60) = amount per second
# https://docs.superfluid.org/docs/protocol/money-streaming/overview#flows-and-flow-rates
MONTHLY_RATE_MULTIPLIER: Final = FVal('2628000')  # ((365/12) * 24 * 60 * 60)


class SuperfluidCommonDecoder(EvmDecoderInterface, ReloadableDecoderMixin):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ):
        super().__init__(evm_inquirer, base_tools, msg_aggregator)
        self.supertoken_addresses: dict[ChecksumEvmAddress, ChecksumEvmAddress | None] = {}
        assert self.node_inquirer.chain_id in CFA_V1_ADDRESSES, f'No Superfluid CFA address defined for {self.node_inquirer.chain_id.name}'  # noqa: E501
        self.cfa_v1_address = CFA_V1_ADDRESSES[self.node_inquirer.chain_id]

    def reload_data(self) -> Mapping['ChecksumEvmAddress', tuple[Any, ...]] | None:
        """Ensure the super token list is up to date.
        Returns a fresh addresses to decoders mapping.
        """
        if should_update_protocol_cache(
                userdb=self.base.database,
                cache_key=CacheType.SUPERFLUID_TOKEN_LIST_VERSION,
                args=((chain_id_str := str(self.node_inquirer.chain_id.serialize())),),
        ) is True:
            query_superfluid_tokens(chain_id=self.node_inquirer.chain_id)

        with GlobalDBHandler().conn.read_ctx() as cursor:
            cached_super_tokens = globaldb_get_general_cache_values(
                cursor=cursor,
                key_parts=(CacheType.SUPERFLUID_SUPER_TOKENS, chain_id_str),
            )

        for token_and_underlying in cached_super_tokens:
            token_address, underlying_address = token_and_underlying.split(',')
            self.supertoken_addresses[string_to_evm_address(token_address)] = (
                string_to_evm_address(underlying_address)
                if underlying_address != 'native' else None
            )

        return self.addresses_to_decoders()

    def _get_or_create_super_token(self, address: ChecksumEvmAddress) -> 'EvmToken':
        """Ensure the super token exists in the DB with the proper protocol and underlying tokens.
        Returns the super token.
        """
        underlying_tokens: list[UnderlyingToken] | None = None
        if (underlying_address := self.supertoken_addresses.get(address)) is not None:
            underlying_tokens = [UnderlyingToken(
                address=self.base.get_or_create_evm_token(
                    address=string_to_evm_address(underlying_address),
                ).evm_address,
                token_kind=TokenKind.ERC20,
                weight=ONE,
            )]

        return get_or_create_evm_token(
            userdb=self.base.database,
            evm_address=address,
            chain_id=self.node_inquirer.chain_id,
            protocol=CPT_SUPERFLUID,
            underlying_tokens=underlying_tokens,
            evm_inquirer=self.node_inquirer,
        )

    def _decode_upgraded_downgraded(
            self,
            context: DecoderContext,
            expected_super_event_type: HistoryEventType,
            super_event_type: HistoryEventType,
            super_event_subtype: HistoryEventSubType,
            super_notes: str,
            expected_underlying_event_type: HistoryEventType,
            underlying_event_type: HistoryEventType,
            underlying_event_subtype: HistoryEventSubType,
            underlying_notes: str,
            is_deposit: bool,
    ) -> EvmDecodingOutput:
        """Decode super token upgraded/downgraded events using the specified event types and notes.
        Orders events with the underlying token event first if it's a deposit or with the super
        token event first if it's a withdrawal as specified by the `is_deposit` argument.
        """
        super_token = self._get_or_create_super_token(address=context.tx_log.address)
        possible_underlying_assets = (
            (self.node_inquirer.native_token, self.node_inquirer.wrapped_native_token)
            if (underlying_token := get_single_underlying_token(token=super_token)) is None else
            (underlying_token,)
        )  # super tokens with native underlying may also wrap/unwrap to the wrapped native token

        # amount in the log event is always in the supertoken's decimals
        amount = asset_normalized_value(
            asset=super_token,
            amount=int.from_bytes(context.tx_log.data[:32]),
        )
        super_event = underlying_event = None
        for event in context.decoded_events:
            if (
                event.event_type == expected_super_event_type and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == super_token and
                event.amount == amount
            ):
                event.counterparty = CPT_SUPERFLUID
                event.event_type = super_event_type
                event.event_subtype = super_event_subtype
                event.notes = super_notes.format(amount=event.amount, asset=super_token.symbol)
                super_event = event
            elif (
                event.event_type == expected_underlying_event_type and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset in possible_underlying_assets and
                event.amount == amount
            ):
                event.counterparty = CPT_SUPERFLUID
                event.event_type = underlying_event_type
                event.event_subtype = underlying_event_subtype
                event.notes = underlying_notes.format(amount=event.amount, asset=event.asset.resolve_to_asset_with_symbol().symbol)  # noqa: E501
                underlying_event = event

        maybe_reshuffle_events(
            ordered_events=[underlying_event, super_event] if is_deposit else [super_event, underlying_event],  # noqa: E501
            events_list=context.decoded_events,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_supertoken_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode super token events. Uses Wrap/Unwrap terminology in the event notes since
        that is what it is called in the Superfluid app.
        """
        if context.tx_log.topics[0] == TOKEN_DOWNGRADED_TOPIC:
            return self._decode_upgraded_downgraded(
                context=context,
                expected_super_event_type=HistoryEventType.SPEND,
                super_event_type=HistoryEventType.SPEND,
                super_event_subtype=HistoryEventSubType.RETURN_WRAPPED,
                super_notes='Return {amount} {asset} to Superfluid',
                expected_underlying_event_type=HistoryEventType.RECEIVE,
                underlying_event_type=HistoryEventType.WITHDRAWAL,
                underlying_event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
                underlying_notes='Unwrap {amount} {asset} from Superfluid',
                is_deposit=False,
            )
        elif context.tx_log.topics[0] == TOKEN_UPGRADED_TOPIC:
            return self._decode_upgraded_downgraded(
                context=context,
                expected_super_event_type=HistoryEventType.RECEIVE,
                super_event_type=HistoryEventType.RECEIVE,
                super_event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                super_notes='Receive {amount} {asset} from Superfluid',
                expected_underlying_event_type=HistoryEventType.SPEND,
                underlying_event_type=HistoryEventType.DEPOSIT,
                underlying_event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
                underlying_notes='Wrap {amount} {asset} with Superfluid super token',
                is_deposit=True,
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_flow_updated(self, context: DecoderContext) -> EvmDecodingOutput:
        if (
            context.tx_log.topics[0] != FLOW_UPDATED_TOPIC or
            not self.base.is_tracked(sender := bytes_to_address(context.tx_log.topics[2]))
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        receiver = bytes_to_address(context.tx_log.topics[3])
        monthly_flow_rate = token_normalized_value(
            token=(super_token := self._get_or_create_super_token(
                address=bytes_to_address(context.tx_log.topics[1]),
            )),
            token_amount=int.from_bytes(context.tx_log.data[:32]),
        ) * MONTHLY_RATE_MULTIPLIER
        return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=super_token,
            amount=ZERO,
            location_label=sender,
            counterparty=CPT_SUPERFLUID,
            notes=(
                f'Stop Superfluid {super_token.symbol} stream from {sender} to {receiver}'
                if monthly_flow_rate == ZERO else
                f'Start Superfluid stream of {monthly_flow_rate} {super_token.symbol} per month from {sender} to {receiver}'  # noqa: E501
            ),
        )])

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.cfa_v1_address: (self._decode_flow_updated,),
        } | dict.fromkeys(self.supertoken_addresses, (self._decode_supertoken_events,))

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_SUPERFLUID,
            label='Superfluid',
            image='superfluid.svg',
        ),)
