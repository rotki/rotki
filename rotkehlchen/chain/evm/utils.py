import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Final

from web3.types import BlockIdentifier

from rotkehlchen.api.websockets.typedefs import ProgressUpdateSubType, WSMessageType
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import (
    AERODROME_POOL_PROTOCOL,
    UNISWAP_PROTOCOL,
    VELODROME_POOL_PROTOCOL,
    ChainID,
    EvmTokenKind,
    Price,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import LP_TOKEN_AS_POOL_CONTRACT_ABIS
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


LP_TOKEN_AS_POOL_PROTOCOL_TO_ABI_NAME: Final[dict[str, 'LP_TOKEN_AS_POOL_CONTRACT_ABIS']] = {
    VELODROME_POOL_PROTOCOL: 'VELO_V2_LP',
    AERODROME_POOL_PROTOCOL: 'VELO_V2_LP',
    UNISWAP_PROTOCOL: 'UNISWAP_V2_LP',
}
FVAL_ERROR_NAME: Final = 'token supply'
FVAL_ERROR_LOCATION: Final = 'uniswap-like pool price query'


def lp_price_from_uniswaplike_pool_contract(
        evm_inquirer: 'EvmNodeInquirer',
        token: EvmToken,
        price_func: Callable[[Asset], Price],
        block_identifier: BlockIdentifier,
) -> Price | None:
    """
    This works for any uniswap like LP token. It calculates the price for an LP token the contract
    of which is also the contract of the pool it represents. For example velodrome or uniswap lp
    tokens. The price is calculated like this:
    price = (Total value of liquidity pool) / (Current supply of LP tokens)
    We need:
    - Price of token 0
    - Price of token 1
    - Pooled amount of token 0
    - Pooled amount of token 1
    - Total supply of pool token

    token is the Uniswap V2 pair token and price_func a function to query
    the price of the assets since this logic can use both current and historical
    prices.
    """
    if token.protocol is None:
        return None

    try:
        abi_name = LP_TOKEN_AS_POOL_PROTOCOL_TO_ABI_NAME[token.protocol]  # the lp token's contract abi that will be used to query the info needed for lp token price calculation  # noqa: E501
    except KeyError:
        log.debug(
            f'There is no suitable contract abi for protocol {token.protocol} '
            f'of token {token.evm_address}. Cannot calculate price',
        )
        return None

    contract = EvmContract(
        address=token.evm_address,
        abi=evm_inquirer.contracts.abi(abi_name),
        deployed_block=0,
    )
    methods = ('token0', 'token1', 'totalSupply', 'getReserves', 'decimals')
    if (
        isinstance(block_identifier, int) and
        block_identifier <= evm_inquirer.contract_multicall.deployed_block
    ):
        log.error(
            f'No multicall contract at {evm_inquirer.chain_name} block {block_identifier}. '
            f'{abi_name} query failed. Should implement direct queries',
        )
        return None

    try:
        output = evm_inquirer.multicall(
            require_success=True,
            calls=[(token.evm_address, contract.encode(method_name=method)) for method in methods],
            block_identifier=block_identifier,
        )
    except (RemoteError, BlockchainQueryError) as e:
        log.error(
            f'Remote error calling {evm_inquirer.chain_name} multicall contract for {abi_name} '
            f'token {token.evm_address} properties: {e!s}',
        )
        return None

    # decode output
    decoded = []
    for (method_output, method_name) in zip(output, methods, strict=True):
        call_success = True
        if call_success and len(method_output) != 0:
            decoded_method = contract.decode(method_output, method_name)
            # decoded_method is a tuple of decoded values. If it's only one then we just append that value. If it's more than one then we append the tuple. getReserves call returns a tuple of token reserves  # noqa: E501
            decoded.append(decoded_method[0] if len(decoded_method) == 1 else decoded_method)
        else:
            log.debug(
                f'{evm_inquirer.chain_name} multicall to {abi_name} failed to fetch field '
                f'{method_name} for token {token.evm_address}',
            )
            return None

    # TODO: Perhaps think of a better way for type checking of expected function return than this?
    assert isinstance(decoded[0], str), 'token0 should return a string'
    assert isinstance(decoded[1], str), 'token1 should return a string'
    assert isinstance(decoded[2], int), 'totalSupply should return an int'
    assert isinstance(decoded[4], int), 'decimals should return an int'
    if len(decoded) < 4:
        log.debug(
            f'Unexpected number of decoded values ({len(decoded)}) while querying price from '
            f'{evm_inquirer.chain_name} {abi_name} for token {token.evm_address}',
        )
        return None
    elif len(decoded[3]) < 2:
        log.debug(
            f'Unexpected number of decoded pool reserves ({len(decoded[3])}) while querying '
            f'price from {evm_inquirer.chain_name} {abi_name} for token {token.evm_address}',
        )
        return None

    try:
        token0 = EvmToken(evm_address_to_identifier(
            address=decoded[0],
            chain_id=token.chain_id,
            token_type=EvmTokenKind.ERC20,
        ))
        token1 = EvmToken(evm_address_to_identifier(
            address=decoded[1],
            chain_id=token.chain_id,
            token_type=EvmTokenKind.ERC20,
        ))
    except (UnknownAsset, WrongAssetType):
        log.debug(
            f'Unknown assets {decoded[0]} {decoded[1]} while querying price from '
            f'{evm_inquirer.chain_name} {abi_name} for token {token.evm_address}',
        )
        return None

    try:
        token0_supply = deserialize_fval(
            value=decoded[3][0] * 10**-token0.get_decimals(),
            name=FVAL_ERROR_NAME,
            location=FVAL_ERROR_LOCATION,
        )
        token1_supply = deserialize_fval(
            value=decoded[3][1] * 10**-token1.get_decimals(),
            name=FVAL_ERROR_NAME,
            location=FVAL_ERROR_LOCATION,
        )
        total_supply = deserialize_fval(
            value=decoded[2] * 10 ** - decoded[4],
            name=FVAL_ERROR_NAME,
            location=FVAL_ERROR_LOCATION,
        )
    except DeserializationError as e:
        log.debug(
            f'Failed to deserialize {evm_inquirer.chain_name} token amounts for token '
            f'{token.evm_address} with values {decoded!s}. f{e}',
        )
        return None
    token0_price = price_func(token0)
    token1_price = price_func(token1)

    if ZERO in (token0_price, token1_price):
        log.debug(
            f"Couldn't retrieve non zero price information for {evm_inquirer.chain_name} tokens "
            f'{token0}, {token1} with result {token0_price}, {token1_price}',
        )
    numerator = token0_supply * token0_price + token1_supply * token1_price
    share_value = numerator / total_supply
    return Price(share_value)


def maybe_notify_cache_query_status(
        msg_aggregator: 'MessagesAggregator',
        last_notified_ts: Timestamp,
        protocol: str,
        chain: ChainID,
        processed: int,
        total: int,
) -> Timestamp:
    """Helper function to notify the cache query status if it's been more than 5 seconds since the
    last notification, and returns the last notified timestamp."""
    if (current_time := ts_now()) - last_notified_ts > 5:
        msg_aggregator.add_message(
            message_type=WSMessageType.PROGRESS_UPDATES,
            data={
                'protocol': protocol,
                'chain': chain,
                'subtype': str(ProgressUpdateSubType.PROTOCOL_CACHE_UPDATES),
                'processed': processed,
                'total': total,
            },
        )
        return current_time

    return last_notified_ts


def maybe_notify_new_pools_status(
        msg_aggregator: 'MessagesAggregator',
        last_notified_ts: Timestamp,
        protocol: str,
        chain: ChainID,
        get_new_pools_count: Callable[[], int],
) -> Timestamp:
    """Helper function to notify the new pools status if it's been more than 5 seconds since the
    last notification, and returns the last notified timestamp."""
    return maybe_notify_cache_query_status(
        msg_aggregator=msg_aggregator,
        last_notified_ts=last_notified_ts,
        protocol=protocol,
        chain=chain,
        processed=0,  # 0 because here we only query pools to find their total number. It will be incremented while processing the pools later  # noqa: E501
        total=get_new_pools_count(),  # notifying the increase in pool count every 5 seconds as we query them  # noqa: E501
    )
