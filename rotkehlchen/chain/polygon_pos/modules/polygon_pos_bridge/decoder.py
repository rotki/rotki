import logging
from collections.abc import Callable
from typing import Any, Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.polygon.constants import CPT_POLYGON, CPT_POLYGON_DETAILS
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import bridge_match_transfer
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

TOKEN_DEPOSITED_TOPIC: Final = b'\xec:\xfb\x06{\xce3\xc5\xa2\x94G\x0e\xc5\xb2\x9egY0\x1c\xd3\x92\x85PI\x0cmH\x81l\xdc/]'  # noqa: E501
WITHDRAW_FOUR_BYTES: Final = b'\x2e\x1a\x7d\x4d'
WITHDRAW_TOPIC: Final = b'\xeb\xff&\x02\xb3\xf4h%\x9e\x1e\x99\xf6\x13\xfe\xd6i\x1f:e&\xef\xfen\xf3\xe7h\xbaz\xe7\xa3lO'  # noqa: E501
LOG_FEE_TRANSFER_TOPIC: Final = b'M\xfe\x1b\xbb\xcf\x07}\xdc>\x01)\x1e\xea-\\p\xc2\xb4"\xb4\x15\xd9VE\xb9\xad\xcf\xd6x\xcb\x1dc'  # noqa: E501
STATE_RECEIVER_ADDRESS: Final = string_to_evm_address('0x0000000000000000000000000000000000001001')
STATE_COMMITTED_TOPIC: Final = b'Z"rU\x90\xb0\xa5\x1c\x929@"?tXQ!d\xb1\x113Y\xa75\xe8n\x7f\'\xf4G\x91\xee'  # noqa: E501
PLASMA_BRIDGE_CHILD_CHAIN: Final = string_to_evm_address('0xD9c7C4ED4B66858301D0cb28Cc88bf655Fe34861')  # noqa: E501
POL_TOKEN_ADDRESS = string_to_evm_address('0x0000000000000000000000000000000000001010')


class PolygonPosBridgeDecoder(EvmDecoderInterface):

    def _decode_withdraw(self, context: DecoderContext) -> DecodingOutput:
        """Decodes bridge withdraw events.

        Ethereum to Polygon bridging uses a state sync mechanism to transfer data from ethereum
        to polygon. See https://docs.polygon.technology/pos/architecture/bor/state-sync/

        Mapped to STATE_RECEIVER_ADDRESS. When it receives a STATE_COMMITTED_TOPIC event, a bridge
        withdrawal has been initiated and the corresponding receive event needs to be modified.
        """
        if context.tx_log.topics[0] != STATE_COMMITTED_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS
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
                    expected_event_type=HistoryEventType.RECEIVE,
                    new_event_type=HistoryEventType.WITHDRAWAL,
                    counterparty=CPT_POLYGON_DETAILS,
                )
                break
        else:
            log.error(f'Failed to find Polygon bridge withdraw event for {context.transaction}')

        return DEFAULT_DECODING_OUTPUT

    def _decode_plasma_withdraw(self, context: DecoderContext) -> DecodingOutput:
        """Decodes withdrawals from plasma bridge.
        No transfer event is decoded automatically, so the withdrawal event must be created here.
        """
        if (
            context.tx_log.topics[0] == TOKEN_DEPOSITED_TOPIC and
            self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[3]))
        ):
            asset = self.base.get_or_create_evm_asset(bytes_to_address(context.tx_log.topics[2]))
            amount = asset_normalized_value(
                amount=int.from_bytes(context.tx_log.data[0:32]),
                asset=asset,
            )
            return DecodingOutput(events=[self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=asset,
                amount=amount,
                location_label=user_address,
                notes=f'Bridge {amount} {asset.resolve_to_asset_with_symbol().symbol} from Ethereum to Polygon POS via Polygon bridge',  # noqa: E501
                counterparty=CPT_POLYGON,
                address=context.tx_log.address,
            )])

        return DEFAULT_DECODING_OUTPUT

    def _decode_deposit(self, context: DecoderContext) -> DecodingOutput:
        """Decodes bridge deposit events.
        The transfer event has not been decoded yet and must be transformed via an action item.

        This is triggered by WITHDRAW_FOUR_BYTES and ERC20_OR_ERC721_TRANSFER, which is quite open.
        To narrow it down we check for the following:
            - transaction has two logs
            - first log is Transfer, second is LogFeeTransfer emitted by POL
            - transfer's from address is a tracked address and to address is ZERO_ADDRESS
        Unfortunately there's nothing else special in the logs to filter against.
        """
        if (
            len(context.all_logs) == 2 and
            context.all_logs[0].topics[0] == ERC20_OR_ERC721_TRANSFER and
            context.all_logs[1].topics[0] == LOG_FEE_TRANSFER_TOPIC and
            context.all_logs[1].address == POL_TOKEN_ADDRESS and
            self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])) and
            bytes_to_address(context.tx_log.topics[2]) == ZERO_ADDRESS
        ):
            asset = self.base.get_or_create_evm_asset(context.tx_log.address)
            amount = asset_normalized_value(
                amount=int.from_bytes(context.tx_log.data[0:32]),
                asset=asset,
            )
            context.action_items.append(ActionItem(
                action='transform',
                from_event_type=HistoryEventType.SPEND,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=asset,
                amount=amount,
                location_label=user_address,
                to_event_type=HistoryEventType.DEPOSIT,
                to_event_subtype=HistoryEventSubType.BRIDGE,
                to_notes=f'Bridge {amount} {asset.resolve_to_asset_with_symbol().symbol} from Polygon POS to Ethereum via Polygon bridge',  # noqa: E501
                to_counterparty=CPT_POLYGON,
            ))

        return DEFAULT_DECODING_OUTPUT

    def _decode_plasma_deposit(self, context: DecoderContext) -> DecodingOutput:
        """Decodes deposits to plasma bridge."""
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == (event_token := event.asset.resolve_to_evm_token()).evm_address
            ):
                user_address = string_to_evm_address(event.location_label)  # type: ignore  # history event location_labels are always initialized
                bridge_match_transfer(
                    event=event,
                    from_address=user_address,
                    to_address=user_address,
                    from_chain=ChainID.POLYGON_POS,
                    to_chain=ChainID.ETHEREUM,
                    amount=event.amount,
                    asset=event_token,
                    expected_event_type=HistoryEventType.SPEND,
                    new_event_type=HistoryEventType.DEPOSIT,
                    counterparty=CPT_POLYGON_DETAILS,
                )
                break
        else:
            log.error(f'Failed to find Polygon bridge plasma deposit event for {context.transaction}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            STATE_RECEIVER_ADDRESS: (self._decode_withdraw,),
            PLASMA_BRIDGE_CHILD_CHAIN: (self._decode_plasma_withdraw,),
        }

    def decoding_by_input_data(self) -> dict[bytes, dict[bytes, Callable]]:
        return {
            WITHDRAW_FOUR_BYTES: {
                ERC20_OR_ERC721_TRANSFER: self._decode_deposit,
                WITHDRAW_TOPIC: self._decode_plasma_deposit,
            },
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CPT_POLYGON_DETAILS,)
