import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.uniswap.utils import get_position_price_from_state
from rotkehlchen.chain.evm.decoding.velodrome.constants import (
    CL_FACTORY_ABI,
    CL_POOL_ABI,
    SLIPSTREAM_CL_FACTORIES,
    SLIPSTREAM_NFPM_ABI,
    SLIPSTREAM_NFPM_ADDRESSES,
)
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import tokenid_to_collectible_id
from rotkehlchen.errors.misc import ContractReverted, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address

if TYPE_CHECKING:
    from collections.abc import Callable

    from web3.types import BlockIdentifier

    from rotkehlchen.assets.asset import Asset, EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import Price

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _query_slipstream_position(
        token: EvmToken,
        evm_inquirer: EvmNodeInquirer,
        block_identifier: BlockIdentifier,
) -> tuple[Any, Any] | None:
    """Read a Slipstream position and the `slot0` state of its pool.

    Returns None if the position can't be read.

    May raise:
    - ContractReverted if the position manager reverts on the position, such as a burned one
    - RemoteError if a contract call failed, with the cause it failed for
    """
    if (
        (collectible_id := tokenid_to_collectible_id(identifier=token.identifier)) is None or
        (nfpm_address := SLIPSTREAM_NFPM_ADDRESSES.get(evm_inquirer.chain_id)) is None or
        (factory_address := SLIPSTREAM_CL_FACTORIES.get(evm_inquirer.chain_id)) is None
    ):
        log.error('Can not price a Slipstream position', token=token, chain=evm_inquirer.chain_name)  # noqa: E501
        return None

    try:
        position = evm_inquirer.call_contract(
            contract_address=nfpm_address,
            abi=SLIPSTREAM_NFPM_ABI,
            method_name='positions',
            arguments=[int(collectible_id)],
            block_identifier=block_identifier,
        )
    except ValueError as e:
        log.error('Can not read a Slipstream position', token=token, error=str(e))
        return None

    try:
        pool_address = deserialize_evm_address(evm_inquirer.call_contract(
            contract_address=factory_address,
            abi=CL_FACTORY_ABI,
            method_name='getPool',
            arguments=[position[2], position[3], position[4]],
            block_identifier=block_identifier,
        ))
        if pool_address == ZERO_ADDRESS:
            log.error('Found no Slipstream pool for position', token=token, chain=evm_inquirer.chain_name)  # noqa: E501
            return None

        slot_0 = evm_inquirer.call_contract(
            contract_address=pool_address,
            abi=CL_POOL_ABI,
            method_name='slot0',
            block_identifier=block_identifier,
        )
    except ContractReverted as e:  # only a revert on the position itself means it is gone
        raise RemoteError(str(e), cause=e.cause) from e
    except (ValueError, DeserializationError) as e:
        log.error(
            'Failed to read the pool of a Slipstream position',
            token=token,
            chain=evm_inquirer.chain_name,
            error=str(e),
        )
        return None

    return position, slot_0


def get_slipstream_position_price(
        token: EvmToken,
        evm_inquirer: EvmNodeInquirer,
        price_func: Callable[[Asset], Price],
        block_identifier: BlockIdentifier = 'latest',
) -> Price:
    """Get the price of a Slipstream (velodrome/aerodrome concentrated liquidity) position
    NFT from its underlying assets, the same way uniswap v3 positions are priced.

    `price_func` is a function to get the price of an asset, allowing this function to be used
    for both current and historical prices. Returns ZERO_PRICE if the position can not be
    queried, which is also the case for burned positions. query_slipstream_position_price
    tells those apart.
    """
    try:
        if (state := _query_slipstream_position(
            token=token,
            evm_inquirer=evm_inquirer,
            block_identifier=block_identifier,
        )) is None:
            return ZERO_PRICE
    except RemoteError as e:
        log.error(
            'Failed to query a Slipstream position',
            token=token,
            chain=evm_inquirer.chain_name,
            error=str(e),
        )
        return ZERO_PRICE

    position, slot_0 = state
    return get_position_price_from_state(
        evm_inquirer=evm_inquirer,
        position=position,
        slot_0=slot_0,
        price_func=price_func,
    )


def query_slipstream_position_price(
        token: EvmToken,
        evm_inquirer: EvmNodeInquirer,
        price_func: Callable[[Asset], Price],
        block_identifier: BlockIdentifier,
) -> Price | None:
    """Get the price of a Slipstream position, telling apart why it has none.

    Returns ZERO_PRICE for a position the position manager reverts on, such as a burned
    one, since it holds nothing, and None for a position that can't be read.

    May raise:
    - RemoteError if a contract call failed, with the cause it failed for
    """
    try:
        if (state := _query_slipstream_position(
            token=token,
            evm_inquirer=evm_inquirer,
            block_identifier=block_identifier,
        )) is None:
            return None
    except ContractReverted as e:
        log.debug('Slipstream position reverted, so it holds nothing', token=token, error=str(e))
        return ZERO_PRICE

    position, slot_0 = state
    return get_position_price_from_state(
        evm_inquirer=evm_inquirer,
        position=position,
        slot_0=slot_0,
        price_func=price_func,
    )
