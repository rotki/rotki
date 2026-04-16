from collections.abc import Callable
from typing import TYPE_CHECKING

from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails, get_versioned_counterparty_label
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import BURN_TOPIC, MINT_TOPIC
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.quickswap.constants import CPT_QUICKSWAP_V2
from rotkehlchen.chain.evm.decoding.quickswap.utils import decode_quickswap_swap
from rotkehlchen.chain.evm.decoding.uniswap.v2.constants import UNISWAP_V2_SWAP_SIGNATURE
from rotkehlchen.chain.evm.decoding.uniswap.v2.decoder import UNISWAP_V2_INIT_CODE_HASH
from rotkehlchen.chain.evm.decoding.uniswap.v2.utils import (
    decode_uniswap_like_deposit_and_withdrawals,
)
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator


class Quickswapv2CommonDecoder(EvmDecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            router_address: 'ChecksumEvmAddress',
            factory_address: 'ChecksumEvmAddress',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.router_address = router_address
        self.factory_address = factory_address

    def _v2_router_post_decoding(
            self,
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """Decode the quickswap v2 router events."""
        first_swap_log = last_swap_log = None
        mint_burn_log = None
        is_deposit = False
        for tx_log in all_logs:
            if tx_log.topics[0] == UNISWAP_V2_SWAP_SIGNATURE:
                if first_swap_log is None:
                    first_swap_log = tx_log
                last_swap_log = tx_log
            elif mint_burn_log is None and tx_log.topics[0] == MINT_TOPIC:
                mint_burn_log = tx_log
                is_deposit = True
            elif mint_burn_log is None and tx_log.topics[0] == BURN_TOPIC:
                mint_burn_log = tx_log
                is_deposit = False

        if first_swap_log is not None:
            decode_quickswap_swap(tx_log=first_swap_log, decoded_events=decoded_events)
            # The uniswap v2 basic decoder (used because tx.to is the quickswap router,
            # not the uniswap router) skips native-currency receive events, so in swaps
            # whose output is the chain's native token the receive side is never paired
            # with the spend. Promote it to TRADE/RECEIVE here using amount_out from the
            # last swap log in the route.
            self._maybe_mark_native_output_receive(
                last_swap_log=last_swap_log,  # type: ignore[arg-type]  # set iff first_swap_log is set
                decoded_events=decoded_events,
            )
            return decoded_events

        if mint_burn_log is not None:
            decode_uniswap_like_deposit_and_withdrawals(
                tx_log=mint_burn_log,
                decoded_events=decoded_events,
                all_logs=all_logs,
                is_deposit=is_deposit,
                counterparty=CPT_QUICKSWAP_V2,
                database=self.node_inquirer.database,
                evm_inquirer=self.node_inquirer,
                factory_address=self.factory_address,
                init_code_hash=UNISWAP_V2_INIT_CODE_HASH,
                tx_hash=transaction.tx_hash,
            )

        return decoded_events

    def _maybe_mark_native_output_receive(
            self,
            last_swap_log: 'EvmTxReceiptLog',
            decoded_events: list['EvmEvent'],
    ) -> None:
        amount_out_0 = int.from_bytes(last_swap_log.data[64:96])
        amount_out_1 = int.from_bytes(last_swap_log.data[96:128])
        amount_out_raw = amount_out_0 if amount_out_0 != 0 else amount_out_1

        spend_event = receive_event = None
        for event in decoded_events:
            if (
                event.event_type == HistoryEventType.TRADE and
                event.event_subtype == HistoryEventSubType.SPEND and
                event.counterparty == CPT_QUICKSWAP_V2
            ):
                spend_event = event
                continue
            if receive_event is not None or event.event_type != HistoryEventType.RECEIVE or event.event_subtype != HistoryEventSubType.NONE:  # noqa: E501
                continue
            try:
                crypto_asset = event.asset.resolve_to_crypto_asset()
            except (UnknownAsset, WrongAssetType):
                continue
            if event.asset != self.node_inquirer.native_token or event.amount != asset_normalized_value(amount=amount_out_raw, asset=crypto_asset):  # noqa: E501
                continue
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.RECEIVE
            event.counterparty = CPT_QUICKSWAP_V2
            event.notes = f'Receive {event.amount} {crypto_asset.symbol} as the result of a swap in {get_versioned_counterparty_label(CPT_QUICKSWAP_V2)}'  # noqa: E501
            receive_event = event

        if spend_event is not None and receive_event is not None:
            maybe_reshuffle_events(
                ordered_events=[spend_event, receive_event],
                events_list=decoded_events,
            )

    # -- DecoderInterface methods

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_QUICKSWAP_V2: [(0, self._v2_router_post_decoding)]}

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return {self.router_address: CPT_QUICKSWAP_V2}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails.from_versioned_counterparty(
            counterparty=CPT_QUICKSWAP_V2,
            image='quickswap.png',
        ),)
