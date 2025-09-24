import logging
from typing import TYPE_CHECKING

from eth_abi import encode
from eth_typing import ABI
from web3 import Web3

from rotkehlchen.chain.decoding.types import get_versioned_counterparty_label
from rotkehlchen.chain.ethereum.utils import generate_address_via_create2
from rotkehlchen.chain.evm.decoding.quickswap.constants import UNISWAP_QUICKSWAP_COUNTERPARTY_MAP
from rotkehlchen.chain.evm.decoding.uniswap.utils import get_position_price_from_underlying
from rotkehlchen.chain.evm.utils import query_contract_response_as_dict
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import tokenid_to_collectible_id
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.types import ChecksumEvmAddress, Price

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def decode_quickswap_swap(
        tx_log: 'EvmTxReceiptLog',
        decoded_events: list['EvmEvent'],
) -> list['EvmEvent']:
    """Quickswap swaps are already decoded by the uniswap decoders since they use the same swap
    tx_log signature. Finds the decoded uniswap events and updates the counterparty and notes.
    """
    for event in decoded_events:
        if not (
                event.event_type == HistoryEventType.TRADE and
                event.address == tx_log.address and
                event.counterparty in UNISWAP_QUICKSWAP_COUNTERPARTY_MAP
        ):
            continue

        event.counterparty = UNISWAP_QUICKSWAP_COUNTERPARTY_MAP[event.counterparty]
        display_name = get_versioned_counterparty_label(event.counterparty)
        if event.event_subtype == HistoryEventSubType.SPEND:
            event.notes = f'Swap {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} in {display_name}'  # noqa: E501
        else:  # receive
            event.notes = f'Receive {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} as the result of a swap in {display_name}'  # noqa: E501

    return decoded_events


def get_quickswap_algebra_position_price(
        inquirer: 'Inquirer',
        token: 'EvmToken',
        nft_manager: 'ChecksumEvmAddress',
        nft_manager_abi: ABI,
        pool_deployer: 'ChecksumEvmAddress',
        pool_abi: ABI,
        pool_init_code_hash: str,
) -> 'Price':
    """Get the price of a Quickswap V3/V4 Algebra LP position."""
    if (collectible_id := tokenid_to_collectible_id(identifier=token.identifier)) is None:
        log.error(f'Failed to find Quickswap position price for {token} due to missing token ID.')
        return ZERO_PRICE

    evm_inquirer = inquirer.get_evm_manager(chain_id=token.chain_id).node_inquirer

    # Get the user liquidity position information using the token ID.
    if (position_info := query_contract_response_as_dict(
            evm_inquirer=evm_inquirer,
            contract_address=nft_manager,
            abi=nft_manager_abi,
            method='positions',
            arguments=[int(collectible_id)],
    )) is None:
        log.error(f'Failed to get Quickswap LP position info for {token}.')
        return ZERO_PRICE

    # Generate the LP contract address with CREATE2 opcode replicated in Python using
    # the init hash, deployer address, and token addresses.
    try:
        pool_address = generate_address_via_create2(
            address=pool_deployer,
            salt=Web3.keccak(encode(types=['address', 'address'], args=[
                (token0_address := deserialize_evm_address(position_info['token0'])),
                (token1_address := deserialize_evm_address(position_info['token1'])),
            ])).hex(),
            init_code=pool_init_code_hash,
            is_init_code_hashed=True,
        )
    except DeserializationError as e:
        log.error(f'Failed to compute Quickswap pool address for {token} due to {e!s}')
        return ZERO_PRICE

    # Get the liquidity pool's state
    if (state_info := query_contract_response_as_dict(
        evm_inquirer=evm_inquirer,
        contract_address=pool_address,
        abi=pool_abi,
        method='globalState',
    )) is None:
        log.error(f'Failed to get Quickswap pool contract globalState for {token}.')
        return ZERO_PRICE

    return get_position_price_from_underlying(
        evm_inquirer=evm_inquirer,
        token0_raw_address=token0_address,
        token1_raw_address=token1_address,
        tick_lower=position_info['tickLower'],
        tick_upper=position_info['tickUpper'],
        liquidity=position_info['liquidity'],
        tick=state_info['tick'],
        price_func=inquirer.find_usd_price,
    )
