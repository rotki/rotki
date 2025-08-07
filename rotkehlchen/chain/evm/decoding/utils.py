import logging
from collections.abc import Callable, Iterable, Sequence
from typing import TYPE_CHECKING, Any, Literal, Optional

from eth_typing import ABI

from rotkehlchen.assets.asset import AssetWithSymbol
from rotkehlchen.assets.utils import get_token
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.utils import maybe_notify_cache_query_status
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.misc import (
    InputError,
    NotERC20Conformant,
    NotERC721Conformant,
    RemoteError,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, Price, Timestamp, UniqueCacheType

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.inquirer import Inquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def maybe_reshuffle_events(
        ordered_events: Sequence[Optional['EvmEvent']],
        events_list: list['EvmEvent'],
) -> None:
    """Takes a list of events to order and makes sure that the sequence index of each
    of them is in ascending order and that the events are consecutive in the
    decoded events list.

    This is for two reasons.
    1. So that it appears uniformly in the UI
    2. So that during accounting we know which type of event comes first in a swap-like event.

    For example for swaps we expect two consecutive events with the first
    being the out event and the second the in event,

    The events are optional since it's also possible they may not be found.
    """
    actual_events = [x for x in ordered_events if x is not None]
    if len(actual_events) <= 1:
        return  # nothing to do

    all_other_events = []
    max_seq_index = -1
    for event in events_list:
        if event not in actual_events:
            all_other_events.append(event)
            max_seq_index = max(event.sequence_index, max_seq_index)

    for idx, event in enumerate(actual_events):
        event.sequence_index = max_seq_index + idx + 1
    events_list = all_other_events + actual_events


def bridge_prepare_data(
        tx_log: 'EvmTxReceiptLog',
        deposit_topics: Sequence[bytes],
        source_chain: ChainID,
        target_chain: ChainID,
        from_address: ChecksumEvmAddress,
        to_address: ChecksumEvmAddress,
) -> tuple[HistoryEventType, HistoryEventType, ChainID, ChainID, ChecksumEvmAddress]:
    """Method to prepare the bridge variables

    `source_chain` is the chain where the current transaction is happening
    `target_chain` is the chain on the other side of the bridge

    When coming here the caller has to make sure that:
    - tx_log topics is either in deposit_topics or else is a withdrawal
    """
    # Determine whether it is a deposit or a withdrawal
    if tx_log.topics[0] in deposit_topics:
        expected_event_type = HistoryEventType.SPEND
        expected_location_label = from_address
        new_event_type = HistoryEventType.DEPOSIT
        from_chain, to_chain = source_chain, target_chain
    else:  # withdrawal
        expected_event_type = HistoryEventType.RECEIVE
        expected_location_label = to_address
        new_event_type = HistoryEventType.WITHDRAWAL
        from_chain, to_chain = target_chain, source_chain

    return expected_event_type, new_event_type, from_chain, to_chain, expected_location_label


def bridge_match_transfer(
        event: 'EvmEvent',
        from_address: ChecksumEvmAddress,
        to_address: ChecksumEvmAddress,
        from_chain: ChainID,
        to_chain: ChainID,
        amount: FVal,
        asset: AssetWithSymbol,
        expected_event_type: HistoryEventType,
        new_event_type: HistoryEventType,
        counterparty: CounterpartyDetails,
) -> None:
    """Action to take when matching a bridge transfer event"""
    from_label, to_label = f' address {from_address}', f' address {to_address}'
    if expected_event_type == HistoryEventType.SPEND:
        if event.location_label == from_address:
            from_label = ''
        if to_address == from_address:
            to_label = ''
    elif expected_event_type == HistoryEventType.RECEIVE:
        if event.location_label == to_address:
            to_label = ''
        if to_address == from_address:
            from_label = ''

    event.event_type = new_event_type
    event.event_subtype = HistoryEventSubType.BRIDGE
    event.counterparty = counterparty.identifier
    event.notes = (
        f'Bridge {amount} {asset.symbol} from {from_chain.label()}{from_label} to '
        f'{to_chain.label()}{to_label} via {counterparty.label} bridge'
    )


def _update_cache_vault_count(
        cache_key: Iterable[str | UniqueCacheType],
        count: int | None = None,
) -> None:
    """Update the count for the specified cache type."""
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_unique_cache_value(
            write_cursor=write_cursor,
            key_parts=cache_key,
            value=str(count) if count is not None else '0',
        )


def update_cached_vaults(
        database: 'DBHandler',
        display_name: str,
        chain: ChainID,
        cache_key: Iterable[str | UniqueCacheType],
        query_vaults: Callable[..., list[dict[str, Any]] | None],
        process_vault: Callable[['DBHandler', dict[str, Any]], None],
) -> None:
    """Update vaults in the cache using the specified query and processing functions.
    Args:
        database (DBHandler): Database to be used when processing vaults.
        display_name (str): Name to use when logging errors.
        cache_key (Iterable[str | UniqueCacheType]): Cache keys used to store vault data.
        query_vaults (Callable): Function to fetch vault data from API or chain.
            Returns a list of vault data dicts or None on error.
        process_vault (Callable): Function to use to process the vaults.
            Must accept the following arguments: a DBHandler and a vault data dict. Returns None.
            May raise NotERC20Conformant, NotERC721Conformant, DeserializationError, and KeyError.
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        last_vault_count = globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=cache_key,
        )

    if (vault_list := query_vaults()) is None:
        _update_cache_vault_count(cache_key=cache_key)  # Update cache timestamp to prevent repeated errors.  # noqa: E501
        return

    _update_cache_vault_count(cache_key=cache_key, count=(vault_count := len(vault_list)))
    try:
        if last_vault_count is not None and vault_count == int(last_vault_count):
            log.debug(
                f'Same number ({vault_count}) of {display_name} vaults returned '
                'from remote as previous query. Skipping vault processing.',
            )
            return
    except ValueError:
        log.error(
            f'Failed to check last {display_name} vault count '
            f'due to {last_vault_count} not being an int',
        )
        return

    last_notified_ts = Timestamp(0)
    for idx, vault in enumerate(vault_list):
        try:
            process_vault(database, vault)
        except (NotERC20Conformant, NotERC721Conformant, DeserializationError, KeyError, InputError) as e:  # noqa: E501
            error = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
            log.error(
                f'Failed to store token information for {display_name} vault '
                f'due to {error}. Vault: {vault}. Skipping...',
            )

        last_notified_ts = maybe_notify_cache_query_status(
            msg_aggregator=database.msg_aggregator,
            last_notified_ts=last_notified_ts,
            protocol=display_name,
            chain=chain,
            processed=idx + 1,
            total=len(vault_list),
        )


def get_vault_price(
        inquirer: 'Inquirer',
        vault_token: 'EvmToken',
        evm_inquirer: 'EvmNodeInquirer',
        display_name: str,
        vault_abi: ABI,
        pps_method: Literal['pricePerShare', 'convertToAssets', 'getPricePerFullShare'],
        pps_method_args: list | None = None,
) -> Price:
    """Gets vault token price by multiplying price per share by the underlying token's USD price.
    Price per share is retrieved from the vault contract using the specified pps_method.
    Returns the vault token price or ZERO_PRICE on error.
    """
    try:
        price_per_share = evm_inquirer.call_contract(
            contract_address=vault_token.evm_address,
            abi=vault_abi,
            method_name=pps_method,
            arguments=pps_method_args,
        )
    except RemoteError as e:
        log.error(
            f'Failed to get price per share for {display_name} '
            f'vault {vault_token} on {evm_inquirer.chain_name}: {e}',
        )
        return ZERO_PRICE

    if (
        len(vault_token.underlying_tokens) == 0 or
        (underlying_token := get_token(
            evm_address=vault_token.underlying_tokens[0].address,
            chain_id=evm_inquirer.chain_id,
        )) is None
    ):
        log.error(
            f'Failed to get underlying token for {display_name} '
            f'vault {vault_token} on {evm_inquirer.chain_name}',
        )
        return ZERO_PRICE

    formatted_pps = token_normalized_value(
        token_amount=price_per_share,
        token=underlying_token,
    )
    return Price(inquirer.find_usd_price(asset=underlying_token) * formatted_pps)
