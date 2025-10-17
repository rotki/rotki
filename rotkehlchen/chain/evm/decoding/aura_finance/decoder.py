import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import (
    asset_normalized_value,
    token_normalized_value_decimals,
)
from rotkehlchen.chain.evm.constants import (
    DEFAULT_TOKEN_DECIMALS,
    DEPOSIT_TOPIC,
    REWARD_PAID_TOPIC_V2,
    WITHDRAWN_TOPIC,
    ZERO_ADDRESS,
)
from rotkehlchen.chain.evm.decoding.aura_finance.constants import CPT_AURA_FINANCE
from rotkehlchen.chain.evm.decoding.balancer.constants import CPT_BALANCER_V2
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

LOCK_4BYTE: Final = b'K\xbc\x17\n'
GET_REWARD_4BYTE: Final = b'pP\xcc\xd9'
CLAIM_REWARDS_L1_4BYTE: Final = b'\xd3F@\xb2'
CLAIM_REWARDS_L2_4BYTE: Final = b'\xc6\xa0y`'
WITHDRAW_AND_UNWRAP_4BYTE: Final = b'\xc3.r\x02'
LOCK_ETHEREUM_AND_BASE_4BYTE: Final = b'(-?\xdf'

LOCKED_TOPIC: Final = b'\x9f\x1e\xc8\xc8\x80\xf7g\x98\xe7\xb7\x932]b^\x9b`\xe4\x08*U<\x98\xf4+l\xda6\x8d\xd6\x00\x08'  # noqa: E501
AURA_STAKED_TOPIC: Final = b'\x14I\xc6\xddxQ\xab\xc3\n\xbf7\xf5w\x15\xf4\x92\x01\x05\x19\x14|\xc2e/\xbc8 ,\x18\xa6\xee\x90'  # noqa: E501
DEPOSITED_TOPIC: Final = b's\xa1\x9d\xd2\x10\xf1\xa7\xf9\x02\x192\x14\xc0\xee\x91\xdd5\xee[M\x92\x0c\xba\x8dQ\x9e\xcae\xa7\xb4\x88\xca'  # noqa: E501

