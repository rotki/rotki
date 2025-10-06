import logging
from typing import Any, Literal

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.decoding.constants import STAKED
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.resolver import tokenid_belongs_to_collection, tokenid_to_collectible_id
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    CLAIM_TOPIC,
    CPT_RUNMONEY,
    JOINED_TOPIC,
    RUNMONEY_CONTRACT_ADDRESS,
    RUNMONEY_MEMBERSHIP_NFT_COLLECTION_IDENTIFIER,
    UNSTAKE_TOPIC,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RunmoneyDecoder(EvmDecoderInterface):
    def _decode_join_event(self, context: DecoderContext) -> EvmDecodingOutput:
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == self.node_inquirer.native_token
            ):
                event.counterparty = CPT_RUNMONEY
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Pay {event.amount} ETH membership fee to join Runmoney club'
            elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    tokenid_belongs_to_collection(event.asset.identifier, RUNMONEY_MEMBERSHIP_NFT_COLLECTION_IDENTIFIER)  # noqa: E501
            ):
                event.counterparty = CPT_RUNMONEY
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive Runmoney membership NFT with id {tokenid_to_collectible_id(event.asset.identifier)} for joining the club'  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    @staticmethod
    def _decode_stake_unstake_event(
            context: DecoderContext,
            from_event_type: Literal[HistoryEventType.SPEND, HistoryEventType.RECEIVE],
            to_event_type: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL],
            to_event_subtype: Literal[HistoryEventSubType.DEPOSIT_ASSET, HistoryEventSubType.REMOVE_ASSET],  # noqa: E501
            action: Literal['deposit', 'withdraw'],
            preposition: Literal['into', 'from'],
    ) -> EvmDecodingOutput:
        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=6,  # usdc token has decimal=6
        )
        for event in context.decoded_events:
            if (
                    event.event_type == from_event_type and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.amount == amount
            ):
                event.counterparty = CPT_RUNMONEY
                event.event_type = to_event_type
                event.event_subtype = to_event_subtype
                event.notes = f'{action.capitalize()} {amount} USDC {preposition} Runmoney'
                break
        else:
            log.error(f'Failed to find runmoney {action} event for transaction {context.transaction}')  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    @staticmethod
    def _decode_claim_event(context: DecoderContext) -> EvmDecodingOutput:
        user_address = bytes_to_address(context.tx_log.topics[1])
        usdc_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=6,  # usdc token has decimal=6
        )
        eth_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            if (
                    event.event_type in (HistoryEventType.RECEIVE, HistoryEventType.WITHDRAWAL) and
                    event.amount in (usdc_amount, eth_amount)
            ):  # no break statement here because we expect two events
                event.counterparty = CPT_RUNMONEY
                event.location_label = user_address
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.REWARD
                event.notes = f'Claim {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} as interest earned from Runmoney'  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_runmoney_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """This decodes the following runmoney.app events:
            - Joined: club membership events (eth fee payment + nft receipt)
            - Staked: usdc deposits into the protocol
            - Unstaked: usdc withdrawals from the protocol
            - BonusClaimed: interest payments in usdc and eth
        """
        if context.tx_log.topics[0] == JOINED_TOPIC:
            return self._decode_join_event(context)

        if context.tx_log.topics[0] == STAKED:
            return self._decode_stake_unstake_event(
                context=context,
                action='deposit',
                from_event_type=HistoryEventType.SPEND,
                to_event_type=HistoryEventType.DEPOSIT,
                to_event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                preposition='into',
            )

        if context.tx_log.topics[0] == UNSTAKE_TOPIC:
            return self._decode_stake_unstake_event(
                context=context,
                action='withdraw',
                from_event_type=HistoryEventType.RECEIVE,
                to_event_type=HistoryEventType.WITHDRAWAL,
                to_event_subtype=HistoryEventSubType.REMOVE_ASSET,
                preposition='from',
            )

        if context.tx_log.topics[0] == CLAIM_TOPIC:
            return self._decode_claim_event(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {RUNMONEY_CONTRACT_ADDRESS: (self._decode_runmoney_events,)}

    @staticmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        return (CounterpartyDetails(
            identifier=CPT_RUNMONEY,
            label='Runmoney',
            image='runmoney.png',
        ),)
