import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi_str
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EthereumTransaction
from rotkehlchen.utils.misc import from_wei
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

from .constants import CPT_ENS

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


ENS_REGISTRAR_CONTROLLER = string_to_evm_address('0x283Af0B28c62C092C9727F1Ee09c02CA627EB7F5')

NAME_RENEWED = b'=\xa2L\x02E\x82\x93\x1c\xfa\xf8&}\x8e\xd2M\x13\xa8*\x80h\xd5\xbd3}0\xecE\xce\xa4\xe5\x06\xae'  # noqa: E501
NAME_RENEWED_ABI = '{"anonymous":false,"inputs":[{"indexed":false,"internalType":"string","name":"name","type":"string"},{"indexed":true,"internalType":"bytes32","name":"label","type":"bytes32"},{"indexed":false,"internalType":"uint256","name":"cost","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"expires","type":"uint256"}],"name":"NameRenewed","type":"event"}'  # noqa: E501


class EnsDecoder(DecoderInterface, CustomizableDateMixin):  # lgtm[py/missing-call-to-init]
    def __init__(  # pylint: disable=super-init-not-called
            self,
            ethereum_manager: 'EthereumManager',  # pylint: disable=unused-argument
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',  # pylint: disable=unused-argument
    ) -> None:
        CustomizableDateMixin.__init__(self, base_tools.database)

    def _decode_name_renewed(
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: Optional[List[ActionItem]],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] != NAME_RENEWED:
            return None, None

        try:
            _, decoded_data = decode_event_data_abi_str(tx_log, NAME_RENEWED_ABI)
        except DeserializationError as e:
            log.debug(f'Failed to decode ENS name renewed event due to {str(e)}')
            return None, None

        name = decoded_data[0]
        amount = from_wei(decoded_data[1])
        expires = decoded_data[2]

        for event in decoded_events:
            # Find the transfer event which should be before the name renewed event
            if event.event_type == HistoryEventType.SPEND and event.asset == A_ETH and event.balance.amount == amount and event.counterparty == tx_log.address:  # noqa: E501
                event.event_type = HistoryEventType.RENEW
                event.event_subtype = HistoryEventSubType.NFT
                event.counterparty = CPT_ENS
                event.notes = f'Renew ENS name {name} for {amount} ETH until {self.timestamp_to_date(expires)}'  # noqa: E501

        return None, None

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> Dict[ChecksumEvmAddress, Tuple[Any, ...]]:
        return {
            ENS_REGISTRAR_CONTROLLER: (self._decode_name_renewed,),  # noqa: E501
        }

    def counterparties(self) -> List[str]:
        return [CPT_ENS]
