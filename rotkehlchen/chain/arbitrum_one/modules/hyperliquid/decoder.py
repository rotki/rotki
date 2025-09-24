
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.arbitrum_one.modules.hyperliquid.constants import (
    BRIDGE_ADDRESS,
    CPT_HYPER,
    FINALIZE_WITHDRAWAL,
)
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_DECODING_OUTPUT
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext, DecodingOutput
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class HyperliquidDecoder(DecoderInterface):
    """Hyperliquid deposit/withdrawals work only with USDC"""

    def _process_deposit(
            self,
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """Deposits to Hyperliquid are just transfers to the bridge contract.
        There aren't any contract calls
        """
        for event in decoded_events:
            if (
                event.address == BRIDGE_ADDRESS and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset.identifier == 'eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'  # USDC  # noqa: E501
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Deposit {event.amount} USDC in Hyperliquid'
                event.counterparty = CPT_HYPER
            # not breaking since there could be more transafers in the same transaction

        return decoded_events

    def _process_withdrawal(self, context: 'DecoderContext') -> 'DecodingOutput':
        """Withdrawals are initiated on the UI and then a validator executes them by calling a
        method in the bridge contract. Multiple withdrawals can be batched
        in the same transaction.
        """
        if context.tx_log.topics[0] != FINALIZE_WITHDRAWAL:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=6,  # usdc has always 6 decimals
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset.identifier == 'eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831' and  # noqa: E501
                event.location_label == user and
                event.amount == amount
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.notes = f'Withdraw {event.amount} USDC from Hyperliquid'
                event.counterparty = CPT_HYPER
                break
        else:
            log.error(f'Did not find hyperliquid withdrawal in {context.transaction}')

        return DEFAULT_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {BRIDGE_ADDRESS: (self._process_withdrawal,)}

    def addresses_to_counterparties(self) -> dict['ChecksumEvmAddress', str]:
        return {string_to_evm_address('0xaf88d065e77c8cC2239327C5EDb3A432268e5831'): CPT_HYPER}

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_HYPER: [(0, self._process_deposit)]}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_HYPER,
            label='Hyperliquid',
            image='hyperliquid.svg',
        ),)