AURA_BAL_VAULT_ADDRESS = string_to_evm_address('0x4EA9317D90b61fc28C418C247ad0CA8939Bbb0e9')
AURA_L2_BOOSTER_LITE_ADDRESS = string_to_evm_address('0x98Ef32edd24e2c92525E59afc4475C1242a30184')
AURA_ETHEREUM_BOOSTER_ADDRESS = string_to_evm_address('0xA57b8d98dAE62B26Ec3bcC4a365338157060B234')

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AuraFinanceCommonDecoder(EvmDecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            claim_zap_address: ChecksumEvmAddress,
            base_reward_tokens: tuple['Asset', 'Asset'],  # this is always the AURA and BAL tokens of the chain  # noqa: E501
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.claim_zap_address = claim_zap_address
        self.base_reward_tokens = base_reward_tokens

    def _decode_lock_aura(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes locking AURA events on Ethereum and Base (vlAURA)."""
        locked_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == locked_amount
            ):
                event.counterparty = CPT_AURA_FINANCE
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Lock {locked_amount} {event.asset.resolve_to_asset_with_symbol().symbol} in auraLocker (vlAURA)'  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_lock_aura_bridged(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes locking AURA events on bridged chains (excluding Ethereum)."""
        locked_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        refund_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == self.node_inquirer.native_token
            ):  # Refund event (if any) comes first
                refund_event = event
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == self.node_inquirer.native_token
            ):
                event.counterparty = CPT_AURA_FINANCE
                event.event_subtype = HistoryEventSubType.FEE
                # Calculate bridge fee, accounting for potential refunds
                actual_bridge_fee = event.amount if refund_event is None else event.amount - refund_event.amount  # noqa: E501
                event.amount = actual_bridge_fee
                event.notes = f'Pay {actual_bridge_fee} {self.node_inquirer.native_token.symbol} as bridge fee (to Ethereum)'  # noqa: E501
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == locked_amount and
                event.address == ZERO_ADDRESS
            ):
                event.counterparty = CPT_AURA_FINANCE
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Lock {locked_amount} {event.asset.resolve_to_asset_with_symbol().symbol} in Aura Finance (bridged)'  # noqa: E501

        if refund_event:  # Remove refund event; it's factored into the bridge fee
            context.decoded_events.remove(refund_event)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_reward_claims(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes Aura Finance reward claiming events.

        It handles three types of reward transactions: 'getReward', 'claimRewards'
        and `withdrawAndUnwrap`.

        `getReward` transactions are to only claim AURA and BAL rewards.
        `claimRewards` transactions handle other reward tokens (including AURA and BAL).
        `withdrawAndUnwrap` transactions withdraw the BPT token and may claim the rewards.
        """
        recipient = bytes_to_address(context.tx_log.topics[1])
        amount_paid = int.from_bytes(context.tx_log.data[:32])
        is_aura_transaction = False
        for event in context.decoded_events:
            # this is_aura_transaction is needed for the case of withdrawals + claim rewards.
            # Since we don't have a way to detect if the transaction is claiming rewards.
            is_aura_transaction = is_aura_transaction or event.counterparty == CPT_AURA_FINANCE
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == recipient and
                (event.asset in self.base_reward_tokens or is_aura_transaction) and
                (
                    # there's an aura token transfer as reward but the RewardPaid
                    # event is not emitted for that so that's handled here.
                    event.amount == asset_normalized_value(
                        amount=amount_paid,
                        asset=(crypto_asset := event.asset.resolve_to_crypto_asset()),
                    ) or
                    event.asset in self.base_reward_tokens
                )
            ):
                event.notes = f'Claim {event.amount} {crypto_asset.symbol} from Aura Finance'
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_AURA_FINANCE

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_deposit_helper(
            self,
            context: DecoderContext,
            deposit_note_suffix: str,
            receive_note_suffix: str,
            received_amount:  FVal | None = None,
    ) -> EvmDecodingOutput:
        """Helper function to decode deposit events where a wrapped token is received.

        Handles both the deposit and wrapped token receiving events. Used for
        auraBAL deposits and booster deposits.
        """
        receive_event = None
        deposit_events: list[EvmEvent] = []
        deposited_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            token = event.asset.resolve_to_asset_with_symbol()
            if (
                (received_amount is None or event.amount == received_amount) and
                event.event_subtype == HistoryEventSubType.NONE and
                event.event_type == HistoryEventType.RECEIVE and
                event.address == ZERO_ADDRESS
            ):
                receive_event = event
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.notes = f'Receive {received_amount or event.amount} {token.symbol} {receive_note_suffix}'  # noqa: E501
                event.counterparty = CPT_AURA_FINANCE
            elif (
                ((
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE
                ) or (
                    event.event_type == HistoryEventType.DEPOSIT and
                    event.event_subtype == HistoryEventSubType.DEPOSIT_FOR_WRAPPED and
                    event.counterparty == CPT_BALANCER_V2
                )) and
                event.amount == deposited_amount
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Deposit {deposited_amount} {token.symbol} {deposit_note_suffix}'
                event.counterparty = CPT_AURA_FINANCE
                deposit_events.append(event)

        maybe_reshuffle_events(
            events_list=context.decoded_events,
            ordered_events=deposit_events + [receive_event],
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_withdraw(self, context: DecoderContext) -> EvmDecodingOutput:
        """This logic processes withdrawals from aura that return BPT tokens"""
        withdrawn_amount_raw = int.from_bytes(context.tx_log.data[0:32])
        user_address = bytes_to_address(context.tx_log.topics[1])
        withdrawn_amount = token_normalized_value_decimals(
            token_amount=withdrawn_amount_raw,
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == withdrawn_amount
            ):
                event.notes = f'Withdraw {withdrawn_amount} {event.asset.symbol_or_name()} from an Aura gauge'  # noqa: E501
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.counterparty = CPT_AURA_FINANCE

                # find the address of the aura vault so we can transform the burning event. The
                # address appears in the `to` of the transaction and not in any other event that
                # we can use to match. The strategy here is to find a burn of tokens that happens
                # with the same amount.
                aura_pool_contract_addr = None
                for log_event in context.all_logs:
                    if log_event.log_index < context.tx_log.log_index:
                        continue

                    if (
                        log_event.topics[0] == ERC20_OR_ERC721_TRANSFER and
                        bytes_to_address(log_event.topics[2]) == ZERO_ADDRESS and
                        log_event.data[0:32] == context.tx_log.data[0:32]
                    ):
                        aura_pool_contract_addr = log_event.address
                        break
                else:
                    log.error(f'Failed to match the burn event of aura tokens in {context.transaction}')  # noqa: E501
                    return DEFAULT_EVM_DECODING_OUTPUT

                aura_token = self.base.get_or_create_evm_token(address=aura_pool_contract_addr)
                action_item = ActionItem(
                    action='transform',
                    from_event_type=HistoryEventType.SPEND,
                    from_event_subtype=HistoryEventSubType.NONE,
                    asset=aura_token,
                    amount=withdrawn_amount,
                    location_label=user_address,
                    to_event_subtype=HistoryEventSubType.RETURN_WRAPPED,
                    to_counterparty=CPT_AURA_FINANCE,
                    to_notes=f'Return {withdrawn_amount} {aura_token.symbol_or_name()} to Aura',
                    paired_events_data=((event,), False),
                )
                return EvmDecodingOutput(action_items=[action_item])

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_deposit_aura_bal(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes auraBAL deposit events (Base, Arbitrum, Polygon)."""
        if context.tx_log.topics[0] != DEPOSIT_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        received_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        return self._decode_deposit_helper(
            context=context,
            received_amount=received_amount,
            deposit_note_suffix='into auraBAL vault',
            receive_note_suffix='from auraBAL vault',
        )

    def _decode_booster_event(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes booster deposit events."""
        if context.tx_log.topics[0] == DEPOSITED_TOPIC:
            return self._decode_deposit_helper(
                context=context,
                deposit_note_suffix='into an Aura gauge',
                receive_note_suffix='from an Aura gauge',
            )

        if context.tx_log.topics[0] == WITHDRAWN_TOPIC:
            return self._decode_withdraw(context=context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        if self.node_inquirer.chain_id == ChainID.ETHEREUM:
            return {
                AURA_ETHEREUM_BOOSTER_ADDRESS: (self._decode_booster_event,),
            }

        return {
            AURA_BAL_VAULT_ADDRESS: (self._decode_deposit_aura_bal,),
            AURA_L2_BOOSTER_LITE_ADDRESS: (self._decode_booster_event,),
        }

    def decoding_by_input_data(self) -> dict[bytes, dict[bytes, Callable]]:
        decoders = {
            GET_REWARD_4BYTE: {REWARD_PAID_TOPIC_V2: self._decode_reward_claims},
            CLAIM_REWARDS_L1_4BYTE: {REWARD_PAID_TOPIC_V2: self._decode_reward_claims},
            CLAIM_REWARDS_L2_4BYTE: {REWARD_PAID_TOPIC_V2: self._decode_reward_claims},
            WITHDRAW_AND_UNWRAP_4BYTE: {REWARD_PAID_TOPIC_V2: self._decode_reward_claims},
        }
        if self.node_inquirer.chain_id in (ChainID.ETHEREUM, ChainID.BASE):
            decoders[LOCK_ETHEREUM_AND_BASE_4BYTE] = {AURA_STAKED_TOPIC: self._decode_lock_aura}
        if self.node_inquirer.chain_id != ChainID.ETHEREUM:
            decoders[LOCK_4BYTE] = {LOCKED_TOPIC: self._decode_lock_aura_bridged}

        return decoders

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_AURA_FINANCE,
            label='Aura Finance',
            image='aura-finance.png'),
        )
