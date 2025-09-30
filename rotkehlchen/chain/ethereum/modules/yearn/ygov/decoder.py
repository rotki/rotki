import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.modules.yearn.constants import CPT_YGOV, YEARN_ICON
from rotkehlchen.chain.ethereum.modules.yearn.ygov.constants import YGOV_ADDRESS
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import REWARD_PAID_TOPIC_V2
from rotkehlchen.chain.evm.decoding.constants import STAKED, WITHDRAWN
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_DECODING_OUTPUT
from rotkehlchen.constants.assets import A_CRVP_DAIUSDCTTUSD, A_YFI
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext, DecodingOutput
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class YearnygovDecoder(EvmDecoderInterface):

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
        )

    def _decode_withdrawal(self, context: 'DecoderContext') -> None:
        """Handle withdraw from the governance contract"""
        withdrawn_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data),
            token_decimals=18,
        )

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_CRVP_DAIUSDCTTUSD and
                event.amount == withdrawn_amount
            ):
                event.counterparty = CPT_YGOV
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.notes = f'Withdraw {event.amount} YFI reward from ygov.finance'
                break

    def _decode_reward_token(self, context: 'DecoderContext') -> None:
        """Handle rewards claim"""
        withdrawn_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data),
            token_decimals=18,
        )

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_YFI and
                event.amount == withdrawn_amount
            ):
                event.counterparty = CPT_YGOV
                event.event_subtype = HistoryEventSubType.REWARD
                event.notes = f'Collect reward of {event.amount} YFI from ygov.finance'
                break

    def _decode_stake(self, context: 'DecoderContext') -> None:
        """Decode depositing the crv pool token in the gov contract"""
        staked_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data),
            token_decimals=18,
        )

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_CRVP_DAIUSDCTTUSD and
                event.amount == staked_amount
            ):
                event.counterparty = CPT_YGOV
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Deposit {event.amount} yDAI+yUSDC+yUSDT+yTUSD in ygov.finance'
                break

    def decode_gov_events(self, context: 'DecoderContext') -> 'DecodingOutput':
        if context.tx_log.topics[0] == REWARD_PAID_TOPIC_V2:
            self._decode_reward_token(context)
        elif context.tx_log.topics[0] == WITHDRAWN:
            self._decode_withdrawal(context)
        elif context.tx_log.topics[0] == STAKED:
            self._decode_stake(context)

        return DEFAULT_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {YGOV_ADDRESS: (self.decode_gov_events,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (
            CounterpartyDetails(
                identifier=CPT_YGOV,
                label='Yearn Governance',
                image=YEARN_ICON,
            ),
        )
