import logging
from typing import TYPE_CHECKING, Any, Callable, Literal, NamedTuple, Optional

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.modules.uniswap.utils import decode_basic_uniswap_info
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import ActionItem
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTokenKind, EvmTransaction, Location
from rotkehlchen.utils.misc import hex_or_bytes_to_int

from ..constants import CPT_UNISWAP_V2, CPT_UNISWAP_V3

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import CryptoAsset
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# https://www.4byte.directory/api/v1/event-signatures/?hex_signature=0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67  # noqa: E501
# https://docs.uniswap.org/protocol/reference/core/interfaces/pool/IUniswapV3PoolEvents#swap
SWAP_SIGNATURE = b'\xc4 y\xf9JcP\xd7\xe6#_)\x17I$\xf9(\xcc*\xc8\x18\xebd\xfe\xd8\x00N\x11_\xbc\xcag'  # noqa: E501
INCREASE_LIQUIDITY_SIGNATURE = b'0g\x04\x8b\xee\xe3\x1b%\xb2\xf1h\x1f\x88\xda\xc88\xc8\xbb\xa3j\xf2[\xfb+|\xf7G:XG\xe3_'  # noqa: E501
COLLECT_LIQUIDITY_SIGNATURE = b"@\xd0\xef\xd1\xa5=`\xec\xbf@\x97\x1b\x9d\xaf}\xc9\x01x\xc3\xaa\xdcz\xab\x17ec'8\xfa\x8b\x8f\x01"  # noqa: E501


UNISWAP_V3_NFT_MANAGER = string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88')
UNISWAP_AUTO_ROUTER_V1 = string_to_evm_address('0xE592427A0AEce92De3Edee1F18E0157C05861564')
UNISWAP_AUTO_ROUTER_V2 = string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45')

UNISWAP_ROUTERS = {UNISWAP_AUTO_ROUTER_V1, UNISWAP_AUTO_ROUTER_V2}


class SwapData(NamedTuple):
    from_asset: Optional[Asset]
    from_amount: FVal
    to_asset: Optional[Asset]
    to_amount: FVal


def _find_from_asset_and_amount(events: list[HistoryBaseEntry]) -> Optional[tuple[Asset, FVal]]:
    """
    Searches for uniswap v2/v3 swaps, detects `from_asset` and sums up `from_amount`.
    Works only with `from_asset` being the same for all swaps.
    """
    from_asset: Optional[Asset] = None
    from_amount = ZERO
    for event in events:
        if (
            event.event_type == HistoryEventType.TRADE and
            event.event_subtype == HistoryEventSubType.SPEND and
            event.counterparty in {CPT_UNISWAP_V2, CPT_UNISWAP_V3}
        ):
            if from_asset is None:
                from_asset = event.asset
            elif from_asset != event.asset:  # We currently support only single `from_asset`.
                return None  # unexpected event

            from_amount += event.balance.amount

    if from_asset is None:
        return None
    return from_asset, from_amount


def _find_to_asset_and_amount(events: list[HistoryBaseEntry]) -> Optional[tuple[Asset, FVal]]:
    """
    Searches for uniswap v2/v3 swaps, detects `to_asset` and sums up `to_amount`.
    Works only with `to_asset` being the same for all swaps.
    Also works with a special case where there is only one receive event at the end.
    """
    to_asset: Optional[Asset] = None
    to_amount = ZERO
    for event in events:
        if (
            event.event_type == HistoryEventType.TRADE and
            event.event_subtype == HistoryEventSubType.RECEIVE and
            event.counterparty in {CPT_UNISWAP_V2, CPT_UNISWAP_V3}
        ):
            # Some swaps have many receive events. The structure is:
            # spend1, receive1, spend2, receive2, ..., spendN, receiveN
            # In this case they will be decoded as trades and we check them here.
            if to_asset is None:
                to_asset = event.asset
            elif to_asset != event.asset:  # We currently support only single `to_asset`.
                return None  # unexpected event
            to_amount += event.balance.amount
        elif event.event_type == HistoryEventType.RECEIVE and to_asset is None:
            # Some other swaps have only a single receive event. The structure is:
            # spend1, spend2, ..., spendN, receive
            # In this case the receive event won't be decoded as a trade and we check it here.
            # to_asset should be None here since it should be the only receive event.
            to_asset = event.asset
            to_amount = event.balance.amount

    if to_asset is None:
        return None
    return to_asset, to_amount


