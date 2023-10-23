import logging
from typing import TYPE_CHECKING, Any, Callable

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.modules.balancer.constants import BALANCER_LABEL, CPT_BALANCER_V2
from rotkehlchen.chain.ethereum.modules.balancer.v2.constants import V2_SWAP, VAULT_ADDRESS
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    FAILED_ENRICHMENT_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Balancerv2Decoder(DecoderInterface):

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
        )
        self.eth = A_ETH.resolve_to_crypto_asset()
        self.weth = A_WETH.resolve_to_evm_token()

    def decode_swap_creation(self, context: DecoderContext) -> DecodingOutput:
        """
        Decode swap in Balancer v2. At the beggining of the transaction a SWAP event is created
        with the information of the tokens and amounts and later some transfers are executed.

        We need to detect this swap event and then match the transferred amounts with the ones
        in the swap event. A special case is the swap of ETH that is wrapped before being sent.
        In this case the token is WETH but we have a tranfer of ETH from the user.
        """
        if context.tx_log.topics[0] != V2_SWAP:
            return DEFAULT_DECODING_OUTPUT

        # The transfer event appears after the swap event, so we need to propagate information
        from_token_address = hex_or_bytes_to_address(context.tx_log.topics[2])
        to_token_address = hex_or_bytes_to_address(context.tx_log.topics[3])
        amount_in = hex_or_bytes_to_int(context.tx_log.data[0:32])
        amount_out = hex_or_bytes_to_int(context.tx_log.data[32:64])

        # Create action item to propagate the information about the swap to the transfer enrichers
        to_token = EvmToken(ethaddress_to_identifier(to_token_address))
        to_amount = asset_normalized_value(
            amount=amount_out,
            asset=to_token,
        )
        action_item = ActionItem(
            action='skip & keep',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=to_token,
            amount=to_amount,
            to_event_type=None,
            to_event_subtype=None,
            to_counterparty=CPT_BALANCER_V2,
            to_notes=None,
            extra_data={
                'from_token': from_token_address,
                'amount_in': amount_in,
            },
        )

        # When ETH is swapped it is wrapped to WETH and the ETH transfer happens before the SWAP
        # event. We need to detect it if we haven't done it yet.
        if len(context.action_items) == 0 and from_token_address == self.weth.evm_address:
            # when swapping eth the transfer event appears before the V2_SWAP event so we need
            # to check if the asset swapped was ETH or not.
            amount_of_eth = asset_normalized_value(
                amount=amount_in,
                asset=self.eth,
            )
            for event in context.decoded_events:
                if (
                    event.asset == A_ETH and event.balance.amount == amount_of_eth and
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE
                ):
                    event.event_type = HistoryEventType.TRADE
                    event.event_subtype = HistoryEventSubType.SPEND
                    event.notes = f'Swap {event.balance.amount} {self.eth.symbol} in Balancer v2'
                    event.counterparty = CPT_BALANCER_V2

        return DecodingOutput(action_items=[action_item])

    def _maybe_enrich_balancer_v2_transfers(
            self,
            context: EnricherContext,
    ) -> TransferEnrichmentOutput:
        """
        Enrich tranfer transactions to account for swaps in balancer v2 protocol.
        May raise:
        - UnknownAsset
        - WrongAssetType
        """
        if context.action_items is None or len(context.action_items) == 0 or context.transaction.to_address != VAULT_ADDRESS:  # noqa: E501
            return FAILED_ENRICHMENT_OUTPUT

        if context.action_items[-1].extra_data is None:
            return FAILED_ENRICHMENT_OUTPUT

        asset = context.event.asset.resolve_to_evm_token()
        if (
            isinstance(context.action_items[-1].asset, EvmToken) is False or
            context.action_items[-1].asset.evm_address != context.tx_log.address or  # type: ignore[attr-defined]  # mypy fails to understand that due the previous statmenet in the or this check won't be evaluated if the asset isn't a token
            context.action_items[-1].amount != context.event.balance.amount
        ):
            return FAILED_ENRICHMENT_OUTPUT

        context.event.counterparty = CPT_BALANCER_V2
        context.event.event_type = HistoryEventType.TRADE
        if asset == context.event.asset:
            context.event.event_subtype = HistoryEventSubType.RECEIVE
            context.event.notes = f'Receive {context.event.balance.amount} {asset.symbol} from Balancer v2'  # noqa: E501
        else:
            context.event.event_subtype = HistoryEventSubType.SPEND

        return TransferEnrichmentOutput(matched_counterparty=CPT_BALANCER_V2)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            VAULT_ADDRESS: (self.decode_swap_creation,),
        }

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_balancer_v2_transfers,
        ]

    def counterparties(self) -> list[CounterpartyDetails]:
        return [CounterpartyDetails(
            identifier=CPT_BALANCER_V2,
            label=BALANCER_LABEL,
            image='balancer.svg',
        )]
