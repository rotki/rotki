import logging
from typing import TYPE_CHECKING, Any, Callable, Optional

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.modules.balancer.types import BalancerV1EventTypes
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import ActionItem
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import CPT_BALANCER_V1, CPT_BALANCER_V2

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
        self.eth = A_ETH.resolve_to_crypto_asset()
        self.weth = A_WETH.resolve_to_evm_token()

    def _decode_v1_pool_event(self, all_logs: list[EvmTxReceiptLog]) -> Optional[list[dict[str, Any]]]:  # noqa: E501
        """Read the list of logs in search for a Balancer v1 event and return the information
        needed to decode the transfers made in the transaction to/from the ds proxy
        """
        # The transfer event appears after the debt generation event, so we need to transform it
        target_logs = []
        for tx_log in all_logs:
            if tx_log.topics[0] == JOIN_V1 or tx_log.topics[0] == EXIT_V1:
                target_logs.append(tx_log)

        if len(target_logs) == 0:
            return None

        events_information = []
        for target_log in target_logs:
            token_address = hex_or_bytes_to_address(target_log.topics[2])
            amount = hex_or_bytes_to_int(target_log.data[0:32])
            if target_log.topics[0] == JOIN_V1:
                balancer_event_type = BalancerV1EventTypes.JOIN
                ds_address = hex_or_bytes_to_address(target_log.topics[1])
            else:
                balancer_event_type = BalancerV1EventTypes.EXIT
                ds_address = target_log.address

            proxy_event_information = {
                'ds_address': ds_address,
                'token_address': token_address,
                'amount': amount,
                'type': balancer_event_type,
            }
            events_information.append(proxy_event_information)

        return events_information

    def decode_swap_creation(
            self,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list[HistoryBaseEntry],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
            action_items: list[ActionItem],
    ) -> tuple[Optional[HistoryBaseEntry], list[ActionItem]]:
        """
        Decode swap in Balancer v2. At the beggining of the transaction a SWAP event is created
        with the information of the tokens and amounts and later some transfers are executed.

        We need to detect this swap event and then match the transferred amounts with the ones
        in the swap event. A special case is the swap of ETH that is wrapped before being sent.
        In this case the token is WETH but we have a tranfer of ETH from the user.
        """
        if tx_log.topics[0] != V2_SWAP:
            return None, []

        # The transfer event appears after the swap event, so we need to propagate information
        from_token_address = hex_or_bytes_to_address(tx_log.topics[2])
        to_token_address = hex_or_bytes_to_address(tx_log.topics[3])
        amount_in = hex_or_bytes_to_int(tx_log.data[0:32])
        amount_out = hex_or_bytes_to_int(tx_log.data[32:64])

        # Create action item to propagate the information about the swap to the transfer enrichers
        to_token = EvmToken(ethaddress_to_identifier(to_token_address))
        to_amount = asset_normalized_value(
            amount=amount_out,
            asset=to_token,
        )
        action_item = ActionItem(
            action='skip & keep',
            sequence_index=tx_log.log_index,
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=to_token,
            amount=to_amount,
            to_event_type=None,
            to_event_subtype=None,
            to_counterparty=CPT_BALANCER_V2,
            to_notes=None,
            extra_data={
                'from_token': from_token_address,
                'amount_in': amount_in,
            },
        )

        # When ETH is swapped it is wrapped to WETH and the ETH transfer happens before the SWAP
        # event. We need to detect it if we haven't done it yet.
        if len(action_items) == 0 and from_token_address == self.weth.evm_address:
            # when swapping eth the transfer event appears before the V2_SWAP event so we need
            # to check if the asset swapped was ETH or not.
            amount_of_eth = asset_normalized_value(
                amount=amount_in,
                asset=self.eth,
            )
            for event in decoded_events:
                if (
                    event.asset == A_ETH and event.balance.amount == amount_of_eth and
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE
                ):
                    event.event_type = HistoryEventType.TRADE
                    event.event_subtype = HistoryEventSubType.SPEND
                    event.notes = f'Swap {event.balance.amount} {self.eth.symbol} in Balancer v2'  # noqa: E501
                    event.counterparty = CPT_BALANCER_V2

        return None, [action_item]

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
        Enrich tranfer transactions to account for swaps in balancer v2 protocol.
        May raise:
        - UnknownAsset
        - WrongAssetType
        """
        if action_items is None or len(action_items) == 0 or transaction.to_address != VAULT_ADDRESS:  # noqa: E501
            return False

        if action_items[-1].extra_data is None:
            return False

        asset = event.asset.resolve_to_evm_token()
        if (
            isinstance(action_items[-1].asset, EvmToken) is False or
            action_items[-1].asset.evm_address != tx_log.address or  # type: ignore[attr-defined]  # noqa: E501 mypy fails to understand that due the previous statmenet in the or this check won't be evaluated if the asset isn't a token
            action_items[-1].amount != event.balance.amount
        ):
            return False

        event.counterparty = CPT_BALANCER_V2
        event.event_type = HistoryEventType.TRADE
        if asset == event.asset:
            event.event_subtype = HistoryEventSubType.RECEIVE
            event.notes = f'Receive {event.balance.amount} {asset.symbol} from Balancer v2'
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
        """
        Enrich balancer v1 transfer to read pool events of:
        - Depositing in the pool
        - Withdrawing from the pool

        In balancer v1 pools are managed using a DSProxy so the account doesn't interact
        directly with the pools.
        """
        events_information = self._decode_v1_pool_event(all_logs=all_logs)
        if events_information is None:
            return False

        for proxied_event in events_information:
            if proxied_event['ds_address'] != event.counterparty:
                continue

            if proxied_event['type'] == BalancerV1EventTypes.JOIN:
                if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE
                ):
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                    event.counterparty = CPT_BALANCER_V1
                    event.notes = f'Receive {event.balance.amount} {token.symbol} from a Balancer v1 pool'  # noqa: E501
                    return True
                if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE
                ):
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.counterparty = CPT_BALANCER_V1
                    event.notes = f'Deposit {event.balance.amount} {token.symbol} to a Balancer v1 pool'  # noqa: E501
                    return True
            elif proxied_event['type'] == BalancerV1EventTypes.EXIT:
                if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE
                ):
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    event.counterparty = CPT_BALANCER_V1
                    event.notes = f'Receive {event.balance.amount} {token.symbol} after removing liquidity from a Balancer v1 pool'  # noqa: E501
                    return True
                if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE
                ):
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    event.counterparty = CPT_BALANCER_V1
                    event.notes = f'Return {event.balance.amount} {token.symbol} to a Balancer v1 pool'  # noqa: E501
                    return True

        return False

    def _check_refunds_v1(
            self,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list[HistoryBaseEntry],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> list[HistoryBaseEntry]:
        """
        It can happen that after sending tokens to the DSProxy in balancer V1 the amount of tokens
        required for the deposit is lower than the amount sent and then those tokens are returned
        to the DSProxy and then to the user.
        """
        deposited_assets = set()

        for event in decoded_events:
            if (
                event.counterparty == CPT_BALANCER_V1 and
                event.event_type == HistoryEventType.DEPOSIT and
                event.event_subtype == HistoryEventSubType.DEPOSIT_ASSET
            ):
                deposited_assets.add(event.asset)
            elif (
                event.counterparty == CPT_BALANCER_V1 and
                event.event_type == HistoryEventType.DEPOSIT and
                event.event_subtype == HistoryEventSubType.RECEIVE_WRAPPED and
                event.asset in deposited_assets
            ):
                # in this case we got refunded one of the assets deposited
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                asset = event.asset.resolve_to_asset_with_symbol()
                event.notes = f'Refunded {event.balance.amount} {asset.symbol} after depositing in Balancer V1 pool'  # noqa: E501

        return decoded_events

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            VAULT_ADDRESS: (self.decode_swap_creation,),
        }

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_balancer_v2_transfers,
            self._maybe_enrich_balancer_v1_events,
        ]

    def counterparties(self) -> list[str]:
        return [CPT_BALANCER_V1, CPT_BALANCER_V2]

    def post_decoding_rules(self) -> list[tuple[int, Callable]]:
        return [(0, self._check_refunds_v1)]
