import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Final, Literal

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, get_decimals
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_DECODING_OUTPUT, DecodingOutput
from rotkehlchen.chain.evm.decoding.types import get_versioned_counterparty_label
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V2, CPT_UNISWAP_V3
from rotkehlchen.chain.evm.decoding.uniswap.v4.constants import V4_SWAP_TOPIC
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import evm_address_to_identifier, tokenid_to_collectible_id
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import InputError, NotERC20Conformant, NotERC721Conformant
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import Price, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import CryptoAsset
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

POW_96: Final = FVal(2**96)
LOG_PRICE: Final = FVal('1.0001')


def decode_basic_uniswap_info(
        amount_sent: int,
        amount_received: int,
        decoded_events: list['EvmEvent'],
        counterparty: str,
        notify_user: Callable[['EvmEvent', str], None],
        native_currency: 'CryptoAsset',
) -> DecodingOutput:
    """
    Check last three events and if they are related to the swap, label them as such.
    We check three events because potential events are: spend, (optionally) approval, receive.
    Earlier events are not related to the current swap.
    """
    display_name = get_versioned_counterparty_label(counterparty)
    spend_event, approval_event, receive_event = None, None, None
    for event in reversed(decoded_events):
        try:
            crypto_asset = event.asset.resolve_to_crypto_asset()
        except (UnknownAsset, WrongAssetType):
            notify_user(event, counterparty)
            return DEFAULT_DECODING_OUTPUT

        if (
            event.event_type == HistoryEventType.INFORMATIONAL and
            event.event_subtype == HistoryEventSubType.APPROVE and
            approval_event is None
        ):
            approval_event = event
        elif (
            event.amount == asset_normalized_value(amount=amount_sent, asset=crypto_asset) and
            event.event_type == HistoryEventType.SPEND and
            # don't touch native asset since there may be multiple such transfers
            # and they are better handled by the aggregator decoder.
            event.asset != native_currency and
            spend_event is None
        ):
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.SPEND
            event.counterparty = counterparty
            event.notes = f'Swap {event.amount} {crypto_asset.symbol} in {display_name}'
            spend_event = event
        elif (
            event.amount == asset_normalized_value(amount=amount_received, asset=crypto_asset) and
            event.event_type == HistoryEventType.RECEIVE and
            event.asset != native_currency and
            receive_event is None
        ):
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.RECEIVE
            event.counterparty = counterparty
            event.notes = f'Receive {event.amount} {crypto_asset.symbol} as a result of a {display_name} swap'  # noqa: E501
            receive_event = event
        elif (
            event.counterparty in {CPT_UNISWAP_V2, CPT_UNISWAP_V3} and
            event.event_type == HistoryEventType.TRADE
        ):
            # The structure of swaps is the following:
            # 1.1 Optional approval event
            # 1.2 Optional spend event
            # 1.3 Optional receive event
            # 1.4 SWAP_SIGNATURE event
            # 2.1 Optional approval event
            # 2.2 Optional spend event
            # 2.3 Optional receive event
            # 2.4 SWAP_SIGNATURE event
            # etc.
            # So if we are at SWAP_SIGNATURE № 2 then all events that are before SWAP_SIGNATURE № 1
            # should have already been decoded, have counterparty set and have type Trade.
            break
        else:  # If what described in the comment above is not met then it is an error.
            log.debug(
                f'Found unexpected event {event.serialize()} during decoding a uniswap swap in '
                f'transaction {event.tx_hash.hex()}. Either uniswap router or an aggregator was '
                f'used and decoding needs to happen in the aggregator-specific decoder.',
            )
            break

    # Make sure that the approval event is NOT between the spend and receive events.
    maybe_reshuffle_events(
        ordered_events=[approval_event, spend_event, receive_event],
        events_list=decoded_events,
    )
    return DecodingOutput(process_swaps=True)


