import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from eth_abi import encode as encode_abi
from web3 import Web3

from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.uniswap.utils import get_position_price_from_underlying
from rotkehlchen.chain.evm.decoding.uniswap.v4.constants import (
    POSITION_MANAGER_ABI,
    STATE_VIEW_ABI,
    UNISWAP_V4_STATE_VIEW_CONTRACTS,
)
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import tokenid_to_collectible_id
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset, EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

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
