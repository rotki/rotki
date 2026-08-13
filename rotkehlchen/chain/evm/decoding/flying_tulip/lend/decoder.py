from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.evm.constants import WITHDRAW_TOPIC
from rotkehlchen.chain.evm.decoding.flying_tulip.constants import FLYING_TULIP_LABEL
from rotkehlchen.chain.evm.decoding.flying_tulip.decoder import FlyingTulipCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    FLYING_TULIP_LEND_DEPLOYMENTS,
    PM_BORROW_TOPIC,
    PM_DEPOSIT_FOR_TOPIC,
    PM_DEPOSIT_TOPIC,
    PM_REPAY_FOR_TOPIC,
    PM_REPAY_TOPIC,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

LEND_LABEL: Final = f'{FLYING_TULIP_LABEL} Lend'


class FlyingTulipLendCommonDecoder(FlyingTulipCommonDecoder):
    """Decode deposits, withdrawals, borrows and repayments of Flying Tulip's
    lending market (the ftDNMM positions manager).

    Only wallet-level movements are decoded: each positions manager event is
    matched against an actual token transfer of the tracked wallet. Events the
    leverage RFQ engines emit while rebalancing funds inside a position have no
    matching wallet transfer (or name an engine as the actor) and are skipped,
    mirroring how the protocol itself attributes them.
    """

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
        self.deployment = FLYING_TULIP_LEND_DEPLOYMENTS[evm_inquirer.chain_id]

    def _decode_positions_manager(self, context: DecoderContext) -> EvmDecodingOutput:
        if (topic := context.tx_log.topics[0]) in (PM_DEPOSIT_TOPIC, WITHDRAW_TOPIC, PM_BORROW_TOPIC, PM_REPAY_TOPIC):  # noqa: E501
            if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):
                return DEFAULT_EVM_DECODING_OUTPUT
            token = self.base.get_or_create_evm_token(
                address=bytes_to_address(context.tx_log.topics[2]),
            )
        elif topic in (PM_DEPOSIT_FOR_TOPIC, PM_REPAY_FOR_TOPIC):
            payer = bytes_to_address(context.tx_log.topics[1])
            beneficiary = bytes_to_address(context.tx_log.topics[2])
            if (
                    payer in self.deployment.engines or  # position-internal rebalancing
                    not self.base.any_tracked([payer, beneficiary])
            ):
                return DEFAULT_EVM_DECODING_OUTPUT
            token = self.base.get_or_create_evm_token(
                address=bytes_to_address(context.tx_log.topics[3]),
            )
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token=token,
        )
        if topic == PM_DEPOSIT_TOPIC:
            return self._transform_or_defer(
                context=context,
                from_event_type=HistoryEventType.SPEND,
                token=token,
                amount=amount,
                location_label=user,
                to_event_type=HistoryEventType.DEPOSIT,
                to_event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
                notes=f'Deposit {amount} {token.symbol} in {LEND_LABEL}',
            )
        if topic == PM_DEPOSIT_FOR_TOPIC:
            notes = f'Deposit {amount} {token.symbol} in {LEND_LABEL}'
            if not self.base.is_tracked(beneficiary):
                notes += f' for {beneficiary}'
            return self._transform_or_defer(
                context=context,
                from_event_type=HistoryEventType.SPEND,
                token=token,
                amount=amount,
                location_label=None,  # the transfer may come from the payer or a session module
                to_event_type=HistoryEventType.DEPOSIT,
                to_event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
                notes=notes,
            )
        if topic == WITHDRAW_TOPIC:
            return self._transform_or_defer(
                context=context,
                from_event_type=HistoryEventType.RECEIVE,
                token=token,
                amount=amount,
                location_label=user,
                to_event_type=HistoryEventType.WITHDRAWAL,
                to_event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
                notes=f'Withdraw {amount} {token.symbol} from {LEND_LABEL}',
            )
        if topic == PM_BORROW_TOPIC:
            return self._transform_or_defer(
                context=context,
                from_event_type=HistoryEventType.RECEIVE,
                token=token,
                amount=amount,
                location_label=user,
                to_event_type=HistoryEventType.RECEIVE,
                to_event_subtype=HistoryEventSubType.GENERATE_DEBT,
                notes=f'Borrow {amount} {token.symbol} from {LEND_LABEL}',
            )
        if topic == PM_REPAY_TOPIC:
            return self._transform_or_defer(
                context=context,
                from_event_type=HistoryEventType.SPEND,
                token=token,
                amount=amount,
                location_label=user,
                to_event_type=HistoryEventType.SPEND,
                to_event_subtype=HistoryEventSubType.PAYBACK_DEBT,
                notes=f'Repay {amount} {token.symbol} in {LEND_LABEL}',
            )

        # PM_REPAY_FOR_TOPIC
        notes = f'Repay {amount} {token.symbol} in {LEND_LABEL}'
        if not self.base.is_tracked(beneficiary):
            notes += f' for {beneficiary}'
        return self._transform_or_defer(
            context=context,
            from_event_type=HistoryEventType.SPEND,
            token=token,
            amount=amount,
            location_label=None,
            to_event_type=HistoryEventType.SPEND,
            to_event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            notes=notes,
        )

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {self.deployment.positions_manager: (self._decode_positions_manager,)}