def get_uniswap_swap_amounts(tx_log: 'EvmTxReceiptLog') -> tuple[int, int]:
    """Get the amount received and amount sent in a swap from the swap tx_log.

    Uniswap represents the delta of tokens in the pool with a signed integer.
    In V3 the negative delta indicates the amount leaving the pool (the user receives them),
    and positive indicates the amount entering the pool (the user sends them to the pool).
    In V4 this is reversed - negative indicates the amount entering the pool (sent by the user),
    and positive indicates the amount leaving the pool (received by the user).

    The caller is responsible for only calling this function with a swap tx_log.
    Returns a tuple of (amount_received, amount_sent).
    """
    delta_token_0 = int.from_bytes(tx_log.data[0:32], signed=True)
    delta_token_1 = int.from_bytes(tx_log.data[32:64], signed=True)
    if delta_token_0 > 0:
        amount_a, amount_b = delta_token_0, -delta_token_1
    else:
        amount_a, amount_b = delta_token_1, -delta_token_0

    if tx_log.topics[0] == V4_SWAP_TOPIC:
        return amount_a, amount_b

    return amount_b, amount_a  # V3


def calculate_sqrt_price(tick: int) -> FVal:
    """Calculate sqrt price from tick."""
    return LOG_PRICE ** (FVal(tick) / 2) * POW_96


def calculate_amount(
        tick_sqrt: FVal,
        tick_lower_sqrt: FVal,
        tick_upper_sqrt: FVal,
        liquidity: int,
        decimals: int,
        token_position: Literal[0, 1],
) -> FVal:
    """Calculates the amount of a token in the Uniswap LP position.
    `token_position` can either be 0 or 1 representing the position of the token in a pair.
    """
    if token_position == 0:
        amount = (liquidity * POW_96 * (tick_upper_sqrt - tick_sqrt) / (tick_upper_sqrt * tick_sqrt)) / 10**decimals  # noqa: E501
    else:  # token_position == 1
        amount = liquidity * (tick_sqrt - tick_lower_sqrt) / POW_96 / 10**decimals

    return FVal(amount)


def get_position_price_from_underlying(
        evm_inquirer: 'EvmNodeInquirer',
        token0_raw_address: str,
        token1_raw_address: str,
        tick_lower: int,
        tick_upper: int,
        liquidity: int,
        tick: int,
        price_func: Callable[['Asset'], Price],
) -> Price:
    """Get a Uniswap LP position's price from its underlying assets and tick/liquidity info.
    price_func is passed to avoid circular imports as well as allowing this function to be used
    for either current or historical prices.
    """
    tick_sqrt = calculate_sqrt_price(max(min(tick, tick_upper), tick_lower))
    tick_lower_sqrt = calculate_sqrt_price(tick_lower)
    tick_upper_sqrt = calculate_sqrt_price(tick_upper)
    position_price = ZERO
    for idx, raw_token_address in enumerate((token0_raw_address, token1_raw_address)):
        try:
            token_address = deserialize_evm_address(raw_token_address)
        except DeserializationError as e:
            log.error(
                f'Encountered invalid address {raw_token_address} while '
                f'getting Uniswap LP position price on {evm_inquirer.chain_name}. {e!s}',
            )
            return ZERO_PRICE

        try:
            underlying_asset = get_or_create_evm_token(
                userdb=evm_inquirer.database,
                evm_inquirer=evm_inquirer,
                evm_address=deserialize_evm_address(token_address),
                chain_id=evm_inquirer.chain_id,
            ) if token_address != ZERO_ADDRESS else evm_inquirer.native_token
        except (NotERC20Conformant, NotERC721Conformant, InputError) as e:
            log.error(
                f'Failed to fetch {evm_inquirer.chain_name} token {token_address} while '
                f'getting Uniswap LP position price due to: {e!s}',
            )
            return ZERO_PRICE

        if (asset_usd_price := price_func(underlying_asset)) == ZERO_PRICE:
            continue

        position_price += calculate_amount(
            tick_sqrt=tick_sqrt,
            tick_lower_sqrt=tick_lower_sqrt,
            tick_upper_sqrt=tick_upper_sqrt,
            liquidity=liquidity,
            decimals=get_decimals(underlying_asset),
            token_position=idx,  # type: ignore  # idx will only be 0 or 1
        ) * asset_usd_price

    return Price(position_price)


