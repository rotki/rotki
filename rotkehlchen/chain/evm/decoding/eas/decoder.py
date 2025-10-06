import logging
from abc import ABC
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_EAS, EAS_CPT_DETAILS

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# In all the currently deployed versions ATTESTED thankfully has same ABI
ATTESTED = b'\x8b\xf4k\xf4\xcf\xd6t\xfasZ=c\xec\x1c\x9a\xd4\x15?\x03<)\x03A\xf3\xa5\x88\xb7V\x85\x14\x1b5'  # noqa: E501


class EASCommonDecoder(EvmDecoderInterface, ABC):
    """This is the Ethereum Attestation Service common decoder

    https://attest.sh/
    https://docs.attest.sh/docs/quick--start/contracts
    """

    def __init__(  # pylint: disable=super-init-not-called
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            attestation_service_address: 'ChecksumEvmAddress',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.attestation_service_address = attestation_service_address

    def _decode_attestation_action(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != ATTESTED:
            return DEFAULT_EVM_DECODING_OUTPUT

        attester = bytes_to_address(context.tx_log.topics[2])
        recipient = bytes_to_address(context.tx_log.topics[1])
        if self.base.is_tracked(attester):
            location_label = attester
        elif self.base.is_tracked(recipient):
            location_label = recipient
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        uid = context.tx_log.data.hex()
        prefix = f'{self.node_inquirer.chain_name}.'
        if self.node_inquirer.chain_id == ChainID.ETHEREUM:
            prefix = ''
        elif self.node_inquirer.chain_id == ChainID.ARBITRUM_ONE:
            prefix = 'arbitrum.'

        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.ATTEST,
            asset=A_ETH,
            amount=ZERO,
            location_label=location_label,
            notes=f'Attest to https://{prefix}easscan.org/attestation/view/0x{uid}',
            counterparty=CPT_EAS,
            address=context.tx_log.address,
        )
        return EvmDecodingOutput(events=[event])

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {self.attestation_service_address: (self._decode_attestation_action,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (EAS_CPT_DETAILS,)
