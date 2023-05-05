from typing import TYPE_CHECKING, Callable, Optional

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.modules.sushiswap.constants import CPT_SUSHISWAP_V2
from rotkehlchen.chain.ethereum.modules.uniswap.v2.common import (
    SUSHISWAP_ROUTER,
    decode_uniswap_like_deposit_and_withdrawals,
    decode_uniswap_v2_like_swap,
    enrich_uniswap_v2_like_lp_tokens_transfers,
)
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecodingOutput,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import SUSHISWAP_PROTOCOL, DecoderEventMappingType, EvmTransaction

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent

# https://www.4byte.directory/api/v1/event-signatures/?hex_signature=0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822  # noqa: E501
SWAP_SIGNATURE = b'\xd7\x8a\xd9_\xa4l\x99KeQ\xd0\xda\x85\xfc\'_\xe6\x13\xce7e\x7f\xb8\xd5\xe3\xd10\x84\x01Y\xd8"'  # noqa: E501
MINT_SIGNATURE = b'L \x9b_\xc8\xadPu\x8f\x13\xe2\xe1\x08\x8b\xa5jV\r\xffi\n\x1co\xef&9OL\x03\x82\x1cO'  # noqa: E501
BURN_SIGNATURE = b'\xdc\xcdA/\x0b\x12R\x81\x9c\xb1\xfd3\x0b\x93"L\xa4&\x12\x89+\xb3\xf4\xf7\x89\x97nm\x81\x93d\x96'  # noqa: E501

SUSHISWAP_V2_FACTORY = string_to_evm_address('0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac')
SUSHISWAP_V2_INIT_CODE_HASH = '0xe18a34eb0e04b04f7a0ac29a6e80748dca96319b42c54d679cb821dca90c6303'  # noqa: E501


class SushiswapDecoder(DecoderInterface):

    def _maybe_decode_v2_swap(
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> DecodingOutput:
        if tx_log.topics[0] == SWAP_SIGNATURE and transaction.to_address == SUSHISWAP_ROUTER:
            return decode_uniswap_v2_like_swap(
                tx_log=tx_log,
                decoded_events=decoded_events,
                transaction=transaction,
                counterparty=CPT_SUSHISWAP_V2,
                database=self.evm_inquirer.database,
                ethereum_inquirer=self.evm_inquirer,  # type: ignore[arg-type]  # is ethereum
                notify_user=self.notify_user,
            )
        return DEFAULT_DECODING_OUTPUT

    def _maybe_decode_v2_liquidity_addition_and_removal(
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list['EvmEvent'],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],
    ) -> DecodingOutput:
        if tx_log.topics[0] == MINT_SIGNATURE:
            return decode_uniswap_like_deposit_and_withdrawals(
                tx_log=tx_log,
                decoded_events=decoded_events,
                all_logs=all_logs,
                event_action_type='addition',
                counterparty=CPT_SUSHISWAP_V2,
                database=self.evm_inquirer.database,
                ethereum_inquirer=self.evm_inquirer,  # type: ignore[arg-type]  # is ethereum
                factory_address=SUSHISWAP_V2_FACTORY,
                init_code_hash=SUSHISWAP_V2_INIT_CODE_HASH,
                tx_hash=transaction.tx_hash,
            )
        if tx_log.topics[0] == BURN_SIGNATURE:
            return decode_uniswap_like_deposit_and_withdrawals(
                tx_log=tx_log,
                decoded_events=decoded_events,
                all_logs=all_logs,
                event_action_type='removal',
                counterparty=CPT_SUSHISWAP_V2,
                database=self.evm_inquirer.database,
                ethereum_inquirer=self.evm_inquirer,  # type: ignore[arg-type]  # is ethereum
                factory_address=SUSHISWAP_V2_FACTORY,
                init_code_hash=SUSHISWAP_V2_INIT_CODE_HASH,
                tx_hash=transaction.tx_hash,
            )
        return DEFAULT_DECODING_OUTPUT

    @staticmethod
    def _maybe_enrich_lp_tokens_transfers(context: EnricherContext) -> TransferEnrichmentOutput:
        return enrich_uniswap_v2_like_lp_tokens_transfers(
            context=context,
            counterparty=CPT_SUSHISWAP_V2,
            lp_token_symbol=SUSHISWAP_PROTOCOL,
        )

    # -- DecoderInterface methods

    def possible_events(self) -> DecoderEventMappingType:
        return {CPT_SUSHISWAP_V2: {
            HistoryEventType.TRADE: {
                HistoryEventSubType.RECEIVE: EventCategory.SWAP_IN,
                HistoryEventSubType.SPEND: EventCategory.SWAP_OUT,
            },
            HistoryEventType.DEPOSIT: {
                HistoryEventSubType.DEPOSIT_ASSET: EventCategory.DEPOSIT,
            },
            HistoryEventType.WITHDRAWAL: {
                HistoryEventSubType.REMOVE_ASSET: EventCategory.WITHDRAW,
            },
            HistoryEventType.SPEND: {
                HistoryEventSubType.RETURN_WRAPPED: EventCategory.SEND,
            },
            HistoryEventType.RECEIVE: {
                HistoryEventSubType.RECEIVE_WRAPPED: EventCategory.RECEIVE,
            },
            HistoryEventType.TRANSFER: {
                HistoryEventSubType.NONE: EventCategory.TRANSFER,
            },
        }}

    def decoding_rules(self) -> list[Callable]:
        return [
            self._maybe_decode_v2_swap,
            self._maybe_decode_v2_liquidity_addition_and_removal,
        ]

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_lp_tokens_transfers,
        ]

    def counterparties(self) -> list[CounterpartyDetails]:
        return [CounterpartyDetails(
            identifier=CPT_SUSHISWAP_V2,
            label='Sushiswap',
            image='sushiswap.svg',
        )]
