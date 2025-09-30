import logging
from typing import Any

import requests

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi_str
from rotkehlchen.chain.ethereum.modules.juicebox.constants import (
    CHARITY_PROJECTS_IDS,
    CHARITY_TAG,
    CPT_JUICEBOX,
    JUICEBOX_IPFS_GATEWAY,
    JUICEBOX_PROJECTS,
    METADATA_CONTENT_OF_ABI,
    PAY_ABI,
    PAY_SIGNATURE,
    TERMINAL_3_1_2,
)
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class JuiceboxDecoder(EvmDecoderInterface):

    def _query_project_name(self, project_id: int) -> tuple[str | None, list[str]]:
        """Query metadata for project id in ipfs"""
        try:
            ipfs_hash = self.node_inquirer.call_contract(
                contract_address=JUICEBOX_PROJECTS,
                abi=METADATA_CONTENT_OF_ABI,
                method_name='metadataContentOf',
                arguments=[project_id, 0],  # 0 is the ipfs hash of the data
            )
        except RemoteError:
            log.error(f'Failed to query ipfs hash for juicebox project {project_id}')
            return None, []

        metadata_url = JUICEBOX_IPFS_GATEWAY + ipfs_hash
        try:
            log.debug(f'Querying juicebox metadata at {metadata_url}')
            metadata: dict[str, Any] = requests.get(
                url=metadata_url,
                timeout=CachedSettings().get_timeout_tuple(),
            ).json()
        except requests.RequestException as e:
            log.error(f'Failed to query juicebox project {project_id} metadata due to {e}')
            return None, []

        return metadata.get('name'), metadata.get('tags', [])

    def _decode_pay(self, context: DecoderContext) -> DecodingOutput:
        """Decode pay with rewards in juicebox"""
        if context.tx_log.topics[0] != PAY_SIGNATURE:
            return DEFAULT_DECODING_OUTPUT

        try:
            topic_data, decoded_data = decode_event_data_abi_str(context.tx_log, PAY_ABI)
        except DeserializationError as e:
            log.error(
                f'Failed to deserialize Juicebox event at '
                f'{context.transaction.tx_hash.hex()} due to {e}',
            )
            return DEFAULT_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=decoded_data[2],
            token_decimals=18,  # it is always ETH
        )
        project_id = topic_data[2]
        project_name, tags = self._query_project_name(project_id=project_id)
        is_donation = project_id in CHARITY_PROJECTS_IDS or CHARITY_TAG in tags
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_ETH and
                event.amount == amount and
                event.location_label == decoded_data[0]
            ):
                event.counterparty = CPT_JUICEBOX
                if is_donation:
                    action_verb = 'Donate'
                    event.event_subtype = HistoryEventSubType.DONATE
                else:
                    action_verb = 'Pay'

                event.notes = f'{action_verb} {amount} ETH at Juicebox'
                if project_name is not None:
                    event.notes += f' to project {project_name}'
                if len(decoded_data[4]) != 0:
                    event.notes += f' with memo: "{decoded_data[4]}"'
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                event.counterparty = CPT_JUICEBOX
                action_verb = 'donating' if is_donation else 'contributing'
                event.notes = f'Receive an NFT for {action_verb} via Juicebox'

        return DEFAULT_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            TERMINAL_3_1_2: (self._decode_pay,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (
            CounterpartyDetails(
                identifier=CPT_JUICEBOX,
                label='Juicebox',
                image='juicebox.svg',
            ),
        )
