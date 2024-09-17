from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.aave.common import Commonv2v3Decoder
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_DECODING_OUTPUT, DecodingOutput
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from ..constants import CPT_AAVE_V2
from .constants import BORROW, DEPOSIT, REPAY

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator


class Aavev2CommonDecoder(Commonv2v3Decoder):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            pool_address: 'ChecksumEvmAddress',
            native_gateways: 'tuple[ChecksumEvmAddress, ...]',
            incentives: 'ChecksumEvmAddress',
            incentives_reward_token: 'ChecksumEvmAddress',
    ):
        Commonv2v3Decoder.__init__(
            self,
            counterparty=CPT_AAVE_V2,
            label='AAVE v2',
            pool_address=pool_address,
            deposit_signature=DEPOSIT,
            borrow_signature=BORROW,
            repay_signature=REPAY,
            native_gateways=native_gateways,
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.incentives = incentives
        self.incentives_reward_token = incentives_reward_token

    def decode_liquidation(self, context: 'DecoderContext') -> None:
        """
        Decode AAVE v2 liquidations. When a liquidation happens the user returns the debt token
        and part of the collateral deposited is lost too. Those two events happen as transfers in
        a transaction started by the liquidator.
        """
        if not self.base.is_tracked(hex_or_bytes_to_address(context.tx_log.topics[3])):
            return

        for event in context.decoded_events:
            if event.event_type != HistoryEventType.SPEND:
                continue

            asset = event.asset.resolve_to_evm_token()
            if asset_normalized_value(
                amount=hex_or_bytes_to_int(context.tx_log.data[32:64]),  # liquidated amount
                asset=asset,
            ) == event.balance.amount and asset.protocol == CPT_AAVE_V2:
                # we are transfering the aTOKEN
                event.event_type = HistoryEventType.LOSS
                event.event_subtype = HistoryEventSubType.LIQUIDATE
                event.notes = f'An {self.label} position got liquidated for {event.balance.amount} {asset.symbol}'  # noqa: E501
                event.counterparty = CPT_AAVE_V2
                event.address = context.tx_log.address
            elif asset_normalized_value(
                amount=hex_or_bytes_to_int(context.tx_log.data[:32]),  # debt amount
                asset=asset,
            ) == event.balance.amount:
                # we are transfering the debt token
                event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                event.notes = f'Payback {event.balance.amount} {asset.symbol} for an {self.label} position'  # noqa: E501
                event.counterparty = CPT_AAVE_V2
                event.address = context.tx_log.address
                event.extra_data = {'is_liquidation': True}  # adding this field to the decoded event to differenciate paybacks happening in liquidations.  # noqa: E501

    def _decode_incentives(self, context: 'DecoderContext') -> DecodingOutput:
        if context.tx_log.topics[0] != b'V7\xd7\xf9b$\x8a\x7f\x05\xa7\xabi\xee\xc6Dn1\xf3\xd0\xa2\x99\xd9\x97\xf15\xa6\\b\x80nx\x91':  # RewardsClaimed  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        return self._decode_incentives_common(
            context=context,
            to_idx=2,
            claimer_raw=context.tx_log.topics[3],
            reward_token_address_32bytes=f'0x000000000000000000000000{self.incentives_reward_token[2:]}',
            amount_raw=context.tx_log.data[0:32],
        )

    # --- DecoderInterface methods

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_AAVE_V2,
            label=CPT_AAVE_V2.capitalize().replace('-v', ' V'),
            image='aave.svg',
        ),)

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            self.incentives: (self._decode_incentives,),
        }
