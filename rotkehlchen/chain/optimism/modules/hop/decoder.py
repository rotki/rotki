from typing import TYPE_CHECKING, Any, Optional

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.constants import CPT_HOP
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import ActionItem
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTokenKind, EvmTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator

ETH_BRIDGE = string_to_evm_address('0x83f6244Bd87662118d96D9a6D44f09dffF14b30E')

TRANSFER_FROM_L1_COMPLETED = b'2\tX\x17i0\x80N\xb6l#C\xc74?\xc06}\xc1bIY\x0c\x0f\x19W\x83\xbe\xe1\x99\xd0\x94'  # noqa: E501


class HopDecoder(DecoderInterface):

    def __init__(  # pylint: disable=super-init-not-called
            self,
            optimism_inquirer: 'OptimismInquirer',  # pylint: disable=unused-argument
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        self.base_tools = base_tools
        self.weth = get_or_create_evm_token(
            userdb=base_tools.database,
            symbol='WETH',
            name='Wrapped Ether',
            decimals=18,
            chain_id=ChainID.OPTIMISM,
            token_kind=EvmTokenKind.ERC20,
            evm_address=string_to_evm_address('0x4200000000000000000000000000000000000006'),
        )
        self.heth = get_or_create_evm_token(
            userdb=self.base_tools.database,
            symbol='hETH',
            name='ETH Hop Token',
            decimals=18,
            chain_id=ChainID.OPTIMISM,
            token_kind=EvmTokenKind.ERC20,
            evm_address=string_to_evm_address('0xE38faf9040c7F09958c638bBDB977083722c5156'),
        )

    def _decode_receive_eth(  # pylint: disable=no-self-use
            self,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list[HistoryBaseEntry],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
            action_items: list[ActionItem],  # pylint: disable=unused-argument
    ) -> tuple[Optional[HistoryBaseEntry], list[ActionItem]]:
        if tx_log.topics[0] != TRANSFER_FROM_L1_COMPLETED:
            return None, []

        recipient = hex_or_bytes_to_address(tx_log.topics[1])
        if not self.base_tools.is_tracked(recipient):
            return None, []

        amount_raw = hex_or_bytes_to_int(tx_log.data[:32])
        heth_amount = token_normalized_value_decimals(amount_raw, 18)

        for event in decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and recipient == event.location_label and event.asset == A_ETH:  # noqa: E501
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_HOP
                event.notes = f'Bridge {event.balance.amount} ETH via hop protocol'
                event.extra_data = {'sent_amount': str(heth_amount)}
                break

        return None, []

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            ETH_BRIDGE: (self._decode_receive_eth,),
        }

    def counterparties(self) -> list[str]:
        return [CPT_HOP]
