import logging
from typing import Any

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import OPTIMISM_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM
from rotkehlchen.constants.assets import A_OPTIMISM_ETH
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, DecoderEventMappingType, EvmTokenKind
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

BRIDGE_ADDRESS = string_to_evm_address('0x4200000000000000000000000000000000000010')

DEPOSIT_FINALIZED = b'\xb0DE#&\x87\x17\xa0&\x98\xbeG\xd0\x80:\xa7F\x8c\x00\xac\xbe\xd2\xf8\xbd\x93\xa0E\x9c\xdea\xdd\x89'  # noqa: E501
WITHDRAWAL_INITIATED = b"s\xd1p\x91\n\xba\x9emP\xb1\x02\xdbR+\x1d\xbc\xd7\x96!oQ(\xb4E\xaa!5'(\x86I~"  # noqa: E501


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OptimismBridgeDecoder(DecoderInterface):
    def _decode_receive_deposit(self, context: DecoderContext) -> DecodingOutput:
        """Decodes a bridging event. Either a deposit or a withdrawal"""
        if context.tx_log.topics[0] not in {DEPOSIT_FINALIZED, WITHDRAWAL_INITIATED}:
            return DEFAULT_DECODING_OUTPUT

        # Read information from event's topics & data
        ethereum_token_address = hex_or_bytes_to_address(context.tx_log.topics[1])
        optimism_token_address = hex_or_bytes_to_address(context.tx_log.topics[2])
        from_address = hex_or_bytes_to_address(context.tx_log.topics[3])
        to_address = hex_or_bytes_to_address(context.tx_log.data[:32])
        raw_amount = hex_or_bytes_to_int(context.tx_log.data[32:64])

        if ethereum_token_address == ZERO_ADDRESS:
            # This means that ETH was bridged
            asset = A_OPTIMISM_ETH.resolve_to_evm_token()
        else:
            # Otherwise it is a ERC20 token bridging event
            try:
                asset = EvmToken(identifier=evm_address_to_identifier(
                    address=optimism_token_address,
                    chain_id=ChainID.OPTIMISM,
                    token_type=EvmTokenKind.ERC20,
                ))
            except (UnknownAsset, WrongAssetType):
                # can't call `notify_user`` since we don't have any particular event here.
                log.error(f'Failed to resolve asset with address {optimism_token_address} to an optimism token')  # noqa: E501
                return DEFAULT_DECODING_OUTPUT

        amount = asset_normalized_value(asset=asset, amount=raw_amount)

        # Determine whether it is a deposit or a withdrawal
        if context.tx_log.topics[0] == DEPOSIT_FINALIZED:
            expected_event_type = HistoryEventType.RECEIVE
            expected_location_label = from_address
            new_event_type = HistoryEventType.DEPOSIT
            from_chain, to_chain = 'ethereum', 'optimism'
        else:  # WITHDRAWAL_INITIATED
            expected_event_type = HistoryEventType.SPEND
            expected_location_label = to_address
            new_event_type = HistoryEventType.WITHDRAWAL
            from_chain, to_chain = 'optimism', 'ethereum'

        # Find the corresponding transfer event and update it
        for event in context.decoded_events:
            if (
                event.event_type == expected_event_type and
                event.location_label == expected_location_label and
                event.address == ZERO_ADDRESS and
                event.asset == asset and
                event.balance.amount == amount
            ):
                event.event_type = new_event_type
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_OPTIMISM
                event.notes = (
                    f'Bridge {amount} {asset.symbol} from {from_chain} address {from_address} to '
                    f'{to_chain} address {to_address} via optimism bridge'
                )

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            BRIDGE_ADDRESS: (self._decode_receive_deposit,),
        }

    def possible_events(self) -> DecoderEventMappingType:
        return {CPT_OPTIMISM: {
            HistoryEventType.DEPOSIT: {
                HistoryEventSubType.BRIDGE: EventCategory.BRIDGE,
            },
            HistoryEventType.WITHDRAWAL: {
                HistoryEventSubType.BRIDGE: EventCategory.BRIDGE,
            },
        }}

    def counterparties(self) -> list[CounterpartyDetails]:
        return [OPTIMISM_CPT_DETAILS]
