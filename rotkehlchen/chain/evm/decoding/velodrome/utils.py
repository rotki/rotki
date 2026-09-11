import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.uniswap.utils import get_position_price_from_underlying
from rotkehlchen.chain.evm.decoding.velodrome.constants import (
    CL_FACTORY_ABI,
    CL_POOL_ABI,
    SLIPSTREAM_CL_FACTORIES,
    SLIPSTREAM_NFPM_ABI,
    SLIPSTREAM_NFPM_ADDRESSES,
)
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import tokenid_to_collectible_id
from rotkehlchen.errors.misc import RemoteError
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
    queried, which is also the case for burned positions.
    """
    if (
        (collectible_id := tokenid_to_collectible_id(identifier=token.identifier)) is None or
        (nfpm_address := SLIPSTREAM_NFPM_ADDRESSES.get(evm_inquirer.chain_id)) is None or
        (factory_address := SLIPSTREAM_CL_FACTORIES.get(evm_inquirer.chain_id)) is None
    ):
        log.error('Can not price a Slipstream position', token=token, chain=evm_inquirer.chain_name)  # noqa: E501
        return ZERO_PRICE

    try:
        position = evm_inquirer.call_contract(
            contract_address=nfpm_address,
            abi=SLIPSTREAM_NFPM_ABI,
            method_name='positions',
            arguments=[int(collectible_id)],
            block_identifier=block_identifier,
        )
        pool_address = deserialize_evm_address(evm_inquirer.call_contract(
            contract_address=factory_address,
            abi=CL_FACTORY_ABI,
            method_name='getPool',
            arguments=[position[2], position[3], position[4]],
            block_identifier=block_identifier,
        ))
        if pool_address == ZERO_ADDRESS:
            log.error('Found no Slipstream pool for position', token=token, chain=evm_inquirer.chain_name)  # noqa: E501
            return ZERO_PRICE

        slot_0 = evm_inquirer.call_contract(
            contract_address=pool_address,
            abi=CL_POOL_ABI,
            method_name='slot0',
            block_identifier=block_identifier,
        )
    except (RemoteError, ValueError, DeserializationError) as e:
        log.error(
            'Failed to query a Slipstream position',
            token=token,
            chain=evm_inquirer.chain_name,
            error=str(e),
        )
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
