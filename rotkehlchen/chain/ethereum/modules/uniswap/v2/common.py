from typing import TYPE_CHECKING, List
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.modules.constants import AMM_ASSETS_SYMBOLS
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import ChainID
from rotkehlchen.types import EvmTokenKind, EvmTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler


def decode_uniswap_v2_like_swap(
        tx_log: EthereumTxReceiptLog,
        decoded_events: List[HistoryBaseEntry],
        transaction: EvmTransaction,
        counterparty: str,
        database: 'DBHandler',
        ethereum_manager: 'EthereumManager',
) -> None:
    """Common logic for decoding uniswap v2 like protocols (uniswap and sushiswap atm)

    Decode trade for uniswap v2 like amm. The approach is to read the events and detect the ones
    where the user sends and receives any asset. The spend asset is the swap executed and
    the received is the result of calling the swap method in the uniswap contract.
    We need to make sure that the events related to the swap are consecutive and for that
    we make use of the maybe_reshuffle_events() function.

    This method will identifiy the correct counterparty using the argument provided and a call to
    get_or_create_evm_token. This call is needed to retrieve the symbol of the pool and determine
    if the pool is from the selected counterparty.
    """

    exclude_amms = dict(AMM_ASSETS_SYMBOLS)
    exclude_amms.pop(counterparty)
    pool_token = get_or_create_evm_token(
        userdb=database,
        evm_address=tx_log.address,
        chain=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        ethereum_manager=ethereum_manager,
    )

    if pool_token.symbol in exclude_amms.values():
        # If the symbol for the current counterparty matches the expected symbol for another
        # counterparty skip the decoding using this rule.
        return

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
        crypto_asset = event.asset.resolve_to_crypto_asset()
        if (
            event.event_type == HistoryEventType.SPEND and
            (
                event.balance.amount == (spend_eth := asset_normalized_value(amount_in, event.asset)) or  # noqa: E501
                event.asset == A_ETH and spend_eth + received_eth == event.balance.amount
            )
        ):
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.SPEND
            event.counterparty = counterparty
            event.notes = f'Swap {event.balance.amount} {crypto_asset.symbol} in {counterparty} from {event.location_label}'  # noqa: E501
            out_event = event
        elif (
            (maybe_buyer == transaction.from_address or event.asset == A_ETH) and
            event.event_type in (HistoryEventType.RECEIVE, HistoryEventType.TRANSFER) and
            event.balance.amount == asset_normalized_value(amount_out, event.asset)
        ):
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.RECEIVE
            event.counterparty = counterparty
            event.notes = f'Receive {event.balance.amount} {crypto_asset.symbol} in {counterparty} from {event.location_label}'  # noqa: E501
            in_event = event
        elif (
            event.event_type == HistoryEventType.RECEIVE and
            event.balance.amount != asset_normalized_value(amount_out, event.asset) and
            event.asset == A_ETH and transaction.from_address == event.location_label
        ):
            # Those are assets returned due to a change in the swap price
            event.event_type = HistoryEventType.TRANSFER
            event.counterparty = counterparty
            event.notes = f'Refund of {event.balance.amount} {crypto_asset.symbol} in {counterparty} due to price change'  # noqa: E501

    maybe_reshuffle_events(out_event=out_event, in_event=in_event)
