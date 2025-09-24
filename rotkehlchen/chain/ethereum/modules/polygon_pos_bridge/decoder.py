import logging
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.polygon.constants import CPT_POLYGON, CPT_POLYGON_DETAILS
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import bridge_match_transfer
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.history.events.structures.evm_event import EvmEvent

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BRIDGE_ADDRESS: Final = string_to_evm_address('0xA0c68C638235ee32657e8f720a23ceC1bFc77C77')
ETH_BRIDGE_ADDRESS: Final = string_to_evm_address('0x8484Ef722627bf18ca5Ae6BcF031c23E6e922B30')
ERC20_BRIDGE_ADDRESS: Final = string_to_evm_address('0x40ec5B33f54e0E8A33A975908C5BA1c14e5BbbDf')
PLASMA_BRIDGE_ADDRESS: Final = string_to_evm_address('0x401F6c983eA34274ec46f84D70b31C151321188b')
WITHDRAW_MANAGER_PROXY_ADDRESS: Final = string_to_evm_address('0x2A88696e0fFA76bAA1338F2C74497cC013495922')  # noqa: E501
POLYGON_STATE_SYNCER_ADDRESS: Final = string_to_evm_address('0x28e4F3a7f651294B9564800b2D01f35189A5bFbE')  # noqa: E501
STATE_SYNCED_TOPIC: Final = b'\x10?\xed\x9d\xb6^\xac\x19\xc4\xd8p\xf4\x9a\xb7R\x0f\xe0;\x99\xf1\x83\x8eY\x96\xca\xf4~\x9eC0\x83\x92'  # noqa: E501
EXITED_ERC20_TOPIC: Final = b'\xbba\xbd\x1b&\xb3hL|\x02\x8f\xf1\xa8\xf6\xda\xbc\xac/\xac\x8a\xc5{f\xfak\x1e\xfbn\xde\xab\x03\xc4'  # noqa: E501
EXITED_ETHER_TOPIC: Final = b'\x0f\xc0\xee\xd4\x1fr\xd3\xdaw\xd0\xf5;\x95\x94\xfcps\xac\xd1^\xe9\xd7\xc56\x81\x9ap\xa6|W\xef<'  # noqa: E501
START_EXIT_TOPIC: Final = b'\xaaS\x03\xfd\xad\x12:\xb5\xec\xae\xfa\xf6\x917\xbf\x862%x9TmC\xa3\xb3\xdd\x14\x8c\xc2\x87\x9do'  # noqa: E501
PROCESS_EXIT_TOPIC: Final = b'\xfe\xb2\x00\r\xca>a|\xd6\xf3\xa8\xbb\xb60\x14\xbbT\xa1$\xaa\xc6\xcc\xbfs\xeer)\xb4\xcd\x01\xf1 '  # noqa: E501


