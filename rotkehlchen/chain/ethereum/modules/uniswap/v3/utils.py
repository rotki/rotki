import logging
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Set, Tuple

from eth_abi import encode_abi
from eth_abi.packed import encode_abi_packed
from eth_utils import to_checksum_address, to_normalized_address
from web3 import Web3
from web3.exceptions import BadFunctionCallOutput

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
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
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants.assets import A_USDC
from rotkehlchen.constants.ethereum import (
    UNISWAP_V3_FACTORY,
    UNISWAP_V3_NFT_MANAGER,
    UNISWAP_V3_POOL_ABI,
)
from rotkehlchen.constants.misc import NFT_DIRECTIVE, ZERO
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError
from rotkehlchen.errors.price import PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, Price
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import get_chunks

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

UNISWAP_V3_POSITIONS_PER_CHUNK = 45
POOL_INIT_CODE_HASH = '0xe34f199b19b2b4f47f68442619d555527d244f78a3297ea89325f843f87b8b54'
UNISWAP_V3_ERROR_MSG = 'Remote error calling multicall contract for uniswap v3 {} for address properties: {}'  # noqa: 501
POW_96 = 2**96
LOG_PRICE = FVal('1.0001')


class UnrecognizedFeeTierException(Exception):
    """Exception raised when a Uniswap V3 LP fee tier is not recognized."""


