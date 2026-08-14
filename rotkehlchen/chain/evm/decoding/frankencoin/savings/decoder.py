from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import TokenEncounterInfo, token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.frankencoin.constants import (
    CPT_FRANKENCOIN,
    ZCHF_ADDRESS,
    ZCHF_DECIMALS,
)
from rotkehlchen.chain.evm.decoding.frankencoin.decoder import FrankencoinCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_EVM_DECODING_OUTPUT
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    INTEREST_COLLECTED_TOPIC,
    SAVED_TOPIC,
    SUPPORTED_ZCHF_SAVINGS_CHAINS,
    WITHDRAWN_TOPIC,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext, EvmDecodingOutput
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.fval import FVal
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator


class FrankencoinSavingsCommonDecoder(FrankencoinCommonDecoder):
    """Decode Frankencoin savings activity identically across EVM chains."""

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.savings_address = SUPPORTED_ZCHF_SAVINGS_CHAINS[evm_inquirer.chain_id]
        self.zchf_address = ZCHF_ADDRESS[evm_inquirer.chain_id]
        self.zchf = self.base.get_or_create_evm_token(
            address=self.zchf_address,
            encounter=TokenEncounterInfo(should_notify=False),
        )

    def _get_transfer_party(
            self,
            context: DecoderContext,
            amount: FVal,
    ) -> ChecksumEvmAddress | None:
        """Return the payer/receiver from the transfer immediately preceding a savings log."""
        try:
            current_log_position = context.all_logs.index(context.tx_log)
        except ValueError:
            return None

        if current_log_position == 0:
            return None

        transfer_log = context.all_logs[current_log_position - 1]
        if (
            len(transfer_log.topics) != 3 or
            transfer_log.address != self.zchf_address or
            transfer_log.topics[0] != ERC20_OR_ERC721_TRANSFER
        ):
            return None

        from_address = bytes_to_address(transfer_log.topics[1])
        to_address = bytes_to_address(transfer_log.topics[2])
        if (
            self.savings_address not in (from_address, to_address) or
            token_normalized_value_decimals(
                token_amount=int.from_bytes(transfer_log.data),
                token_decimals=ZCHF_DECIMALS,
            ) != amount
        ):
            return None

        return to_address if from_address == self.savings_address else from_address

    def _decode_savings_event(self, context: DecoderContext) -> EvmDecodingOutput:
        """Turn raw savings logs/transfers into rotki history events."""
        if len(context.tx_log.topics) < 2:
            return DEFAULT_EVM_DECODING_OUTPUT

        topic = context.tx_log.topics[0]
        if topic not in (SAVED_TOPIC, INTEREST_COLLECTED_TOPIC, WITHDRAWN_TOPIC):
            return DEFAULT_EVM_DECODING_OUTPUT

        # The indexed account is the savings owner, which may differ from payer or receiver.
        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token_decimals=ZCHF_DECIMALS,
        )

        if topic == SAVED_TOPIC:
            self.decode_saved_topic(context, amount, user_address)
        elif topic == WITHDRAWN_TOPIC:
            self.decode_withdrawn_topic(context, amount, user_address)
        else:
            # This is internal accounting; only net interest accrues to the saver.
            referral_fee = token_normalized_value_decimals(
                token_amount=int.from_bytes(context.tx_log.data[32:64]),
                token_decimals=ZCHF_DECIMALS,
            )
            amount -= referral_fee
            context.decoded_events.append(self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.INTEREST,
                asset=self.zchf,
                amount=amount,
                location_label=user_address,
                notes=f'Received {amount} zCHF as interests in Frankencoin Savings Module',
                counterparty=CPT_FRANKENCOIN,
                address=self.savings_address,
            ))

        return DEFAULT_EVM_DECODING_OUTPUT

    def decode_saved_topic(
            self,
            context: DecoderContext,
            amount: FVal,
            user_address: ChecksumEvmAddress,
    ) -> None:
        event = context.decoded_events[-1] if context.decoded_events else None
        if (
                event is not None and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == amount and
                event.address == self.savings_address and
                event.asset == self.zchf
        ):
            event.event_type = HistoryEventType.DEPOSIT
            event.event_subtype = HistoryEventSubType.DEPOSIT_TO_PROTOCOL
            event.counterparty = CPT_FRANKENCOIN
            if event.location_label == user_address:
                event.notes = f'Deposit {amount} zCHF in Frankencoin Savings Module'
            else:
                # Attribute an on-behalf deposit to its savings owner.
                payer = event.location_label
                event.notes = f'Deposit {amount} zCHF in Frankencoin Savings Module by {payer}'
                event.location_label = user_address
        else:
            # Deposit initiated from an untracked address
            transfer_party = self._get_transfer_party(context=context, amount=amount)
            event_type = HistoryEventType.DEPOSIT
            event_subtype = HistoryEventSubType.DEPOSIT_TO_PROTOCOL
            notes = f'Deposit {amount} zCHF in Frankencoin Savings Module'
            if transfer_party is not None:
                notes += f' paid by {transfer_party}'
            context.decoded_events.append(self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=event_type,
                event_subtype=event_subtype,
                asset=self.zchf,
                amount=amount,
                location_label=user_address,
                notes=notes,
                counterparty=CPT_FRANKENCOIN,
                address=self.savings_address,
            ))

    def decode_withdrawn_topic(
            self,
            context: DecoderContext,
            amount: FVal,
            user_address: ChecksumEvmAddress,
    ) -> None:
        event = context.decoded_events[-1] if context.decoded_events else None
        if (
            event is not None and
            event.event_type == HistoryEventType.RECEIVE and
            event.event_subtype == HistoryEventSubType.NONE and
            event.amount == amount and
            event.address == self.savings_address and
            event.asset == self.zchf
        ):
            event.event_type = HistoryEventType.WITHDRAWAL
            event.event_subtype = HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
            event.counterparty = CPT_FRANKENCOIN
            if event.location_label == user_address:
                event.notes = f'Withdraw {amount} zCHF from Frankencoin Savings Module'
            else:
                # Attribute a withdrawal sent elsewhere to its savings owner.
                receiver = event.location_label
                event.notes = (
                    f'Withdraw {amount} zCHF from Frankencoin Savings Module to {receiver}'
                )
                event.location_label = user_address
        else:
            # Withdrawal sent to an untracked address
            transfer_party = self._get_transfer_party(context=context, amount=amount)
            event_type = HistoryEventType.WITHDRAWAL
            event_subtype = HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
            notes = f'Withdraw {amount} zCHF from Frankencoin Savings Module'
            if transfer_party is not None:
                notes += f' sent to {transfer_party}'
            context.decoded_events.append(self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=event_type,
                event_subtype=event_subtype,
                asset=self.zchf,
                amount=amount,
                location_label=user_address,
                notes=notes,
                counterparty=CPT_FRANKENCOIN,
                address=self.savings_address,
            ))

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        """Run the savings decoder only for logs emitted by this chain's deployment."""
        return {self.savings_address: (self._decode_savings_event,)}
