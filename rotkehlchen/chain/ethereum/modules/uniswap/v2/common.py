import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

from eth_utils import to_hex
from web3 import Web3

from rotkehlchen.assets.asset import Asset, CryptoAsset, EvmToken, UnderlyingToken
from rotkehlchen.assets.utils import (
    TokenEncounterInfo,
    edit_token_and_clean_cache,
    get_or_create_evm_token,
)
from rotkehlchen.chain.ethereum.modules.constants import AMM_ASSETS_SYMBOLS
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, generate_address_via_create2
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V2
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.constants.resolver import ChainID
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import NotERC20Conformant
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    SUSHISWAP_PROTOCOL,
    UNISWAP_PROTOCOL,
    ChecksumEvmAddress,
    EvmTransaction,
    EVMTxHash,
    TokenKind,
)
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.evm_event import EvmEvent

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
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
        token_kind=TokenKind.ERC20,
        evm_inquirer=ethereum_inquirer,
        encounter=TokenEncounterInfo(tx_hash=transaction.tx_hash),
    )

    if pool_token.symbol in exclude_amms.values():
        # If the symbol for the current counterparty matches the expected symbol for another
        # counterparty skip the decoding using this rule.
        return DEFAULT_DECODING_OUTPUT

    # When the router chains multiple swaps in one transaction only the last swap has
    # the buyer in the topic. In that case we know it is the last swap and the receiver is
    # the user
    maybe_buyer = bytes_to_address(tx_log.topics[2])
    out_event = in_event = None

    # amount_in is the amount that enters the pool and amount_out the one
    # that leaves the pool
    amount_in_0, amount_in_1 = int.from_bytes(tx_log.data[0:32]), int.from_bytes(tx_log.data[32:64])  # noqa: E501
    amount_out_0, amount_out_1 = int.from_bytes(tx_log.data[64:96]), int.from_bytes(tx_log.data[96:128])  # noqa: E501
    amount_in, amount_out = amount_in_0, amount_out_0
    if amount_in == ZERO:
        amount_in = amount_in_1
    if amount_out == ZERO:
        amount_out = amount_out_1

    received_eth = ZERO
    for event in decoded_events:
        if event.asset == A_ETH and event.event_type == HistoryEventType.RECEIVE:
            received_eth += event.amount

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
                event.amount == (spend_eth := asset_normalized_value(
                    amount=amount_in,
                    asset=crypto_asset,
                )) or
                (event.asset == A_ETH and spend_eth + received_eth == event.amount)
            )
        ):
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.SPEND
            event.counterparty = counterparty
            event.notes = f'Swap {event.amount} {crypto_asset.symbol} in {counterparty} from {event.location_label}'  # noqa: E501
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
            event.amount == asset_normalized_value(
                amount=amount_out,
                asset=crypto_asset,
            )
        ):
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.RECEIVE
            event.counterparty = counterparty
            event.notes = f'Receive {event.amount} {crypto_asset.symbol} in {counterparty} from {event.location_label}'  # noqa: E501
            in_event = event
        elif (
            event.event_type == HistoryEventType.RECEIVE and
            event.amount != asset_normalized_value(
                amount=amount_out,
                asset=crypto_asset,
            ) and
            event.asset == A_ETH and
            transaction.from_address == event.location_label and
            event.address in (SUSHISWAP_ROUTER, UNISWAP_V2_ROUTER)
        ):
            # this is to make sure it's the amm issuing the refund and not an aggregator making a swap  # noqa: E501
            # Those are assets returned due to a change in the swap price
            event.event_type = HistoryEventType.WITHDRAWAL
            event.event_subtype = HistoryEventSubType.REFUND
            event.counterparty = counterparty
            event.notes = f'Refund of {event.amount} {crypto_asset.symbol} in {counterparty} due to price change'  # noqa: E501

    maybe_reshuffle_events(ordered_events=[out_event, in_event], events_list=decoded_events)
    return DecodingOutput(process_swaps=True)


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
    https://etherscan.io/tx/0x00007120e5281e9bdf9a57739e3ecaf736013e4a1a31ecfe44f719c229cc2cbd (withdrawal of weth)
    """  # noqa: E501
    resolved_eth = A_ETH.resolve_to_crypto_asset()
    target_pool_address = tx_log.address
    amount0_raw = int.from_bytes(tx_log.data[:32])
    amount1_raw = int.from_bytes(tx_log.data[32:64])

    token0: EvmToken | None = None
    token1: EvmToken | None = None
    asset_0: Asset | None = None
    asset_1: Asset | None = None
    event0_idx = event1_idx = None

    if event_action_type == 'addition':
        notes = 'Deposit {amount} {asset} to {counterparty} LP {pool_address}'
        from_event_type = (HistoryEventType.SPEND, HistoryEventSubType.NONE)
        to_event_type = (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_FOR_WRAPPED)
    else:  # can only be 'removal'
        notes = 'Remove {amount} {asset} from {counterparty} LP {pool_address}'
        from_event_type = (HistoryEventType.RECEIVE, HistoryEventSubType.NONE)
        to_event_type = (HistoryEventType.WITHDRAWAL, HistoryEventSubType.REDEEM_WRAPPED)

    # First, get the tokens deposited into the pool. The reason for this approach is
    # to circumvent scenarios where the mint/burn event comes before the needed transfer events.
    for other_log in all_logs:
        if other_log.topics[0] == ERC20_OR_ERC721_TRANSFER and int.from_bytes(other_log.data[:32]) == amount0_raw:  # noqa: E501
            token0 = get_or_create_evm_token(
                userdb=database,
                evm_address=other_log.address,
                chain_id=ChainID.ETHEREUM,
                token_kind=TokenKind.ERC20,
                evm_inquirer=ethereum_inquirer,
                encounter=TokenEncounterInfo(tx_hash=tx_hash),
            )
            # we make a distinction between token and asset since for eth uniswap moves around
            # WETH but we could receive ETH
            asset_0 = resolved_eth if token0 == A_WETH else token0
        elif other_log.topics[0] == ERC20_OR_ERC721_TRANSFER and int.from_bytes(other_log.data[:32]) == amount1_raw:  # noqa: E501
            token1 = get_or_create_evm_token(
                userdb=database,
                evm_address=other_log.address,
                chain_id=ChainID.ETHEREUM,
                token_kind=TokenKind.ERC20,
                evm_inquirer=ethereum_inquirer,
                encounter=TokenEncounterInfo(tx_hash=tx_hash),
            )
            asset_1 = resolved_eth if token1 == A_WETH else token1

    if token0 is None or token1 is None or asset_0 is None or asset_1 is None:
        return DEFAULT_DECODING_OUTPUT

    # determine the pool address from the pair of token addresses, if it matches
    # the one found earlier, mutate the decoded event or create an action item where necessary.
    pool_address = _compute_uniswap_v2_like_pool_address(
        token0=token0,
        token1=token1,
        factory_address=factory_address,
        init_code_hash=init_code_hash,
    )
    if pool_address != target_pool_address:  # we didn't find the correct pool
        return DEFAULT_DECODING_OUTPUT

    amount0 = asset_normalized_value(amount0_raw, token0)
    amount1 = asset_normalized_value(amount1_raw, token1)
    underlying_tokens = [
        UnderlyingToken(address=token0.evm_address, token_kind=TokenKind.ERC20, weight=FVal(0.5)),
        UnderlyingToken(address=token1.evm_address, token_kind=TokenKind.ERC20, weight=FVal(0.5)),
    ]

    try:
        token_is_uniswap_v2_lp = counterparty == CPT_UNISWAP_V2
        pool_token = get_or_create_evm_token(
            userdb=database,
            evm_address=pool_address,
            chain_id=ChainID.ETHEREUM,
            token_kind=TokenKind.ERC20,
            evm_inquirer=ethereum_inquirer,
            encounter=TokenEncounterInfo(tx_hash=tx_hash),
            underlying_tokens=underlying_tokens,
            protocol=UNISWAP_PROTOCOL if token_is_uniswap_v2_lp else None,
        )

        symbol = pool_token.symbol
        if symbol in {UNISWAP_PROTOCOL, SUSHISWAP_PROTOCOL}:
            # uniswap and sushiswap provide the same symbol for all the LP tokens. In order to
            # provide a better UX if the default symbol is used then change the symbol to
            # include the symbols of the underlying tokens.
            symbol = f'{symbol} {token0.symbol}-{token1.symbol}'

        edit_token_and_clean_cache(
            evm_inquirer=None,  # we don't need to query again information from chain
            evm_token=pool_token,
            name=pool_token.name,
            symbol=symbol,
            decimals=pool_token.decimals,
            started=pool_token.started,
            underlying_tokens=underlying_tokens,
        )
    except NotERC20Conformant:
        log.error(
            f'Failed to create the pool token since it does not conform to ERC20. '
            f'expected: {pool_address} for {token0.evm_address}-{token1.evm_address}',
        )
        return DEFAULT_DECODING_OUTPUT

    # find already decoded events of the transfers and store the id to mutate after
    # confirmation that it is indeed Uniswap V2 like Pool.
    for idx, event in enumerate(decoded_events):
        resolved_asset = event.asset.resolve_to_crypto_asset()
        if (
            event.event_type == from_event_type[0] and
            event.event_subtype == from_event_type[1] and
            (resolved_asset in (asset_0, token0)) and
            event.amount == asset_normalized_value(amount0_raw, resolved_asset)
        ):
            asset_0 = resolved_asset  # here we know exactly if it is ETH or WETH (or any other asset) so assign the asset  # noqa: E501
            event0_idx = idx
        elif (
            event.event_type == from_event_type[0] and
            event.event_subtype == from_event_type[1] and
            (resolved_asset in (asset_1, token1)) and
            event.amount == asset_normalized_value(amount1_raw, resolved_asset)
        ):
            asset_1 = resolved_asset
            event1_idx = idx
        elif (
            resolved_asset == pool_token and
            event.event_type == HistoryEventType.RECEIVE and
            event.event_subtype == HistoryEventSubType.NONE and
            event.address == ZERO_ADDRESS
        ):
            event.counterparty = counterparty
            event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
            event.notes = f'Receive {event.amount} {resolved_asset.symbol} from {counterparty} pool'  # noqa: E501
            GlobalDBHandler.set_token_protocol_if_missing(
                token=event.asset.resolve_to_evm_token(),
                new_protocol=UNISWAP_PROTOCOL if resolved_asset.symbol.startswith('UNI-V2') else SUSHISWAP_PROTOCOL,  # noqa: E501
            )
        elif (
            resolved_asset == pool_token and
            event.event_type == HistoryEventType.SPEND and
            event.event_subtype == HistoryEventSubType.NONE and
            event.address == tx_log.address  # the recipient of the transfer is the pool  # noqa: E501
        ):
            event.counterparty = counterparty
            event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
            event.notes = f'Send {event.amount} {resolved_asset.symbol} to {counterparty} pool'

    new_action_items = []
    extra_data = {'pool_address': pool_address}
    for asset, decoded_event_idx, amount in ((asset_0, event0_idx, amount0), (asset_1, event1_idx, amount1)):  # noqa: E501
        asset_symbol = asset.resolve_to_asset_with_symbol().symbol
        if decoded_event_idx is None:
            action_item = ActionItem(
                action='transform',
                from_event_type=from_event_type[0],
                from_event_subtype=from_event_type[1],
                asset=asset,
                amount=amount,
                to_event_type=to_event_type[0],
                to_event_subtype=to_event_type[1],
                to_notes=notes.format(
                    amount=amount,
                    asset=asset_symbol,
                    counterparty=counterparty,
                    pool_address=pool_address,
                ),
                to_counterparty=counterparty,
                extra_data=extra_data,
            )
            new_action_items.append(action_item)
            continue

        decoded_events[decoded_event_idx].counterparty = counterparty
        decoded_events[decoded_event_idx].event_type = to_event_type[0]
        decoded_events[decoded_event_idx].event_subtype = to_event_type[1]
        decoded_events[decoded_event_idx].notes = notes.format(
            amount=amount,
            asset=asset_symbol,
            counterparty=counterparty,
            pool_address=pool_address,
        )
        decoded_events[decoded_event_idx].extra_data = extra_data

    return DecodingOutput(action_items=new_action_items)


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
            salt=to_hex(Web3.solidity_keccak(  # pylint: disable=no-value-for-parameter
                abi_types=['address', 'address'],
                values=[token0.evm_address, token1.evm_address],
            )),
            init_code=init_code_hash,
            is_init_code_hashed=True,
        )
    except DeserializationError:
        return ZERO_ADDRESS
