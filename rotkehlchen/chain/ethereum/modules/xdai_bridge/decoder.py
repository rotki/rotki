from collections.abc import Callable
from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.ethereum.decoding.constants import CPT_GNOSIS_CHAIN
from rotkehlchen.chain.evm.decoding.structures import (
    FAILED_ENRICHMENT_OUTPUT,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.xdai_bridge.decoder import XdaiBridgeCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChainID

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

BRIDGE_ADDRESS: Final = string_to_evm_address('0x4aa42145Aa6Ebf72e164C9bBC74fbD3788045016')
# Transitional peripheral contract before xDAIForeignBridge is upgraded to USDS
XDAI_BRIDGE_PERIPHERAL_PRE_USDS: Final = string_to_evm_address('0xF676cc15Eb6d15b794aeC65bC20052aFB53D9052')  # noqa: E501
# TODO: Add the xdai bridge peripheral contract address after the DAI->USDS upgrade is live.
# See https://github.com/orgs/rotki/projects/11/views/2?pane=issue&itemId=122014729
USER_REQUESTED_FOR_AFFIRMATION: Final = b'\x1dI\x1aB}\x1f\x8c\xc0\xd4GIo0\x0f\xac9\xf70a"H\x1d\x8ef4Q\xeb&\x82t\x14k'  # noqa: E501
USER_REQUESTED_FOR_AFFIRMATION_WITH_NONCE: Final = b'\xf6\x96\x8eh\x9b=\x8c$\xf2,\x10\xc2\xa3%k\xb5\xcaH:GN\x11\xba\xc0\x84#\xba\xa0I\xe3\x8a\xe8'  # noqa: E501
RELAYED_MESSAGE: Final = b'J\xb7\xd5\x813m\x92\xed\xbe\xa2&6\xa6\x13\xe8\xe7l\x99\xac\x7f\x91\x13|\x15#\xdb8\xdb\xfb;\xf3)'  # noqa: E501


class XdaiBridgeDecoder(XdaiBridgeCommonDecoder):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            deposit_topics=(
                USER_REQUESTED_FOR_AFFIRMATION,
                USER_REQUESTED_FOR_AFFIRMATION_WITH_NONCE,
            ),
            withdrawal_topic=RELAYED_MESSAGE,
            bridge_address=BRIDGE_ADDRESS,
            bridged_asset=A_DAI,
            source_chain=ChainID.ETHEREUM,
            target_chain=ChainID.GNOSIS,
            peripheral_addresses=(XDAI_BRIDGE_PERIPHERAL_PRE_USDS,),
        )

    def _maybe_enrich_dai_transfers(self, context: EnricherContext) -> TransferEnrichmentOutput:
        """Unfortunately not all xDAI bridging emits the event we match.

        So we need this special matching of DAI transfers to the bridge address
        in order to find all bridging events.
        """
        if (
                context.event.event_type == HistoryEventType.SPEND and
                context.event.event_subtype == HistoryEventSubType.NONE and
                context.event.asset == A_DAI and
                context.event.address == BRIDGE_ADDRESS
        ):
            context.event.event_type = HistoryEventType.DEPOSIT
            context.event.event_subtype = HistoryEventSubType.BRIDGE
            context.event.notes = f'Bridge {context.event.amount} DAI from Ethereum to Gnosis via Gnosis Chain bridge'  # noqa: E501
            context.event.counterparty = CPT_GNOSIS_CHAIN
            context.event.address = BRIDGE_ADDRESS
            return TransferEnrichmentOutput(matched_counterparty=CPT_GNOSIS_CHAIN)
        return FAILED_ENRICHMENT_OUTPUT

    # -- DecoderInterface methods

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_dai_transfers,
        ]
