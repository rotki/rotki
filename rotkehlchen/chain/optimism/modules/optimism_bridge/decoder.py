import logging
from typing import Any, Final

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
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import bridge_match_transfer, bridge_prepare_data
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_OPTIMISM_ETH
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTokenKind
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

BRIDGE_ADDRESSES: Final = (
    string_to_evm_address('0x4200000000000000000000000000000000000010'),  # Normal Bridge
    string_to_evm_address('0x467194771dAe2967Aef3ECbEDD3Bf9a310C76C65'),  # L2DAITokenBridge
)

DEPOSIT_FINALIZED: Final = b'\xb0DE#&\x87\x17\xa0&\x98\xbeG\xd0\x80:\xa7F\x8c\x00\xac\xbe\xd2\xf8\xbd\x93\xa0E\x9c\xdea\xdd\x89'  # noqa: E501
WITHDRAWAL_INITIATED: Final = b"s\xd1p\x91\n\xba\x9emP\xb1\x02\xdbR+\x1d\xbc\xd7\x96!oQ(\xb4E\xaa!5'(\x86I~"  # noqa: E501


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OptimismBridgeDecoder(DecoderInterface):
    def _decode_receive_deposit(self, context: DecoderContext) -> DecodingOutput:
        """Decodes a bridging event. Either a deposit or a withdrawal
        DAI uses special bridge. See https://github.com/makerdao/optimism-dai-bridge
        """
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

        expected_event_type, new_event_type, from_chain, to_chain, expected_location_label = bridge_prepare_data(  # noqa: E501
            tx_log=context.tx_log,  # args are opposite here due to the way logs are
            deposit_topics=(WITHDRAWAL_INITIATED,),
            source_chain=ChainID.OPTIMISM,
            target_chain=ChainID.ETHEREUM,
            from_address=to_address,
            to_address=from_address,
        )

        # Find the corresponding transfer event and update it
        for event in context.decoded_events:
            if (
                event.event_type == expected_event_type and
                event.location_label == expected_location_label and
                event.address == ZERO_ADDRESS and
                event.asset == asset and
                event.balance.amount == amount
            ):
                bridge_match_transfer(
                    event=event,
                    from_address=from_address,
                    to_address=to_address,
                    from_chain=from_chain,
                    to_chain=to_chain,
                    amount=amount,
                    asset=asset,
                    expected_event_type=expected_event_type,
                    new_event_type=new_event_type,
                    counterparty=OPTIMISM_CPT_DETAILS,
                )

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(BRIDGE_ADDRESSES, (self._decode_receive_deposit,))

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (OPTIMISM_CPT_DETAILS,)