class Uniswapv3Decoder(DecoderInterface):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.uniswap_v3_nft = Asset(f'eip155:1/erc721:{UNISWAP_V3_NFT_MANAGER}')
        self.eth = A_ETH.resolve_to_crypto_asset()
        self.base_tools = base_tools
        self.ethereum_inquirer = ethereum_inquirer

    def _decode_deposits_and_withdrawals(
            self,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list[HistoryBaseEntry],
            all_logs: list[EvmTxReceiptLog],
            action_items: Optional[list[ActionItem]],
    ) -> tuple[Optional[HistoryBaseEntry], list[ActionItem]]:
        if tx_log.topics[0] == INCREASE_LIQUIDITY_SIGNATURE:
            return self._maybe_decode_v3_deposit_or_withdrawal(
                tx_log=tx_log,
                transaction=transaction,
                decoded_events=decoded_events,
                all_logs=all_logs,
                action_items=action_items,
                event_action_type='addition',
            )
        if tx_log.topics[0] == COLLECT_LIQUIDITY_SIGNATURE:
            return self._maybe_decode_v3_deposit_or_withdrawal(
                tx_log=tx_log,
                transaction=transaction,
                decoded_events=decoded_events,
                all_logs=all_logs,
                action_items=action_items,
                event_action_type='removal',
            )

        return None, []

    def _maybe_decode_v3_swap(  # pylint: disable=no-self-use
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list[HistoryBaseEntry],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> None:
        """
        Detect some basic uniswap v3 events. This method doesn't ensure the order of the events
        and other things, but just labels some of the events as uniswap v3 events.
        The order should be ensured by the post-decoding rules.
        """
        if tx_log.topics[0] != SWAP_SIGNATURE:
            return

        # Uniswap V3 represents the delta of tokens in the pool with a signed integer
        # for each token. In the transaction we have the difference of tokens in the pool
        # for the token0 [0:32] and the token1 [32:64]. If that difference is negative it
        # means that the tokens are leaving the pool (the user receives them) and if it is
        # positive they get into the pool (the user sends them to the pool)
        delta_token_0 = hex_or_bytes_to_int(tx_log.data[0:32], signed=True)
        delta_token_1 = hex_or_bytes_to_int(tx_log.data[32:64], signed=True)
        if delta_token_0 > 0:
            amount_sent, amount_received = delta_token_0, -delta_token_1
        else:
            amount_sent, amount_received = delta_token_1, -delta_token_0

        # Uniswap V3 pools are used with complex routers/aggregators and there can be
        # multiple spend and multiple receive events that are hard to decode by looking only
        # at a single swap event. Because of that here we decode only basic info, leaving the rest
        # of the work to the router/aggregator-specific decoding methods.
        decode_basic_uniswap_info(
            amount_sent=amount_sent,
            amount_received=amount_received,
            decoded_events=decoded_events,
            counterparty=CPT_UNISWAP_V3,
            notify_user=self.notify_user,
        )

    # --- Routers methods ---

    def _decode_eth_to_token_swap(
            self,
            decoded_events: list[HistoryBaseEntry],
            send_eth_event: HistoryBaseEntry,
    ) -> Optional[SwapData]:
        """
        Decode a swap of ETH to a token. Such swap consists of 3 events:
        1. Sending ETH to the router.
        2. If there is a refund, receiving ETH from the router.
        3. Receiving tokens from the router.
        """
        from_amount = send_eth_event.balance.amount
        for event in decoded_events:
            if event.asset == A_ETH and event.event_type == HistoryEventType.RECEIVE:
                # Optional refund event. Can be only one at max. Exists if price has changed.
                from_amount -= event.balance.amount
                break

        to_data = _find_to_asset_and_amount(decoded_events)
        if to_data is None:
            return None

        return SwapData(
            from_asset=A_ETH,
            from_amount=from_amount,
            to_asset=to_data[0],
            to_amount=to_data[1],
        )

    def _decode_token_to_eth_swap(
            self,
            decoded_events: list[HistoryBaseEntry],
            receive_eth_event: HistoryBaseEntry,
    ) -> Optional[SwapData]:
        from_data = _find_from_asset_and_amount(decoded_events)
        if from_data is None:
            return None

        return SwapData(
            from_asset=from_data[0],
            from_amount=from_data[1],
            to_asset=A_ETH,
            to_amount=receive_eth_event.balance.amount,
        )

    def _decode_token_to_token_swap(
            self,
            decoded_events: list[HistoryBaseEntry],
    ) -> Optional[SwapData]:
        from_data = _find_from_asset_and_amount(decoded_events)
        to_data = _find_to_asset_and_amount(decoded_events)
        if from_data is None or to_data is None:
            return None

        return SwapData(
            from_asset=from_data[0],
            from_amount=from_data[1],
            to_asset=to_data[0],
            to_amount=to_data[1],
        )

    def _routers_post_decoding(
            self,
            transaction: EvmTransaction,
            decoded_events: list[HistoryBaseEntry],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> list[HistoryBaseEntry]:
        """
        Ensures that if an auto router (either v1 or v2) is used, events have correct order and
        are properly combined (i.e. each swap consists only of one spend and one receive event).

        Right now supports only swaps that are made through official uniswap auto routers and have
        only one source / destination token.

        If it fails to decode a swap, it will return the original list of events.

        This function checks for three types of swaps:
        1. Swap from eth to token
        2. Swap from token to eth
        3. Swap from token to token (with a single receive or multiple receive events)
        """
        if transaction.to_address not in UNISWAP_ROUTERS:
            return decoded_events  # work only with the known routers for now
        if len(decoded_events) < 3:
            # The minimum is 3 events: gas, spend, receive.
            return decoded_events

        eth_event = None
        for event in decoded_events:
            if event.asset == A_ETH and event.counterparty != CPT_GAS:
                eth_event = event
                break

        # Since we check that the to_address is a known router, we can be sure that the ETH
        # transfer event (and other events) are parts of the swap.
        if eth_event is not None:
            if eth_event.event_type == HistoryEventType.SPEND:
                # This is a swap from eth to token
                swap_data = self._decode_eth_to_token_swap(decoded_events, eth_event)
            else:  # Receive
                # This is a swap from token to eth
                swap_data = self._decode_token_to_eth_swap(decoded_events, eth_event)
        else:
            # Then this should be a swap from token to token
            swap_data = self._decode_token_to_token_swap(decoded_events)

        if swap_data is None or swap_data.from_asset is None or swap_data.to_asset is None:
            log.error(f'Failed to decode a uniswap swap for transaction {transaction.tx_hash.hex()}')  # noqa: E501
            return decoded_events

        # These should never raise any errors since `from_asset` and `to_asset` are either ETH or
        # have already been resolved to tokens during erc20 transfers decoding.
        from_crypto_asset = swap_data.from_asset.resolve_to_crypto_asset()
        to_crypto_asset = swap_data.to_asset.resolve_to_crypto_asset()

        gas_event = None
        for event in decoded_events:
            if event.counterparty == CPT_GAS:
                gas_event = event
                break

        assert gas_event is not None, 'Gas event should always exist when interacting with a uniswap auto router'  # noqa: E501
        gas_event.sequence_index = 0

        timestamp = decoded_events[0].timestamp  # all events have same timestamp
        from_event = HistoryBaseEntry(
            event_identifier=transaction.tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BLOCKCHAIN,
            location_label=transaction.from_address,
            asset=from_crypto_asset,
            balance=Balance(amount=swap_data.from_amount),
            notes=f'Swap {swap_data.from_amount} {from_crypto_asset.symbol} via {CPT_UNISWAP_V3} auto router',  # noqa: E501
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            counterparty=CPT_UNISWAP_V3,
        )

        to_event = HistoryBaseEntry(
            event_identifier=transaction.tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BLOCKCHAIN,
            location_label=transaction.from_address,
            asset=to_crypto_asset,
            balance=Balance(amount=swap_data.to_amount),
            notes=f'Receive {swap_data.to_amount} {to_crypto_asset.symbol} as the result of a swap via {CPT_UNISWAP_V3} auto router',  # noqa: E501
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            counterparty=CPT_UNISWAP_V3,
        )

        return [gas_event, from_event, to_event]

    def _maybe_decode_v3_deposit_or_withdrawal(
            self,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list[HistoryBaseEntry],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
            action_items: Optional[list[ActionItem]],  # pylint: disable=unused-argument
            event_action_type: Literal['addition', 'removal'],
    ) -> tuple[Optional[HistoryBaseEntry], list[ActionItem]]:
        """
        This method decodes a Uniswap V3 LP liquidity increase or decrease.

        Examples of such transactions are:
        https://etherscan.io/tx/0x6bf3588f669a784adf5def3c0db149b0cdbcca775e472bb35f00acedee263c4c (deposit)
        https://etherscan.io/tx/0x76c312fe1c8604de5175c37dcbbb99cc8699336f3e4840e9e29e3383970f6c6d (withdrawal)
        """  # noqa: E501
        new_action_items = []
        liquidity_pool_id = hex_or_bytes_to_int(tx_log.topics[1])
        amount0_raw = hex_or_bytes_to_int(tx_log.data[32:64])
        amount1_raw = hex_or_bytes_to_int(tx_log.data[64:96])

        if event_action_type == 'addition':
            notes = 'Add {} {} of liquidity to Uniswap V3 LP position {}'
            from_event_type = (HistoryEventType.SPEND, HistoryEventSubType.NONE)
            to_event_type = (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)
        else:
            notes = 'Collect {} {} of liquidity from Uniswap V3 LP position {}'
            from_event_type = (HistoryEventType.RECEIVE, HistoryEventSubType.NONE)
            to_event_type = (HistoryEventType.WITHDRAWAL, HistoryEventSubType.REMOVE_ASSET)

        liquidity_pool_position_info = self.ethereum_inquirer.contracts.contract('UNISWAP_V3_NFT_MANAGER').call(  # noqa: E501
            node_inquirer=self.ethereum_inquirer,
            method_name='positions',
            arguments=[liquidity_pool_id],
        )
        # 2 -> first token in the pair
        # 3 -> second token in the pair
        for token, amount in zip(liquidity_pool_position_info[2:4], (amount0_raw, amount1_raw)):
            token_with_data: 'CryptoAsset' = get_or_create_evm_token(
                userdb=self.ethereum_inquirer.database,
                evm_address=token,
                chain_id=ChainID.ETHEREUM,
                token_kind=EvmTokenKind.ERC20,
                evm_inquirer=self.ethereum_inquirer,
            )
            token_with_data = self.eth if token_with_data == A_WETH else token_with_data
            normalized_amount = asset_normalized_value(amount, token_with_data)

            found_event = False
            for event in decoded_events:
                if (
                        event.asset == token_with_data and
                        event.balance.amount == normalized_amount and
                        event.event_type == from_event_type[0] and
                        event.event_subtype == from_event_type[1]
                ):
                    found_event = True
                    event.event_type = to_event_type[0]
                    event.event_subtype = to_event_type[1]
                    event.counterparty = CPT_UNISWAP_V3
                    event.notes = notes.format(normalized_amount, token_with_data.symbol, liquidity_pool_id)  # noqa: E501
                    break

            if found_event is False:
                new_action_items.append(
                    ActionItem(
                        action='transform',
                        sequence_index=self.base_tools.get_next_sequence_counter(),
                        from_event_type=from_event_type[0],
                        from_event_subtype=from_event_type[1],
                        asset=token_with_data,
                        amount=normalized_amount,
                        to_event_type=to_event_type[0],
                        to_event_subtype=to_event_type[1],
                        to_notes=notes.format(normalized_amount, token_with_data.symbol, liquidity_pool_id),  # noqa: E501
                        to_counterparty=CPT_UNISWAP_V3,
                    ),
                )

        return None, new_action_items

    def _maybe_enrich_liquidity_pool_creation(
            self,
            token: EvmToken,  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            event: HistoryBaseEntry,
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> bool:
        """This method enriches Uniswap V3 LP creation transactions."""
        if (
            event.asset == self.uniswap_v3_nft and
            event.balance.amount == ONE and
            event.counterparty == ZERO_ADDRESS and
            event.event_type == HistoryEventType.RECEIVE and
            event.event_subtype == HistoryEventSubType.NONE
        ):
            event.event_subtype = HistoryEventSubType.NFT
            event.notes = f'Create Uniswap V3 LP position with id {hex_or_bytes_to_int(tx_log.topics[3])}'  # noqa: E501
            event.counterparty = CPT_UNISWAP_V3
            return True

        return False
    # -- DecoderInterface methods

    def decoding_rules(self) -> list[Callable]:
        return [
            self._maybe_decode_v3_swap,
        ]

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            UNISWAP_V3_NFT_MANAGER: (self._decode_deposits_and_withdrawals,),
        }

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_liquidity_pool_creation,
        ]

    def counterparties(self) -> list[str]:
        return [CPT_UNISWAP_V3]

    def post_decoding_rules(self) -> list[tuple[int, Callable]]:
        return [(0, self._routers_post_decoding)]
