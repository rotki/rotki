import logging
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface, ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.gnosis.modules.gnosis_pay.constants import (
    CPT_GNOSIS_PAY,
    GNOSIS_PAY_CASHBACK_ADDRESS,
    GNOSIS_PAY_CPT_DETAILS,
    GNOSIS_PAY_REFERRAL_ADDRESS,
    GNOSIS_PAY_SPENDER_ADDRESS,
    GNOSIS_PAY_SPENDING_COLLECTOR,
    SPEND,
)
from rotkehlchen.externalapis.gnosispay import init_gnosis_pay
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GnosisPayDecoder(DecoderInterface, ReloadableDecoderMixin):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.gnosispay_api = init_gnosis_pay(self.base.database)

    def reload_data(self) -> Mapping[ChecksumEvmAddress, tuple[Any, ...]] | None:
        """Reload the gnosis pay api from the DB with the credentials"""
        self.gnosispay_api = init_gnosis_pay(self.base.database)
        return self.addresses_to_decoders()

    def decode_cashback_events(self, context: DecoderContext) -> DecodingOutput:
        """Cashback events are simple transfers from cashback collector to user's safe"""
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset.identifier == 'eip155:100/erc20:0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb'  # noqa: E501
            ):
                event.counterparty = CPT_GNOSIS_PAY
                event.event_subtype = HistoryEventSubType.CASHBACK
                event.notes = f'Receive cashback of {event.amount} GNO from Gnosis Pay'

        return DecodingOutput(matched_counterparty=CPT_GNOSIS_PAY)

    def decode_referral_events(self, context: DecoderContext) -> DecodingOutput:
        """Referral events are simple transfers from the address to user's safe"""
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                event.counterparty = CPT_GNOSIS_PAY
                event.event_subtype = HistoryEventSubType.REWARD
                event.notes = f'Receive referral reward of {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from Gnosis Pay'  # noqa: E501

        return DecodingOutput(matched_counterparty=CPT_GNOSIS_PAY)

    def decode_refund_events(self, context: DecoderContext) -> DecodingOutput:
        """Refund events are simple transfers from spending collector's safe to user's safe"""
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                asset = event.asset.resolve_to_asset_with_symbol()
                event.counterparty = CPT_GNOSIS_PAY
                event.event_subtype = HistoryEventSubType.REFUND
                event.notes = f'Receive refund of {event.amount} {asset.symbol} from Gnosis Pay'

                if (
                        self.gnosispay_api is not None and
                        (
                            new_notes := self.gnosispay_api.maybe_find_update_refund(
                                tx_hash=context.transaction.tx_hash,
                                tx_timestamp=context.transaction.timestamp,
                                amount=event.amount,
                                asset=asset,
                            )) is not None
                ):
                    event.notes = new_notes

        return DecodingOutput(matched_counterparty=CPT_GNOSIS_PAY)

    def decode_spend(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != SPEND:
            return DEFAULT_DECODING_OUTPUT

        token = self.base.get_or_create_evm_token(
            address=bytes_to_address(context.tx_log.data[0:32]),
        )
        # Account is the roles module, which is the 2nd module in the array
        # when doing getModulesPaginated("0x0000000000000000000000000000000000000001")
        # with pageSize 100
        # hex_or_bytes_to_address(context.tx_log.data[32:64])  # noqa: ERA001
        # should we use it?
        raw_amount = int.from_bytes(context.tx_log.data[96:128])
        amount = token_normalized_value(raw_amount, token)

        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == token and
                    event.amount == amount
            ):
                event.counterparty = CPT_GNOSIS_PAY
                event.event_subtype = HistoryEventSubType.PAYMENT
                event.notes = f'Spend {event.amount} {token.symbol} via Gnosis Pay'
                break

        else:
            log.error(f'Could not find gnosis pay spend event in {context.transaction}')

        return DecodingOutput(matched_counterparty=CPT_GNOSIS_PAY)

    def _handle_post_processing(
            self,
            decoded_events: list['EvmEvent'],
            has_premium: bool,
    ) -> None:
        if self.gnosispay_api is None or not has_premium:
            return

        # refunds are handled in a different way by the decoder so we don't try to query for them
        log.debug(f'Executing gnosis pay post processing for {len(decoded_events)} events')
        self.gnosispay_api.update_events(
            tx_timestamps={
                event.tx_hash: event.get_timestamp_in_sec()
                for event in decoded_events if event.event_subtype == HistoryEventSubType.PAYMENT
            },
        )

    def post_processing_rules(self) -> dict[str, tuple[Callable]]:
        return {CPT_GNOSIS_PAY: (self._handle_post_processing,)}

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            GNOSIS_PAY_REFERRAL_ADDRESS: (self.decode_referral_events,),
            GNOSIS_PAY_CASHBACK_ADDRESS: (self.decode_cashback_events,),
            GNOSIS_PAY_SPENDER_ADDRESS: (self.decode_spend,),
            GNOSIS_PAY_SPENDING_COLLECTOR: (self.decode_refund_events,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (GNOSIS_PAY_CPT_DETAILS,)
