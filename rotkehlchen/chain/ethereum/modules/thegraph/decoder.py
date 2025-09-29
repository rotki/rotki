from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.modules.thegraph.constants import CONTRACT_STAKING
from rotkehlchen.chain.ethereum.utils import (
    token_normalized_value,
    token_normalized_value_decimals,
)
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.thegraph.constants import CPT_THEGRAPH
from rotkehlchen.chain.evm.decoding.thegraph.decoder import ThegraphCommonDecoder
from rotkehlchen.constants.assets import A_GRT
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    APPROVE_PROTOCOL,
    DELEGATION_TRANSFERRED_TO_L2,
    GRAPH_L1_LOCK_TRANSFER_TOOL,
    TOKEN_DESTINATIONS_APPROVED,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class ThegraphDecoder(ThegraphCommonDecoder):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            native_asset=A_GRT,
            staking_contract=CONTRACT_STAKING,
        )

    def _decode_delegation_transferred_to_l2(self, context: DecoderContext) -> DecodingOutput:
        """Decode a transfer delegating GRT from ethereum to arbitrum"""
        if context.tx_log.topics[0] != DELEGATION_TRANSFERRED_TO_L2:
            return self._decode_delegator_staking(context)

        delegator = bytes_to_address(context.tx_log.topics[1])
        delegator_l2 = bytes_to_address(context.tx_log.topics[2])
        user_address = self.get_user_address(delegator, delegator_l2)
        if not user_address or not self.base.any_tracked([user_address, delegator, delegator_l2]):
            return DEFAULT_DECODING_OUTPUT

        indexer = bytes_to_address(context.tx_log.topics[3])
        indexer_l2 = bytes_to_address(context.tx_log.data[:32])
        transferred_delegation_tokens = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[32:]),
            token=self.token,
        )
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=self.token,
            amount=FVal(transferred_delegation_tokens),
            notes=f'Delegation of {transferred_delegation_tokens} GRT transferred from indexer {indexer} to L2 indexer {indexer_l2}.',  # noqa: E501
            location_label=context.transaction.from_address,
            counterparty=CPT_THEGRAPH,
            address=context.transaction.to_address,
            extra_data={'delegator_l2': delegator_l2, 'indexer_l2': indexer_l2, 'beneficiary': user_address},  # noqa: E501
            product=EvmProduct.STAKING,
        )
        return DecodingOutput(events=[event])

    def _decode_token_destination_approved(self, context: DecoderContext) -> DecodingOutput:
        """Decode a TokenDestinationsApproved event from the L1 bridge. This event is emitted
        when a user approves a token destination to be used for delegation in L2. We use this
        to query the logs to find the delegation address."""
        if context.tx_log.topics[0] != TOKEN_DESTINATIONS_APPROVED:
            return DEFAULT_DECODING_OUTPUT

        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=self.token,
            amount=ZERO,
            location_label=context.transaction.from_address,
            notes='Approve contract transfer',
            counterparty=CPT_THEGRAPH,
            address=context.tx_log.address,
        )
        return DecodingOutput(events=[event])

    def _decode_contract_deposit(self, context: DecoderContext) -> DecodingOutput:
        """Decode a deposit of ETH to cover the arbitrum fees of delegating GRT"""
        user_address = self.get_user_address(bytes_to_address(context.tx_log.topics[1]))
        if not user_address or not self.base.is_tracked(user_address):
            return DEFAULT_DECODING_OUTPUT

        indexer = bytes_to_address(context.tx_log.topics[1])
        raw_amount = int.from_bytes(context.tx_log.data)
        amount = token_normalized_value_decimals(raw_amount, DEFAULT_TOKEN_DECIMALS)
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == context.transaction.from_address and
                event.amount == amount
            ):
                event.event_subtype = HistoryEventSubType.FEE
                event.notes = f'Deposit {event.amount} ETH to {event.address} contract to pay for the gas in L2.'  # noqa: E501
                event.counterparty = CPT_THEGRAPH
                event.extra_data = {'indexer': indexer}
                break

        return DEFAULT_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.staking_contract: (self._decode_delegation_transferred_to_l2,),
            GRAPH_L1_LOCK_TRANSFER_TOOL: (self._decode_contract_deposit,),
        }

    def decoding_by_input_data(self) -> dict[bytes, dict[bytes, Callable]]:
        return {APPROVE_PROTOCOL: {TOKEN_DESTINATIONS_APPROVED: self._decode_token_destination_approved}}  # noqa: E501
