import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.constants import (
    CPT_GITCOIN,
    FUNDS_CLAIMED,
    GITCOIN_CPT_DETAILS,
)
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import DONATION_SENT

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GitcoinOldCommonDecoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            bulkcheckout_address: ChecksumEvmAddress | None = None,
            matching_contracts: list[tuple[ChecksumEvmAddress, str, Asset]] | None = None,
    ) -> None:
        """
        - bulkcheckout address is the bulk checkout address for the network
        - matching_contracts is a list containing the matching contracts data
        from which donors can claim the matching funds.
        - matching_contract2 is the same but for contracts containing a different
        funds claimed log event structure
        """
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.bulkcheckout_address = bulkcheckout_address
        self.matching_contracts = matching_contracts

    def _decode_bulkcheckout(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != DONATION_SENT:
            return DEFAULT_DECODING_OUTPUT

        donor_tracked, dst_tracked = False, False
        if self.base.is_tracked(donor := hex_or_bytes_to_address(context.tx_log.topics[3])):
            donor_tracked = True

        if self.base.is_tracked(destination := hex_or_bytes_to_address(context.tx_log.data)):
            dst_tracked = True

        if donor_tracked is False and dst_tracked is False:
            return DEFAULT_DECODING_OUTPUT

        asset = self.base.get_or_create_evm_asset(hex_or_bytes_to_address(context.tx_log.topics[1]))  # this checks for ETH special address inside # noqa: E501
        amount = asset_normalized_value(
            amount=hex_or_bytes_to_int(context.tx_log.topics[2]),
            asset=asset,
        )

        for event in context.decoded_events:
            if event.asset == asset and event.balance.amount == amount:
                if dst_tracked:
                    event.event_type = HistoryEventType.RECEIVE
                    event.event_subtype = HistoryEventSubType.DONATE
                    event.counterparty = CPT_GITCOIN
                    event.location_label = destination
                    event.address = donor
                    event.notes = f'Receive donation of {amount} {asset.resolve_to_asset_with_symbol().symbol} from {donor} via gitcoin'  # noqa: E501
                else:
                    event.event_type = HistoryEventType.SPEND
                    event.event_subtype = HistoryEventSubType.DONATE
                    event.counterparty = CPT_GITCOIN
                    event.location_label = donor
                    event.address = destination
                    event.notes = f'Donate {amount} {asset.resolve_to_asset_with_symbol().symbol} to {destination} via gitcoin'  # noqa: E501

                break

        else:  # not found so transfer event gets decoded later
            if dst_tracked:
                from_event_type = HistoryEventType.RECEIVE
                location_label = destination
                address = donor
                notes = f'Receive donation of {amount} {asset.resolve_to_asset_with_symbol().symbol} from {donor} via gitcoin'  # noqa: E501
            else:
                from_event_type = HistoryEventType.SPEND
                location_label = donor
                address = destination
                notes = f'Donate {amount} {asset.resolve_to_asset_with_symbol().symbol} to {destination} via gitcoin'  # noqa: E501

            action_item = ActionItem(
                action='transform',
                from_event_type=from_event_type,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=asset,
                amount=amount,
                to_event_subtype=HistoryEventSubType.DONATE,
                to_location_label=location_label,
                to_address=address,
                to_notes=notes,
                to_counterparty=CPT_GITCOIN,
            )
            return DecodingOutput(action_items=[action_item])

        return DEFAULT_DECODING_OUTPUT

    def _decode_matching_claim_common(
            self,
            context: DecoderContext,
            name: str,
            asset: Asset,
            claimee_raw: bytes,
            amount_raw: bytes,
    ) -> DecodingOutput:
        """Decode the matching funds claim based on the given name and asset. We need
        to provide the name and the asset as this is based per contract and does not change.

        For the token we could query it but the name we can't. Still since it's hard
        coded per contract and we have a hard coded list it's best to not ask the chain
        and do an extra network query since this is immutable."""
        if context.tx_log.topics[0] != FUNDS_CLAIMED:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.any_tracked([claimee := hex_or_bytes_to_address(claimee_raw), context.transaction.from_address]):  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        asset = asset.resolve_to_crypto_asset()
        amount = asset_normalized_value(
            amount=hex_or_bytes_to_int(amount_raw),
            asset=asset,
        )
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == asset and
                    event.balance.amount == amount and
                    event.location_label == claimee
            ):
                event.event_subtype = HistoryEventSubType.DONATE
                event.counterparty = CPT_GITCOIN
                event.notes = f'Claim {amount} {asset.symbol} as matching funds payout of gitcoin {name}'  # noqa: E501
                if context.transaction.from_address != claimee:
                    event.notes += f' for {claimee}'
                break

        else:
            log.error(
                f'Failed to find the gitcoin matching receive transfer for {self.evm_inquirer.chain_name} transaction {context.transaction.tx_hash.hex()}.',  # noqa: E501
            )

        return DEFAULT_DECODING_OUTPUT

    def _decode_matching_claim(self, context: DecoderContext, name: str, asset: Asset) -> DecodingOutput:  # noqa: E501
        """The normal case seen in mainnet. Example transaction:
        https://etherscan.io/tx/0xc7ba01598f7fee42bb3923af95355d676ad38ec0aebdcdf49eaf7cb74d2150b2
        """
        if context.tx_log.topics[0] == FUNDS_CLAIMED:
            return self._decode_matching_claim_common(
                context=context,
                name=name,
                asset=asset,
                claimee_raw=context.tx_log.topics[1],
                amount_raw=context.tx_log.topics[2],
            )

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        mapping: dict[ChecksumEvmAddress, tuple[Any, ...]] = {}
        if self.bulkcheckout_address:
            mapping = {
                self.bulkcheckout_address: (self._decode_bulkcheckout,),
            }

        if self.matching_contracts:
            mapping |= {
                address: (self._decode_matching_claim, name, asset) for address, name, asset in self.matching_contracts  # noqa: E501
            }

        return mapping

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (GITCOIN_CPT_DETAILS,)
