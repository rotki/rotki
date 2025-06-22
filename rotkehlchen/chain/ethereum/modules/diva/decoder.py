import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.evm.decoding.constants import DELEGATE_CHANGED
from rotkehlchen.chain.evm.decoding.interfaces import (
    GovernableDecoderInterface,
    MerkleClaimDecoderInterface,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DIVA
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_DIVA, DIVA_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
DIVA_AIDROP_CONTRACT = string_to_evm_address('0x777E2B2Cc7980A6bAC92910B95269895EEf0d2E8')
DIVA_GOVERNOR = string_to_evm_address('0xFb6B7C11a55C57767643F1FF65c34C8693a11A70')


class DivaDecoder(GovernableDecoderInterface, MerkleClaimDecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            protocol=CPT_DIVA,
            proposals_url='https://www.tally.xyz/gov/diva/proposal',
        )
        self.diva = A_DIVA.resolve_to_evm_token()

    def _decode_delegation_change(self, context: DecoderContext) -> DecodingOutput:
        """Decode a change in the delegated address"""
        if context.tx_log.topics[0] != DELEGATE_CHANGED:
            return DEFAULT_DECODING_OUTPUT

        delegator = bytes_to_address(context.tx_log.topics[1])
        delegate = bytes_to_address(context.tx_log.topics[3])

        if self.base.is_tracked(delegator):
            event_address = delegator
        else:
            event_address = delegate

        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=self.diva,
            amount=ZERO,
            location_label=event_address,
            notes=f'Change DIVA Delegate from {delegator} to {delegate}',
            counterparty=CPT_DIVA,
        )
        return DecodingOutput(events=[event], refresh_balances=False)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            DIVA_GOVERNOR: (self._decode_governance,),
            DIVA_ADDRESS: (self._decode_delegation_change,),
            DIVA_AIDROP_CONTRACT: (
                self._decode_merkle_claim,
                CPT_DIVA,  # counterparty
                self.diva.identifier,  # token id
                18,  # token decimals
                'DIVA from the DIVA airdrop',  # notes suffix
                'diva',
            ),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_DIVA, label='Diva', image='diva.svg'),)
