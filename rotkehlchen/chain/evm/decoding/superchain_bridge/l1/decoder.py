from abc import ABC
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import bridge_match_transfer, bridge_prepare_data
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChainID, ChecksumEvmAddress, TokenKind
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


ERC20_DEPOSIT_INITIATED: Final = b'q\x85\x94\x02z\xbdN\xae\xd5\x9f\x95\x16%c\xe0\xccm\x0e\x8d[\x86\xb1\xc7\xbe\x8b\x1b\n\xc34=\x03\x96'  # noqa: E501
ETH_DEPOSIT_INITIATED: Final = b'5\xd7\x9a\xb8\x1f+ \x17\xe1\x9a\xfb\\Uqw\x88wx-z\x87\x86\xf5\x90\x7f\x93\xb0\xf4p/O#'  # noqa: E501
ERC20_WITHDRAWAL_FINALIZED: Final = b'<\xee\xe0l\x1e7d\x8f\xcb\xb6\xedR\xe1{>\x1f\'Z\x1f\x8c{"\xa8K+\x84s$1\xe0F\xb3'  # noqa: E501
ETH_WITHDRAWAL_FINALIZED: Final = b'*\xc6\x9e\xe8\x04\xd9\xa7\xa0\x98BI\xf5\x08\xdf\xab|\xb2SKF[l\xe1X\x0f\x99\xa3\x8b\xa9\xc5\xe61'  # noqa: E501
WITHDRAWAL_PROVEN: Final = b'g\xa6 \x8c\xfc\xc0\x80\x1dP\xf6\xcb\xe7ds?O\xdd\xf6j\xc0\xb0DB\x06\x1a\x8a\x8c\x0c\xb6\xb6?b'  # noqa: E501


class SuperchainL1SideCommonBridgeDecoder(DecoderInterface, ABC):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            bridge_addresses: tuple['ChecksumEvmAddress', ...],
            counterparty: 'CounterpartyDetails',
            l2_chain: 'ChainID',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.bride_addresses = bridge_addresses
        self.counterparty = counterparty
        self.l2_chain = l2_chain

    def _decode_bridge(self, context: DecoderContext) -> DecodingOutput:
        """Decodes a bridging(deposit or withdrawal) event for superchain chains.

        Note:
            DAI uses special bridge for OP mainnet.

        See:
             https://github.com/makerdao/optimism-dai-bridge
             https://docs.optimism.io/app-developers/bridging/custom-bridge
        """
        if context.tx_log.topics[0] not in {
            ETH_DEPOSIT_INITIATED,
            ETH_WITHDRAWAL_FINALIZED,
            ERC20_DEPOSIT_INITIATED,
            ERC20_WITHDRAWAL_FINALIZED,
        }:
            # Make sure that we are decoding a supported event.
            return DEFAULT_DECODING_OUTPUT

        # Read information from event's topics & data
        if context.tx_log.topics[0] in {ETH_DEPOSIT_INITIATED, ETH_WITHDRAWAL_FINALIZED}:
            asset = A_ETH.resolve_to_crypto_asset()
            raw_amount = int.from_bytes(context.tx_log.data[:32])
            amount = asset_normalized_value(raw_amount, asset)
            from_address = bytes_to_address(context.tx_log.topics[1])
            to_address = bytes_to_address(context.tx_log.topics[2])
        else:  # ERC20_DEPOSIT_INITIATED and ERC20_WITHDRAWAL_FINALIZED
            ethereum_token_address = bytes_to_address(context.tx_log.topics[1])
            asset = EvmToken(evm_address_to_identifier(
                address=ethereum_token_address,
                chain_id=ChainID.ETHEREUM,
                token_type=TokenKind.ERC20,
            ))
            raw_amount = int.from_bytes(context.tx_log.data[32:64])
            amount = asset_normalized_value(raw_amount, asset)
            from_address = bytes_to_address(context.tx_log.topics[3])
            to_address = bytes_to_address(context.tx_log.data[:32])

        expected_event_type, new_event_type, from_chain, to_chain, expected_location_label = bridge_prepare_data(  # noqa: E501
            tx_log=context.tx_log,
            deposit_topics=(ETH_DEPOSIT_INITIATED, ERC20_DEPOSIT_INITIATED),
            target_chain=self.l2_chain,
            source_chain=ChainID.ETHEREUM,
            from_address=from_address,
            to_address=to_address,
        )

        # Find the corresponding transfer event and update it
        for event in context.decoded_events:
            if (
                event.event_type == expected_event_type and
                event.location_label == expected_location_label and
                event.address in self.bride_addresses and
                event.asset == asset and
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

    def _decode_prove_withdrawal(self, context: DecoderContext) -> DecodingOutput:
        """Decodes a proving withdrawal event."""
        if context.tx_log.topics[0] != WITHDRAWAL_PROVEN:
            return DEFAULT_DECODING_OUTPUT

        withdrawal_hash = context.tx_log.topics[1].hex()
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=context.transaction.from_address,
            notes=f'Prove optimism bridge withdrawal 0x{withdrawal_hash}',
            counterparty=self.counterparty.identifier,
            address=context.tx_log.address,
        )
        return DecodingOutput(events=[event])

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(self.bride_addresses, (self._decode_bridge,))
