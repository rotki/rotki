from collections.abc import Callable
from typing import TYPE_CHECKING, Final

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.constants import BURN_TOPIC, MINT_TOPIC
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V2, UNISWAP_ICON
from rotkehlchen.chain.evm.decoding.uniswap.utils import decode_basic_uniswap_info
from rotkehlchen.chain.evm.decoding.uniswap.v2.utils import (
    decode_uniswap_like_deposit_and_withdrawals,
    decode_uniswap_v2_like_swap,
)
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.constants import ZERO
from rotkehlchen.types import EvmTransaction

from .constants import UNISWAP_V2_SWAP_SIGNATURE

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

UNISWAP_V2_INIT_CODE_HASH: Final = '0x96e8ac4277198ff8b6f785478aa9a39f403cb768dd02cbee326c3e7da348845f'  # noqa: E501


class Uniswapv2CommonDecoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
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

    def _decode_basic_swap_info(
            self,
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> DecodingOutput:
        """
        Decodes only basic swap info. Basic swap info includes trying to find approval, spend and
        receive events for this particular swap but doesn't include ensuring order of events if the
        swap was made by an aggregator.
        """
        # amount_in is the amount that enters the pool and amount_out the one
        # that leaves the pool
        amount_in_token_0, amount_in_token_1 = int.from_bytes(tx_log.data[0:32]), int.from_bytes(tx_log.data[32:64])  # noqa: E501
        amount_out_token_0, amount_out_token_1 = int.from_bytes(tx_log.data[64:96]), int.from_bytes(tx_log.data[96:128])  # noqa: E501
        amount_in, amount_out = amount_in_token_0, amount_out_token_0
        if amount_in == ZERO:
            amount_in = amount_in_token_1
        if amount_out == ZERO:
            amount_out = amount_out_token_1

        return decode_basic_uniswap_info(
            amount_sent=amount_in,
            amount_received=amount_out,
            decoded_events=decoded_events,
            counterparty=CPT_UNISWAP_V2,
            notify_user=self.notify_user,
            native_currency=self.evm_inquirer.native_token,
        )

    def _maybe_decode_v2_swap(
            self,
            token: EvmToken | None,  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> DecodingOutput:
        if tx_log.topics[0] == UNISWAP_V2_SWAP_SIGNATURE:
            if transaction.to_address == self.router_address:
                # If uniswap v2 router is used, then we can decode an entire swap.
                # Uniswap v2 router is a simple router that always has a single spend and a single
                # receive event.
                return decode_uniswap_v2_like_swap(
                    tx_log=tx_log,
                    decoded_events=decoded_events,
                    transaction=transaction,
                    counterparty=CPT_UNISWAP_V2,
                    router_address=self.router_address,
                    database=self.evm_inquirer.database,
                    evm_inquirer=self.evm_inquirer,
                    notify_user=self.notify_user,
                )

            # Else some aggregator (potentially complex) is used, so we decode only basic info
            # and other properties should be decoded by the aggregator decoding methods later.
            return self._decode_basic_swap_info(tx_log=tx_log, decoded_events=decoded_events)

        return DEFAULT_DECODING_OUTPUT

    def _maybe_decode_v2_liquidity_addition_and_removal(
            self,
            token: EvmToken | None,  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],
    ) -> DecodingOutput:
        if tx_log.topics[0] == MINT_TOPIC:
            return decode_uniswap_like_deposit_and_withdrawals(
                tx_log=tx_log,
                decoded_events=decoded_events,
                all_logs=all_logs,
                is_deposit=True,
                counterparty=CPT_UNISWAP_V2,
                evm_inquirer=self.evm_inquirer,
                database=self.evm_inquirer.database,
                factory_address=self.factory_address,
                init_code_hash=UNISWAP_V2_INIT_CODE_HASH,
                tx_hash=transaction.tx_hash,
            )
        if tx_log.topics[0] == BURN_TOPIC:
            return decode_uniswap_like_deposit_and_withdrawals(
                tx_log=tx_log,
                decoded_events=decoded_events,
                all_logs=all_logs,
                is_deposit=False,
                counterparty=CPT_UNISWAP_V2,
                evm_inquirer=self.evm_inquirer,
                database=self.evm_inquirer.database,
                factory_address=self.factory_address,
                init_code_hash=UNISWAP_V2_INIT_CODE_HASH,
                tx_hash=transaction.tx_hash,
            )
        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def decoding_rules(self) -> list[Callable]:
        return [
            self._maybe_decode_v2_swap,
            self._maybe_decode_v2_liquidity_addition_and_removal,
        ]

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails.from_versioned_counterparty(
            counterparty=CPT_UNISWAP_V2,
            image=UNISWAP_ICON,
        ),)
