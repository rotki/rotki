import logging
from abc import ABC
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import bridge_match_transfer, bridge_prepare_data
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, TokenKind
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


DEPOSIT_FINALIZED: Final = b'\xb0DE#&\x87\x17\xa0&\x98\xbeG\xd0\x80:\xa7F\x8c\x00\xac\xbe\xd2\xf8\xbd\x93\xa0E\x9c\xdea\xdd\x89'  # noqa: E501
WITHDRAWAL_INITIATED: Final = b"s\xd1p\x91\n\xba\x9emP\xb1\x02\xdbR+\x1d\xbc\xd7\x96!oQ(\xb4E\xaa!5'(\x86I~"  # noqa: E501

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SuperchainL2SideBridgeCommonDecoder(DecoderInterface, ABC):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            native_assets: Sequence['Asset'],
            bridge_addresses: tuple['ChecksumEvmAddress', ...],
            counterparty: 'CounterpartyDetails',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.bride_addresses = bridge_addresses
        # native assets is a sequence because in optimism there is:
        # 1. ETH transfers (no event emitted)
        # 2. Legacy "system" transfers via 0xDeadDeAddeAddEAddeadDEaDDEAdDeaDDeAD0000
        self.native_assets = native_assets
        self.counterparty = counterparty

    def _decode_receive_or_deposit(self, context: DecoderContext) -> DecodingOutput:
        """Decodes a bridging event.

        Note:
            DAI uses special bridge.

        See:
             https://github.com/makerdao/optimism-dai-bridge
             https://docs.optimism.io/app-developers/bridging/custom-bridge
        """
        if context.tx_log.topics[0] not in {DEPOSIT_FINALIZED, WITHDRAWAL_INITIATED}:
            return DEFAULT_DECODING_OUTPUT

        # Read information from event's topics & data
        l1_token_address = bytes_to_address(context.tx_log.topics[1])
        l2_token_address = bytes_to_address(context.tx_log.topics[2])
        from_address = bytes_to_address(context.tx_log.topics[3])
        to_address = bytes_to_address(context.tx_log.data[:32])
        raw_amount = int.from_bytes(context.tx_log.data[32:64])

        if l1_token_address == ZERO_ADDRESS:
            # This means that ETH was bridged
            asset = self.evm_inquirer.native_token
            valid_assets = self.native_assets
        else:
            # Otherwise it is an ERC20 token bridging event
            try:
                asset = EvmToken(identifier=evm_address_to_identifier(
                    address=l2_token_address,
                    chain_id=self.evm_inquirer.chain_id,
                    token_type=TokenKind.ERC20,
                ))
                valid_assets = (asset,)
            except (UnknownAsset, WrongAssetType):
                # can't call `notify_user`` since we don't have any particular event here.
                log.error(f'Failed to resolve asset with address {l2_token_address} to an {self.evm_inquirer.chain_name} token')  # noqa: E501
                return DEFAULT_DECODING_OUTPUT

        amount = asset_normalized_value(asset=asset, amount=raw_amount)

        expected_event_type, new_event_type, from_chain, to_chain, expected_location_label = bridge_prepare_data(  # noqa: E501
            tx_log=context.tx_log,  # args are opposite here due to the way logs are
            deposit_topics=(WITHDRAWAL_INITIATED,),
            source_chain=self.evm_inquirer.chain_id,
            target_chain=ChainID.ETHEREUM,
            from_address=to_address,
            to_address=from_address,
        )

        # Find the corresponding transfer event and update it
        for event in context.decoded_events:
            if (
                event.event_type == expected_event_type and
                event.location_label == expected_location_label and
                event.address in (ZERO_ADDRESS, *self.bride_addresses) and
                event.asset in valid_assets and
                event.amount == amount
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
                    counterparty=self.counterparty,
                )

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(self.bride_addresses, (self._decode_receive_or_deposit,))