def uniswap_v3_lp_token_balances(
        userdb: 'DBHandler',
        address: ChecksumEvmAddress,
        ethereum: 'EthereumManager',
        msg_aggregator: MessagesAggregator,
        price_known_tokens: Set[EvmToken],
        price_unknown_tokens: Set[EvmToken],
) -> List[NFTLiquidityPool]:
    """
    Fetches all the Uniswap V3 LP positions for the specified address.
    1. Use the NFT Positions contract to call the `balanceOf` method to get number of positions.
    2. Loop through from 0 to (positions - 1) using the index and address to call
    `tokenOfOwnerByIndex` method which gives the NFT ID that represents a LP position.
    3. Use the token ID gotten above to call the `positions` method to get the current state of the
    liquidity position.
    4. Use the `positions` data to generate the LP address using the `compute_pool_address` method.
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
    nft_manager_contract = EvmContract(
        address=UNISWAP_V3_NFT_MANAGER.address,
        abi=UNISWAP_V3_NFT_MANAGER.abi,
        deployed_block=UNISWAP_V3_NFT_MANAGER.deployed_block,
    )
    balances: List[NFTLiquidityPool] = []
    try:
        amount_of_positions = nft_manager_contract.call(
            manager=ethereum,
            method_name='balanceOf',
            arguments=[address],
        )
    except RemoteError as e:
        raise RemoteError(
            f'Error calling nft manager contract to fetch of LP positions count for '
            f'an address with properties: {str(e)}',
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
                        UNISWAP_V3_NFT_MANAGER.address,
                        nft_manager_contract.encode('tokenOfOwnerByIndex', [address, index]),
                    )
                    for index in chunk
                ],
            )
        except RemoteError as e:
            log.error(UNISWAP_V3_ERROR_MSG.format('nft contract token ids', str(e)))
            continue

        tokens_ids = [
            nft_manager_contract.decode(   # pylint: disable=unsubscriptable-object
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
                        UNISWAP_V3_NFT_MANAGER.address,
                        nft_manager_contract.encode('positions', [token_id]),
                    )
                    for token_id in tokens_ids
                ],
            )
        except RemoteError as e:
            log.error(UNISWAP_V3_ERROR_MSG.format('nft contract positions', str(e)))
            continue
        positions = [
            nft_manager_contract.decode(
                result=data[1],
                method_name='positions',
                arguments=[tokens_ids[index]],
            )
            for index, data in enumerate(positions_multicall) if data[0] is True
        ]
        # Generate the LP contract address with CREATE2 opcode replicated in Python using
        # factory_address, token_0, token1 and the fee of the LP all gotten from the position.
        pool_addresses = [
            compute_pool_address(
                token0_address_raw=position[2],
                token1_address_raw=position[3],
                fee=position[4],
            )
            for position in positions
        ]
        pool_contracts = [
            EvmContract(
                address=pool_address,
                abi=UNISWAP_V3_POOL_ABI,
                deployed_block=UNISWAP_V3_FACTORY.deployed_block,
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
                    for entry in zip(pool_addresses, pool_contracts)
                ],
            )
        except RemoteError as e:
            log.error(UNISWAP_V3_ERROR_MSG.format('pool contract slot0', str(e)))
            continue
        slots_0 = [
            entry[0].decode(entry[1][1], 'slot0')
            for entry in zip(pool_contracts, slots_0_multicall) if entry[1][0] is True
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
                    f'due to: {str(e)}',
                )
                continue
        # Get the ranges of price for which each position is valid for.
        # Get the amount of each token present in an LP position.
        price_ranges = []
        amounts_0 = []
        amounts_1 = []
        for (position, slot_0, token_a, token_b) in zip(positions, slots_0, tokens_a, tokens_b):
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
                    for entry in zip(pool_addresses, pool_contracts)
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
                error_msg = f'Error calculating total amount of tokens in pool due to: {str(e)}'
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
                    price_known_tokens=price_known_tokens,
                    price_unknown_tokens=price_unknown_tokens,
                ))
    return balances


def compute_pool_address(
        token0_address_raw: str,
        token1_address_raw: str,
        fee: int,
) -> ChecksumEvmAddress:
    """
    Generate the pool address from the Uniswap Factory Address, pair of tokens
    and the fee using CREATE2 opcode.
    """
    token_0 = to_checksum_address(token0_address_raw)
    token_1 = to_checksum_address(token1_address_raw)
    parameters = []
    # Sort the addresses
    if int(token_0, 16) < int(token_1, 16):
        parameters = [token_0, token_1, fee]
    else:
        parameters = [token_1, token_0, fee]
    abi_encoded_1 = encode_abi(
        ['address', 'address', 'uint24'],
        parameters,
    )
    # pylint: disable=no-value-for-parameter
    salt = Web3.solidityKeccak(abi_types=['bytes'], values=['0x' + abi_encoded_1.hex()])
    abi_encoded_2 = encode_abi_packed(['address', 'bytes32'], (UNISWAP_V3_FACTORY.address, salt))
    # pylint: disable=no-value-for-parameter
    raw_address_bytes = Web3.solidityKeccak(
        abi_types=['bytes', 'bytes'],
        values=['0xff' + abi_encoded_2.hex(), POOL_INIT_CODE_HASH],
    )
    address = to_checksum_address(raw_address_bytes[12:].hex())
    return address


def calculate_price_range(
        tick_lower: int,
        tick_upper: int,
        decimal_0: int,
        decimal_1: int,
) -> Tuple[FVal, FVal]:
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
) -> Tuple[FVal, FVal, FVal]:
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
) -> Tuple[FVal, FVal]:
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
    total_amount_0 = ((liquidity * POW_96 * (sqrt_b - sqrt_a) / sqrt_b / sqrt_a) / 10**decimal_0)
    total_amount_1 = liquidity * (sqrt_b - sqrt_a) / POW_96 / 10**decimal_1

    return FVal(total_amount_0), FVal(total_amount_1)


def _decode_uniswap_v3_token(entry: Dict[str, Any]) -> TokenDetails:
    return TokenDetails(
        address=to_checksum_address(entry['address']),
        name=entry['name'],
        symbol=entry['symbol'],
        decimals=entry['decimals'],
        amount=FVal(entry['amount']),
    )


def _decode_uniswap_v3_result(
        userdb: 'DBHandler',
        data: Tuple,
        price_known_tokens: Set[EvmToken],
        price_unknown_tokens: Set[EvmToken],
) -> NFTLiquidityPool:
    """
    Takes the data aggregated from the Positions NFT contract & LP contract and converts it
    into an `NFTLiquidityPool` which is a representation of a Uniswap V3 LP position.

    The tokens dictionaries in `data` argument contain the following keys;
    address, name, symbol, decimals & amount.
    They are present at all times, although values might be empty.

    Edge cases whereby a token does not conform to ERC20 standard,the user balance is set to ZERO.
    """
    nft_id = NFT_DIRECTIVE + to_normalized_address(UNISWAP_V3_NFT_MANAGER.address) + '_' + str(data[0])  # noqa: E501
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
                chain=ChainID.ETHEREUM,
                name=token.name,
                decimals=token.decimals,
            )
            asset_balance = token.amount
        except NotERC20Conformant as e:
            log.error(
                f'Error fetching ethereum token {str(token.address)} while decoding Uniswap V3 LP '
                f'position due to: {str(e)}',
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
        ethereum: 'EthereumManager',
        unknown_tokens: Set[EvmToken],
) -> AssetToPrice:
    """Get token price using Uniswap V3 Oracle."""
    oracle = UniswapV3Oracle(eth_manager=ethereum)
    asset_price: AssetToPrice = {}
    for from_token in unknown_tokens:
        try:
            price, _ = oracle.query_current_price(from_token, A_USDC.resolve_to_asset_with_oracles(), False)  # noqa: E501
            asset_price[from_token.evm_address] = price
        except (PriceQueryUnsupportedAsset, RemoteError) as e:
            log.error(
                f'Failed to find price for {str(from_token)}/{str(A_USDC) } LP using '
                f'Uniswap V3 oracle due to: {str(e)}.',
            )
            asset_price[from_token.evm_address] = Price(ZERO)

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