def decode_uniswap_v3_like_position_create_or_exit(
        decoded_events: list['EvmEvent'],
        evm_inquirer: 'EvmNodeInquirer',
        nft_manager: 'ChecksumEvmAddress',
        counterparty: str,
        token_symbol: str,
        token_name: str,
) -> list['EvmEvent']:
    """Decode Uniswap V3 like position create/exit events.
    Args:
        decoded_events: the list of decoded events to process.
        evm_inquirer: the evm node inquirer.
        nft_manager: the address of the NFT manager contract.
        counterparty: the counterparty to use for the events.
        token_symbol: the symbol to set for the token. Will have the position id appended to it,
            so if `UNI-V3-POS` is specified, then it will be something like `UNI-V3-POS-1234`.
        token_name: the name to set for the token. Will also have the position id appended to it,
            so if `Uniswap V3 Positions` is specified, it will be `Uniswap V3 Positions #1234`.
    """
    deposit_events, withdrawal_events, receive_events, return_events = [], [], [], []
    for event in decoded_events:
        if (
            event.event_type in (HistoryEventType.SPEND, HistoryEventType.RECEIVE) and
            event.event_subtype == HistoryEventSubType.NONE and
            event.address == ZERO_ADDRESS and
            event.amount == ONE and
            (position_id := tokenid_to_collectible_id(
                identifier=event.asset.identifier,
            )) is not None and
            event.asset == Asset(evm_address_to_identifier(
                address=nft_manager,
                chain_id=evm_inquirer.chain_id,
                token_type=TokenKind.ERC721,
                collectible_id=position_id,
            ))
        ):
            if event.event_type == HistoryEventType.SPEND:
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                verb = 'Exit'
                return_events.append(event)
            else:  # HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                verb = 'Create'
                receive_events.append(event)
                # Update the position token's protocol, name, and symbol.
                # Appends the position id to the specified token name and symbol.
                get_or_create_evm_token(
                    userdb=evm_inquirer.database,
                    evm_address=nft_manager,
                    chain_id=evm_inquirer.chain_id,
                    token_kind=TokenKind.ERC721,
                    symbol=f'{token_symbol}-{position_id}',
                    name=f'{token_name} #{position_id}',
                    collectible_id=position_id,
                    protocol=counterparty,
                )

            event.counterparty = counterparty
            event.notes = f'{verb} {get_versioned_counterparty_label(counterparty)} LP with id {position_id}'  # noqa: E501
        elif event.counterparty == counterparty:
            if (
                    event.event_type == HistoryEventType.DEPOSIT and
                    event.event_subtype == HistoryEventSubType.DEPOSIT_ASSET
            ):
                deposit_events.append(event)
            elif (
                    event.event_type == HistoryEventType.WITHDRAWAL and
                    event.event_subtype == HistoryEventSubType.REMOVE_ASSET
            ):
                withdrawal_events.append(event)

    # Convert the deposit/withdrawal event subtypes to deposit_for_wrapped/redeem_wrapped
    # if there is a corresponding receive_wrapped/return_wrapped event
    for receive_returns, deposit_withdraws, subtype in (
            (receive_events, deposit_events, HistoryEventSubType.DEPOSIT_FOR_WRAPPED),
            (return_events, withdrawal_events, HistoryEventSubType.REDEEM_WRAPPED),
    ):
        if len(receive_returns) == 0 or len(deposit_withdraws) == 0:
            continue

        for event in deposit_withdraws:
            event.event_subtype = subtype

    maybe_reshuffle_events(
        ordered_events=return_events + deposit_events + withdrawal_events + receive_events,
        events_list=decoded_events,
    )
    return decoded_events
