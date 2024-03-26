import logging
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.aave.common import Commonv2v3Decoder
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTokenKind
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from ..constants import AAVE_LABEL, CPT_AAVE_V3
from .constants import BORROW, BURN, DEPOSIT, REPAY

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Aavev3CommonDecoder(Commonv2v3Decoder):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            pool_address: 'ChecksumEvmAddress',
            eth_gateways: 'tuple[ChecksumEvmAddress, ...]',
            treasury: 'ChecksumEvmAddress',
    ):
        Commonv2v3Decoder.__init__(
            self,
            counterparty=CPT_AAVE_V3,
            label='AAVE v3',
            pool_address=pool_address,
            deposit_signature=DEPOSIT,
            borrow_signature=BORROW,
            repay_signature=REPAY,
            eth_gateways=eth_gateways,
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.treasury = treasury

    def decode_liquidation(self, context: 'DecoderContext') -> None:
        """
        Decode AAVE v3 liquidations. When a liquidation happens the user returns the debt token
        and part of the collateral deposited is lost too. Those two events happen as transfers in
        a transaction started by the liquidator.
        """
        if not self.base.is_tracked(hex_or_bytes_to_address(context.tx_log.topics[3])):  # liquidator  # noqa: E501
            return

        amounts = [  # payback amount and liquidation amount
            asset_normalized_value(
                amount=hex_or_bytes_to_int(log.data[:32]),
                asset=EvmToken(evm_address_to_identifier(
                    address=log.address,
                    token_type=EvmTokenKind.ERC20,
                    chain_id=self.evm_inquirer.chain_id,
                )),
            ) for log in context.all_logs
            if log.topics[0] == BURN and log.topics[1] == context.tx_log.topics[3]
        ]

        if len(amounts) != 2:
            log.warning(
                f'Found invalid number of payback and liquidation amounts '
                f'in AAVE v3 liquidation: {context.transaction.tx_hash.hex()}',
            )
            return

        for event in context.decoded_events:
            if event.event_type != HistoryEventType.SPEND:
                continue

            asset = event.asset.resolve_to_evm_token()
            if amounts[1] == event.balance.amount and event.address == ZERO_ADDRESS:
                # we are transfering the debt token
                event.event_subtype = HistoryEventSubType.LIQUIDATE
                event.notes = f'An {self.label} position got liquidated for {event.balance.amount} {asset.symbol}'  # noqa: E501
                event.counterparty = CPT_AAVE_V3
                event.address = context.tx_log.address
            elif amounts[0] == event.balance.amount and event.address == ZERO_ADDRESS:
                # we are transfering the aTOKEN
                event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                event.notes = f'Payback {event.balance.amount} {asset.symbol} for an {self.label} position'  # noqa: E501
                event.counterparty = CPT_AAVE_V3
                event.address = context.tx_log.address
                event.extra_data = {'is_liquidation': True}  # adding this field to the decoded event to differentiate paybacks happening in liquidations.  # noqa: E501
            elif event.address == self.treasury:  # fee
                event.event_subtype = HistoryEventSubType.FEE
                event.notes = f'Spend {event.balance.amount} {asset.symbol} as an {self.label} fee'
                event.counterparty = CPT_AAVE_V3

    @staticmethod  # DecoderInterface method
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_AAVE_V3, label=AAVE_LABEL, image='aave.svg'),)
