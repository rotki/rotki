import logging
from typing import TYPE_CHECKING, Any, Callable, Optional

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.balancer.types import BalancerV1EventTypes
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import ActionItem
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import CPT_BALANCER_V1, CPT_BALANCER_V2

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

V2_SWAP = b'!p\xc7A\xc4\x151\xae\xc2\x0e|\x10|$\xee\xcf\xdd\x15\xe6\x9c\x9b\xb0\xa8\xdd7\xb1\x84\x0b\x9e\x0b {'  # noqa: E501
JOIN_V1 = b'c\x98-\xf1\x0e\xfd\x8d\xfa\xaa\xa0\xfc\xc7\xf5\x0b-\x93\xb7\xcb\xa2l\xccH\xad\xee(s"\rH]\xc3\x9a'  # noqa: E501
EXIT_V1 = b'\xe7L\x91U+d\xc2\xe2\xe7\xbd%V9\xe0\x04\xe6\x93\xbd>\x1d\x01\xcc3\xe6V\x10\xb8j\xfc\xc1\xff\xed'  # noqa: E501
VAULT_ADDRESS = string_to_evm_address('0xBA12222222228d8Ba445958a75a0704d566BF2C8')

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BalancerDecoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.base_tools = base_tools
        self.eth = A_ETH.resolve_to_crypto_asset()
        self.weth = A_WETH.resolve_to_evm_token()

    def _decode_v1_pool_event(self, all_logs: list[EvmTxReceiptLog]) -> Optional[list[ActionItem]]:
        """Read the list of logs in search for a Balancer V1 event and return the information
        needed to decode the transfers made in the transaction to/from the ds proxy
        """
        # The transfer event appears after the debt generation event, so we need to transform it
        target_logs = []
        for tx_log in all_logs:
            if tx_log.topics[0] == JOIN_V1 or tx_log.topics[0] == EXIT_V1:
                target_logs.append(tx_log)

        if len(target_logs) == 0:
            return None

        action_items = []
        for target_log in target_logs:
            token_address = hex_or_bytes_to_address(target_log.topics[2])
            amount = hex_or_bytes_to_int(target_log.data[0:32])
            if target_log.topics[0] == JOIN_V1:
                balancer_event_type = BalancerV1EventTypes.JOIN
                from_event_type = HistoryEventType.SPEND
                ds_address = hex_or_bytes_to_address(target_log.topics[1])

            else:
                balancer_event_type = BalancerV1EventTypes.EXIT
                from_event_type = HistoryEventType.RECEIVE
                ds_address = target_log.address

            action_item = ActionItem(
                action='transform',
                sequence_index=target_log.log_index,
                from_event_type=from_event_type,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=self.eth,
                amount=ZERO,
                to_event_type=None,
                to_event_subtype=None,
                to_counterparty=CPT_BALANCER_V1,
                to_notes=None,
                extra_data={
                    'ds_address': ds_address,
                    'token_address': token_address,
                    'amount': amount,
                    'type': balancer_event_type,
                },
            )
            action_items.append(action_item)

        return action_items

    def _decode_swap_creation(
            self,
            tx_log: EvmTxReceiptLog,
            decoded_events: list[HistoryBaseEntry],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
    ) -> tuple[Optional[HistoryBaseEntry], list[ActionItem]]:
        # The transfer event appears after the debt generation event, so we need to transform it
        from_token = hex_or_bytes_to_address(tx_log.topics[2])
        to_token = hex_or_bytes_to_address(tx_log.topics[3])
        amount_in = hex_or_bytes_to_int(tx_log.data[0:32])
        amount_out = hex_or_bytes_to_int(tx_log.data[32:64])
        action_item = ActionItem(
            action='transform',
            sequence_index=tx_log.log_index,
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=self.eth,
            amount=ZERO,
            to_event_type=HistoryEventType.WITHDRAWAL,
            to_event_subtype=HistoryEventSubType.GENERATE_DEBT,
            to_counterparty=CPT_BALANCER_V2,
            to_notes=None,
            extra_data={
                'from_token': from_token,
                'to_token': to_token,
                'amount_in': amount_in,
                'amount_out': amount_out,
            },
        )

        amount_in_if_eth = asset_normalized_value(
            amount=amount_in,
            asset=self.eth,
        )

        if len(action_items) == 0 and from_token == self.weth.evm_address:
            for event in decoded_events:
                if (
                    event.asset == A_ETH and event.balance.amount == amount_in_if_eth and
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE
                ):
                    event.event_type = HistoryEventType.TRADE
                    event.event_subtype = HistoryEventSubType.SPEND
                    event.notes = f'Swap {event.balance.amount} {self.eth.symbol} in balancer V2 from {event.location_label}'  # noqa: E501
                    event.counterparty = CPT_BALANCER_V2

        return None, [action_item]

    def decode_balancer_v2_event(
            self,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list[HistoryBaseEntry],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
            action_items: list[ActionItem],
    ) -> tuple[Optional[HistoryBaseEntry], list[ActionItem]]:
        if tx_log.topics[0] == V2_SWAP:
            return self._decode_swap_creation(
                tx_log=tx_log,
                decoded_events=decoded_events,
                action_items=action_items,
            )
        return None, []

    def _maybe_enrich_balancer_v2_transfers(  # pylint: disable=no-self-use
            self,
            token: 'EvmToken',  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            event: HistoryBaseEntry,
            action_items: list[ActionItem],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> bool:
        """
        Enrich tranfer transactions to address for jar deposits and withdrawals
        May raise:
        - UnknownAsset
        - WrongAssetType
        """
        if action_items is None or len(action_items) == 0 or transaction.to_address != VAULT_ADDRESS:  # noqa: E501
            return False

        assert action_items[-1].extra_data is not None
        asset = event.asset.resolve_to_evm_token()
        to_amount = asset_normalized_value(
            amount=action_items[-1].extra_data['amount_out'],
            asset=asset,
        )

        if (
            action_items[-1].extra_data['to_token'] != tx_log.address or
            event.balance.amount != to_amount
        ):
            return False

        is_receive = asset.evm_address == action_items[-1].extra_data['to_token']

        event.counterparty = CPT_BALANCER_V2
        event.event_type = HistoryEventType.TRADE
        if is_receive:
            event.event_subtype = HistoryEventSubType.RECEIVE
            event.notes = f'Receive {event.balance.amount} {asset.symbol} in balancer V2 from {event.location_label}'  # noqa: E501
        else:
            event.event_subtype = HistoryEventSubType.SPEND

        return True

    def _maybe_enrich_balancer_v1_events(
        self,
        token: 'EvmToken',
        tx_log: EvmTxReceiptLog,  # pylint: disable=unused-argument
        transaction: EvmTransaction,  # pylint: disable=unused-argument
        event: HistoryBaseEntry,
        action_items: list[ActionItem],  # pylint: disable=unused-argument
        all_logs: list[EvmTxReceiptLog],
    ) -> bool:
        actions = self._decode_v1_pool_event(all_logs=all_logs)
        if actions is None:
            return False

        for action in actions:
            assert action.extra_data is not None
            if (
                action.extra_data['type'] == BalancerV1EventTypes.JOIN and
                action.extra_data['ds_address'] == event.counterparty
            ):
                if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE
                ):
                    # otherwise this is the event that we have to edit
                    event.event_type = HistoryEventType.STAKING
                    event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                    event.counterparty = CPT_BALANCER_V1
                    event.notes = f'Receive {event.balance.amount} {token.symbol} as deposit in Balancer V1 pool'  # noqa: E501
                    return True
                if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE
                ):
                    # otherwise this is the event that we have to edit
                    event.event_type = HistoryEventType.STAKING
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.counterparty = CPT_BALANCER_V1
                    event.notes = f'Deposit {event.balance.amount} {token.symbol} in Balancer V1 pool'  # noqa: E501
                    return True
            if (
                action.extra_data['type'] == BalancerV1EventTypes.EXIT and
                action.extra_data['ds_address'] == event.counterparty
            ):
                if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE
                ):
                    # otherwise this is the event that we have to edit
                    event.event_type = HistoryEventType.STAKING
                    event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    event.counterparty = CPT_BALANCER_V1
                    event.notes = f'Receive {event.balance.amount} {token.symbol} after removing liquidity in Balancer V1 pool'  # noqa: E501
                    return True
                if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE
                ):
                    # otherwise this is the event that we have to edit
                    event.event_type = HistoryEventType.STAKING
                    event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    event.counterparty = CPT_BALANCER_V1
                    event.notes = f'Return {event.balance.amount} {token.symbol} to Balancer V1 pool'  # noqa: E501
                    return True

        return False

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            VAULT_ADDRESS: (self.decode_balancer_v2_event,),
        }

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_balancer_v2_transfers,
            self._maybe_enrich_balancer_v1_events,
        ]

    def counterparties(self) -> list[str]:
        return [CPT_BALANCER_V1, CPT_BALANCER_V2]
