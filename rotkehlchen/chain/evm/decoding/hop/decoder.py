import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.utils import (
    token_normalized_value,
    token_normalized_value_decimals,
)
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.hop.constants import CPT_HOP, HOP_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.hop.structures import HopBridgeEventData
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import (
    ADD_LIQUIDITY,
    REMOVE_LIQUIDITY,
    REMOVE_LIQUIDITY_ONE,
    REWARDS_PAID,
    STAKED,
    TOKEN_SWAP,
    TRANSFER_FROM_L1_COMPLETED,
    TRANSFER_SENT,
    WITHDRAWAL_BONDED,
    WITHDRAWN,
    WITHDREW,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class HopCommonDecoder(DecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            bridges: dict[ChecksumEvmAddress, HopBridgeEventData],
            reward_contracts: set[ChecksumEvmAddress],
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.bridges = bridges
        # this maps each saddle swap address to its corresponding asset identifier
        self.swaps_to_asset = {
            value.saddle_swap: value.identifier
            for _, value in bridges.items()
            if value.saddle_swap is not None
        }
        self.reward_contracts = reward_contracts

    def _get_bridge_asset_amount(self, amount_raw: int, identifier: str) -> FVal:
        """Normalize raw amount based on bridge asset type."""
        if identifier == A_ETH.identifier:
            return token_normalized_value_decimals(amount_raw, DEFAULT_TOKEN_DECIMALS)

        return token_normalized_value(amount_raw, Asset(identifier).resolve_to_evm_token())

    def _generate_bridge_note(
            self,
            amount: FVal,
            asset: Asset,
            recipient: ChecksumEvmAddress | None = None,
            sender: ChecksumEvmAddress | None = None,
            chain_id: int | None = None,
    ) -> str:
        """Generate a note for bridging a specified amount of an asset to a recipient address."""
        chain_label = ''

        if chain_id is not None:
            try:
                chain_label = f'to {ChainID.deserialize(chain_id).label()} '
            except DeserializationError:
                chain_label = ''

        target_str = ''
        if recipient and sender and recipient != sender:
            target_str = f'at address {recipient} '

        return f'Bridge {amount} {asset.symbol_or_name()} {chain_label}{target_str}via Hop protocol'  # noqa: E501

    def _decode_withdrawal_bonded(self, context: DecoderContext) -> DecodingOutput:
        """This function is used to decode the WithdrawalBonded events on Hop protocol."""
        if not self.base.is_tracked(hex_or_bytes_to_address(context.transaction.input_data[4:36])):
            return DEFAULT_DECODING_OUTPUT

        if (bridge := self.bridges.get(context.tx_log.address)) is None:
            return DEFAULT_DECODING_OUTPUT

        for event in context.decoded_events:
            if (
                event.address in (bridge.amm_wrapper, context.tx_log.address) and
                event.asset.identifier == bridge.identifier and
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.notes = self._generate_bridge_note(
                    amount=event.balance.amount, asset=event.asset,
                )
                event.counterparty = CPT_HOP
                break

        else:
            asset = Asset(bridge.identifier)
            amount = hex_or_bytes_to_int(context.transaction.input_data[36:68])
            bonder_fee = hex_or_bytes_to_int(context.transaction.input_data[100:132])
            norm_amount = token_normalized_value(
                token_amount=amount - bonder_fee, token=asset.resolve_to_evm_token(),
            )
            action_item = ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=asset,
                to_event_type=HistoryEventType.WITHDRAWAL,
                to_event_subtype=HistoryEventSubType.BRIDGE,
                to_notes=self._generate_bridge_note(amount=norm_amount, asset=asset),
                to_counterparty=CPT_HOP,
            )
            return DecodingOutput(action_items=[action_item])

        return DEFAULT_DECODING_OUTPUT

    def _decode_transfer_sent(self, context: DecoderContext) -> DecodingOutput:
        """This function is used to decode the TransferSentToL2 events on Hop protocol."""
        if not self.base.is_tracked(recipient := hex_or_bytes_to_address(context.tx_log.topics[3])):  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        if (bridge := self.bridges.get(context.tx_log.address)) is None:
            return DEFAULT_DECODING_OUTPUT

        amount_raw = hex_or_bytes_to_int(context.tx_log.data[:32])
        amount = self._get_bridge_asset_amount(amount_raw=amount_raw, identifier=bridge.identifier)
        bonder_fee_raw = hex_or_bytes_to_int(context.tx_log.data[64:96])
        bonder_fee = token_normalized_value_decimals(bonder_fee_raw, DEFAULT_TOKEN_DECIMALS)
        for event in context.decoded_events:
            if (
                event.address in (bridge.amm_wrapper, context.tx_log.address) and
                event.asset.identifier == bridge.identifier and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_HOP

                if bonder_fee > ZERO:
                    event.balance.amount = amount - bonder_fee
                    fee_event = self.base.make_event_next_index(
                        tx_hash=event.tx_hash,
                        timestamp=context.transaction.timestamp,
                        event_type=HistoryEventType.SPEND,
                        event_subtype=HistoryEventSubType.FEE,
                        asset=event.asset,
                        balance=Balance(amount=bonder_fee),
                        location_label=event.location_label,
                        notes=f'Spend {bonder_fee} {event.asset.symbol_or_name()} as a hop fee',
                        counterparty=CPT_HOP,
                        address=event.address,
                    )
                    context.decoded_events.append(fee_event)
                    maybe_reshuffle_events(
                        ordered_events=[event, fee_event],
                        events_list=context.decoded_events,
                    )
                event.notes = self._generate_bridge_note(
                    amount=event.balance.amount,
                    asset=event.asset,
                    recipient=recipient,
                    sender=string_to_evm_address(event.location_label) if event.location_label else None,  # noqa: E501
                    chain_id=hex_or_bytes_to_int(context.tx_log.topics[2]),
                )
                break

            if (
                # send method (0xa6bd1b33) works differently than normal bridge events
                # this is returning the hTOKEN to redeem the TOKEN in L1
                # that's why we are considering it as a Burn below in the notes.
                event.address == ZERO_ADDRESS and
                event.asset.identifier == bridge.hop_identifier and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_HOP
                event.notes = f'Burn {event.balance.amount} of Hop {event.asset.symbol_or_name()}'
                break

        return DEFAULT_DECODING_OUTPUT

    def _decode_withdrawal(self, context: DecoderContext) -> DecodingOutput:
        """This function is used to decode the Withdrew event on Hop protocol."""
        if not self.base.is_tracked(hex_or_bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_DECODING_OUTPUT

        if (bridge := self.bridges.get(context.tx_log.address)) is None:
            return DEFAULT_DECODING_OUTPUT

        amount_raw = hex_or_bytes_to_int(context.tx_log.data[:32])
        amount = self._get_bridge_asset_amount(amount_raw=amount_raw, identifier=bridge.identifier)
        for event in context.decoded_events:
            if (
                event.address in (bridge.amm_wrapper, context.tx_log.address) and
                event.asset.identifier == bridge.identifier and
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.balance.amount == amount
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.notes = self._generate_bridge_note(
                    amount=event.balance.amount, asset=event.asset,
                )
                event.counterparty = CPT_HOP
                break

        else:
            # corresponding receive not found, create an ActionItem
            # to update the event when it's decoded
            asset = Asset(bridge.identifier)
            amount_raw = hex_or_bytes_to_int(context.transaction.input_data[36:68])
            bonder_fee = hex_or_bytes_to_int(context.transaction.input_data[100:132])
            norm_amount = token_normalized_value(
                token_amount=amount_raw - bonder_fee, token=asset.resolve_to_evm_token(),
            )
            action_item = ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=Asset(bridge.identifier),
                amount=norm_amount,
                to_event_type=HistoryEventType.WITHDRAWAL,
                to_event_subtype=HistoryEventSubType.BRIDGE,
                to_notes=self._generate_bridge_note(amount=norm_amount, asset=asset),
                to_counterparty=CPT_HOP,
            )
            return DecodingOutput(action_items=[action_item])

        return DEFAULT_DECODING_OUTPUT

    def _decode_transfer_from_l1(self, context: DecoderContext) -> DecodingOutput:
        """This function is used to decode the TRANSFER_FROM_L1_COMPLETED event on Hop protocol."""
        if not self.base.is_tracked(recipient := hex_or_bytes_to_address(context.tx_log.topics[1])):  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        if (bridge := self.bridges.get(context.tx_log.address)) is None:
            return DEFAULT_DECODING_OUTPUT

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and recipient == event.location_label and event.asset.identifier == bridge.identifier:  # noqa: E501
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_HOP
                event.notes = self._generate_bridge_note(
                    amount=event.balance.amount,
                    asset=event.asset,
                    recipient=recipient,
                    sender=string_to_evm_address(event.location_label) if event.location_label else None,  # noqa: E501
                )
                break

        return DecodingOutput(matched_counterparty=CPT_HOP)

    def _decode_token_swap(self, context: DecoderContext) -> DecodingOutput:
        """Decodes a TokenSwap event to set the proper bridged amount"""
        for item in context.action_items:
            if item.to_event_subtype == HistoryEventSubType.BRIDGE:
                tokens_bought = hex_or_bytes_to_int(context.tx_log.data[32:64])
                asset = item.asset.resolve_to_evm_token()
                amount = token_normalized_value(tokens_bought, asset)
                item.to_notes = self._generate_bridge_note(amount=amount, asset=asset)
                break
        return DEFAULT_DECODING_OUTPUT

    def _decode_add_liquidity(self, context: DecoderContext) -> DecodingOutput:
        if not self.base.is_tracked(user_address := hex_or_bytes_to_address(context.tx_log.topics[1])):  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        first_token_amount = token_normalized_value_decimals(
            token_amount=hex_or_bytes_to_int(context.tx_log.data[160:192]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        second_token_amount = token_normalized_value_decimals(
            token_amount=hex_or_bytes_to_int(context.tx_log.data[192:224]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        token_amounts = {x for x in (first_token_amount, second_token_amount) if x != ZERO}
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                event.balance.amount in token_amounts
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_HOP
                event.notes = f'Deposit {event.balance.amount} {event.asset.symbol_or_name()} to Hop'  # noqa: E501
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address
            ):
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_HOP
                event.notes = f'Receive {event.balance.amount} {event.asset.symbol_or_name()} after providing liquidity in Hop'  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_remove_liquidity(self, context: DecoderContext, lp_amount_raw: int) -> DecodingOutput:  # noqa: E501
        """Decodes RemoveLiquidity and RemoveLiquidityOne events.
        RemoveLiquidity is emitted when both sides of the liquidity pool are withdrawn,
        whereas RemoveLiquidityOne is emitted when only one side of the liquidity pool
        is withdrawn."""
        if (liquidity_data := self._decode_common_liquidity(context)) is None:
            return DEFAULT_DECODING_OUTPUT

        user_address, token_amounts = liquidity_data
        lp_amount = token_normalized_value_decimals(
            token_amount=lp_amount_raw,
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        return self._handle_event_decoding(
            decoded_events=context.decoded_events,
            user_address=user_address,
            lp_amount=lp_amount,
            token_amounts=token_amounts,
        )

    def _decode_common_liquidity(self, context: DecoderContext) -> tuple['ChecksumEvmAddress', set[FVal]] | None:  # noqa: E501
        """This function is used to decode the common resources of RemoveLiquidity and
        RemoveLiquidityOne events."""
        if not self.base.is_tracked(user_address := hex_or_bytes_to_address(context.tx_log.topics[1])):  # noqa: E501
            return None

        if (swap_asset_id := self.swaps_to_asset.get(context.tx_log.address)) is None:
            return None

        first_token_amount = self._get_bridge_asset_amount(
            amount_raw=hex_or_bytes_to_int(context.tx_log.data[96:128]),
            identifier=swap_asset_id,
        )
        second_token_amount = self._get_bridge_asset_amount(
            amount_raw=hex_or_bytes_to_int(context.tx_log.data[128:160]),
            identifier=swap_asset_id,
        )
        # Filtering out zero amounts to not clash with any other events
        # And here zero basically means asset not provided for LPing
        token_amounts = {x for x in (first_token_amount, second_token_amount) if x != ZERO}
        return user_address, token_amounts

    def _handle_event_decoding(
            self,
            decoded_events: list[EvmEvent],
            user_address: str,
            lp_amount: FVal,
            token_amounts: set[FVal],
    ) -> DecodingOutput:
        """This function is used to enrich the RemoveLiquidity and RemoveLiquidityOne events
        with proper event types and notes.
        """
        for event in decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                event.balance.amount == lp_amount
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_HOP
                event.notes = f'Return {event.balance.amount} {event.asset.symbol_or_name()}'
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                event.balance.amount in token_amounts
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_HOP
                event.notes = f'Withdraw {event.balance.amount} {event.asset.symbol_or_name()} from Hop'  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_saddle_swap(self, context: DecoderContext) -> DecodingOutput:
        """This function is used to decode the lp events done via Hop protocol."""
        if context.tx_log.topics[0] == TOKEN_SWAP:
            return self._decode_token_swap(context=context)

        if context.tx_log.topics[0] == ADD_LIQUIDITY:
            return self._decode_add_liquidity(context=context)

        if context.tx_log.topics[0] == REMOVE_LIQUIDITY:
            return self._decode_remove_liquidity(
                context=context,
                lp_amount_raw=hex_or_bytes_to_int(context.transaction.input_data[4:36]),
            )

        if context.tx_log.topics[0] == REMOVE_LIQUIDITY_ONE:
            return self._decode_remove_liquidity(
                context=context,
                lp_amount_raw=hex_or_bytes_to_int(context.tx_log.data[:32]),
            )

        return DEFAULT_DECODING_OUTPUT

    def _decode_staking_events(self, context: DecoderContext) -> DecodingOutput:
        """Decode events related to staking (stake, unstake, claim rewards) on Hop protocol."""
        if context.tx_log.topics[0] == STAKED:
            return self._decode_common_staking(
                context=context,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                action='Stake',
                preposition='in',
                product=EvmProduct.STAKING,
            )

        if context.tx_log.topics[0] == REWARDS_PAID:
            return self._decode_common_staking(
                context=context,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.REWARD,
                action='Claim',
                preposition='from',
            )

        if context.tx_log.topics[0] == WITHDRAWN:
            return self._decode_common_staking(
                context=context,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.REMOVE_ASSET,
                action='Unstake',
                preposition='from',
            )

        return DEFAULT_DECODING_OUTPUT

    def _decode_common_staking(
            self,
            context: DecoderContext,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            action: str,
            preposition: str,
            product: EvmProduct | None = None,
    ) -> DecodingOutput:
        amount = token_normalized_value_decimals(
            token_amount=hex_or_bytes_to_int(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            if (
                event.event_type == event_type and
                event.event_subtype == HistoryEventSubType.NONE and
                event.balance.amount == amount
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = event_subtype
                event.counterparty = CPT_HOP
                event.notes = f'{action} {amount} {event.asset.symbol_or_name()} {preposition} Hop'
                event.product = product
                break

        return DEFAULT_DECODING_OUTPUT

    def _decode_events(self, context: DecoderContext) -> DecodingOutput:
        """This function is used to decode the bridging events done via Hop protocol."""
        if context.tx_log.topics[0] == WITHDRAWAL_BONDED:
            return self._decode_withdrawal_bonded(context=context)

        if context.tx_log.topics[0] == TRANSFER_SENT:
            return self._decode_transfer_sent(context=context)

        if context.tx_log.topics[0] == WITHDREW:
            return self._decode_withdrawal(context=context)

        if context.tx_log.topics[0] == TRANSFER_FROM_L1_COMPLETED:
            return self._decode_transfer_from_l1(context=context)

        return DEFAULT_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        addresses = set(self.bridges.keys())
        saddle_swaps = {
            bridge.saddle_swap for bridge in self.bridges.values() if bridge.saddle_swap
        }
        return (
            dict.fromkeys(addresses, (self._decode_events,)) |
            dict.fromkeys(saddle_swaps, (self._decode_saddle_swap,)) |
            dict.fromkeys(self.reward_contracts, (self._decode_staking_events,))
        )

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (HOP_CPT_DETAILS,)
