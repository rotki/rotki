import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import TokenEncounterInfo
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEPOSIT_TOPIC, WITHDRAW_TOPIC_V3
from rotkehlchen.chain.evm.decoding.constants import ERC4626_ABI
from rotkehlchen.chain.evm.decoding.spark.constants import CPT_SPARK
from rotkehlchen.chain.evm.decoding.spark.decoder import SparkCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import SWAP_TOPIC

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SparksavingsCommonDecoder(SparkCommonDecoder):
    """Common decoder for Spark Savings protocol operations.

    This decoder handles Spark Savings yield-bearing token interactions:

    • Direct token deposits and withdrawals - ERC4626 vault operations for Spark tokens (sUSDS, sUSDC, sDAI, etc.)
    • PSM (Peg Stability Module) operations - Swapping between assets and their Spark Savings equivalents
    """  # noqa: E501
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            spark_savings_tokens: tuple['ChecksumEvmAddress', ...],
            psm_address: 'ChecksumEvmAddress | None' = None,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.psm_address = psm_address
        self.spark_savings_tokens = spark_savings_tokens

    def _decode_psm_deposit_withdrawal(self, context: DecoderContext) -> DecodingOutput:
        """Decodes PSM (Peg Stability Module) deposit and withdrawal events.
        PSM allows swapping between assets and their wrapped Spark Savings equivalents.
        """
        if context.tx_log.topics[0] != SWAP_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        asset_in = self.base.get_or_create_evm_token(bytes_to_address(context.tx_log.topics[1]))
        asset_out = self.base.get_or_create_evm_token(bytes_to_address(context.tx_log.topics[2]))
        amount_in = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=asset_in.decimals,
        )
        amount_out = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[64:96]),
            token_decimals=asset_out.decimals,
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == amount_in and
                event.asset == asset_in
            ):
                event.counterparty = CPT_SPARK
                if asset_in.evm_address not in self.spark_savings_tokens:
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                    event.notes = f'Deposit {amount_in} {asset_in.symbol} in Spark Savings'
                else:  # swap exact out
                    event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    event.notes = f'Return {amount_in} {asset_in.symbol} into Spark Savings'

            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == amount_out and
                event.asset == asset_out
            ):
                event.counterparty = CPT_SPARK
                if asset_out.evm_address in self.spark_savings_tokens:
                    event.event_type = HistoryEventType.RECEIVE
                    event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                    event.notes = f'Receive {amount_out} {asset_out.symbol} from depositing into Spark Savings'  # noqa: E501
                else:  # swap exact out
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                    event.notes = f'Remove {amount_out} {asset_out.symbol} from Spark Savings'

        return DEFAULT_DECODING_OUTPUT

    def _decode_spark_tokens_deposit_withdrawal(self, context: DecoderContext) -> DecodingOutput:
        """Decodes deposit and withdrawal events for Spark tokens (e.g., sUSDC).
        Similar to PSM deposits/withdrawals but for direct token interactions.
        """

        # skip if there are later deposit/withdraw events (we only want to process the last one)
        if (
            context.tx_log.topics[0] not in (DEPOSIT_TOPIC, WITHDRAW_TOPIC_V3) or
            any(
                log.log_index > context.tx_log.log_index and
                log.topics[0] in (DEPOSIT_TOPIC, WITHDRAW_TOPIC_V3)
                for log in context.all_logs
            )
        ):
            return DEFAULT_DECODING_OUTPUT

        vault_token = self.base.get_or_create_evm_token(
            address=context.tx_log.address,
            encounter=(encounter := TokenEncounterInfo(should_notify=False)),
        )
        underlying_token = self.base.get_or_create_evm_token(
            address=deserialize_evm_address(self.evm_inquirer.call_contract(
                contract_address=vault_token.evm_address,
                abi=ERC4626_ABI,
                method_name='asset',
            )),
            encounter=encounter,
        )

        underlying_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=underlying_token.decimals,
        )
        shares_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=vault_token.decimals,
        )
        in_event = out_event = None
        for event in context.decoded_events:
            if context.tx_log.topics[0] == DEPOSIT_TOPIC:
                if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.amount == underlying_amount and
                    # the native token check is for gnosis since xDAI can be deposited
                    event.asset in (underlying_token, self.evm_inquirer.native_token)
                ):
                    event.counterparty = CPT_SPARK
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                    event.notes = f'Deposit {underlying_amount} {event.asset.resolve_to_asset_with_symbol().symbol} in Spark Savings'  # noqa: E501
                    out_event = event
                elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.amount == shares_amount and
                    event.asset == vault_token
                ):
                    event.counterparty = CPT_SPARK
                    event.event_type = HistoryEventType.RECEIVE
                    event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                    event.notes = f'Receive {shares_amount} {vault_token.symbol} from depositing into Spark Savings'  # noqa: E501
                    in_event = event
            elif (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == shares_amount and
                event.asset == vault_token
            ):
                event.counterparty = CPT_SPARK
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.notes = f'Return {shares_amount} {vault_token.symbol} to Spark Savings'
                out_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == underlying_amount and
                # the native token check is for gnosis since xDAI can be deposited
                event.asset in (underlying_token, self.evm_inquirer.native_token)
            ):
                event.counterparty = CPT_SPARK
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.notes = f'Remove {underlying_amount} {event.asset.resolve_to_asset_with_symbol().symbol} from Spark Savings'  # noqa: E501
                in_event = event

        action_items = []
        if context.tx_log.topics[0] == DEPOSIT_TOPIC and in_event is None:
            # For deposits, create action item for the receive event that's not being decoded
            action_items.append(ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=vault_token,
                amount=shares_amount,
                to_event_type=HistoryEventType.RECEIVE,
                to_event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                to_notes=f'Receive {shares_amount} {vault_token.symbol} from depositing into Spark Savings',  # noqa: E501
                to_counterparty=CPT_SPARK,
                paired_events_data=([out_event] if out_event else [], True),
            ))
            return DecodingOutput(action_items=action_items)

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return DecodingOutput(action_items=action_items)

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        decoders = dict.fromkeys(self.spark_savings_tokens, (self._decode_spark_tokens_deposit_withdrawal,))  # noqa: E501
        if self.psm_address is not None:
            decoders |= {self.psm_address: (self._decode_psm_deposit_withdrawal,)}

        return decoders
