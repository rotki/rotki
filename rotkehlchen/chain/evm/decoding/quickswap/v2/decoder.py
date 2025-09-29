from collections.abc import Callable
from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.constants import BURN_TOPIC, MINT_TOPIC
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.quickswap.constants import CPT_QUICKSWAP_V2
from rotkehlchen.chain.evm.decoding.quickswap.utils import decode_quickswap_swap
from rotkehlchen.chain.evm.decoding.uniswap.v2.constants import UNISWAP_V2_SWAP_SIGNATURE
from rotkehlchen.chain.evm.decoding.uniswap.v2.decoder import UNISWAP_V2_INIT_CODE_HASH
from rotkehlchen.chain.evm.decoding.uniswap.v2.utils import (
    decode_uniswap_like_deposit_and_withdrawals,
)
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator


class Quickswapv2CommonDecoder(DecoderInterface):

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
        for tx_log in all_logs:
            if tx_log.topics[0] == UNISWAP_V2_SWAP_SIGNATURE:
                return decode_quickswap_swap(tx_log=tx_log, decoded_events=decoded_events)
            elif tx_log.topics[0] == MINT_TOPIC:
                is_deposit = True
                break
            elif tx_log.topics[0] == BURN_TOPIC:
                is_deposit = False
                break
        else:
            return decoded_events

        decode_uniswap_like_deposit_and_withdrawals(
            tx_log=tx_log,
            decoded_events=decoded_events,
            all_logs=all_logs,
            is_deposit=is_deposit,
            counterparty=CPT_QUICKSWAP_V2,
            database=self.evm_inquirer.database,
            evm_inquirer=self.evm_inquirer,
            factory_address=self.factory_address,
            init_code_hash=UNISWAP_V2_INIT_CODE_HASH,
            tx_hash=transaction.tx_hash,
        )
        return decoded_events

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
