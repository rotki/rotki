from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import BURN_MONERIUM_SIGNATURE, CPT_MONERIUM

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class MoneriumCommonDecoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            native_asset: Asset,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.eure_token = native_asset.resolve_to_evm_token()

    def _decode_mint_and_burn(self, context: DecoderContext) -> DecodingOutput:
        """Decode mint and burn events for monerium"""

        if context.tx_log.topics[0] != ERC20_OR_ERC721_TRANSFER:
            return DEFAULT_DECODING_OUTPUT

        from_address = hex_or_bytes_to_address(value=context.all_logs[0].topics[1])
        to_address = hex_or_bytes_to_address(value=context.all_logs[0].topics[2])

        amount_raw = hex_or_bytes_to_int(value=context.tx_log.data)
        amount = token_normalized_value_decimals(
            token_amount=amount_raw,
            token_decimals=self.eure_token.decimals,
        )

        # Not iterating over the events because the logic for decoding erc_20 transfers
        # has not been executed before calling this decoding logic
        event = None
        if from_address == ZERO_ADDRESS:
            # Create a mint event
            event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=self.eure_token,
                balance=Balance(amount=amount),
                location_label=to_address,
                notes=f'Mint {amount} {self.eure_token.symbol}',
                counterparty=CPT_MONERIUM,
            )

        elif (
            to_address == ZERO_ADDRESS and
            context.transaction.input_data.startswith(BURN_MONERIUM_SIGNATURE)
        ):
            # Create a burn event
            event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=self.eure_token,
                balance=Balance(amount=amount),
                location_label=from_address,
                notes=f'Burn {amount} {self.eure_token.symbol}',
                counterparty=CPT_MONERIUM,
            )

        return DecodingOutput(event=event, refresh_balances=False)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.eure_token.evm_address: (self._decode_mint_and_burn,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(CPT_MONERIUM, 'Monerium', 'monerium.svg'),)
