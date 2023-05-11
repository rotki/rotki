from typing import TYPE_CHECKING, Callable, Literal, Optional

from web3 import Web3

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import CryptoAsset
from rotkehlchen.assets.utils import TokenSeenAt, get_or_create_evm_token
from rotkehlchen.chain.ethereum.modules.constants import AMM_ASSETS_SYMBOLS
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, generate_address_via_create2
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    FAILED_ENRICHMENT_OUTPUT,
    ActionItem,
    DecodingOutput,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import ChainID
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.types import ChecksumEvmAddress, EvmTokenKind, EvmTransaction, EVMTxHash
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler

UNISWAP_V2_ROUTER = string_to_evm_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D')
SUSHISWAP_ROUTER = string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F')


def decode_uniswap_v2_like_swap(
        tx_log: EvmTxReceiptLog,
        decoded_events: list['EvmEvent'],
        transaction: EvmTransaction,
        counterparty: str,
        database: 'DBHandler',
        ethereum_inquirer: 'EthereumInquirer',
        notify_user: Callable[['EvmEvent', str], None],
) -> DecodingOutput:
    """Common logic for decoding uniswap v2 like protocols (uniswap and sushiswap atm)

    Decode trade for uniswap v2 like amm. The approach is to read the events and detect the ones
    where the user sends and receives any asset. The spend asset is the swap executed and
    the received is the result of calling the swap method in the uniswap contract.
    We need to make sure that the events related to the swap are consecutive and for that
    we make use of the maybe_reshuffle_events() function.

    This method will identify the correct counterparty using the argument provided and a call to
    get_or_create_evm_token. This call is needed to retrieve the symbol of the pool and determine
    if the pool is from the selected counterparty.
    """

    exclude_amms = dict(AMM_ASSETS_SYMBOLS)
    exclude_amms.pop(counterparty)
    pool_token = get_or_create_evm_token(
        userdb=database,
        evm_address=tx_log.address,
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        evm_inquirer=ethereum_inquirer,
        seen=TokenSeenAt(tx_hash=transaction.tx_hash),
    )

    if pool_token.symbol in exclude_amms.values():
        # If the symbol for the current counterparty matches the expected symbol for another
        # counterparty skip the decoding using this rule.
        return DEFAULT_DECODING_OUTPUT

    # When the router chains multiple swaps in one transaction only the last swap has
    # the buyer in the topic. In that case we know it is the last swap and the receiver is
    # the user
    maybe_buyer = hex_or_bytes_to_address(tx_log.topics[2])
    out_event = in_event = None

    # amount_in is the amount that enters the pool and amount_out the one
    # that leaves the pool
    amount_in_0, amount_in_1 = hex_or_bytes_to_int(tx_log.data[0:32]), hex_or_bytes_to_int(tx_log.data[32:64])  # noqa: E501
    amount_out_0, amount_out_1 = hex_or_bytes_to_int(tx_log.data[64:96]), hex_or_bytes_to_int(tx_log.data[96:128])  # noqa: E501
    amount_in, amount_out = amount_in_0, amount_out_0
    if amount_in == ZERO:
        amount_in = amount_in_1
    if amount_out == ZERO:
        amount_out = amount_out_1

    received_eth = ZERO
    for event in decoded_events:
        if event.asset == A_ETH and event.event_type == HistoryEventType.RECEIVE:
            received_eth += event.balance.amount

    for event in decoded_events:
        # When we look for the spend event we have to take into consideration the case
        # where not all the ETH is converted. The ETH that is not converted is returned
        # in an internal transaction to the user.
        try:
            crypto_asset = event.asset.resolve_to_crypto_asset()
        except (UnknownAsset, WrongAssetType):
            notify_user(event, counterparty)
            return DEFAULT_DECODING_OUTPUT

        if (
            event.event_type == HistoryEventType.SPEND and
            (
                event.balance.amount == (spend_eth := asset_normalized_value(
                    amount=amount_in,
                    asset=crypto_asset,
                )) or
                event.asset == A_ETH and spend_eth + received_eth == event.balance.amount
            )
        ):
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.SPEND
            event.counterparty = counterparty
            event.notes = f'Swap {event.balance.amount} {crypto_asset.symbol} in {counterparty} from {event.location_label}'  # noqa: E501
            out_event = event
        elif (  # out_event is already decoded
            event.event_type == HistoryEventType.TRADE and
            event.event_subtype == HistoryEventSubType.SPEND and
            event.counterparty == counterparty
        ):
            out_event = event
        elif (
            (maybe_buyer == transaction.from_address or event.asset == A_ETH) and
            event.event_type in (HistoryEventType.RECEIVE, HistoryEventType.TRANSFER) and
            event.balance.amount == asset_normalized_value(
                amount=amount_out,
                asset=crypto_asset,
            )
        ):
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.RECEIVE
            event.counterparty = counterparty
            event.notes = f'Receive {event.balance.amount} {crypto_asset.symbol} in {counterparty} from {event.location_label}'  # noqa: E501
            in_event = event
        elif (
            event.event_type == HistoryEventType.RECEIVE and
            event.balance.amount != asset_normalized_value(
                amount=amount_out,
                asset=crypto_asset,
            ) and
            event.asset == A_ETH and
            transaction.from_address == event.location_label and
            event.address in (SUSHISWAP_ROUTER, UNISWAP_V2_ROUTER)
        ):
            # this is to make sure it's the amm issuing the refund and not an aggregator making a swap  # noqa: E501
            # Those are assets returned due to a change in the swap price
            event.event_type = HistoryEventType.TRANSFER
            event.event_subtype = HistoryEventSubType.NONE
            event.counterparty = counterparty
            event.notes = f'Refund of {event.balance.amount} {crypto_asset.symbol} in {counterparty} due to price change'  # noqa: E501

    maybe_reshuffle_events(out_event=out_event, in_event=in_event, events_list=decoded_events)
    return DEFAULT_DECODING_OUTPUT


