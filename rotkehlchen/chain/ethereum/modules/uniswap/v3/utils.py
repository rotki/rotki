import logging
from typing import TYPE_CHECKING, Any, Literal

from eth_abi import encode_abi
from eth_utils import to_checksum_address, to_normalized_address
from web3 import Web3
from web3.exceptions import BadFunctionCallOutput

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import AssetToPrice, LiquidityPoolAsset
from rotkehlchen.chain.ethereum.interfaces.ammswap.utils import (
    TokenDetails,
    update_asset_price_in_lp_balances,
)
from rotkehlchen.chain.ethereum.modules.uniswap.v3.types import (
    AddressToUniswapV3LPBalances,
    NFTLiquidityPool,
)
from rotkehlchen.chain.ethereum.oracles.uniswap import UniswapV3Oracle
from rotkehlchen.chain.ethereum.utils import generate_address_via_create2
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_USDC
from rotkehlchen.constants.misc import NFT_DIRECTIVE
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError
from rotkehlchen.errors.price import PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import get_chunks

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

UNISWAP_V3_POSITIONS_PER_CHUNK = 45
POOL_INIT_CODE_HASH = '0xe34f199b19b2b4f47f68442619d555527d244f78a3297ea89325f843f87b8b54'
UNISWAP_V3_ERROR_MSG = 'Remote error calling multicall contract for uniswap v3 {} for address properties: {}'  # noqa: E501
POW_96 = 2**96
LOG_PRICE = FVal('1.0001')


class UnrecognizedFeeTierException(Exception):
    """Exception raised when a Uniswap V3 LP fee tier is not recognized."""


