from collections.abc import Callable
from typing import TYPE_CHECKING, Final

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.modules.sushiswap.constants import CPT_SUSHISWAP_V2
from rotkehlchen.chain.ethereum.modules.uniswap.v2.common import (
    SUSHISWAP_ROUTER,
    decode_uniswap_like_deposit_and_withdrawals,
    decode_uniswap_v2_like_swap,
)
from rotkehlchen.chain.ethereum.modules.uniswap.v2.constants import SWAP_SIGNATURE
from rotkehlchen.chain.evm.constants import BURN_TOPIC, MINT_TOPIC
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import EvmTransaction

if TYPE_CHECKING:
    from rotkehlchen.history.events.structures.evm_event import EvmEvent

SUSHISWAP_V2_FACTORY: Final = string_to_evm_address('0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac')
SUSHISWAP_V2_INIT_CODE_HASH: Final = '0xe18a34eb0e04b04f7a0ac29a6e80748dca96319b42c54d679cb821dca90c6303'  # noqa: E501


class SushiswapDecoder(DecoderInterface):

    def _maybe_decode_v2_swap(
            self,
            token: EvmToken | None,  # pylint: disable=unused-argument
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
            token: EvmToken | None,  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list['EvmEvent'],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],
    ) -> DecodingOutput:
        if tx_log.topics[0] == MINT_TOPIC:
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
        if tx_log.topics[0] == BURN_TOPIC:
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

    # -- DecoderInterface methods

    def decoding_rules(self) -> list[Callable]:
        return [
            self._maybe_decode_v2_swap,
            self._maybe_decode_v2_liquidity_addition_and_removal,
        ]

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_SUSHISWAP_V2,
            label='Sushiswap',
            image='sushiswap.svg',
        ),)
