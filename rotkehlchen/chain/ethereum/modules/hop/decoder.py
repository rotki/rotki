from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.hop.constants import CPT_HOP, HOP_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.hop.decoder import HopCommonDecoder
from rotkehlchen.chain.evm.decoding.interfaces import GovernableDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import BRIDGES, HOP_GOVERNOR

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

TRANSFER_TO_L2 = b'\n\x06\x07h\x8c\x86\xec\x17u\xab\xcd\xba\xb7\xb3::5\xa6\xc9\xcd\xe6w\xc9\xbe\x88\x01P\xc21\xcck\x0b'  # noqa: E501


class HopDecoder(HopCommonDecoder, GovernableDecoderInterface):
    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        HopCommonDecoder.__init__(  # using direct constructor calls due to
            self,  # having diamond inheritance. TODO: Perhaps Governable should be a mixin?
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            bridges=BRIDGES,
            reward_contracts=set(),
        )
        GovernableDecoderInterface.__init__(
            self,
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            protocol=CPT_HOP,
            proposals_url='https://www.tally.xyz/gov/hop/proposal',
        )

    def _decode_send_to_l2(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != TRANSFER_TO_L2:
            return super()._decode_events(context=context)

        if self.base.is_tracked(recipient := bytes_to_address(context.tx_log.topics[2])) is None:
            return DEFAULT_DECODING_OUTPUT

        if (bridge := self.bridges.get(context.tx_log.address)) is None:
            return DEFAULT_DECODING_OUTPUT

        amount_raw = int.from_bytes(context.tx_log.data[:32])
        amount = self._get_bridge_asset_amount(amount_raw=amount_raw, identifier=bridge.identifier)

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.SPEND and event.address == context.tx_log.address and event.asset.identifier == bridge.identifier and event.amount == amount:  # noqa: E501
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_HOP
                event.notes = self._generate_bridge_note(
                    amount=amount,
                    asset=event.asset,
                    recipient=recipient,
                    sender=string_to_evm_address(event.location_label) if event.location_label else None,  # noqa: E501
                    chain_id=int.from_bytes(context.tx_log.topics[1]),
                )
                break

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(set(self.bridges.keys()), (self._decode_send_to_l2,)) | {
            HOP_GOVERNOR: (self._decode_governance,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (HOP_CPT_DETAILS,)
