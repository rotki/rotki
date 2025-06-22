import logging
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.efp.constants import CPT_EFP
from rotkehlchen.chain.evm.decoding.efp.decoder import EfpCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EvmTokenKind
from rotkehlchen.utils.misc import bytes_to_address

from .constants import EFP_LIST_REGISTRY

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

UPDATE_ACCOUNT_METADATA: Final = b"\xb0bt$-\xd2\xa5/\xd1\x8f\xff\x98=Z\xd9\xb3\x12.\x1ee\xc4\xa3\xcf\x9b\xd6\xbb'+G\xf0\x111"  # noqa: E501


class EfpDecoder(EfpCommonDecoder):

    def __init__(
            self,
            base_inquirer: 'BaseInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=base_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            list_records_contract=string_to_evm_address('0x41Aa48Ef3c0446b46a5b1cc6337FF3d3716E2A33'),
        )

    def _decode_account_metadata_events(self, context: DecoderContext) -> DecodingOutput:
        """Decode events from the EFPAccountMetadata contract, currently only deployed on Base.
        See https://docs.ethfollow.xyz/production/deployments
        """
        if context.tx_log.topics[0] != UPDATE_ACCOUNT_METADATA:
            return DEFAULT_DECODING_OUTPUT

        if (context.tx_log.data[96:128].rstrip(b'\x00').decode()) != 'primary-list':
            return DEFAULT_DECODING_OUTPUT

        return DecodingOutput(events=[self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=(user_address := bytes_to_address(context.tx_log.topics[1])),
            notes=f'Create EFP primary list for {user_address}',
            counterparty=CPT_EFP,
        )])

    def _decode_list_registry_events(self, context: DecoderContext) -> DecodingOutput:
        """Decode events from the EFPListRegistry contract, currently only deployed on Base.
        See https://docs.ethfollow.xyz/production/deployments
        """
        if (  # filter to only erc721 transfers
            context.tx_log.topics[0] != ERC20_OR_ERC721_TRANSFER or
            len(context.tx_log.topics) != 4  # erc721 should have 4
        ):
            return DEFAULT_DECODING_OUTPUT

        return DecodingOutput(action_items=[ActionItem(
            action='transform',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            location_label=(user_address := bytes_to_address(context.tx_log.topics[2])),
            asset=Asset(evm_address_to_identifier(  # EFP List NFT
                address=EFP_LIST_REGISTRY,
                chain_id=self.evm_inquirer.chain_id,
                token_type=EvmTokenKind.ERC721,
                collectible_id=str(int.from_bytes(context.tx_log.topics[3])),
            )),
            address=ZERO_ADDRESS,
            to_notes=f'Receive EFP list NFT for {user_address}',
            to_counterparty=CPT_EFP,
        )])

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            string_to_evm_address('0x5289fE5daBC021D02FDDf23d4a4DF96F4E0F17EF'): (self._decode_account_metadata_events,),  # EFPAccountMetadata  # noqa: E501
            EFP_LIST_REGISTRY: (self._decode_list_registry_events,),
        }
