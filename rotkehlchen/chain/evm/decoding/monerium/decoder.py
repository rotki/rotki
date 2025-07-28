from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface, ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.externalapis.monerium import init_monerium
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    BURN_MONERIUM_SIGNATURE,
    BURN_MONERIUM_SIGNATURE_V2,
    BURNFROM_MONERIUM_SIGNATURE,
    CPT_MONERIUM,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator


class MoneriumCommonDecoder(DecoderInterface, ReloadableDecoderMixin):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            monerium_token_addresses: set[ChecksumEvmAddress],
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.monerium_token_addresses = monerium_token_addresses
        self.monerium_api = init_monerium(database=self.base.database)

    def reload_data(self) -> Mapping[ChecksumEvmAddress, tuple[Any, ...]] | None:
        """Reload the monerium api from the DB with the credentials"""
        self.monerium_api = init_monerium(database=self.base.database)
        return self.addresses_to_decoders()

    def _decode_mint_and_burn(self, context: DecoderContext) -> DecodingOutput:
        """Decode mint and burn events for monerium"""

        if context.tx_log.topics[0] != ERC20_OR_ERC721_TRANSFER:
            return DEFAULT_DECODING_OUTPUT

        from_address = bytes_to_address(value=context.tx_log.topics[1])
        to_address = bytes_to_address(value=context.tx_log.topics[2])

        token = get_or_create_evm_token(
            userdb=self.evm_inquirer.database,
            evm_address=context.tx_log.address,
            chain_id=self.evm_inquirer.chain_id,
            evm_inquirer=self.evm_inquirer,
        )
        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data),
            token_decimals=token.decimals,
        )

        # Not iterating over the events because the logic for decoding erc_20 transfers
        # has not been executed before calling this decoding logic
        event = None
        if from_address == ZERO_ADDRESS and self.base.is_tracked(to_address):  # Create mint event
            event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=token,
                amount=amount,
                location_label=to_address,
                notes=f'Mint {amount} {token.symbol_or_name()}',
                counterparty=CPT_MONERIUM,
            )

        elif (
                to_address == ZERO_ADDRESS and
                self.base.is_tracked(from_address) and
                context.transaction.input_data.startswith((BURN_MONERIUM_SIGNATURE, BURNFROM_MONERIUM_SIGNATURE, BURN_MONERIUM_SIGNATURE_V2))  # noqa: E501
        ):  # Create a burn event
            event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=token,
                amount=amount,
                location_label=from_address,
                notes=f'Burn {amount} {token.symbol_or_name()}',
                counterparty=CPT_MONERIUM,
            )

        return DecodingOutput(
            events=[event] if event is not None else None,
            refresh_balances=False,
            matched_counterparty=CPT_MONERIUM,
        )

    def _handle_post_processing(
            self,
            decoded_events: list['EvmEvent'],
            has_premium: bool,
    ) -> None:
        if self.monerium_api is None or not has_premium:
            return

        self.monerium_api.update_events(events=decoded_events)

    # -- DecoderInterface methods

    def post_processing_rules(self) -> dict[str, tuple[Callable]]:
        return {CPT_MONERIUM: (self._handle_post_processing,)}

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(self.monerium_token_addresses, (self._decode_mint_and_burn,))

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(CPT_MONERIUM, 'Monerium', 'monerium.svg'),)
