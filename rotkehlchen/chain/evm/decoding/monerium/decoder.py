import logging
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface, ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.monerium import init_monerium
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    BURN_MONERIUM_SIGNATURE,
    BURN_MONERIUM_SIGNATURE_V2,
    BURNFROM_MONERIUM_SIGNATURE,
    CPT_MONERIUM,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class MoneriumCommonDecoder(EvmDecoderInterface, ReloadableDecoderMixin):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
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

    def _v1_to_v2_migration_hashes(self) -> set[str]:
        """Hashes of the transactions minting v2 tokens by Monerium for the v1 to v2 migration
        Events in those transactions shouldn't be decoded as mints.
        Present in gnosis, polygon and ethereum.
        """
        return set()

    def _decode_mint_and_burn(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode mint and burn events for monerium"""
        if str(context.transaction.tx_hash) in self._v1_to_v2_migration_hashes():
            # stop processing the transaction if it is a migration from v1 to v2
            return EvmDecodingOutput(stop_processing=True)

        if context.tx_log.topics[0] != ERC20_OR_ERC721_TRANSFER:
            return DEFAULT_EVM_DECODING_OUTPUT

        from_address = bytes_to_address(value=context.tx_log.topics[1])
        to_address = bytes_to_address(value=context.tx_log.topics[2])

        token = get_or_create_evm_token(
            userdb=self.node_inquirer.database,
            evm_address=context.tx_log.address,
            chain_id=self.node_inquirer.chain_id,
            evm_inquirer=self.node_inquirer,
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

        return EvmDecodingOutput(
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

        try:
            self.monerium_api.update_events(events=decoded_events)
        except RemoteError as e:
            log.error(
                f'Failed to process monerium events in {decoded_events[0].tx_ref!s} on '
                f'{decoded_events[0].location} due to {e}. Skipping monerium post processing.',
            )

    # -- DecoderInterface methods

    def post_processing_rules(self) -> dict[str, tuple[Callable]]:
        return {CPT_MONERIUM: (self._handle_post_processing,)}

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(self.monerium_token_addresses, (self._decode_mint_and_burn,))

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(CPT_MONERIUM, 'Monerium', 'monerium.svg'),)
