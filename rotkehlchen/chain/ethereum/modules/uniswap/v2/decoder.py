from typing import TYPE_CHECKING, Callable, Optional

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.modules.uniswap.constants import CPT_UNISWAP_V2
from rotkehlchen.chain.ethereum.modules.uniswap.utils import decode_basic_uniswap_info
from rotkehlchen.chain.ethereum.modules.uniswap.v2.common import (
    UNISWAP_V2_ROUTER,
    decode_uniswap_like_deposit_and_withdrawals,
    decode_uniswap_v2_like_swap,
    enrich_uniswap_v2_like_lp_tokens_transfers,
)
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import ActionItem
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.types import UNISWAP_PROTOCOL, EvmTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent


# https://www.4byte.directory/api/v1/event-signatures/?hex_signature=0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822  # noqa: E501
SWAP_SIGNATURE = b'\xd7\x8a\xd9_\xa4l\x99KeQ\xd0\xda\x85\xfc\'_\xe6\x13\xce7e\x7f\xb8\xd5\xe3\xd10\x84\x01Y\xd8"'  # noqa: E501
MINT_SIGNATURE = b'L \x9b_\xc8\xadPu\x8f\x13\xe2\xe1\x08\x8b\xa5jV\r\xffi\n\x1co\xef&9OL\x03\x82\x1cO'  # noqa: E501
BURN_SIGNATURE = b'\xdc\xcdA/\x0b\x12R\x81\x9c\xb1\xfd3\x0b\x93"L\xa4&\x12\x89+\xb3\xf4\xf7\x89\x97nm\x81\x93d\x96'  # noqa: E501

UNISWAP_V2_FACTORY = string_to_evm_address('0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f')
UNISWAP_V2_INIT_CODE_HASH = '0x96e8ac4277198ff8b6f785478aa9a39f403cb768dd02cbee326c3e7da348845f'  # noqa: E501


class Uniswapv2Decoder(DecoderInterface):

    def _decode_basic_swap_info(
            self,
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> tuple[Optional['EvmEvent'], list[ActionItem]]:
        """
        Decodes only basic swap info. Basic swap info includes trying to find approval, spend and
        receive events for this particular swap but doesn't include ensuring order of events if the
        swap was made by an aggregator.
        """
        # amount_in is the amount that enters the pool and amount_out the one
        # that leaves the pool
        amount_in_token_0, amount_in_token_1 = hex_or_bytes_to_int(tx_log.data[0:32]), hex_or_bytes_to_int(tx_log.data[32:64])  # noqa: E501
        amount_out_token_0, amount_out_token_1 = hex_or_bytes_to_int(tx_log.data[64:96]), hex_or_bytes_to_int(tx_log.data[96:128])  # noqa: E501
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
        )

    def _maybe_decode_v2_swap(
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> tuple[Optional['EvmEvent'], list[ActionItem]]:
        if tx_log.topics[0] == SWAP_SIGNATURE:
            if transaction.to_address == UNISWAP_V2_ROUTER:
                # If uniswap v2 router is used, then we can decode an entire swap.
                # Uniswap v2 router is a simple router that always has a single spend and a single
                # receive event.
                return decode_uniswap_v2_like_swap(
                    tx_log=tx_log,
                    decoded_events=decoded_events,
                    transaction=transaction,
                    counterparty=CPT_UNISWAP_V2,
                    database=self.evm_inquirer.database,
                    ethereum_inquirer=self.evm_inquirer,  # type: ignore[arg-type]  # is ethereum
                    notify_user=self.notify_user,
                )

            # Else some aggregator (potentially complex) is used, so we decode only basic info
            # and other properties should be decoded by the aggregator decoding methods later.
            return self._decode_basic_swap_info(tx_log=tx_log, decoded_events=decoded_events)

        return None, []

    def _maybe_decode_v2_liquidity_addition_and_removal(
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list['EvmEvent'],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],
    ) -> tuple[Optional['EvmEvent'], list[ActionItem]]:
        if tx_log.topics[0] == MINT_SIGNATURE:
            return decode_uniswap_like_deposit_and_withdrawals(
                tx_log=tx_log,
                decoded_events=decoded_events,
                all_logs=all_logs,
                event_action_type='addition',
                counterparty=CPT_UNISWAP_V2,
                ethereum_inquirer=self.evm_inquirer,  # type: ignore[arg-type]  # is ethereum
                database=self.evm_inquirer.database,
                factory_address=UNISWAP_V2_FACTORY,
                init_code_hash=UNISWAP_V2_INIT_CODE_HASH,
                tx_hash=transaction.tx_hash,
            )
        if tx_log.topics[0] == BURN_SIGNATURE:
            return decode_uniswap_like_deposit_and_withdrawals(
                tx_log=tx_log,
                decoded_events=decoded_events,
                all_logs=all_logs,
                event_action_type='removal',
                counterparty=CPT_UNISWAP_V2,
                ethereum_inquirer=self.evm_inquirer,  # type: ignore[arg-type]  # is ethereum
                database=self.evm_inquirer.database,
                factory_address=UNISWAP_V2_FACTORY,
                init_code_hash=UNISWAP_V2_INIT_CODE_HASH,
                tx_hash=transaction.tx_hash,
            )
        return None, []

    @staticmethod
    def _maybe_enrich_lp_tokens_transfers(
            token: EvmToken,  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,  # pylint: disable=unused-argument
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            event: 'EvmEvent',
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> bool:
        return enrich_uniswap_v2_like_lp_tokens_transfers(
            token=token,
            tx_log=tx_log,
            transaction=transaction,
            event=event,
            action_items=action_items,
            all_logs=all_logs,
            counterparty=CPT_UNISWAP_V2,
            lp_token_symbol=UNISWAP_PROTOCOL,
        )

    # -- DecoderInterface methods

    def decoding_rules(self) -> list[Callable]:
        return [
            self._maybe_decode_v2_swap,
            self._maybe_decode_v2_liquidity_addition_and_removal,
        ]

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_lp_tokens_transfers,
        ]

    def counterparties(self) -> list[str]:
        return [CPT_UNISWAP_V2]
