from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.modules.aave.common import Commonv2v3Decoder
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from ..constants import AAVE_LABEL, CPT_AAVE_V2
from .constants import BORROW, DEPOSIT, ETH_GATEWAYS, POOL_ADDRESS, REPAY

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Aavev2Decoder(Commonv2v3Decoder):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ):
        Commonv2v3Decoder.__init__(
            self,
            counterparty=CPT_AAVE_V2,
            label='AAVE v2',
            pool_address=POOL_ADDRESS,
            deposit_signature=DEPOSIT,
            borrow_signature=BORROW,
            repay_signature=REPAY,
            eth_gateways=ETH_GATEWAYS,
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )

    def decode_liquidation(
            self,
            context: 'DecoderContext',
    ) -> None:
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

    @staticmethod  # DecoderInterface method
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_AAVE_V2, label=AAVE_LABEL, image='aave.svg'),)
