import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Callable, Optional

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface, ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_ENRICHMENT_OUTPUT,
    ActionItem,
    DecodingOutput,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address

from .constants import CPT_CURVE
from .pools_cache import read_curve_pools

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


ADD_LIQUIDITY = b'B?d\x95\xa0\x8f\xc6RB\\\xf4\xed\r\x1f\x9e7\xe5q\xd9\xb9R\x9b\x1c\x1c#\xcc\xe7\x80\xb2\xe7\xdf\r'  # noqa: E501
ADD_LIQUIDITY_2_ASSETS = b'&\xf5Z\x85\x08\x1d$\x97N\x85\xc6\xc0\x00E\xd0\xf0E9\x91\xe9Xs\xf5+\xff\r!\xaf@y\xa7h'  # noqa: E501
ADD_LIQUIDITY_4_ASSETS = b'?\x19\x15w^\x0c\x9a8\xa5z{\xb7\xf1\xf9\x00_Ho\xb9\x04\xe1\xf8J\xa2\x156MVs\x19\xa5\x8d'  # noqa: E501
REMOVE_LIQUIDITY = b"Z\xd0V\xf2\xe2\x8a\x8c\xec# \x15@k\x846h\xc1\xe3l\xdaY\x81'\xec;\x8cY\xb8\xc7's\xa0"  # noqa: E501
REMOVE_ONE = b'\x9e\x96\xdd;\x99z*%~\xecM\xf9\xbbn\xafbn m\xf5\xf5C\xbd\x966\x82\xd1C0\x0b\xe3\x10'  # noqa: E501
REMOVE_LIQUIDITY_3_ASSETS = b'\xa4\x9dL\xf0&V\xae\xbf\x8cw\x1fZ\x85\x85c\x8a*\x15\xeel\x97\xcfr\x05\xd4 \x8e\xd7\xc1\xdf%-'  # noqa: E501
REMOVE_LIQUIDITY_4_ASSETS = b'\x98x\xca7^\x10o*C\xc3\xb5\x99\xfcbEh\x13\x1cL\x9aK\xa6j\x14V7\x15v;\xe9\xd5\x9d'  # noqa: E501
REMOVE_LIQUIDITY_IMBALANCE = b'\xb9d\xb7/s\xf5\xef[\xf0\xfd\xc5Y\xb2\xfa\xb9\xa7\xb1*9\xe4x\x17\xa5G\xf1\xf0\xae\xe4\x7f\xeb\xd6\x02'  # noqa: E501
CURVE_Y_DEPOSIT = string_to_evm_address('0xbBC81d23Ea2c3ec7e56D39296F0cbB648873a5d3')
DEFAULT_DECODING_OUTPUT = DecodingOutput(counterparty=CPT_CURVE)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CurveDecoder(DecoderInterface, ReloadableDecoderMixin):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',  # pylint: disable=unused-argument
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.curve_pools = read_curve_pools()
        self.ethereum = ethereum_inquirer

    def _decode_curve_remove_events(
            self,
            transaction: EvmTransaction,
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
            user_address: ChecksumEvmAddress,
    ) -> DecodingOutput:
        """Decode information related to withdrawing assets from curve pools"""
        withdrawal_events: list['EvmEvent'] = []
        return_event: Optional['EvmEvent'] = None
        for event in decoded_events:
            try:
                crypto_asset = event.asset.resolve_to_crypto_asset()
            except (UnknownAsset, WrongAssetType):
                self.notify_user(event=event, counterparty=CPT_CURVE)
                continue

            if (  # Withdraw eth
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_ETH and
                event.location_label == user_address
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_CURVE
                event.notes = f'Remove {event.balance.amount} {crypto_asset.symbol} from the curve pool'  # noqa: E501
                withdrawal_events.append(event)
            elif (  # Withdraw send wrapped
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == transaction.from_address and
                (
                    user_address == event.location_label or
                    tx_log.topics[0] == REMOVE_LIQUIDITY_IMBALANCE
                )
            ):
                event.event_type = HistoryEventType.SPEND
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_CURVE
                event.notes = f'Return {event.balance.amount} {crypto_asset.symbol}'
                return_event = event
            elif (  # Withdraw receive asset
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == transaction.from_address and
                user_address == event.location_label and
                tx_log.address in self.curve_pools
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_CURVE
                event.notes = f'Remove {event.balance.amount} {crypto_asset.symbol} from the curve pool {tx_log.address}'  # noqa: E501
                withdrawal_events.append(event)

        # Make sure that the order is the following:
        # 1. Return pool token event
        # 2. Withdrawal 1
        # 3. Withdrawal 2
        # etc.
        if return_event is None or len(withdrawal_events) == 0:
            log.debug(
                f'Expected to see a receive pool token event and deposit events for a curve pool, '
                f'but have not found them. Tx_hash: {transaction.tx_hash.hex()} '
                f'User address: {user_address}',
            )
            return DEFAULT_DECODING_OUTPUT

        return_event.extra_data = {'withdrawal_events_num': len(withdrawal_events)}  # for accounting  # noqa: E501
        previous_event = return_event
        for event in withdrawal_events:
            maybe_reshuffle_events(previous_event, event, decoded_events)
            previous_event = event
        return DEFAULT_DECODING_OUTPUT

    def _decode_curve_deposit_events(
            self,
            transaction: EvmTransaction,
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
            user_address: ChecksumEvmAddress,
    ) -> DecodingOutput:
        """Decode information related to depositing assets in curve pools"""
        deposit_events: list['EvmEvent'] = []
        receive_event: Optional['EvmEvent'] = None
        for event in decoded_events:
            try:
                crypto_asset = event.asset.resolve_to_crypto_asset()
            except (UnknownAsset, WrongAssetType):
                self.notify_user(event=event, counterparty=CPT_CURVE)
                continue

            if (  # Deposit ETH
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_ETH and
                event.location_label == user_address
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_CURVE
                event.notes = f'Deposit {event.balance.amount} {crypto_asset.symbol} in curve pool'  # noqa: E501
                deposit_events.append(event)
            elif (  # deposit give asset
                (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == user_address and
                    tx_log.address in self.curve_pools
                ) or
                (
                    tx_log.topics[0] == ADD_LIQUIDITY_4_ASSETS and
                    user_address == CURVE_Y_DEPOSIT and
                    event.asset != A_ETH
                )
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_CURVE
                event.notes = f'Deposit {event.balance.amount} {crypto_asset.symbol} in curve pool'  # noqa: E501
                if tx_log.address in self.curve_pools:
                    event.notes += f' {tx_log.address}'
                deposit_events.append(event)
            elif (  # Deposit receive pool token
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                tx_log.address in self.curve_pools
            ):
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_CURVE
                event.notes = f'Receive {event.balance.amount} {crypto_asset.symbol} after depositing in curve pool {tx_log.address}'  # noqa: E501
                receive_event = event
            elif (  # deposit give asset
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                tx_log.address in self.curve_pools
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_CURVE
                event.notes = f'Deposit {event.balance.amount} {crypto_asset.symbol} in curve pool {tx_log.address}'  # noqa: E501
                deposit_events.append(event)

        # Make sure that the order is the following:
        # 1. Receive pool token event
        # 2. Deposit 1
        # 3. Deposit 2
        # etc.
        if receive_event is None or len(deposit_events) == 0:
            log.debug(
                f'Expected to see a receive pool token event and deposit events for a curve pool, '
                f'but have not found them. Tx_hash: {transaction.tx_hash.hex()} '
                f'User address: {user_address}',
            )
            return DEFAULT_DECODING_OUTPUT

        receive_event.extra_data = {'deposit_events_num': len(deposit_events)}  # for accounting
        previous_event = receive_event
        for event in deposit_events:
            maybe_reshuffle_events(previous_event, event, decoded_events)
            previous_event = event
        return DEFAULT_DECODING_OUTPUT

    def _decode_curve_events(
            self,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
            action_items: Optional[list[ActionItem]],  # pylint: disable=unused-argument
    ) -> DecodingOutput:
        if tx_log.topics[0] in (
            REMOVE_LIQUIDITY,
            REMOVE_ONE,
            REMOVE_LIQUIDITY_IMBALANCE,
            REMOVE_LIQUIDITY_3_ASSETS,
            REMOVE_LIQUIDITY_4_ASSETS,
        ):
            user_address = hex_or_bytes_to_address(tx_log.topics[1])
            return self._decode_curve_remove_events(
                tx_log=tx_log,
                transaction=transaction,
                decoded_events=decoded_events,
                user_address=user_address,
            )
        if tx_log.topics[0] in (
            ADD_LIQUIDITY,
            ADD_LIQUIDITY_2_ASSETS,
            ADD_LIQUIDITY_4_ASSETS,
        ):
            user_address = hex_or_bytes_to_address(tx_log.topics[1])
            return self._decode_curve_deposit_events(
                transaction=transaction,
                tx_log=tx_log,
                decoded_events=decoded_events,
                user_address=user_address,
            )

        return DEFAULT_DECODING_OUTPUT

    @staticmethod
    def _maybe_enrich_curve_transfers(
            token: EvmToken,  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            event: 'EvmEvent',
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> TransferEnrichmentOutput:
        """
        May raise:
        - UnknownAsset
        - WrongAssetType
        """
        source_address = hex_or_bytes_to_address(tx_log.topics[1])
        to_address = hex_or_bytes_to_address(tx_log.topics[2])
        if (  # deposit give asset
            event.event_type == HistoryEventType.RECEIVE and
            event.event_subtype == HistoryEventSubType.NONE and
            source_address == CURVE_Y_DEPOSIT and
            transaction.from_address == to_address
        ):
            crypto_asset = event.asset.resolve_to_crypto_asset()
            event.event_type = HistoryEventType.WITHDRAWAL
            event.event_subtype = HistoryEventSubType.REMOVE_ASSET
            event.counterparty = CPT_CURVE
            event.notes = f'Receive {event.balance.amount} {crypto_asset.symbol} from the curve pool {CURVE_Y_DEPOSIT}'  # noqa: E501
            return TransferEnrichmentOutput(counterparty=CPT_CURVE)
        return DEFAULT_ENRICHMENT_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            address: (self._decode_curve_events,)
            for address in self.curve_pools
        }

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_curve_transfers,
        ]

    def counterparties(self) -> list[str]:
        return [CPT_CURVE]

    def reload_data(self) -> Optional[Mapping[ChecksumEvmAddress, tuple[Any, ...]]]:
        """Make sure curve pools are recently queried from the chain, saved in the DB
        and loaded to the decoder's memory.

        If a query happens and any new mappings are generated they are returned,
        otherwise `None` is returned.
        """
        self.ethereum.assure_curve_protocol_cache_is_queried()
        new_curve_pools = read_curve_pools()
        curve_pools_diff = new_curve_pools - self.curve_pools
        if curve_pools_diff == set():
            return None

        new_mapping: Mapping[ChecksumEvmAddress, tuple[Callable]] = {
            pool_addr: (self._decode_curve_events,)
            for pool_addr in curve_pools_diff
        }
        self.curve_pools = new_curve_pools
        return new_mapping
