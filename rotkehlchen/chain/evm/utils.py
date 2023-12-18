import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Final

from web3.types import BlockIdentifier

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import UNISWAP_PROTOCOL, VELODROME_POOL_PROTOCOL, EvmTokenKind, Price

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import LP_TOKEN_AS_POOL_CONTRACT_ABIS


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


LP_TOKEN_AS_POOL_PROTOCOL_TO_ABI_NAME: Final[dict[str, 'LP_TOKEN_AS_POOL_CONTRACT_ABIS']] = {
    VELODROME_POOL_PROTOCOL: 'VELO_V2_LP',
    UNISWAP_PROTOCOL: 'UNISWAP_V2_LP',
}
FVAL_ERROR_NAME: Final = 'token supply'
FVAL_ERROR_LOCATION: Final = 'uniswap-like pool price query'


def lp_price_from_uniswaplike_pool_contract(
        evm_inquirer: 'EvmNodeInquirer',
        token: EvmToken,
        token_price_func: Callable,
        token_price_func_args: list[Any],
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
            value=decoded[3][0] * 10**-token0.decimals,
            name=FVAL_ERROR_NAME,
            location=FVAL_ERROR_LOCATION,
        )
        token1_supply = deserialize_fval(
            value=decoded[3][1] * 10**-token1.decimals,
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
    token0_price = token_price_func(token0, *token_price_func_args)
    token1_price = token_price_func(token1, *token_price_func_args)

    if ZERO in (token0_price, token1_price):
        log.debug(
            f"Couldn't retrieve non zero price information for {evm_inquirer.chain_name} tokens "
            f'{token0}, {token1} with result {token0_price}, {token1_price}',
        )
    numerator = token0_supply * token0_price + token1_supply * token1_price
    share_value = numerator / total_supply
    return Price(share_value)