def uniswap_v3_lp_token_balances(
        userdb: 'DBHandler',
        address: ChecksumEvmAddress,
        ethereum: 'EthereumInquirer',
        msg_aggregator: MessagesAggregator,
        price_known_tokens: set[EvmToken],
        price_unknown_tokens: set[EvmToken],
) -> list[NFTLiquidityPool]:
    """
    Fetches all the Uniswap V3 LP positions for the specified address.
    1. Use the NFT Positions contract to call the `balanceOf` method to get number of positions.
    2. Loop through from 0 to (positions - 1) using the index and address to call
    `tokenOfOwnerByIndex` method which gives the NFT ID that represents a LP position.
    3. Use the token ID gotten above to call the `positions` method to get the current state of the
    liquidity position.
    4. Use the `positions` data to generate the LP address using the
    `_compute_pool_address` method.
    5. Use the pool contract of the addresses generate and call the `slot0` method to get the
    LP state.
    6. Get basic information of the tokens in the LP pairs.
    7. Calculate the price ranges for which the LP position is valid for.
    8. Calculate the amount of tokens in the LP position.
    9. Calculate the amount of tokens in the LP.

    The indices returned from calling `positions` method on the NFT contract.
    0 -> nonce	uint96
    1 -> operator	address
    2 -> token0	address
    3 -> token1	address
    4 -> fee	uint24
    5 -> tickLower	int24
    6 -> tickUpper	int24
    7 -> liquidity	uint128
    8 -> feeGrowthInside0LastX128  uint256
    9 -> feeGrowthInside1LastX128  uint256
    10 -> tokensOwed0	uint128
    11 -> tokensOwed1	uint128
    https://docs.uniswap.org/protocol/reference/periphery/interfaces/INonfungiblePositionManager#return-values

    If the multicall fails due to `RemoteError` or one of the calls isn't successful, it is omitted
    from the chunk.

    May raise RemoteError if querying NFT manager contract fails.
    """
    uniswap_v3_nft_manager = ethereum.contracts.contract(string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'))  # noqa: E501
    uniswap_v3_factory = ethereum.contracts.contract(string_to_evm_address('0x1F98431c8aD98523631AE4a59f267346ea31F984'))  # noqa: E501
    uniswap_v3_pool_abi = ethereum.contracts.abi('UNISWAP_V3_POOL')
    balances: list[NFTLiquidityPool] = []
    try:
        amount_of_positions = uniswap_v3_nft_manager.call(
            node_inquirer=ethereum,
            method_name='balanceOf',
            arguments=[address],
        )
    except RemoteError as e:
        raise RemoteError(
            f'Error calling nft manager contract to fetch of LP positions count for '
            f'an address with properties: {e!s}',
        ) from e

    if amount_of_positions == 0:
        return balances

    chunks = list(get_chunks(list(range(amount_of_positions)), n=UNISWAP_V3_POSITIONS_PER_CHUNK))
    for chunk in chunks:
        try:
            # Get tokens IDs from the Positions NFT contract using the user address and
            # the indexes i.e from 0 to (total number of user positions in the chunk - 1)
            tokens_ids_multicall = ethereum.multicall_2(
                require_success=False,
                calls=[
                    (
                        uniswap_v3_nft_manager.address,
                        uniswap_v3_nft_manager.encode('tokenOfOwnerByIndex', [address, index]),
                    )
                    for index in chunk
                ],
            )
        except RemoteError as e:
            log.error(UNISWAP_V3_ERROR_MSG.format('nft contract token ids', str(e)))
            continue

        tokens_ids = [
            uniswap_v3_nft_manager.decode(
                result=data[1],
                method_name='tokenOfOwnerByIndex',
                arguments=[address, index],
            )[0]
            for index, data in enumerate(tokens_ids_multicall) if data[0] is True
        ]
        try:
            # Get the user liquidity position using the token ID retrieved.
            positions_multicall = ethereum.multicall_2(
                require_success=False,
                calls=[
                    (
                        uniswap_v3_nft_manager.address,
                        uniswap_v3_nft_manager.encode('positions', [token_id]),
                    )
                    for token_id in tokens_ids
                ],
            )
        except RemoteError as e:
            log.error(UNISWAP_V3_ERROR_MSG.format('nft contract positions', str(e)))
            continue
        positions = [
            uniswap_v3_nft_manager.decode(
                result=data[1],
                method_name='positions',
                arguments=[tokens_ids[index]],
            )
            for index, data in enumerate(positions_multicall) if data[0] is True
        ]
        # Generate the LP contract address with CREATE2 opcode replicated in Python using
        # factory_address, token_0, token1 and the fee of the LP all gotten from the position.
        pool_addresses = [
            _compute_pool_address(
                uniswap_v3_factory_address=uniswap_v3_factory.address,
                token0_address_raw=position[2],
                token1_address_raw=position[3],
                fee=position[4],
            )
            for position in positions
        ]
        pool_contracts = [
            EvmContract(
                address=pool_address,
                abi=uniswap_v3_pool_abi,
                deployed_block=uniswap_v3_factory.deployed_block,
            )
            for pool_address in pool_addresses
        ]
        try:
            # Get the liquidity pool's state i.e `slot0` by iterating through
            # a pair of the LP address and its contract and reading the `slot0`
            slots_0_multicall = ethereum.multicall_2(
                require_success=False,
                calls=[
                    (entry[0], entry[1].encode('slot0'))
                    for entry in zip(pool_addresses, pool_contracts, strict=True)
                ],
            )
        except RemoteError as e:
            log.error(UNISWAP_V3_ERROR_MSG.format('pool contract slot0', str(e)))
            continue

        slots_0 = [
            entry[0].decode(entry[1][1], 'slot0')  # length equal due to multical args
            for entry in zip(pool_contracts, slots_0_multicall, strict=True) if entry[1][0] is True
        ]
        tokens_a, tokens_b = [], []
        for position in positions:
            try:
                token1_info = ethereum.get_erc20_contract_info(to_checksum_address(position[2]))
                tokens_a.append(token1_info)
                token2_info = ethereum.get_erc20_contract_info(to_checksum_address(position[3]))
                tokens_b.append(token2_info)
            except (BadFunctionCallOutput, ValueError) as e:
                log.error(
                    f'Error retrieving contract information for address: {position[2]} '
                    f'due to: {e!s}',
                )
                continue
        # Get the ranges of price for which each position is valid for.
        # Get the amount of each token present in an LP position.
        price_ranges = []
        amounts_0 = []
        amounts_1 = []
        for (position, slot_0, token_a, token_b) in zip(positions, slots_0, tokens_a, tokens_b, strict=True):  # noqa: E501
            price_ranges.append(
                calculate_price_range(
                    tick_lower=position[5],
                    tick_upper=position[6],
                    decimal_0=token_a['decimals'],
                    decimal_1=token_b['decimals'],
                ),
            )
            amounts_0.append(
                calculate_amount(
                    tick_lower=position[5],
                    liquidity=position[7],
                    tick_upper=position[6],
                    decimals=token_a['decimals'],
                    tick=slot_0[1],
                    token_position=0,
                ),
            )
            amounts_1.append(
                calculate_amount(
                    tick_lower=position[5],
                    liquidity=position[7],
                    tick_upper=position[6],
                    decimals=token_b['decimals'],
                    tick=slot_0[1],
                    token_position=1,
                ),
            )
        # First, get the total liquidity of the LPs.
        # Use the value of the liquidity to get the total amount of tokens in LPs.
        total_tokens_in_pools = []
        try:
            liquidity_in_pools_multicall = ethereum.multicall_2(
                require_success=False,
                calls=[
                    (entry[0], entry[1].encode('liquidity'))
                    for entry in zip(pool_addresses, pool_contracts, strict=True)
                ],
            )
        except RemoteError as e:
            log.error(UNISWAP_V3_ERROR_MSG.format('pool contract liquidity', str(e)))
            continue

        for _entry in zip(
                pool_contracts,
                liquidity_in_pools_multicall,
                positions,
                slots_0,
                tokens_a,
                tokens_b,
                strict=True,
        ):
            liquidity_in_pool = _entry[0].decode(_entry[1][1], 'liquidity')[0]
            try:
                total_tokens_in_pools.append(
                    calculate_total_amounts_of_tokens(
                        liquidity=liquidity_in_pool,
                        tick=_entry[3][1],
                        fee=_entry[2][4],
                        decimal_0=_entry[4]['decimals'],
                        decimal_1=_entry[5]['decimals'],
                    ),
                )
            except UnrecognizedFeeTierException as e:
                error_msg = f'Error calculating total amount of tokens in pool due to: {e!s}'
                log.error(error_msg)
                msg_aggregator.add_error(error_msg)
                continue

        for item in zip(
                tokens_ids,
                pool_addresses,
                positions,
                price_ranges,
                tokens_a,
                tokens_b,
                amounts_0,
                amounts_1,
                total_tokens_in_pools,
                strict=True,
        ):
            if FVal(item[6]) > ZERO or FVal(item[7]) > ZERO:
                item[4].update({
                    'amount': item[6],
                    'address': item[2][2],
                    'total_amount': item[8][0],
                })
                item[5].update({
                    'amount': item[7],
                    'address': item[2][3],
                    'total_amount': item[8][1],
                })
                balances.append(_decode_uniswap_v3_result(
                    userdb=userdb,
                    data=item,
                    uniswap_v3_nft_manager_address=uniswap_v3_nft_manager.address,
                    price_known_tokens=price_known_tokens,
                    price_unknown_tokens=price_unknown_tokens,
                ))
    return balances


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
        salt=Web3.toHex(Web3.keccak(encode_abi(['address', 'address', 'uint24'], parameters))),
        init_code=POOL_INIT_CODE_HASH,
        is_init_code_hashed=True,
    )


