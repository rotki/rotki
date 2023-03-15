import logging
from typing import Any, Optional

from eth_utils import encode_hex

from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.constants import ETH2_DEPOSIT_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import ActionItem
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import from_gwei, hex_or_bytes_to_int

from .constants import CPT_ETH2

DEPOSIT_EVENT = b'd\x9b\xbcb\xd0\xe3\x13B\xaf\xeaN\\\xd8-@I\xe7\xe1\xee\x91/\xc0\x88\x9a\xa7\x90\x80;\xe3\x908\xc5'  # noqa: E501

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Eth2Decoder(DecoderInterface):

    def _decode_eth2_deposit_event(
            self,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list[EvmEvent],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
            action_items: Optional[list[ActionItem]],  # pylint: disable=unused-argument
    ) -> tuple[Optional[EvmEvent], list[ActionItem]]:
        if tx_log.topics[0] != DEPOSIT_EVENT:
            return None, []

        pubkey = encode_hex(tx_log.data[192:240])
        withdrawal_credentials = encode_hex(tx_log.data[288:320])
        amount = from_gwei(hex_or_bytes_to_int(tx_log.data[352:360], byteorder='little'))
        deposit_index = hex_or_bytes_to_int(tx_log.data[544:552 + 8], byteorder='little')  # is not same as validator index  # noqa: E501
        for event in decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_ETH and
                event.balance.amount == amount
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_ETH2
                event.notes = f'Deposit {amount} ETH to validator with pubkey {pubkey}. Deposit index: {deposit_index}. Withdrawal credentials: {withdrawal_credentials}'  # noqa: E501
                event.extra_data = {'withdrawal_credentials': withdrawal_credentials}

        return None, []

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            ETH2_DEPOSIT_ADDRESS: (self._decode_eth2_deposit_event,),
        }

    def counterparties(self) -> list[str]:
        return [CPT_ETH2]
