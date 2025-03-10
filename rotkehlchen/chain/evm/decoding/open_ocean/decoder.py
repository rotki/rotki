import logging
from abc import ABC
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.uniswap.constants import (
    UNISWAP_V2_SWAP_SIGNATURE,
    UNISWAP_V3_SWAP_SIGNATURE,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_OPENOCEAN, OPENOCEAN_EXCHANGE_ADDRESS, OPENOCEAN_LABEL, SWAPPED_TOPIC

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset, CryptoAsset
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OpenOceanDecoder(DecoderInterface, ABC):

    def _get_asset_and_amount(
            self,
            asset_address: 'ChecksumEvmAddress',
            raw_amount: int,
    ) -> tuple['CryptoAsset', 'FVal']:
        """Get asset and normalized amount from asset address and raw amount.
        Handles decimals when asset is native rather than an erc20 token.
        Uses native token if address is ZERO_ADDRESS:
        https://github.com/openocean-finance/OpenOceanExchangeV2/blob/5e83cc1cf0a29a3ab23e405f9528b876ff8b1478/contracts/libraries/UniversalERC20.sol#L62
        """
        asset = self.base.get_or_create_evm_asset(address=asset_address) if asset_address != ZERO_ADDRESS else self.evm_inquirer.native_token  # noqa: E501
        amount = token_normalized_value_decimals(
            token_amount=raw_amount,
            token_decimals=DEFAULT_TOKEN_DECIMALS if asset == self.evm_inquirer.native_token else asset.resolve_to_evm_token().decimals,  # noqa: E501
        )
        return asset, amount

    def _decode_swapped(self, context: DecoderContext) -> DecodingOutput:
        """Decode OpenOcean swaps that include a SWAPPED_TOPIC tx_log event."""
        if context.tx_log.topics[0] != SWAPPED_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        spend_asset, spend_amount = self._get_asset_and_amount(
            asset_address=bytes_to_address(context.tx_log.topics[2]),
            raw_amount=int.from_bytes(context.tx_log.data[64:96]),
        )
        receive_asset, receive_amount = self._get_asset_and_amount(
            asset_address=bytes_to_address(context.tx_log.topics[3]),
            raw_amount=int.from_bytes(context.tx_log.data[96:128]),
        )
        self._decode_swap(
            transaction=context.transaction,
            decoded_events=context.decoded_events,
            spend_asset=spend_asset,
            spend_amount=spend_amount,
            receive_asset=receive_asset,
            receive_amount=receive_amount,
        )
        return DEFAULT_DECODING_OUTPUT

    @staticmethod
    def _decode_swap(
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            spend_asset: 'Asset | None' = None,
            spend_amount: 'FVal | None' = None,
            receive_asset: 'Asset | None' = None,
            receive_amount: 'FVal | None' = None,
    ) -> None:
        """Decode OpenOcean swap in/out events.
        If assets and amounts are None they are ignored, and only the event type is matched.
        Checks TRADE event types in addition to the plain SPEND/RECEIVE since an event may
        have already been processed by a previous decoder like uniswap.
        Returns the list of decoded events.
        """
        in_event, out_event = None, None
        for event in decoded_events:
            if ((
                (event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE) or  # noqa: E501
                (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.SPEND)) and  # noqa: E501
                (spend_asset is None or event.asset == spend_asset) and
                (spend_amount is None or event.amount == spend_amount)
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Swap {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} in {OPENOCEAN_LABEL}'  # noqa: E501
                event.counterparty = CPT_OPENOCEAN
                out_event = event
            elif ((
                (event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE) or  # noqa: E501
                (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.RECEIVE)) and  # noqa: E501
                (receive_asset is None or event.asset == receive_asset) and
                (receive_amount is None or event.amount == receive_amount)
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from {OPENOCEAN_LABEL} swap'  # noqa: E501
                event.counterparty = CPT_OPENOCEAN
                in_event = event

        if in_event is None or out_event is None:
            log.warning(f'Failed to find both out and in events for {OPENOCEAN_LABEL} swap transaction {transaction}')  # noqa: E501

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=decoded_events,
        )

    def _handle_post_decoding(
            self,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """Handle post decoding for OpenOcean.
        Decodes swaps that used uniswap and have no SWAPPED_TOPIC tx_log.
        """
        if SWAPPED_TOPIC in (topics := {tx_log.topics[0] for tx_log in all_logs}):
            return decoded_events  # Prevent re-decoding if tx with SWAPPED_TOPIC tx_log also used uniswap  # noqa: E501
        elif UNISWAP_V2_SWAP_SIGNATURE in topics or UNISWAP_V3_SWAP_SIGNATURE in topics:
            # No SWAPPED_TOPIC txlog so can't specify assets and amounts to check in _decode_swap.
            # But any spend/receive should be part of a swap here, so only checking type/subtype
            # in _decode_swap should work correctly.
            self._decode_swap(transaction=transaction, decoded_events=decoded_events)

        return decoded_events

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {OPENOCEAN_EXCHANGE_ADDRESS: (self._decode_swapped,)}

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return {OPENOCEAN_EXCHANGE_ADDRESS: CPT_OPENOCEAN}

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_OPENOCEAN: [(0, self._handle_post_decoding)]}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_OPENOCEAN,
            label=OPENOCEAN_LABEL,
            image='openocean.png',
        ),)