def calculate_price_range(
        tick_lower: int,
        tick_upper: int,
        decimal_0: int,
        decimal_1: int,
) -> tuple[FVal, FVal]:
    """Calculates the price range for a Uniswap V3 LP position."""
    sqrt_a = LOG_PRICE**tick_lower
    sqrt_b = LOG_PRICE**tick_upper

    sqrt_adjusted_a = sqrt_a * FVal(10**(decimal_0 - decimal_1))
    sqrt_adjusted_b = sqrt_b * FVal(10**(decimal_0 - decimal_1))

    return FVal(1 / sqrt_adjusted_b), FVal(1 / sqrt_adjusted_a)


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


def calculate_total_amounts_of_tokens(
        liquidity: int,
        tick: int,
        fee: Literal[100, 500, 3000, 10000],
        decimal_0: int,
        decimal_1: int,
) -> tuple[FVal, FVal]:
    """
    Calculates the total amount of tokens present in a liquidity pool.
    A fee of 10000 represents 200 ticks spacing, 3000 represents 60 ticks spacing and
    500 represents 10 ticks spacing.
    """
    if fee == 10000:
        tick_a = tick - (tick % 200)
        tick_b = tick + 200
    elif fee == 3000:
        tick_a = tick - (tick % 60)
        tick_b = tick + 60
    elif fee == 500:
        tick_a = tick - (tick % 10)
        tick_b = tick + 10
    elif fee == 100:
        tick_a = tick - (tick % 1)
        tick_b = tick + 1
    # This is to prevent new fee tiers from raising `referenced before initialised` error.
    else:
        raise UnrecognizedFeeTierException(
            f'Encountered an unrecognised Uniswap V3 LP fee tier: {fee}. '
            f'Please open a Github issue: https://github.com/rotki/rotki/issues',
        )

    sqrt_a = LOG_PRICE**FVal(tick_a / 2) * POW_96
    sqrt_b = LOG_PRICE**FVal(tick_b / 2) * POW_96
    total_amount_0 = (liquidity * POW_96 * (sqrt_b - sqrt_a) / sqrt_b / sqrt_a) / 10**decimal_0
    total_amount_1 = liquidity * (sqrt_b - sqrt_a) / POW_96 / 10**decimal_1

    return FVal(total_amount_0), FVal(total_amount_1)


