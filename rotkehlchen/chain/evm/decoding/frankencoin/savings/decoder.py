from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.frankencoin.constants import CPT_FRANKENCOIN, ZCHF_ADDRESS
from rotkehlchen.chain.evm.decoding.frankencoin.decoder import FrankencoinCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_EVM_DECODING_OUTPUT
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    INTEREST_COLLECTED_TOPIC,
    SAVED_TOPIC,
    SAVINGS_CONTRACT_ADDRESS,
    WITHDRAWN_TOPIC,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext, EvmDecodingOutput
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
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
        # Select the deployment belonging to the decoder's current chain.
        self.savings = SAVINGS_CONTRACT_ADDRESS[evm_inquirer.chain_id]
        self.zchf = self.base.get_or_create_evm_token(address=ZCHF_ADDRESS[evm_inquirer.chain_id])

    def _decode_savings_event(self, context: DecoderContext) -> EvmDecodingOutput:
        """Turn raw savings logs/transfers into rotki history events.
        """
        topic = context.tx_log.topics[0]
        if topic not in (SAVED_TOPIC, INTEREST_COLLECTED_TOPIC, WITHDRAWN_TOPIC):
            return DEFAULT_EVM_DECODING_OUTPUT

        # The indexed account is the savings owner, which may differ from payer or receiver.
        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
                token_amount=int.from_bytes(context.tx_log.data[0:32]),
                token_decimals=self.zchf.decimals,
            )

        if topic in (SAVED_TOPIC, WITHDRAWN_TOPIC):
            # ZCHF emits its Transfer immediately before the Savings event.
            event = context.decoded_events[-1] if context.decoded_events else None
            if (
                event is not None and
                topic == SAVED_TOPIC and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == amount and
                event.address == self.savings and
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
                    event.extra_data = {'payer': payer}
                    event.location_label = user_address

            elif (
                    event is not None and
                    topic == WITHDRAWN_TOPIC and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.amount == amount and
                    event.address == self.savings and
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
                    event.notes = f'Withdraw {amount} zCHF from Frankencoin Savings Module to {receiver}'
                    event.extra_data = {'receiver': receiver}
                    event.location_label = user_address

            else:
                # An untracked endpoint produces no decoded transfer, so inspect its raw log.
                user = None
                try:
                    current_log_position = context.all_logs.index(context.tx_log)
                    if (current_log_position != 0 and
                        len(context.all_logs[current_log_position - 1].topics) == 3):
                        transfer_log = context.all_logs[current_log_position - 1]
                        from_address = bytes_to_address(transfer_log.topics[1])
                        to_address = bytes_to_address(transfer_log.topics[2])
                        if (transfer_log.address == self.zchf.evm_address and
                            transfer_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                            self.savings in (from_address, to_address) and
                            token_normalized_value_decimals(
                                token_amount=int.from_bytes(transfer_log.data),
                                token_decimals=self.zchf.decimals,
                            ) == amount
                        ):
                            if self.savings == from_address:
                                user = bytes_to_address(transfer_log.topics[2])
                            else:
                                user = bytes_to_address(transfer_log.topics[1])
                except ValueError:
                    user = None

                extra_data = None

                if topic == SAVED_TOPIC:
                    event_type = HistoryEventType.DEPOSIT
                    event_subtype = HistoryEventSubType.DEPOSIT_TO_PROTOCOL
                    notes = f'Deposit {amount} zCHF in Frankencoin Savings Module'
                    if user is not None:
                        notes += f' paid by {user}'
                        extra_data = {'payer': user}

                else:
                    event_type = HistoryEventType.WITHDRAWAL
                    event_subtype = HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
                    notes = f'Withdraw {amount} zCHF from Frankencoin Savings Module'
                    if user is not None:
                        notes += f' sent to {user}'
                        extra_data = {'receiver': user}

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
                        address=self.savings,
                        extra_data=extra_data,
                    ))

        elif topic == INTEREST_COLLECTED_TOPIC:
            # This is internal accounting; only net interest accrues to the saver.
            referral_fee = token_normalized_value_decimals(
                token_amount=int.from_bytes(context.tx_log.data[32:64]),
                token_decimals=self.zchf.decimals,
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
                address=self.savings,
            ))

        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        """Run the savings decoder only for logs emitted by this chain's deployment."""
        return {self.savings: (self._decode_savings_event,)}
