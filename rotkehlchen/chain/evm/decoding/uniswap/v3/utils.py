import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Final, Literal

from eth_abi import encode as encode_abi
from eth_utils import to_checksum_address, to_hex
from web3 import Web3
from web3.exceptions import Web3Exception
from web3.types import BlockIdentifier

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.ethereum.oracles.constants import UNISWAP_FACTORY_ADDRESSES
from rotkehlchen.chain.ethereum.utils import generate_address_via_create2
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import tokenid_to_collectible_id
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Price

from .constants import UNISWAP_V3_NFT_MANAGER_ADDRESSES

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

POOL_INIT_CODE_HASH: Final = '0xe34f199b19b2b4f47f68442619d555527d244f78a3297ea89325f843f87b8b54'
POW_96: Final = 2**96
LOG_PRICE: Final = FVal('1.0001')


def _compute_pool_address(
        uniswap_v3_factory_address: ChecksumEvmAddress,
        token0_address_raw: str,
        token1_address_raw: str,
        fee: int,
) -> ChecksumEvmAddress:
    """
    Generate the pool address from the Uniswap Factory Address, a pair of tokens
    and the fee using CREATE2 opcode.

    May raise:
    - DeserializationError
    """
    token_0 = to_checksum_address(token0_address_raw)
    token_1 = to_checksum_address(token1_address_raw)
    # Sort the addresses
    if int(token_0, 16) < int(token_1, 16):
        parameters = [token_0, token_1, fee]
    else:
        parameters = [token_1, token_0, fee]

    return generate_address_via_create2(
        address=uniswap_v3_factory_address,
        salt=to_hex(Web3.keccak(encode_abi(['address', 'address', 'uint24'], parameters))),
        init_code=POOL_INIT_CODE_HASH,
        is_init_code_hashed=True,
    )


def compute_sqrt_values_for_amounts(
        tick_lower: int,
        tick_upper: int,
        tick: int,
) -> tuple[FVal, FVal, FVal]:
    """Computes the values for `sqrt`, `sqrt_a`, sqrt_b`"""
    sqrt_a = LOG_PRICE**FVal(tick_lower / 2) * POW_96
    sqrt_b = LOG_PRICE**FVal(tick_upper / 2) * POW_96
    sqrt = LOG_PRICE**FVal(tick / 2) * POW_96
    sqrt = max(min(sqrt, sqrt_b), sqrt_a)

    return sqrt, sqrt_a, sqrt_b


def calculate_amount(
        tick_lower: int,
        liquidity: int,
        tick_upper: int,
        decimals: int,
        tick: int,
        token_position: Literal[0, 1],
) -> FVal:
    """
    Calculates the amount of a token in the Uniswap V3 LP position.
    `token_position` can either be 0 or 1 representing the position of the token in a pair.
    """
    sqrt, sqrt_a, sqrt_b = compute_sqrt_values_for_amounts(
        tick_lower=tick_lower,
        tick_upper=tick_upper,
        tick=tick,
    )
    if token_position == 0:
        amount = (liquidity * POW_96 * (sqrt_b - sqrt) / (sqrt_b * sqrt)) / 10**decimals
    elif token_position == 1:
        amount = liquidity * (sqrt - sqrt_a) / POW_96 / 10**decimals

    return FVal(amount)


def get_uniswap_v3_position_price(
        evm_inquirer: 'EvmNodeInquirer',
        token: 'EvmToken',
        price_func: Callable[[Asset], Price],
        block_identifier: BlockIdentifier = 'latest',
) -> Price:
    """
    Get the price of a Uniswap V3 LP position identified by the token's collectible ID.

    `price_func` is a function to get the price of the asset, allowing this function to be used
    for both current and historical prices.
    """
    if (collectible_id := tokenid_to_collectible_id(identifier=token.identifier)) is None:
        log.error(f'Failed to find Uniswap V3 position price for {token} due to missing token ID.')
        return ZERO_PRICE

    uniswap_v3_nft_manager = evm_inquirer.contracts.contract(UNISWAP_V3_NFT_MANAGER_ADDRESSES[evm_inquirer.chain_id])  # noqa: E501
    uniswap_v3_factory = evm_inquirer.contracts.contract(UNISWAP_FACTORY_ADDRESSES[3][evm_inquirer.chain_id])  # noqa: E501
    uniswap_v3_pool_abi = evm_inquirer.contracts.abi('UNISWAP_V3_POOL')

    # Get the user liquidity position information using the token ID.
    # See https://docs.uniswap.org/contracts/v3/reference/periphery/interfaces/INonfungiblePositionManager#positions
    try:
        position = evm_inquirer.call_contract(
            contract_address=uniswap_v3_nft_manager.address,
            abi=uniswap_v3_nft_manager.abi,
            method_name='positions',
            arguments=[int(collectible_id)],
            block_identifier=block_identifier,
        )
    except (RemoteError, ValueError) as e:
        log.error(f'Failed to query Uniswap V3 position information from nft contract for {token} due to {e!s}')  # noqa: E501
        return ZERO_PRICE

    # Generate the LP contract address with CREATE2 opcode replicated in Python using
    # factory_address, token_0, token1 and the fee of the LP all gotten from the position.
    try:
        pool_address = _compute_pool_address(
            uniswap_v3_factory_address=uniswap_v3_factory.address,
            token0_address_raw=position[2],
            token1_address_raw=position[3],
            fee=position[4],
        )
    except DeserializationError as e:
        log.error(f'Failed to compute Uniswap V3 pool address for {token} due to {e!s}')
        return ZERO_PRICE

    try:  # Get the liquidity pool's state i.e `slot0`
        slot_0 = evm_inquirer.call_contract(
            contract_address=pool_address,
            abi=uniswap_v3_pool_abi,
            method_name='slot0',
            block_identifier=block_identifier,
        )
    except RemoteError as e:
        log.error(f'Failed to query Uniswap V3 pool contract slot0 for {token} due to {e!s}')
        return ZERO_PRICE

    position_price = ZERO
    for index, address in enumerate(position[2:4]):
        try:
            token_info = evm_inquirer.get_erc20_contract_info(token_address := to_checksum_address(address))  # noqa: E501
        except (Web3Exception, ValueError) as e:
            log.error(
                f'Failed to retrieve contract information for {evm_inquirer.chain_name} token '
                f'{address} while getting Uniswap V3 LP position price due to: {e!s}',
            )
            return ZERO_PRICE

        token_balance = calculate_amount(
            tick_lower=position[5],
            liquidity=position[7],
            tick_upper=position[6],
            decimals=token_info['decimals'],
            tick=slot_0[1],
            token_position=index,  # type: ignore  # index will only be 0 or 1
        )

        try:
            asset = get_or_create_evm_token(
                userdb=evm_inquirer.database,
                symbol=token_info['symbol'],
                evm_address=token_address,
                chain_id=evm_inquirer.chain_id,
                name=token_info['name'],
                decimals=token_info['decimals'],
                encounter=TokenEncounterInfo(description='Uniswap v3 LP positions query'),
            )
        except NotERC20Conformant as e:
            log.error(
                f'Failed to fetch {evm_inquirer.chain_name} token {token_address!s} while '
                f'getting Uniswap V3 LP position price  due to: {e!s}',
            )
            continue

        asset_usd_price = price_func(asset)
        if asset_usd_price == ZERO_PRICE:
            continue

        position_price += FVal(token_balance * asset_usd_price)

    return Price(position_price)
