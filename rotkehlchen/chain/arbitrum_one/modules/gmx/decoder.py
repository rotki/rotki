import logging
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.assets.asset import Asset, CryptoAsset
from rotkehlchen.chain.arbitrum_one.decoding.interfaces import ArbitrumDecoderInterface
from rotkehlchen.chain.arbitrum_one.modules.gmx.constants import (
    CPT_GMX,
    CREATE_INCREASE_TOPIC,
    EXECUTE_DECREASE_ABI,
    EXECUTE_DECREASE_TOPIC,
    EXECUTE_INCREASE_ABI,
    GMX_POSITION_ROUTER,
    GMX_REWARD_ROUTER,
    GMX_ROUTER_ADDRESS,
    STAKE_GMX,
    SWAP_TOPIC,
)
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi_str
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.constants.assets import A_ETH, A_WETH_ARB
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _asset_matches(token: CryptoAsset, event_asset: Asset) -> bool:
    if token == A_WETH_ARB:
        return event_asset in (A_WETH_ARB, A_ETH)

    return token == event_asset


class GmxDecoder(ArbitrumDecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.eth = A_ETH.resolve_to_crypto_asset()

    def _decode_swap_event(self, context: DecoderContext) -> DecodingOutput:
        """Decodes swaps using the GMX vault"""
        if context.tx_log.topics[0] != SWAP_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        account = bytes_to_address(context.tx_log.data[0:32])
        if self.base.is_tracked(account) is False:
            return DEFAULT_DECODING_OUTPUT

        token_out = self.base.get_or_create_evm_asset(bytes_to_address(context.tx_log.data[32:64]))
        token_in = self.base.get_or_create_evm_asset(bytes_to_address(context.tx_log.data[64:96]))
        amount_out = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[96:128]),
            asset=token_out,
        )
        amount_in = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[128:160]),
            asset=token_in,
        )

        out_event = in_event = None
        for event in context.decoded_events:
            if (
                event.asset == token_out and
                event.event_type == HistoryEventType.SPEND and
                event.amount == amount_out
            ):
                event.counterparty = CPT_GMX
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Swap {event.amount} {token_out.symbol} in GMX'
                out_event = event
            elif (
                event.asset == token_in and
                event.event_type == HistoryEventType.RECEIVE and
                event.amount == amount_in
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {event.amount} {token_in.symbol} as the result of a GMX swap'  # noqa: E501
                in_event = event

        if not (out_event and in_event):
            return DEFAULT_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return DecodingOutput(process_swaps=True)

    def decode_position_change(self, context: DecoderContext) -> DecodingOutput:
        """Decode an increase or decrease in short/long positions in GMX V1"""
        verb_text: Literal['increase', 'decrease']
        if context.tx_log.topics[0] == CREATE_INCREASE_TOPIC:
            verb_text = 'increase'
            # event type to look for in the decoded events
            base_event_type = HistoryEventType.SPEND
            # new types of the decoded event
            event_type = HistoryEventType.DEPOSIT
            event_subtype = HistoryEventSubType.DEPOSIT_ASSET
            abi_code = EXECUTE_INCREASE_ABI
            # index in the decoded data for the fee amount
            fee_index = 7
        elif context.tx_log.topics[0] == EXECUTE_DECREASE_TOPIC:
            verb_text = 'decrease'
            base_event_type = HistoryEventType.RECEIVE
            event_type = HistoryEventType.WITHDRAWAL
            event_subtype = HistoryEventSubType.REMOVE_ASSET
            abi_code = EXECUTE_DECREASE_ABI
            fee_index = 8
        else:
            return DEFAULT_DECODING_OUTPUT

        account = bytes_to_address(context.tx_log.topics[1])
        if self.base.is_tracked(account) is False:
            return DEFAULT_DECODING_OUTPUT

        try:
            _, decoded_data = decode_event_data_abi_str(context.tx_log, abi_code)
        except DeserializationError as e:
            log.error(
                f'Failed to deserialize GMX event {verb_text=} at '
                f'{context.transaction.tx_hash.hex()} due to {e}',
            )
            return DEFAULT_DECODING_OUTPUT

        path_token = self.base.get_or_create_evm_asset(decoded_data[0][0])
        amount_change = asset_normalized_value(amount=decoded_data[2], asset=path_token)
        fee_amount = asset_normalized_value(amount=decoded_data[fee_index], asset=self.eth)
        is_long = decoded_data[5]
        transferred_amount = amount_change
        if path_token == A_WETH_ARB:
            transferred_amount += fee_amount

        for event in context.decoded_events:
            if (
                event.location_label == account and
                event.event_type == base_event_type and
                (
                    (verb_text == 'increase' and event.amount == transferred_amount) or
                    verb_text == 'decrease'  # when it is a decrease we don't know the amount that will be received  # noqa: E501
                ) and
                _asset_matches(token=path_token, event_asset=event.asset)
            ):
                event.counterparty = CPT_GMX
                event.event_type = event_type
                event.event_subtype = event_subtype
                position_type = 'long position' if is_long is True else 'short position'
                event_asset = event.asset.resolve_to_asset_with_symbol()
                if verb_text == 'increase':
                    event.amount = amount_change  # we will create a fee event
                    note_proposition = 'with'
                else:
                    note_proposition = 'withdrawing'

                event.notes = f'{verb_text.capitalize()} {position_type} {note_proposition} {event.amount} {event_asset.symbol} in GMX'  # noqa: E501

                # And now create a new event for the fee
                context.decoded_events.append(self.base.make_event_from_transaction(
                    transaction=context.transaction,
                    tx_log=context.tx_log,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=A_ETH,
                    amount=fee_amount,
                    location_label=event.location_label,
                    notes=f'Spend {fee_amount} ETH as GMX fee',
                    counterparty=CPT_GMX,
                    address=context.transaction.to_address,
                ))
                event.extra_data = {
                    'collateral_token': decoded_data[0][-1],
                    'index_token': decoded_data[1],
                    'is_long': is_long,
                }
                break  # stop iterating

        return DEFAULT_DECODING_OUTPUT

    def _decode_stake(self, context: DecoderContext) -> DecodingOutput:
        """Decode staking events in the GMX protocol for the GMX asset"""
        if context.tx_log.topics[0] != STAKE_GMX:
            return DEFAULT_DECODING_OUTPUT

        account = bytes_to_address(context.tx_log.data[0:32])
        token_addrs = bytes_to_address(context.tx_log.data[32:64])
        amount_raw = int.from_bytes(context.tx_log.data[64:96])

        staked_token = self.base.get_or_create_evm_asset(address=token_addrs)
        amount = asset_normalized_value(amount=amount_raw, asset=staked_token)

        for event in context.decoded_events:
            if (
                event.location_label == account and
                event.event_type == HistoryEventType.SPEND and
                event.amount == amount
            ):
                event.counterparty = CPT_GMX
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                # the contract when staking GMX also creates transfers for (sGMX, sbGMX, sbfGMX)
                asset = event.asset.resolve_to_crypto_asset()
                event.notes = f'Stake {amount} {asset.symbol} in GMX'
            elif (
                event.location_label == account and
                event.event_type == HistoryEventType.RECEIVE and
                event.amount == amount
            ):
                event.counterparty = CPT_GMX
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                asset = event.asset.resolve_to_crypto_asset()
                event.notes = f'Receive {event.amount} {asset.symbol} after staking in GMX'

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            GMX_ROUTER_ADDRESS: (self._decode_swap_event,),
            GMX_POSITION_ROUTER: (self.decode_position_change,),
            GMX_REWARD_ROUTER: (self._decode_stake,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (
            CounterpartyDetails(
                identifier=CPT_GMX,
                label='GMX',
                image='gmx.svg',
            ),
        )
