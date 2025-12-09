import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import asset_normalized_value
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
    CPT_SUPERFLUID,
    TOKEN_DOWNGRADED_TOPIC,
    TOKEN_UPGRADED_TOPIC,
)
from rotkehlchen.chain.evm.decoding.superfluid.utils import query_superfluid_tokens
from rotkehlchen.chain.evm.decoding.utils import get_protocol_token_addresses
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SuperfluidCommonDecoder(EvmDecoderInterface, ReloadableDecoderMixin):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ):
        super().__init__(evm_inquirer, base_tools, msg_aggregator)
        self.supertoken_addresses: set[ChecksumEvmAddress] = set()

    def reload_data(self) -> Mapping['ChecksumEvmAddress', tuple[Any, ...]] | None:
        """Ensure the super token list is up to date.
        Returns a fresh addresses to decoders mapping.
        """
        if should_update_protocol_cache(
                userdb=self.base.database,
                cache_key=CacheType.SUPERFLUID_TOKEN_LIST_VERSION,
                args=(str(self.node_inquirer.chain_id.serialize()),),
        ) is True:
            query_superfluid_tokens(evm_inquirer=self.node_inquirer)

        self.supertoken_addresses = get_protocol_token_addresses(
            protocol=CPT_SUPERFLUID,
            chain_id=self.node_inquirer.chain_id,
            existing_tokens=self.supertoken_addresses,
        )
        return self.addresses_to_decoders()

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
        if (super_token := self.base.get_evm_token(address=context.tx_log.address)) is None:
            log.debug(
                f'Encountered Superfluid upgrade/downgrade event with '
                f'unknown super token in transaction {context.transaction}',
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        possible_underlying_assets = (
            (self.base.get_evm_token(address=super_token.underlying_tokens[0].address),)
            if super_token.underlying_tokens is not None and len(super_token.underlying_tokens) > 0 else  # noqa: E501
            (self.node_inquirer.native_token, self.node_inquirer.wrapped_native_token)
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

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(self.supertoken_addresses, (self._decode_supertoken_events, ))

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_SUPERFLUID,
            label='Superfluid',
            image='superfluid.svg',
        ),)
