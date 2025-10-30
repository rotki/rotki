import json
import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset, CryptoAsset
from rotkehlchen.chain.arbitrum_one.modules.clrfund.constants import (
    CLRFUND_CPT_DETAILS,
    CPT_CLRFUND,
    REQUEST_SUBMITTED_ABI,
)
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi_str
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.constants import FUNDS_CLAIMED
from rotkehlchen.chain.evm.decoding.interfaces import CommonGrantsDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ClrfundCommonDecoder(CommonGrantsDecoderMixin):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',  # pylint: disable=unused-argument
            rounds_data: list[tuple[ChecksumEvmAddress, ChecksumEvmAddress, str, Asset]],
    ) -> None:
        """Initialize Clrfund decoder. Rounds exist in arbitrum and gnosis chains
        https://clr.fund/#/rounds

        Round data contain:
        - the funding round address. That's where participants withdraw donations from
        and where contributors donate to
        - the recipient registry address. That's where participant apply to participate
        - round name
        - asset used to donate/payout in the round
        """
        CommonGrantsDecoderMixin.__init__(
            self,
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.rounds_data = rounds_data

    def _decode_funding_round_events(self, context: DecoderContext, name: str, asset: Asset) -> EvmDecodingOutput:  # noqa: E501
        if context.tx_log.topics[0] == FUNDS_CLAIMED:
            return self._decode_matching_claim_common(
                context=context,
                name=name,
                asset=asset,
                claimee_raw=context.tx_log.topics[2],
                amount_raw=context.tx_log.data,
                counterparty=CPT_CLRFUND,
            )
        elif context.tx_log.topics[0] == b"\x16\xa9\xaa9\xafI\xf1i\x91\x1e\x97sG\x97Q\x98\xc5\x03R_r@\xd6\x89*bo\x02'd/\xce":  # Voted  # noqa: E501
            return self._decode_voted(context=context, name=name)
        elif context.tx_log.topics[0] == b'M\x15MJ\xae!k\xedm\t&\xdbw\xc0\r\xf2\xb5|k[\xa4\xee\xe0Wu\xde \xfa\xce\xde:{':  # Contribution  # noqa: E501
            return self._decode_contribution(context=context, asset=asset.resolve_to_crypto_asset(), name=name)  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_voted(self, context: DecoderContext, name: str) -> EvmDecodingOutput:
        if not self.base.any_tracked([user := bytes_to_address(context.tx_log.topics[1]), context.transaction.from_address]):  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        new_event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user,
            notes=f'Vote in Clrfund {name}',
            counterparty=CPT_CLRFUND,
            address=context.tx_log.address,
        )
        return EvmDecodingOutput(events=[new_event])

    def _decode_contribution(self, context: DecoderContext, asset: CryptoAsset, name: str) -> EvmDecodingOutput:  # noqa: E501
        if not self.base.any_tracked([sender := bytes_to_address(context.tx_log.topics[1]), context.transaction.from_address]):  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data),
            asset=asset,
        )
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == asset and
                    event.amount == amount and
                    event.address == context.tx_log.address
            ):
                event.location_label = sender
                event.event_subtype = HistoryEventSubType.DONATE
                event.counterparty = CPT_CLRFUND
                event.address = context.tx_log.address
                event.notes = f'Donate {amount} {asset.symbol} to Clrfund {name}'
                break

        else:  # not found
            log.error(f'Failed to find clrfund donation event for {self.node_inquirer.chain_name} {context.transaction.tx_hash!s}')  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_recipient_registry(self, context: DecoderContext, name: str) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != b'\xbbJ\xd3\x18\xe5\x17\x03W\xf8\xe7\xd2]\xee\xfe\\\xf0+\xc8\x18,\xbb\x95`\x0c"\xa1\x10Yx\xa8\xf1\xb8':  # RequestSubmitted # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.any_tracked([recipient := bytes_to_address(context.tx_log.data[:32]), context.transaction.from_address]):  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        try:  # using decode_event_data_abi_str since data contains a string
            _, decoded_data = decode_event_data_abi_str(context.tx_log, REQUEST_SUBMITTED_ABI)
        except DeserializationError as e:
            log.error(f'Failed to decode clrfund request submitted event due to {e!s} for {self.node_inquirer.chain_name} {context.transaction.tx_hash!s}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        jsondata, new_event = {}, None
        try:
            jsondata = json.loads(decoded_data[1])
        except json.JSONDecodeError as e:
            log.error(f'Failed to decode json from clrfund data: {decoded_data[1]} due to {e!s}')

        notes = f'Apply to clrfund {name} with {jsondata.get("name", "a project")}'
        for event in context.decoded_events:  # find the payment to the contract for applying
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == self.node_inquirer.native_token and
                    event.address == context.tx_log.address
            ):
                event.event_subtype = HistoryEventSubType.FEE
                event.counterparty = CPT_CLRFUND
                event.notes = f'{notes} and pay a {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} fee'  # noqa: E501
                break

        else:  # event not found. Perhaps no fee? Just make info event
            new_event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ZERO,
                location_label=recipient,
                notes=f'Apply to clrfund for {jsondata.get("name", "a project")}',
                counterparty=CPT_CLRFUND,
                address=context.tx_log.address,
            )

        return EvmDecodingOutput(events=[new_event] if new_event is not None else None)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        mappings: dict[ChecksumEvmAddress, tuple[Any, ...]] = {}
        for funding_address, recipient_registry_address, name, asset in self.rounds_data:
            mappings[funding_address] = (self._decode_funding_round_events, name, asset)
            mappings[recipient_registry_address] = (self._decode_recipient_registry, name)

        return mappings

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CLRFUND_CPT_DETAILS,)
