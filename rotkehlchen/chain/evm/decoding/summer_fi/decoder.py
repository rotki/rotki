from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.summer_fi.constants import ACCOUNT_CREATED_TOPIC, CPT_SUMMER_FI
from rotkehlchen.constants import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator


class SummerFiCommonDecoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            account_factory: 'ChecksumEvmAddress',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.account_factory = account_factory

    def _decode_account_creation(self, context: DecoderContext) -> DecodingOutput:
        """Decode smart account creation events."""
        if (
            context.tx_log.topics[0] != ACCOUNT_CREATED_TOPIC or
            not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[2]))
        ):
            return DEFAULT_DECODING_OUTPUT

        proxy_address = bytes_to_address(context.tx_log.topics[1])
        vault_id = int.from_bytes(context.tx_log.topics[3])
        return DecodingOutput(events=[self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.CREATE,
            asset=self.evm_inquirer.native_token,
            amount=ZERO,
            location_label=user_address,
            notes=f'Create Summer.fi smart account {proxy_address} with id {vault_id}',
            counterparty=CPT_SUMMER_FI,
            address=context.tx_log.address,
            extra_data={'proxy_address': proxy_address, 'vault_id': vault_id},
        )])

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {self.account_factory: (self._decode_account_creation,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_SUMMER_FI,
            label='Summer.fi',
            image='summer_fi.svg',
        ),)
