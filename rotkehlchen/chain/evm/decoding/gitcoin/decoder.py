import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.constants import (
    CPT_GITCOIN,
    FUNDS_CLAIMED,
    GITCOIN_CPT_DETAILS,
)
from rotkehlchen.chain.evm.decoding.interfaces import CommonGrantsDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import DONATION_SENT, PAYOUT_CLAIMED

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GitcoinOldCommonDecoder(CommonGrantsDecoderMixin):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            bulkcheckout_address: ChecksumEvmAddress | None = None,
            funds_claimed_matching_contracts: list[tuple[ChecksumEvmAddress, str, Asset]] | None = None,  # noqa: E501
            payout_claimed_matching_contracts1: list[tuple[ChecksumEvmAddress, str, Asset]] | None = None,  # noqa: E501
            payout_claimed_matching_contracts2: list[tuple[ChecksumEvmAddress, str, Asset]] | None = None,  # noqa: E501
    ) -> None:
        """
        - bulkcheckout address is the bulk checkout address for the network
        - funds_claimed_matching_contracts is a list containing the matching contracts data
        from which donors can claim the matching funds. Matches the FundsClaimed event.
        - payout_claimed_matching_contract is the same but for contracts containing
        the PayoutClaimed event structure.
        """
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.bulkcheckout_address = bulkcheckout_address
        self.funds_claimed_matching_contracts = funds_claimed_matching_contracts
        self.payout_claimed_matching_contracts1 = payout_claimed_matching_contracts1
        self.payout_claimed_matching_contracts2 = payout_claimed_matching_contracts2

    def _decode_bulkcheckout(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != DONATION_SENT:
            return DEFAULT_EVM_DECODING_OUTPUT

        donor_tracked, dst_tracked = False, False
        if self.base.is_tracked(donor := bytes_to_address(context.tx_log.topics[3])):
            donor_tracked = True

        if self.base.is_tracked(destination := bytes_to_address(context.tx_log.data)):
            dst_tracked = True

        if donor_tracked is False and dst_tracked is False:
            return DEFAULT_EVM_DECODING_OUTPUT

        asset = self.base.get_or_create_evm_asset(bytes_to_address(context.tx_log.topics[1]))  # this checks for ETH special address inside # noqa: E501
        amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.topics[2]),
            asset=asset,
        )

        for event in context.decoded_events:
            if event.asset == asset and event.amount == amount:
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
            return EvmDecodingOutput(action_items=[action_item])

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_funds_claimed_matching(self, context: DecoderContext, name: str, asset: Asset) -> EvmDecodingOutput:  # noqa: E501
        """The > GR13 case seen in mainnet. Example transaction:
        https://etherscan.io/tx/0xc7ba01598f7fee42bb3923af95355d676ad38ec0aebdcdf49eaf7cb74d2150b2
        """
        if context.tx_log.topics[0] == FUNDS_CLAIMED:
            return self._decode_matching_claim_common(
                context=context,
                name=name,
                asset=asset,
                claimee_raw=context.tx_log.topics[1],
                amount_raw=context.tx_log.topics[2],
                counterparty=CPT_GITCOIN,
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_payout_claimed_matching_amount_in_data(self, context: DecoderContext, name: str, asset: Asset) -> EvmDecodingOutput:  # noqa: E501
        """The GR12 case seen in mainnet. Example transaction:
        https://etherscan.io/tx/0x5acb6ddac6b72fc6ff45e6a387cf8316c1478dfbaff513918c4cc8731858b362
        """
        if context.tx_log.topics[0] == PAYOUT_CLAIMED:
            return self._decode_matching_claim_common(
                context=context,
                name=name,
                asset=asset,
                claimee_raw=context.tx_log.topics[1],
                amount_raw=context.tx_log.data,
                counterparty=CPT_GITCOIN,
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_payout_claimed_matching_recipient_in_data(self, context: DecoderContext, name: str, asset: Asset) -> EvmDecodingOutput:  # noqa: E501
        """The GR10-11 case seen in mainnet. Recipient also in data. Example transaction:
        https://etherscan.io/tx/0x3a069b8cef0d25068fbd2ae4e46ddd552451ed1bbe3737fbaaca05eeb87d9425
        """
        if context.tx_log.topics[0] == PAYOUT_CLAIMED:
            return self._decode_matching_claim_common(
                context=context,
                name=name,
                asset=asset,
                claimee_raw=context.tx_log.data[0:32],
                amount_raw=context.tx_log.data[32:64],
                counterparty=CPT_GITCOIN,
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        mapping: dict[ChecksumEvmAddress, tuple[Any, ...]] = {}
        if self.bulkcheckout_address:
            mapping = {
                self.bulkcheckout_address: (self._decode_bulkcheckout,),
            }

        if self.funds_claimed_matching_contracts:
            mapping |= {
                address: (self._decode_funds_claimed_matching, name, asset) for address, name, asset in self.funds_claimed_matching_contracts  # noqa: E501
            }

        if self.payout_claimed_matching_contracts1:
            mapping |= {
                address: (self._decode_payout_claimed_matching_amount_in_data, name, asset) for address, name, asset in self.payout_claimed_matching_contracts1  # noqa: E501
            }

        if self.payout_claimed_matching_contracts2:
            mapping |= {
                address: (self._decode_payout_claimed_matching_recipient_in_data, name, asset) for address, name, asset in self.payout_claimed_matching_contracts2  # noqa: E501
            }

        return mapping

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (GITCOIN_CPT_DETAILS,)
