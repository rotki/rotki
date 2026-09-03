import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import UNSTAKE_TOPIC, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.flying_tulip.constants import (
    CPT_FLYING_TULIP,
    FLYING_TULIP_LABEL,
)
from rotkehlchen.chain.evm.decoding.flying_tulip.decoder import FlyingTulipCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants import ONE
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import TokenKind
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    DIVESTED_TOPIC,
    FLYING_TULIP_PUT_DEPLOYMENTS,
    INVESTED_TOPIC,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class FlyingTulipPutCommonDecoder(FlyingTulipCommonDecoder):
    """Decode ftPUT activity (Flying Tulip's FT put positions).

    Investing allocates FT inside a put position NFT in exchange for
    collateral. Divesting returns collateral at the strike price, while
    withdrawing takes the allocated FT out of the position instead.
    """

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
        self.deployment = FLYING_TULIP_PUT_DEPLOYMENTS[evm_inquirer.chain_id]

    def _find_position_nft_event(
            self,
            context: DecoderContext,
            position_id: int,
            event_type: HistoryEventType,
    ) -> EvmEvent | None:
        """Return the transfer of the position NFT this event belongs to.

        A position is held as an ERC-721 whose token id is the position id, so
        the collateral that goes in is exchanged for the NFT and the NFT is
        given back to take the collateral out.
        """
        return self._find_matching_transfer(
            context=context,
            event_type=event_type,
            asset=Asset(evm_address_to_identifier(
                address=self.deployment.position_nft,
                chain_id=self.node_inquirer.chain_id,
                token_type=TokenKind.ERC721,
                collectible_id=str(position_id),
            )),
            amount=ONE,
            allowed_labels=None,
            allowed_addresses=(ZERO_ADDRESS,),
        )

    def _decode_position_return(
            self,
            context: DecoderContext,
            nft_event: EvmEvent,
            payout_event: EvmEvent | None,
            position_id: int,
    ) -> None:
        """Give the position back: the NFT is burned for what it paid out.

        The burn is decoded even without a payout to pair it with, since a
        payout that went to a wallet nobody tracks still closed the position.
        """
        nft_event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
        nft_event.notes = f'Return the {FLYING_TULIP_LABEL} put position #{position_id}'
        nft_event.counterparty = CPT_FLYING_TULIP
        maybe_reshuffle_events(
            ordered_events=[nft_event, payout_event],
            events_list=context.decoded_events,
        )

    def _decode_put_manager(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == INVESTED_TOPIC:
            # No tracked-participant gate here: the funder of a proxy invest for
            # another recipient appears only in the wallet transfer, which the
            # matcher below requires to belong to a tracked wallet anyway.
            investor = bytes_to_address(context.tx_log.data[0:32])
            position_id = int.from_bytes(context.tx_log.data[64:96])
            token = self.base.get_or_create_evm_token(
                address=bytes_to_address(context.tx_log.data[160:192]),
            )
            amount = token_normalized_value(
                token_amount=int.from_bytes(context.tx_log.data[192:224]),
                token=token,
            )
            # The position NFT is what the protocol gives back for the
            # collateral, so the deposit is only wrapped when it was minted here.
            nft_event = self._find_position_nft_event(
                context=context,
                position_id=position_id,
                event_type=HistoryEventType.RECEIVE,
            )
            # An investment is either funded straight into the manager, or the
            # user funds an investing proxy which then appears as the investor,
            # so the eligible transfer counterparties are exactly those two.
            # Any tracked wallet may be the funder (the proxy also allows
            # investing for a different position recipient).
            if (invest_event := self._transform_matching_event(
                context=context,
                from_event_type=HistoryEventType.SPEND,
                token=token,
                amount=amount,
                allowed_labels=None,
                allowed_addresses=(self.deployment.put_manager, investor),
                to_event_type=HistoryEventType.DEPOSIT,
                to_event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED if nft_event is not None else HistoryEventSubType.DEPOSIT_TO_PROTOCOL,  # noqa: E501
                notes=f'Invest {amount} {token.symbol} in {FLYING_TULIP_LABEL} put position #{position_id}',  # noqa: E501
            )) is None:
                log.debug('Found no matching transfer for a put event in %s', context.transaction)

            if nft_event is not None:
                # The position is the recipient's whoever paid for it, so it is
                # decoded even when the collateral came from a wallet nobody
                # tracks and there is no deposit to pair it with.
                nft_event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                nft_event.notes = f'Receive the {FLYING_TULIP_LABEL} put position #{position_id}'
                nft_event.counterparty = CPT_FLYING_TULIP
                maybe_reshuffle_events(
                    ordered_events=[invest_event, nft_event],
                    events_list=context.decoded_events,
                )
            return DEFAULT_EVM_DECODING_OUTPUT

        if (topic := context.tx_log.topics[0]) not in (DIVESTED_TOPIC, UNSTAKE_TOPIC):
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(owner := bytes_to_address(context.tx_log.data[0:32])):
            return DEFAULT_EVM_DECODING_OUTPUT

        position_id = int.from_bytes(context.tx_log.data[32:64])
        if topic == DIVESTED_TOPIC:
            token_address = bytes_to_address(context.tx_log.data[128:160])
            amount_raw = int.from_bytes(context.tx_log.data[160:192])
            allowed_addresses = self.deployment.collateral_wrappers | {self.deployment.put_manager}
            action = 'Divest'
        else:
            token_address = self.deployment.ft_token
            amount_raw = int.from_bytes(context.tx_log.data[64:96])
            allowed_addresses = frozenset((self.deployment.put_manager,))
            action = 'Withdraw'

        token = self.base.get_or_create_evm_token(address=token_address)
        amount = token_normalized_value(token_amount=amount_raw, token=token)
        nft_event = self._find_position_nft_event(
            context=context,
            position_id=position_id,
            event_type=HistoryEventType.SPEND,
        )
        if (payout_event := self._transform_matching_event(
            context=context,
            from_event_type=HistoryEventType.RECEIVE,
            token=token,
            amount=amount,
            allowed_labels=(owner,),
            allowed_addresses=allowed_addresses,
            to_event_type=HistoryEventType.WITHDRAWAL,
            to_event_subtype=HistoryEventSubType.REDEEM_WRAPPED if nft_event is not None else HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,  # noqa: E501
            notes=f'{action} {amount} {token.symbol} from {FLYING_TULIP_LABEL} put position #{position_id}',  # noqa: E501
        )) is None:
            log.debug('Found no matching transfer for a put event in %s', context.transaction)

        if nft_event is not None:
            self._decode_position_return(
                context=context,
                nft_event=nft_event,
                payout_event=payout_event,
                position_id=position_id,
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.deployment.put_manager: (self._decode_put_manager,)}
