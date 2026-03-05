import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import asset_normalized_value, token_normalized_value_decimals
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.modules.aave.constants import REDEEM_TOPIC
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    COOLDOWN_TOPIC,
    CPT_GHO,
    GHO_IDENTIFIER,
    STAKE_TOPIC,
    STAKED_GHO_ADDRESS,
    STKGHO_IDENTIFIER,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class AaveghoDecoder(EvmDecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )

    def _decode_cooldown_event(self, context: 'DecoderContext') -> EvmDecodingOutput:
        """Decode cooldown activation on stkGHO, starting the unstaking window."""
        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[:32]),
            asset=(staked_asset := self.base.get_or_create_evm_asset(context.tx_log.address)),
        )
        return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=staked_asset,
            amount=amount,
            location_label=user_address,
            notes=f'Activate cooldown for {amount} stkGHO',
            counterparty=CPT_GHO,
            address=context.tx_log.address,
        )])

    def _decode_stake_or_redeem_event(
            self,
            context: 'DecoderContext',
            is_stake: bool,
    ) -> EvmDecodingOutput:
        """Decode staking GHO for stkGHO or redeeming stkGHO back to GHO."""
        if not self.base.any_tracked([
            bytes_to_address(context.tx_log.topics[1]),
            bytes_to_address(context.tx_log.topics[2]),
        ]):
            return DEFAULT_EVM_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        out_event, in_event = None, None
        for event in context.decoded_events:
            if event.event_subtype != HistoryEventSubType.NONE or event.amount != amount:
                continue

            if is_stake:
                if (
                        event.event_type == HistoryEventType.SPEND and
                        event.asset.identifier == GHO_IDENTIFIER
                ):
                    event.event_type = HistoryEventType.STAKING
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.notes = f'Stake {amount} GHO'
                    event.counterparty = CPT_GHO
                    out_event = event
                elif (
                        event.event_type == HistoryEventType.RECEIVE and
                        event.asset.identifier == STKGHO_IDENTIFIER
                ):
                    event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                    event.notes = f'Receive {amount} stkGHO from staking in GHO'
                    event.counterparty = CPT_GHO
                    in_event = event
            else:  # noqa: PLR5501
                if (
                        event.event_type == HistoryEventType.SPEND and
                        event.asset.identifier == STKGHO_IDENTIFIER
                ):
                    event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    event.notes = f'Unstake {amount} stkGHO'
                    event.counterparty = CPT_GHO
                    out_event = event
                elif (
                        event.event_type == HistoryEventType.RECEIVE and
                        event.asset.identifier == GHO_IDENTIFIER
                ):
                    event.event_type = HistoryEventType.STAKING
                    event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    event.notes = f'Receive {amount} GHO after unstaking from GHO'
                    event.counterparty = CPT_GHO
                    in_event = event

        if out_event is None or in_event is None:
            log.error(f'Could not find matching events for stkGHO {"stake" if is_stake else "redeem"} in {context.transaction.tx_hash!s}')  # noqa: E501

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_staked_gho_events(self, context: 'DecoderContext') -> EvmDecodingOutput:
        """Route stkGHO contract events to the appropriate decoder."""
        match context.tx_log.topics[0]:
            case topic if topic == COOLDOWN_TOPIC:
                return self._decode_cooldown_event(context)
            case topic if topic == REDEEM_TOPIC:
                return self._decode_stake_or_redeem_event(context=context, is_stake=False)
            case topic if topic == STAKE_TOPIC:
                return self._decode_stake_or_redeem_event(context=context, is_stake=True)
            case _:
                return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {STAKED_GHO_ADDRESS: (self._decode_staked_gho_events,)}

    @staticmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        return (CounterpartyDetails(identifier=CPT_GHO, label='Gho', image='gho.svg'),)