def _decode_uniswap_v3_token(entry: dict[str, Any]) -> TokenDetails:
    return TokenDetails(
        address=to_checksum_address(entry['address']),
        name=entry['name'],
        symbol=entry['symbol'],
        decimals=entry['decimals'],
        amount=FVal(entry['amount']),
    )


def _decode_uniswap_v3_result(
        userdb: 'DBHandler',
        data: tuple,
        uniswap_v3_nft_manager_address: ChecksumEvmAddress,
        price_known_tokens: set[EvmToken],
        price_unknown_tokens: set[EvmToken],
) -> NFTLiquidityPool:
    """
    Takes the data aggregated from the Positions NFT contract & LP contract and converts it
    into an `NFTLiquidityPool` which is a representation of a Uniswap V3 LP position.

    The tokens dictionaries in `data` argument contain the following keys;
    address, name, symbol, decimals & amount.
    They are present at all times, although values might be empty.

    Edge cases whereby a token does not conform to ERC20 standard,the user balance is set to ZERO.
    """
    nft_id = NFT_DIRECTIVE + to_normalized_address(uniswap_v3_nft_manager_address) + '_' + str(data[0])  # noqa: E501
    pool_token = data[1]
    token0 = _decode_uniswap_v3_token(data[4])
    token1 = _decode_uniswap_v3_token(data[5])
    total_amounts_of_tokens = {
        token0.address: data[4]['total_amount'],
        token1.address: data[5]['total_amount'],
    }

    assets = []
    for token in (token0, token1):
        # Set the asset balance to ZERO if the asset raises `NotERC20Conformant` exception
        asset_balance = ZERO
        try:
            asset = get_or_create_evm_token(
                userdb=userdb,
                symbol=token.symbol,
                evm_address=token.address,
                chain_id=ChainID.ETHEREUM,
                name=token.name,
                decimals=token.decimals,
                encounter=TokenEncounterInfo(description='Uniswap v3 LP positions query'),
            )
            asset_balance = token.amount
        except NotERC20Conformant as e:
            log.error(
                f'Error fetching ethereum token {token.address!s} while decoding Uniswap V3 LP '
                f'position due to: {e!s}',
            )
        # Classify the asset either as price known or unknown
        if asset.has_oracle():
            price_known_tokens.add(asset)
        else:
            price_unknown_tokens.add(asset)
        assets.append(LiquidityPoolAsset(
            token=asset,
            total_amount=total_amounts_of_tokens[token.address],
            user_balance=Balance(amount=asset_balance),
        ))
    # total_supply is None because Uniswap V3 LP does not represent positions as tokens.
    pool = NFTLiquidityPool(
        address=pool_token,
        price_range=(FVal(data[3][0]), FVal(data[3][1])),
        nft_id=nft_id,
        assets=assets,
        total_supply=None,
        user_balance=Balance(amount=ZERO),
    )
    return pool


def get_unknown_asset_price_chain(
        ethereum: 'EthereumInquirer',
        unknown_tokens: set[EvmToken],
) -> AssetToPrice:
    """Get token price using Uniswap V3 Oracle."""
    oracle = UniswapV3Oracle(ethereum_inquirer=ethereum)
    asset_price: AssetToPrice = {}
    for from_token in unknown_tokens:
        try:
            price, _ = oracle.query_current_price(from_token, A_USDC.resolve_to_asset_with_oracles(), False)  # noqa: E501
            asset_price[from_token.evm_address] = price
        except (PriceQueryUnsupportedAsset, RemoteError) as e:
            log.error(
                f'Failed to find price for {from_token!s}/{A_USDC!s} LP using '
                f'Uniswap V3 oracle due to: {e!s}.',
            )
            asset_price[from_token.evm_address] = ZERO_PRICE

    return asset_price


def update_asset_price_in_uniswap_v3_lp_balances(
        address_balances: AddressToUniswapV3LPBalances,
        known_asset_price: 'AssetToPrice',
        unknown_asset_price: 'AssetToPrice',
) -> None:
    """Update the Uniswap V3 pools underlying assets prices in USD"""
    update_asset_price_in_lp_balances(
        address_balances=address_balances,
        known_asset_price=known_asset_price,
        unknown_asset_price=unknown_asset_price,
    )
