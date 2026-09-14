import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.cctp.constants import (
    CCTP_CPT_DETAILS,
    CCTP_DOMAIN_MAPPING,
    CCTP_SOLANA_DOMAIN,
    CPT_CCTP,
    DEPOSIT_FOR_BURN_V2,
    MESSAGE_RECEIVED_V2,
    MINT_AND_WITHDRAW_V2,
    USDC_DECIMALS,
)
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import set_bridge_extra_data
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, SupportedBlockchain
from rotkehlchen.utils.misc import bytes_to_address, bytes_to_solana_address

if TYPE_CHECKING:
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CctpV2CommonDecoder(EvmDecoderInterface):
    """Decoder for CCTP V2 contracts which use different event signatures from V1."""
    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
            token_messenger: ChecksumEvmAddress,
            message_transmitter: ChecksumEvmAddress,
            asset_identifier: str,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.token_messenger = token_messenger
        self.message_transmitter = message_transmitter
        self.asset_identifier = asset_identifier

    def _decode_deposit_v2(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode V2 DepositForBurn events. V2 adds maxFee, minFinalityThreshold, hookData."""
        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_EVM_DECODING_OUTPUT

        to_chain = int.from_bytes(context.tx_log.data[64:96])
        deposit_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token_decimals=USDC_DECIMALS,
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset.identifier == self.asset_identifier and
                event.amount == deposit_amount and
                event.location_label == user_address
            ):
                to_address: str | None
                if (mapped_to_chain := CCTP_DOMAIN_MAPPING.get(to_chain)) is not None:
                    to_chain_value: ChainID | int | str = mapped_to_chain
                    to_chain_label = mapped_to_chain.label()
                    to_address = bytes_to_address(context.tx_log.data[32:64])
                elif to_chain == CCTP_SOLANA_DOMAIN:
                    to_chain_value = SupportedBlockchain.SOLANA.serialize()
                    to_chain_label = 'Solana'
                    to_address = bytes_to_solana_address(context.tx_log.data[32:64])
                else:
                    log.error(f'Could not find chain ID {to_chain} for CCTP V2 transfer from {self.node_inquirer.chain_name}')  # noqa: E501
                    to_chain_value = to_chain
                    to_chain_label = str(to_chain)
                    to_address = None
                chain_info = f' from {self.node_inquirer.chain_id.label()} to {to_chain_label}'
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.notes = f'Bridge {event.amount} USDC{chain_info} via CCTP'
                event.counterparty = CPT_CCTP
                # V2 has no protocol transfer id in the source logs: the message nonce
                # is only assigned by Circle's attestation service at receive time.
                set_bridge_extra_data(
                    event=event,
                    from_chain=self.node_inquirer.chain_id,
                    to_chain=to_chain_value,
                    from_address=user_address,
                    to_address=to_address,
                )
                break
        else:
            log.error(f'Could not find matching spend event for {self.node_inquirer.chain_name} CCTP V2 bridge deposit {context.transaction.tx_hash!s}')  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_withdraw_v2(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode V2 MintAndWithdraw events. V2 adds feeCollected param."""
        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        deposit_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token_decimals=USDC_DECIMALS,
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset.identifier == self.asset_identifier and
                event.amount == deposit_amount and
                event.location_label == user_address
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.notes = f'Bridge {event.amount} USDC via CCTP'
                event.counterparty = CPT_CCTP
                set_bridge_extra_data(
                    event=event,
                    from_chain=None,
                    to_chain=self.node_inquirer.chain_id,
                    to_address=user_address,
                )
                break
        else:
            log.error(f'Could not find matching receive event for {self.node_inquirer.chain_name} CCTP V2 bridge withdrawal {context.transaction.tx_hash!s}')  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_message_received_v2(self, context: DecoderContext) -> EvmDecodingOutput:
        """Adds chain information to event notes for V2 withdrawals.
        V2 MessageReceived uses bytes32 nonce instead of uint64 and adds sender."""
        if context.tx_log.topics[0] != MESSAGE_RECEIVED_V2:
            return DEFAULT_EVM_DECODING_OUTPUT

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.WITHDRAWAL and
                event.event_subtype == HistoryEventSubType.BRIDGE and
                event.counterparty == CPT_CCTP
            ):
                from_chain = int.from_bytes(context.tx_log.data[:32])
                if (mapped_from_chain := CCTP_DOMAIN_MAPPING.get(from_chain)) is not None:
                    from_chain_value: ChainID | int | str = mapped_from_chain
                    from_chain_label = mapped_from_chain.label()
                elif from_chain == CCTP_SOLANA_DOMAIN:
                    from_chain_value = SupportedBlockchain.SOLANA.serialize()
                    from_chain_label = 'Solana'
                else:
                    log.error(f'Could not find chain ID {from_chain} for CCTP V2 transfer to {self.node_inquirer.chain_name}')  # noqa: E501
                    from_chain_value = from_chain
                    from_chain_label = str(from_chain)
                event.notes = f'Bridge {event.amount} USDC from {from_chain_label} to {self.node_inquirer.chain_id.label()} via CCTP'  # noqa: E501
                set_bridge_extra_data(
                    event=event,
                    from_chain=from_chain_value,
                    to_chain=self.node_inquirer.chain_id,
                    transfer_id=f'0x{context.tx_log.topics[2].hex()}',
                )
                break
        else:
            log.error(f'Could not find matching withdrawal event for {self.node_inquirer.chain_name} CCTP V2 bridge chain information {context.transaction.tx_hash!s}')  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_bridge_v2(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == DEPOSIT_FOR_BURN_V2:
            return self._decode_deposit_v2(context)

        if context.tx_log.topics[0] == MINT_AND_WITHDRAW_V2:
            return self._decode_withdraw_v2(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CCTP_CPT_DETAILS,)

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.token_messenger: (self._decode_bridge_v2,),
            self.message_transmitter: (self._decode_message_received_v2,),
        }