class PolygonPosBridgeDecoder(DecoderInterface):

    def _decode_deposit(self, context: DecoderContext) -> DecodingOutput:
        """Decodes ETH and ERC20 bridge deposit events.

        Ethereum to Polygon bridging uses a state sync mechanism to transfer data from ethereum
        to polygon. See https://docs.polygon.technology/pos/architecture/bor/state-sync/

        Mapped to POLYGON_STATE_SYNCER_ADDRESS. When it receives a STATE_SYNCED_TOPIC event,
        a bridge deposit has been initiated and the corresponding spend event needs to be modified.
        """
        if context.tx_log.topics[0] != STATE_SYNCED_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address in {BRIDGE_ADDRESS, ERC20_BRIDGE_ADDRESS, PLASMA_BRIDGE_ADDRESS}
            ):
                user_address = string_to_evm_address(event.location_label)  # type: ignore  # history event location_labels are always initialized
                bridge_match_transfer(
                    event=event,
                    from_address=user_address,
                    to_address=user_address,
                    from_chain=ChainID.ETHEREUM,
                    to_chain=ChainID.POLYGON_POS,
                    amount=event.amount,
                    asset=event.asset.resolve_to_asset_with_symbol(),
                    expected_event_type=HistoryEventType.SPEND,
                    new_event_type=HistoryEventType.DEPOSIT,
                    counterparty=CPT_POLYGON_DETAILS,
                )
                break
        else:
            log.error(f'Failed to find Polygon bridge deposit event for {context.transaction}')

        return DEFAULT_DECODING_OUTPUT

    def _decode_withdraw(self, context: DecoderContext) -> DecodingOutput:
        """Decode ETH and ERC20 bridge withdraw events. (not Plasma, see _decode_plasma_withdraw)

        Mapped to BRIDGE_ADDRESS, ETH_BRIDGE_ADDRESS, and ERC20_BRIDGE_ADDRESS. Also called
        from _decode_plasma_process_exit. Checks if the topic indicates a withdrawal has been
        initiated, and then modifies the corresponding receive event.
        """
        if context.tx_log.topics[0] not in {EXITED_ERC20_TOPIC, EXITED_ETHER_TOPIC, PROCESS_EXIT_TOPIC}:  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address in {BRIDGE_ADDRESS, ETH_BRIDGE_ADDRESS, ERC20_BRIDGE_ADDRESS, PLASMA_BRIDGE_ADDRESS}  # noqa: E501
            ):
                user_address = string_to_evm_address(event.location_label)  # type: ignore  # history event location_labels are always initialized
                bridge_match_transfer(
                    event=event,
                    from_address=user_address,
                    to_address=user_address,
                    from_chain=ChainID.POLYGON_POS,
                    to_chain=ChainID.ETHEREUM,
                    amount=event.amount,
                    asset=event.asset.resolve_to_asset_with_symbol(),
                    expected_event_type=HistoryEventType.RECEIVE,
                    new_event_type=HistoryEventType.WITHDRAWAL,
                    counterparty=CPT_POLYGON_DETAILS,
                )
                break
        else:
            log.error(f'Failed to find Polygon bridge withdraw event for {context.transaction}')

        return DEFAULT_DECODING_OUTPUT

    @staticmethod
    def _is_exit_nft_event(event: 'EvmEvent', match_event_type: HistoryEventType) -> bool:
        """Check if the event matches the specified type and involves the Exit NFT."""
        return (
            event.event_type == match_event_type and
            event.event_subtype == HistoryEventSubType.NONE and
            event.address == ZERO_ADDRESS and
            event.asset.resolve_to_evm_token().token_kind == TokenKind.ERC721
        )

    def _decode_plasma_receive_exit_nft(self, context: DecoderContext) -> DecodingOutput:
        """Decodes Plasma bridge receive exit nft event."""
        for event in context.decoded_events:
            if self._is_exit_nft_event(event=event, match_event_type=HistoryEventType.RECEIVE):
                event.notes = 'Receive Exit NFT from Polygon Bridge'
                event.counterparty = CPT_POLYGON
                break
        else:
            log.error(f'Failed to find Polygon bridge receive Exit NFT event for {context.transaction}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_plasma_process_exit(self, context: DecoderContext) -> DecodingOutput:
        """Decodes Plasma bridge process exit events."""
        for event in context.decoded_events:
            if self._is_exit_nft_event(event=event, match_event_type=HistoryEventType.SPEND):
                event.notes = 'Return Exit NFT to Polygon Bridge'
                event.counterparty = CPT_POLYGON
                break
        else:
            log.error(f'Failed to find Polygon bridge return Exit NFT event for {context.transaction}')  # noqa: E501

        return self._decode_withdraw(context=context)

    def _decode_plasma_withdraw(self, context: DecoderContext) -> DecodingOutput:
        """Decodes withdrawals via Plasma bridge.
        Bridging via Plasma bridge spans two transactions:
            - start exit: begins the withdrawal process and user receives an Exit NFT
            - process exit: user returns the NFT and receives bridged tokens.
        """
        if context.tx_log.topics[0] == START_EXIT_TOPIC:
            return self._decode_plasma_receive_exit_nft(context=context)
        elif context.tx_log.topics[0] == PROCESS_EXIT_TOPIC:
            return self._decode_plasma_process_exit(context=context)

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            POLYGON_STATE_SYNCER_ADDRESS: (self._decode_deposit,),
            BRIDGE_ADDRESS: (self._decode_withdraw,),
            ETH_BRIDGE_ADDRESS: (self._decode_withdraw,),
            ERC20_BRIDGE_ADDRESS: (self._decode_withdraw,),
            WITHDRAW_MANAGER_PROXY_ADDRESS: (self._decode_plasma_withdraw,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CPT_POLYGON_DETAILS,)
