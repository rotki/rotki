import logging
from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING

from eth_abi import encode as encode_abi
from web3 import Web3

from rotkehlchen.chain.decoding.types import get_versioned_counterparty_label
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, asset_raw_value
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.uniswap.utils import (
    get_position_price_from_underlying,
    get_uniswap_swap_amounts,
)
from rotkehlchen.chain.evm.decoding.uniswap.v4.constants import (
    POSITION_MANAGER_ABI,
    STATE_VIEW_ABI,
    UNISWAP_V4_STATE_VIEW_CONTRACTS,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import tokenid_to_collectible_id
from rotkehlchen.errors.asset import WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction, Price
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset, EvmToken
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def get_uniswap_v4_position_price(
        evm_inquirer: 'EvmNodeInquirer',
        token: 'EvmToken',
        price_func: Callable[['Asset'], Price],
) -> Price:
    """Get the price of a Uniswap V4 LP position nft."""
    if (token_id_str := tokenid_to_collectible_id(identifier=token.identifier)) is None:
        log.error(f'Failed to find Uniswap V4 position price for {token} due to missing token ID.')
        return ZERO_PRICE

    if (state_view_address := UNISWAP_V4_STATE_VIEW_CONTRACTS.get(evm_inquirer.chain_id)) is None:
        log.error(
            f'There is no Uniswap V4 StateView contract defined '
            f'for chain {evm_inquirer.chain_id}. Should not happen.',
        )
        return ZERO_PRICE

    token_id = int(token_id_str)
    position_manager_contract = EvmContract(
        address=token.evm_address,
        abi=POSITION_MANAGER_ABI,
    )
    try:
        results = evm_inquirer.multicall(
            calls=[(
                position_manager_contract.address,
                position_manager_contract.encode(method_name=method, arguments=[token_id]),
            ) for method in ('getPoolAndPositionInfo', 'getPositionLiquidity')],
        )
        pool_key, position_info = position_manager_contract.decode(
            result=results[0],
            method_name='getPoolAndPositionInfo',
            arguments=[token_id],
        )
        liquidity = position_manager_contract.decode(
            result=results[1],
            method_name='getPositionLiquidity',
            arguments=[token_id],
        )[0]
        # Decode tick_lower and tick_upper from uint256 positionInfo
        # Layout: poolId: 25 bytes, tickUpper: 3 bytes, tickLower: 3 bytes, hasSubscriber: 1 byte
        # See https://docs.uniswap.org/contracts/v4/reference/periphery/libraries/PositionInfoLibrary  # noqa: E501
        position_bytes = position_info.to_bytes(32)
        tick_lower = int.from_bytes(position_bytes[28:31], signed=True)
        tick_upper = int.from_bytes(position_bytes[25:28], signed=True)
    except (RemoteError, DeserializationError, IndexError, OverflowError, AttributeError) as e:
        log.error(f'Failed to query Uniswap V4 position information for {token} due to {e!s}')
        return ZERO_PRICE

    try:
        tick = evm_inquirer.call_contract(
            contract_address=state_view_address,
            abi=STATE_VIEW_ABI,
            method_name='getSlot0',
            arguments=[Web3.keccak(encode_abi(
                types=['address', 'address', 'uint24', 'int24', 'address'],
                args=pool_key,
            ))],
        )[1]  # response contains sqrtPriceX96, tick, protocolFee, lpFee
    except (RemoteError, IndexError) as e:
        log.error(f'Failed to query Uniswap V4 StateView.getSlot0 for {token} due to {e!s}')
        return ZERO_PRICE

    return get_position_price_from_underlying(
        evm_inquirer=evm_inquirer,
        token0_raw_address=pool_key[0],
        token1_raw_address=pool_key[1],
        tick_lower=tick_lower,
        tick_upper=tick_upper,
        liquidity=liquidity,
        tick=tick,
        price_func=price_func,
    )


def decode_uniswap_v4_like_swaps(
        transaction: 'EvmTransaction',
        decoded_events: list['EvmEvent'],
        all_logs: list['EvmTxReceiptLog'],
        base_tools: 'BaseDecoderTools',
        swap_topics: tuple[bytes, ...],
        counterparty: str,
        router_address: ChecksumEvmAddress,
        wrapped_native_currency: 'Asset',
) -> list['EvmEvent']:
    """Decode Uniswap V4 like swaps."""
    amounts_received, amounts_sent, pools_used, possible_fees = set(), set(), set(), defaultdict(set)  # noqa: E501
    # Since tokens may be swapped multiple times before reaching the desired token, we must
    # check the amounts from multiple swap logs if present.
    for tx_log in all_logs:
        if tx_log.topics[0] in swap_topics:
            amount_received, amount_sent = get_uniswap_swap_amounts(tx_log=tx_log)
            amounts_received.add(amount_received)
            amounts_sent.add(amount_sent)
            pools_used.add(tx_log.address)
        elif (
            tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
            ((from_addr := bytes_to_address(tx_log.topics[1])) == router_address or
            from_addr in pools_used) and
            not base_tools.is_tracked(bytes_to_address(tx_log.topics[2]))
        ):
            possible_fees[tx_log.address].add(int.from_bytes(tx_log.data[:32]))

    if len(amounts_received) == 0:
        log.error(f'Could not find swap log in {transaction}')
        return decoded_events

    spend_event, receive_event, fee_event = None, None, None
    display_name = get_versioned_counterparty_label(counterparty)
    for event in decoded_events:
        if not (event.address == router_address or event.address in pools_used):
            continue

        if (
            ((
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE
            ) or (
                event.event_type == HistoryEventType.TRADE and
                event.event_subtype == HistoryEventSubType.SPEND
            )) and
            asset_raw_value(
                amount=event.amount,
                asset=(resolved_asset := event.asset.resolve_to_crypto_asset()),
            ) in amounts_sent
        ):
            event.counterparty = counterparty
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.SPEND
            event.notes = f'Swap {event.amount} {resolved_asset.symbol} in {display_name}'
            spend_event = event
        elif ((
            event.event_type == HistoryEventType.RECEIVE and
            event.event_subtype == HistoryEventSubType.NONE
        ) or (
            event.event_type == HistoryEventType.TRADE and
            event.event_subtype == HistoryEventSubType.RECEIVE
        )):
            if (event_raw_amount := asset_raw_value(
                amount=event.amount,
                asset=(resolved_asset := event.asset.resolve_to_crypto_asset()),
            )) not in amounts_received:
                # In some cases a fee is deducted from the receive amount before it is sent to
                # the user. Check if this receive event actually has the right amount to match
                # this swap after adding the fee back on.
                try:  # First, get the received token's address
                    fee_token_address = (  # Fee will be in the wrapped version of the native currency.  # noqa: E501
                        event.asset if event.asset != base_tools.evm_inquirer.native_token
                        else wrapped_native_currency
                    ).resolve_to_evm_token().evm_address
                except WrongAssetType:
                    log.error(
                        f'{display_name} swap receive asset {event.asset} is not the native '
                        f'currency or an EVM token in {transaction}. Should not happen.')
                    continue

                # Match against the amounts for possible fee transfers of this token
                if (raw_fee_amount := next((
                    amount for amount in possible_fees[fee_token_address]
                    if event_raw_amount + amount in amounts_received
                ), None)) is None:
                    continue  # this receive is not related to this swap

                event.amount += (fee_amount := asset_normalized_value(
                    asset=resolved_asset,
                    amount=raw_fee_amount,
                ))
                fee_event = base_tools.make_event_next_index(
                    tx_hash=event.tx_hash,
                    timestamp=transaction.timestamp,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=resolved_asset,
                    amount=fee_amount,
                    location_label=event.location_label,
                    notes=f'Spend {fee_amount} {resolved_asset.symbol} as a {display_name} fee',
                    counterparty=counterparty,
                    address=event.address,
                )

            event.counterparty = counterparty
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.RECEIVE
            event.notes = f'Receive {event.amount} {resolved_asset.symbol} after a swap in {display_name}'  # noqa: E501
            receive_event = event

    if spend_event is None or receive_event is None:
        log.error(f'Failed to find both out and in events for {display_name} swap {transaction}')
        return decoded_events

    ordered_events = [spend_event, receive_event]
    if fee_event is not None:
        decoded_events.append(fee_event)
        ordered_events.append(fee_event)

    maybe_reshuffle_events(ordered_events=ordered_events, events_list=decoded_events)
    return decoded_events