def decode_uniswap_like_deposit_and_withdrawals(
        tx_log: EvmTxReceiptLog,
        decoded_events: list['EvmEvent'],
        all_logs: list[EvmTxReceiptLog],
        event_action_type: Literal['addition', 'removal'],
        counterparty: str,
        database: 'DBHandler',
        ethereum_inquirer: 'EthereumInquirer',
        factory_address: ChecksumEvmAddress,
        init_code_hash: str,
        tx_hash: EVMTxHash,
) -> DecodingOutput:
    """
    This is a common logic for Uniswap V2 like AMMs e.g Sushiswap.
    This method decodes a liquidity addition or removal to Uniswap V2 pool.

    Examples of such transactions are:
    https://etherscan.io/tx/0x1bab8a89a6a3f8cb127cfaf7cd58809201a4e230d0a05f9e067674749605959e (deposit)
    https://etherscan.io/tx/0x0936a16e1d3655e832c60bed52040fd5ac0d99d03865d11225b3183dba318f43 (withdrawal)
    """  # noqa: E501
    resolved_eth = A_ETH.resolve_to_crypto_asset()
    target_pool_address = tx_log.address
    amount0_raw = hex_or_bytes_to_int(tx_log.data[:32])
    amount1_raw = hex_or_bytes_to_int(tx_log.data[32:64])

    token0: Optional[CryptoAsset] = None
    token1: Optional[CryptoAsset] = None
    event0_idx = event1_idx = None

    if event_action_type == 'addition':
        notes = 'Deposit {amount} {asset} to {counterparty} LP {pool_address}'
        from_event_type = (HistoryEventType.SPEND, HistoryEventSubType.NONE)
        to_event_type = (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)
    else:  # can only be 'removal'
        notes = 'Remove {amount} {asset} from {counterparty} LP {pool_address}'
        from_event_type = (HistoryEventType.RECEIVE, HistoryEventSubType.NONE)
        to_event_type = (HistoryEventType.WITHDRAWAL, HistoryEventSubType.REMOVE_ASSET)

    # First, get the tokens deposited into the pool. The reason for this approach is
    # to circumvent scenarios where the mint/burn event comes before the needed transfer events.
    for other_log in all_logs:
        if other_log.topics[0] == ERC20_OR_ERC721_TRANSFER and hex_or_bytes_to_int(other_log.data[:32]) == amount0_raw:  # noqa: E501
            token0 = get_or_create_evm_token(
                userdb=database,
                evm_address=other_log.address,
                chain_id=ChainID.ETHEREUM,
                token_kind=EvmTokenKind.ERC20,
                evm_inquirer=ethereum_inquirer,
                seen=TokenSeenAt(tx_hash=tx_hash),
            )
            token0 = resolved_eth if token0 == A_WETH else token0
        elif other_log.topics[0] == ERC20_OR_ERC721_TRANSFER and hex_or_bytes_to_int(other_log.data[:32]) == amount1_raw:  # noqa: E501
            token1 = get_or_create_evm_token(
                userdb=database,
                evm_address=other_log.address,
                chain_id=ChainID.ETHEREUM,
                token_kind=EvmTokenKind.ERC20,
                evm_inquirer=ethereum_inquirer,
                seen=TokenSeenAt(tx_hash=tx_hash),
            )
            token1 = resolved_eth if token1 == A_WETH else token1

    if token0 is None or token1 is None:
        return DEFAULT_DECODING_OUTPUT

    amount0 = asset_normalized_value(amount0_raw, token0)
    amount1 = asset_normalized_value(amount1_raw, token1)

    # Second, find already decoded events of the transfers and store the id to mutate after
    # confirmation that it is indeed Uniswap V2 like Pool.
    for idx, event in enumerate(decoded_events):
        resolved_asset = event.asset.resolve_to_crypto_asset()
        if (
            event.event_type == from_event_type[0] and
            event.event_subtype == from_event_type[1] and
            resolved_asset == token0 and
            event.balance.amount == asset_normalized_value(amount0_raw, resolved_asset)
        ):
            event0_idx = idx

        elif (
            event.event_type == from_event_type[0] and
            event.event_subtype == from_event_type[1] and
            resolved_asset == token1 and
            event.balance.amount == asset_normalized_value(amount1_raw, resolved_asset)
        ):
            event1_idx = idx

    # Finally, determine the pool address from the pair of token addresses, if it matches
    # the one found earlier, mutate the decoded event or create an action item where necessary.
    pool_address = _compute_uniswap_v2_like_pool_address(
        token0=token0,
        token1=token1,
        factory_address=factory_address,
        init_code_hash=init_code_hash,
    )

    new_action_items = []
    if pool_address == target_pool_address:
        for asset, decoded_event_idx, amount in [(token0, event0_idx, amount0), (token1, event1_idx, amount1)]:  # noqa: E501
            if decoded_event_idx is None:
                action_item = ActionItem(
                    action='transform',
                    sequence_index=tx_log.log_index,
                    from_event_type=from_event_type[0],
                    from_event_subtype=from_event_type[1],
                    asset=asset,
                    amount=amount,
                    to_event_type=to_event_type[0],
                    to_event_subtype=to_event_type[1],
                    to_notes=notes.format(
                        amount=amount,
                        asset=asset.symbol,
                        counterparty=counterparty,
                        pool_address=pool_address,
                    ),
                    to_counterparty=counterparty,
                )
                new_action_items.append(action_item)
                continue

            decoded_events[decoded_event_idx].counterparty = counterparty
            decoded_events[decoded_event_idx].event_type = to_event_type[0]
            decoded_events[decoded_event_idx].event_subtype = to_event_type[1]
            decoded_events[decoded_event_idx].notes = notes.format(
                amount=amount,
                asset=asset.symbol,
                counterparty=counterparty,
                pool_address=pool_address,
            )

    return DecodingOutput(action_items=new_action_items)


