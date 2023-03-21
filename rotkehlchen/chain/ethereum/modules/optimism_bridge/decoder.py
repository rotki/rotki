from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import ActionItem, DecodingOutput
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTokenKind, EvmTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent


BRIDGE_ADDRESS = string_to_evm_address('0x99C9fc46f92E8a1c0deC1b1747d010903E884bE1')

ERC20_DEPOSIT_INITIATED = b'q\x85\x94\x02z\xbdN\xae\xd5\x9f\x95\x16%c\xe0\xccm\x0e\x8d[\x86\xb1\xc7\xbe\x8b\x1b\n\xc34=\x03\x96'  # noqa: E501
ETH_DEPOSIT_INITIATED = b'5\xd7\x9a\xb8\x1f+ \x17\xe1\x9a\xfb\\Uqw\x88wx-z\x87\x86\xf5\x90\x7f\x93\xb0\xf4p/O#'  # noqa: E501
ERC20_WITHDRAWAL_FINALIZED = b'<\xee\xe0l\x1e7d\x8f\xcb\xb6\xedR\xe1{>\x1f\'Z\x1f\x8c{"\xa8K+\x84s$1\xe0F\xb3'  # noqa: E501
ETH_WITHDRAWAL_FINALIZED = b'*\xc6\x9e\xe8\x04\xd9\xa7\xa0\x98BI\xf5\x08\xdf\xab|\xb2SKF[l\xe1X\x0f\x99\xa3\x8b\xa9\xc5\xe61'  # noqa: E501


class OptimismBridgeDecoder(DecoderInterface):
    def _decode_bridge(
            self,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list['EvmEvent'],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
            action_items: list[ActionItem],  # pylint: disable=unused-argument
    ) -> DecodingOutput:
        """Decodes a bridging event. Either a deposit or a withdrawal."""
        if tx_log.topics[0] not in {
            ETH_DEPOSIT_INITIATED,
            ETH_WITHDRAWAL_FINALIZED,
            ERC20_DEPOSIT_INITIATED,
            ERC20_WITHDRAWAL_FINALIZED,
        }:
            # Make sure that we are decoding a supported event.
            return DecodingOutput(counterparty=CPT_OPTIMISM)

        # Read information from event's topics & data
        if tx_log.topics[0] in {ETH_DEPOSIT_INITIATED, ETH_WITHDRAWAL_FINALIZED}:
            asset = A_ETH.resolve_to_crypto_asset()
            raw_amount = hex_or_bytes_to_int(tx_log.data[:32])
            amount = asset_normalized_value(raw_amount, asset)
            from_address = hex_or_bytes_to_address(tx_log.topics[1])
            to_address = hex_or_bytes_to_address(tx_log.topics[2])
        else:  # ERC20_DEPOSIT_INITIATED and ERC20_WITHDRAWAL_FINALIZED
            ethereum_token_address = hex_or_bytes_to_address(tx_log.topics[1])
            asset = EvmToken(evm_address_to_identifier(
                address=ethereum_token_address,
                chain_id=ChainID.ETHEREUM,
                token_type=EvmTokenKind.ERC20,
            ))
            raw_amount = hex_or_bytes_to_int(tx_log.data[32:64])
            amount = asset_normalized_value(raw_amount, asset)
            from_address = hex_or_bytes_to_address(tx_log.topics[3])
            to_address = hex_or_bytes_to_address(tx_log.data[:32])

        # Determine whether it is a deposit or a withdrawal
        if tx_log.topics[0] in {ETH_DEPOSIT_INITIATED, ERC20_DEPOSIT_INITIATED}:
            expected_event_type = HistoryEventType.SPEND
            expected_location_label = from_address
            new_event_type = HistoryEventType.DEPOSIT
            from_chain, to_chain = 'ethereum', 'optimism'
        else:  # ETH_WITHDRAWAL_FINALIZED and ERC20_WITHDRAWAL_FINALIZED
            expected_event_type = HistoryEventType.RECEIVE
            expected_location_label = to_address
            new_event_type = HistoryEventType.WITHDRAWAL
            from_chain, to_chain = 'optimism', 'ethereum'

        # Find the corresponding transfer event and update it
        for event in decoded_events:
            if (
                event.event_type == expected_event_type and
                event.location_label == expected_location_label and
                event.address == BRIDGE_ADDRESS and
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

        return DecodingOutput(counterparty=CPT_OPTIMISM)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            BRIDGE_ADDRESS: (self._decode_bridge,),
        }

    def counterparties(self) -> list[str]:
        return [CPT_OPTIMISM]
