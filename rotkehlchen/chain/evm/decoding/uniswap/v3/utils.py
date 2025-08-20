import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Final

from eth_abi import encode as encode_abi
from eth_utils import to_checksum_address, to_hex
from web3 import Web3
from web3.types import BlockIdentifier

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.oracles.constants import UNISWAP_FACTORY_ADDRESSES
from rotkehlchen.chain.ethereum.utils import generate_address_via_create2
from rotkehlchen.chain.evm.decoding.uniswap.utils import get_position_price_from_underlying
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import tokenid_to_collectible_id
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Price

from .constants import UNISWAP_V3_NFT_MANAGER_ADDRESSES

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

POOL_INIT_CODE_HASH: Final = '0xe34f199b19b2b4f47f68442619d555527d244f78a3297ea89325f843f87b8b54'


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

    return get_position_price_from_underlying(
        evm_inquirer=evm_inquirer,
        token0_raw_address=position[2],
        token1_raw_address=position[3],
        tick_lower=position[5],
        tick_upper=position[6],
        liquidity=position[7],
        tick=slot_0[1],
        price_func=price_func,
    )