def enrich_uniswap_v2_like_lp_tokens_transfers(
        context: EnricherContext,
        counterparty: str,
        lp_token_symbol: Literal['UNI-V2', 'SLP'],
) -> TransferEnrichmentOutput:
    """This function enriches LP tokens transfers of Uniswap V2 like AMMs."""
    resolved_asset = context.event.asset.resolve_to_crypto_asset()
    if (
        resolved_asset.symbol == lp_token_symbol and
        context.event.event_type == HistoryEventType.RECEIVE and
        context.event.event_subtype == HistoryEventSubType.NONE and
        context.event.address == ZERO_ADDRESS
    ):
        context.event.counterparty = counterparty
        context.event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
        context.event.notes = f'Receive {context.event.balance.amount} {resolved_asset.symbol} from {counterparty} pool'  # noqa: E501
        return TransferEnrichmentOutput(matched_counterparty=counterparty)

    if (
        resolved_asset.symbol == lp_token_symbol and
        context.event.event_type == HistoryEventType.SPEND and
        context.event.event_subtype == HistoryEventSubType.NONE and
        context.event.address == context.tx_log.address  # the recipient of the transfer is the pool  # noqa: E501
    ):
        context.event.counterparty = counterparty
        context.event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
        context.event.notes = f'Send {context.event.balance.amount} {resolved_asset.symbol} to {counterparty} pool'  # noqa: E501
        return TransferEnrichmentOutput(matched_counterparty=counterparty)

    return FAILED_ENRICHMENT_OUTPUT


def _compute_uniswap_v2_like_pool_address(
        token0: CryptoAsset,
        token1: CryptoAsset,
        factory_address: ChecksumEvmAddress,
        init_code_hash: str,
) -> ChecksumEvmAddress:
    """
    Compute the pool address for Uniswap V2 like AMMs using CREATE2.
    In case of an error, zero address is returned.
    """
    try:
        token0 = A_WETH.resolve_to_evm_token() if token0 == A_ETH else token0.resolve_to_evm_token()  # noqa: E501
        token1 = A_WETH.resolve_to_evm_token() if token1 == A_ETH else token1.resolve_to_evm_token()  # noqa: E501
    except WrongAssetType:
        return ZERO_ADDRESS

    try:
        return generate_address_via_create2(
            address=factory_address,
            salt=Web3.toHex(Web3.solidityKeccak(  # pylint: disable=no-value-for-parameter
                abi_types=['address', 'address'],
                values=[token0.evm_address, token1.evm_address],
            )),
            init_code=init_code_hash,
            is_init_code_hashed=True,
        )
    except DeserializationError:
        return ZERO_ADDRESS
