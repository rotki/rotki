import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Final, NamedTuple

from eth_abi import encode as encode_abi
from eth_utils import to_checksum_address, to_hex
from web3 import Web3
from web3.types import BlockIdentifier

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.decoding.types import get_versioned_counterparty_label
from rotkehlchen.chain.ethereum.oracles.constants import UNISWAP_FACTORY_ADDRESSES
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, generate_address_via_create2
from rotkehlchen.chain.evm.decoding.structures import ActionItem, DecoderContext, EvmDecodingOutput
from rotkehlchen.chain.evm.decoding.uniswap.utils import get_position_price_from_underlying
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import tokenid_to_collectible_id
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChecksumEvmAddress, Price, TokenKind

from .constants import UNISWAP_V3_NFT_MANAGER_ADDRESSES

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.fval import FVal

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

POOL_INIT_CODE_HASH: Final = '0xe34f199b19b2b4f47f68442619d555527d244f78a3297ea89325f843f87b8b54'


class CryptoAssetAmount(NamedTuple):
    """This is used to represent a pair of resolved crypto asset to an amount."""
    asset: 'EvmToken'
    amount: 'FVal'


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


def decode_uniswap_v3_like_deposit_or_withdrawal(
        context: DecoderContext,
        is_deposit: bool,
        counterparty: str,
        token0_raw_address: str,
        token1_raw_address: str,
        amount0_raw: int,
        amount1_raw: int,
        position_id: int,
        evm_inquirer: 'EvmNodeInquirer',
        wrapped_native_currency: Asset,
) -> EvmDecodingOutput:
    """This method decodes a Uniswap V3 like LP liquidity increase or decrease.

    Examples of such transactions are:
    https://etherscan.io/tx/0x6bf3588f669a784adf5def3c0db149b0cdbcca775e472bb35f00acedee263c4c (deposit)
    https://etherscan.io/tx/0x76c312fe1c8604de5175c37dcbbb99cc8699336f3e4840e9e29e3383970f6c6d (withdrawal)
    """  # noqa: E501
    new_action_items = []
    display_name = get_versioned_counterparty_label(counterparty)
    if is_deposit:
        notes = f'Deposit {{amount}} {{asset}} to {display_name} LP {position_id}'
        from_event_type = HistoryEventType.SPEND
        to_event_type = HistoryEventType.DEPOSIT
        to_event_subtype = HistoryEventSubType.DEPOSIT_ASSET
    else:  # can only be 'removal'
        notes = f'Remove {{amount}} {{asset}} from {display_name} LP {position_id}'
        from_event_type = HistoryEventType.RECEIVE
        to_event_type = HistoryEventType.WITHDRAWAL
        to_event_subtype = HistoryEventSubType.REMOVE_ASSET

    resolved_assets_and_amounts: list[CryptoAssetAmount] = []
    for token, amount in (
            (deserialize_evm_address(token0_raw_address), amount0_raw),
            (deserialize_evm_address(token1_raw_address), amount1_raw),
    ):
        token_with_data = get_or_create_evm_token(
            userdb=evm_inquirer.database,
            evm_address=token,
            chain_id=evm_inquirer.chain_id,
            token_kind=TokenKind.ERC20,
            evm_inquirer=evm_inquirer,
            encounter=TokenEncounterInfo(tx_ref=context.transaction.tx_hash),
        )
        resolved_assets_and_amounts.append(CryptoAssetAmount(
            asset=token_with_data,
            amount=asset_normalized_value(amount, token_with_data),
        ))

    found_events = [False, False]
    refund_event = None
    for event in context.decoded_events:
        if event.event_subtype != HistoryEventSubType.NONE:
            continue  # Avoid performing other checks if the event has a subtype other than NONE

        for idx, resolved_asset_amount in enumerate(resolved_assets_and_amounts):
            if found_events[idx]:
                continue  # Skip if we already found an event for this token

            if resolved_asset_amount.asset == wrapped_native_currency and event.asset == evm_inquirer.native_token:  # noqa: E501
                maybe_event_asset_symbol = event.asset.symbol_or_name()
            else:
                if event.asset != resolved_asset_amount.asset:
                    continue

                maybe_event_asset_symbol = resolved_asset_amount.asset.symbol

            if (
                    from_event_type == HistoryEventType.SPEND and
                    event.event_type == HistoryEventType.RECEIVE
            ):
                # Unlike approved tokens where the contract requests an exact amount,
                # the approximate amount of the native asset sent may require a refund.
                refund_event = event
            elif event.event_type == from_event_type:
                if event.amount != resolved_asset_amount.amount:
                    if (
                            refund_event is not None and
                            event.amount - refund_event.amount == resolved_asset_amount.amount
                    ):
                        event.amount = resolved_asset_amount.amount
                    else:
                        continue

                found_events[idx] = True
                event.event_type = to_event_type
                event.event_subtype = to_event_subtype
                event.counterparty = counterparty
                event.notes = notes.format(amount=event.amount, asset=maybe_event_asset_symbol)
                break

    if refund_event is not None:
        context.decoded_events.remove(refund_event)

    for resolved_asset_amount, found in zip(resolved_assets_and_amounts, found_events, strict=False):  # noqa: E501
        if found:
            continue  # Skip events that were found in decoded_events and are already modified.

        new_action_items.append(
            ActionItem(
                action='transform',
                from_event_type=from_event_type,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=resolved_asset_amount.asset,
                amount=resolved_asset_amount.amount,
                to_event_type=to_event_type,
                to_event_subtype=to_event_subtype,
                to_notes=notes.format(
                    amount=resolved_asset_amount.amount,
                    asset=resolved_asset_amount.asset.symbol,
                ),
                to_counterparty=counterparty,
            ),
        )

    return EvmDecodingOutput(
        action_items=new_action_items,
        matched_counterparty=counterparty,
    )
