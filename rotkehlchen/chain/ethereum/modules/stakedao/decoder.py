import logging
from typing import Any

from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, Timestamp
from rotkehlchen.utils.misc import bytes_to_address, timestamp_to_date

from .constants import (
    CLAIMED_WITH_BOUNTY,
    CLAIMED_WITH_BRIBE,
    CPT_STAKEDAO,
    STAKEDAO_CLAIMER1,
    STAKEDAO_CLAIMER2,
    STAKEDAO_CLAIMER_OLD,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class StakedaoDecoder(DecoderInterface):

    def _decode_claim(
            self,
            context: DecoderContext,
            reward_token_address: ChecksumEvmAddress,
            amount: int,
            period: Timestamp,
    ) -> DecodingOutput:
        """Base functionality for claiming different types of stakedao votemarket bribes"""
        claimed_token = get_or_create_evm_token(
            userdb=self.base.database,
            evm_address=reward_token_address,
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=self.evm_inquirer,
        )
        normalized_amount = token_normalized_value(amount, claimed_token)
        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.asset == claimed_token and event.amount == normalized_amount:  # noqa: E501
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_STAKEDAO
                event.notes = f'Claim {normalized_amount} {claimed_token.symbol} from StakeDAO veCRV bribes for the period starting at {timestamp_to_date(period, formatstr="%d/%m/%Y %H:%M:%S")}'  # noqa: E501
                event.product = EvmProduct.BRIBE
                break
        else:  # not found
            log.error(f'Stakedao bribe transfer was not found for {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_claim_with_bounty(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != CLAIMED_WITH_BOUNTY:
            return DEFAULT_DECODING_OUTPUT

        # we are not checking user address in the logs as user is not always
        # the recipient according to the contract
        reward_token_address = bytes_to_address(context.tx_log.data[0:32])
        amount = int.from_bytes(context.tx_log.data[32:64])
        period = Timestamp(int.from_bytes(context.tx_log.data[96:128]))
        return self._decode_claim(context=context, reward_token_address=reward_token_address, amount=amount, period=period)  # noqa: E501

    def _decode_claim_with_bribe(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != CLAIMED_WITH_BRIBE:
            return DEFAULT_DECODING_OUTPUT

        # we are not checking user address in the logs as user is not always
        # the recipient according to the contract
        reward_token_address = bytes_to_address(context.tx_log.topics[2])
        amount = int.from_bytes(context.tx_log.data[0:32])
        period = Timestamp(int.from_bytes(context.tx_log.data[32:64]))
        return self._decode_claim(context=context, reward_token_address=reward_token_address, amount=amount, period=period)  # noqa: E501

    # -- DecoderInterface methods

    @staticmethod
    def possible_products() -> dict[str, list[EvmProduct]]:
        return {
            CPT_STAKEDAO: [EvmProduct.BRIBE],
        }

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            STAKEDAO_CLAIMER1: (self._decode_claim_with_bounty,),
            STAKEDAO_CLAIMER2: (self._decode_claim_with_bounty,),
            STAKEDAO_CLAIMER_OLD: (self._decode_claim_with_bribe,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_STAKEDAO,
            label='Stakedao',
            image='stakedao.png',
        ),)
