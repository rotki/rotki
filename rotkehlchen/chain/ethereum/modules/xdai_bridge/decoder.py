from typing import TYPE_CHECKING, Final

from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GNOSIS_CHAIN
from rotkehlchen.chain.evm.decoding.structures import (
    FAILED_ENRICHMENT_OUTPUT,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.utils import set_bridge_extra_data
from rotkehlchen.chain.evm.decoding.xdai_bridge.decoder import (
    XdaiBridgeCommonDecoder,
    get_logged_transfer_id,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChainID

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

BRIDGE_ADDRESS: Final = string_to_evm_address('0x4aa42145Aa6Ebf72e164C9bBC74fbD3788045016')
# Transitional peripheral contract before xDAIForeignBridge is upgraded to USDS
XDAI_BRIDGE_PERIPHERAL_PRE_USDS: Final = string_to_evm_address('0xF676cc15Eb6d15b794aeC65bC20052aFB53D9052')  # noqa: E501
# Peripheral contract used after the upgrade. It takes the user's DAI, converts it to USDS
# through the Sky DaiUsds converter and deposits the USDS in the bridge.
XDAI_BRIDGE_PERIPHERAL_USDS: Final = string_to_evm_address('0x3b6669727927b934753B018EB421a84Ed4eb0a43')  # noqa: E501
USER_REQUESTED_FOR_AFFIRMATION: Final = b'\x1dI\x1aB}\x1f\x8c\xc0\xd4GIo0\x0f\xac9\xf70a"H\x1d\x8ef4Q\xeb&\x82t\x14k'  # noqa: E501
USER_REQUESTED_FOR_AFFIRMATION_WITH_NONCE: Final = b'\xf6\x96\x8eh\x9b=\x8c$\xf2,\x10\xc2\xa3%k\xb5\xcaH:GN\x11\xba\xc0\x84#\xba\xa0I\xe3\x8a\xe8'  # noqa: E501
RELAYED_MESSAGE: Final = b'J\xb7\xd5\x813m\x92\xed\xbe\xa2&6\xa6\x13\xe8\xe7l\x99\xac\x7f\x91\x13|\x15#\xdb8\xdb\xfb;\xf3)'  # noqa: E501


class XdaiBridgeDecoder(XdaiBridgeCommonDecoder):

    def __init__(
            self,
            ethereum_inquirer: EthereumInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
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
            peripheral_addresses=(
                XDAI_BRIDGE_PERIPHERAL_PRE_USDS,
                XDAI_BRIDGE_PERIPHERAL_USDS,
            ),
        )

    def _find_deposit_transfer_id(self, context: EnricherContext) -> str:
        """Find the id the gnosis side will use to reference this deposit.

        A deposit the bridge logs with a nonce is affirmed on gnosis by that nonce, while
        one it does not log at all is affirmed by the source transaction hash. The bridge
        logs the deposit right after taking the tokens, so the log is looked up by amount
        among those following the transfer being enriched. That way a transaction bridging
        more than once does not take the id of another of its transfers.
        """
        for tx_log in context.all_logs:
            if (
                tx_log.log_index > context.tx_log.log_index and
                tx_log.address == BRIDGE_ADDRESS and
                len(tx_log.topics) != 0 and
                tx_log.topics[0] == USER_REQUESTED_FOR_AFFIRMATION_WITH_NONCE and
                asset_normalized_value(
                    amount=int.from_bytes(tx_log.data[32:64]),
                    asset=context.token,
                ) == context.event.amount and
                (transfer_id := get_logged_transfer_id(tx_log)) is not None
            ):
                return transfer_id

        return context.transaction.tx_hash.hex()

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
            set_bridge_extra_data(
                event=context.event,
                from_chain=ChainID.ETHEREUM,
                to_chain=ChainID.GNOSIS,
                from_address=context.transaction.from_address,
                transfer_id=self._find_deposit_transfer_id(context),
            )
            return TransferEnrichmentOutput(matched_counterparty=CPT_GNOSIS_CHAIN)
        return FAILED_ENRICHMENT_OUTPUT

    # -- DecoderInterface methods

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_dai_transfers,
        ]
