import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.api.websockets.typedefs import ProgressUpdateSubType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.liquity.constants import CPT_LIQUITY
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_LQTY, A_LUSD
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.price import query_price_or_use_default
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.user_messages import MessagesAggregator, WSMessageType
from rotkehlchen.utils.misc import ts_ms_to_sec

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

# This queries for events having a specific combination of asset + staking type + reward and
# being from liquity. This helps to filter if they are from the stability pool or the LQTY
# staking. Then we need to consider the rewards in other assets that appear in the same
# transaction and this is why we use the IN operator as filter.
QUERY_STAKING_EVENTS = """
WHERE group_identifier IN
(SELECT A.group_identifier FROM history_events AS A JOIN history_events AS B ON A.group_identifier = B.group_identifier
    JOIN chain_events_info AS C ON A.identifier=C.identifier WHERE C.counterparty=? AND A.asset=?
    AND B.asset=? AND B.subtype != ? AND B.type == ?
) AND type=? AND subtype=?
"""  # noqa: E501
BINDINGS_STAKING_EVENTS = [
    CPT_LIQUITY, A_LQTY.identifier, A_LUSD.identifier, HistoryEventSubType.DEPOSIT_ASSET.serialize(),  # noqa: E501
    HistoryEventType.STAKING.serialize(), HistoryEventType.STAKING.serialize(),
    HistoryEventSubType.REWARD.serialize(),
]
# stability pool rewards
QUERY_STABILITY_POOL_EVENTS = """
WHERE group_identifier IN (
    SELECT A.group_identifier FROM history_events AS A JOIN history_events AS B ON
    A.group_identifier = B.group_identifier JOIN chain_events_info AS C ON A.identifier=C.identifier
    WHERE C.counterparty = 'liquity' AND B.asset=? AND B.subtype=?
) AND type=? AND subtype=?
"""  # noqa: E501
BINDINGS_STABILITY_POOL_EVENTS = [
    A_LQTY.identifier,
    HistoryEventSubType.REWARD.serialize(),
    HistoryEventType.STAKING.serialize(),
    HistoryEventSubType.REWARD.serialize(),
]
QUERY_STABILITY_POOL_DEPOSITS = (
    'SELECT amount, timestamp, asset FROM history_events JOIN chain_events_info ON '
    'history_events.identifier=chain_events_info.identifier WHERE counterparty=? '
    'AND asset=? AND type=? AND subtype=?'
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def calculate_pool_metrics(
        cursor: 'DBCursor',
        query: str,
        bindings: Sequence[Any],
) -> tuple[FVal, FVal]:
    """Calculate total amount and value for stability pool transactions"""
    cursor.execute(query, bindings)
    total_amount, total_value = ZERO, ZERO
    for raw_amount, timestamp, asset in cursor:
        price = query_price_or_use_default(
            asset=Asset(asset),
            time=ts_ms_to_sec(timestamp),
            default_value=ZERO,
            location='stability_pool_price',
        )
        try:
            amount = deserialize_fval(
                value=raw_amount,
                name='amount',
                location='calculate_pool_metrics',
            )
        except DeserializationError:
            log.error(f'Failed to deserialize amount {raw_amount} when reading liquity events')
            continue

        total_amount += amount
        total_value += amount * price

    return total_amount, total_value


def staking_query_progress(
        msg_aggregator: MessagesAggregator,
        step: Literal[0, 1, 2, 3, 4],
) -> None:
    msg_aggregator.add_message(
        message_type=WSMessageType.PROGRESS_UPDATES,
        data={
            'total': 4,
            'processed': step,
            'subtype': str(ProgressUpdateSubType.LIQUITY_STAKING_QUERY),
        },
    )


def _get_amount_and_value_stats(
        cursor: 'DBCursor',
        history_events_db: DBHistoryEvents,
        query_staking: str,
        bindings_staking: list[Any],
        query_stability_pool: str,
        bindings_stability_pool: list[Any],
        query_stability_pool_deposits: str,
        deposit_pool_bindings: list[Any],
        withdrawal_pool_bindings: list[Any],
        msg_aggregator: MessagesAggregator,
) -> dict[str, Any]:
    """
    Query the database using the given pre-computed filters and create a report
    with all the information related to staking
    """
    staking_query_progress(msg_aggregator=msg_aggregator, step=0)
    staking_rewards_breakdown, total_value_gains_staking = history_events_db.get_amount_and_value_stats(  # noqa: E501
        cursor=cursor,
        query_filters=query_staking,
        bindings=bindings_staking,
        counterparty=CPT_LIQUITY,
    )
    staking_query_progress(msg_aggregator=msg_aggregator, step=1)
    stability_rewards_breakdown, total_value_gains_stability_pool = history_events_db.get_amount_and_value_stats(  # noqa: E501
        cursor=cursor,
        query_filters=query_stability_pool,
        bindings=bindings_stability_pool,
        counterparty=CPT_LIQUITY,
    )
    staking_query_progress(msg_aggregator=msg_aggregator, step=2)
    # get stats about LUSD deposited in the stability pool
    stability_pool_amount_deposited, stability_pool_value_deposited = calculate_pool_metrics(
        cursor=cursor,
        query=query_stability_pool_deposits,
        bindings=deposit_pool_bindings,
    )
    staking_query_progress(msg_aggregator=msg_aggregator, step=3)
    stability_pool_amount_withdrawn, stability_pool_value_withdrawn = calculate_pool_metrics(
        cursor=cursor,
        query=query_stability_pool_deposits,
        bindings=withdrawal_pool_bindings,
    )
    staking_query_progress(msg_aggregator=msg_aggregator, step=4)

    return {
        'total_value_gains_stability_pool': total_value_gains_stability_pool,
        'total_value_gains_staking': total_value_gains_staking,
        'total_deposited_stability_pool': stability_pool_amount_deposited,
        'total_withdrawn_stability_pool': stability_pool_amount_withdrawn,
        'total_deposited_stability_pool_value': stability_pool_value_deposited,
        'total_withdrawn_stability_pool_value': stability_pool_value_withdrawn,
        'staking_gains': [
            {
                'asset': entry[0],
                'amount': entry[1],
                'value': entry[2],
            } for entry in staking_rewards_breakdown
        ],
        'stability_pool_gains': [
            {
                'asset': entry[0],
                'amount': entry[1],
                'value': entry[2],
            } for entry in stability_rewards_breakdown
        ],
    }


def get_stats(database: 'DBHandler', addresses: Sequence[ChecksumEvmAddress]) -> dict[str, Any]:
    """
    Query staking information for the liquity module related to both the LQTY staking
    and the stability pool. It returns a dictionary combining the information from all
    the addresses and stats per address.
    """
    result: dict[str, Any] = {}
    if len(addresses) == 0:
        return result

    history_events_db = DBHistoryEvents(database)
    with database.conn.read_ctx() as cursor:
        result['global_stats'] = _get_amount_and_value_stats(
            cursor=cursor,
            history_events_db=history_events_db,
            query_staking=QUERY_STAKING_EVENTS,
            bindings_staking=BINDINGS_STAKING_EVENTS,
            query_stability_pool=QUERY_STABILITY_POOL_EVENTS,
            bindings_stability_pool=BINDINGS_STABILITY_POOL_EVENTS,
            query_stability_pool_deposits=QUERY_STABILITY_POOL_DEPOSITS,
            deposit_pool_bindings=[CPT_LIQUITY, A_LUSD.identifier, HistoryEventType.STAKING.serialize(), HistoryEventSubType.DEPOSIT_ASSET.serialize()],  # noqa: E501
            withdrawal_pool_bindings=[CPT_LIQUITY, A_LUSD.identifier, HistoryEventType.STAKING.serialize(), HistoryEventSubType.REMOVE_ASSET.serialize()],  # noqa: E501
            msg_aggregator=database.msg_aggregator,
        )

        result['by_address'] = {}
        query_staking_events_with_address = QUERY_STAKING_EVENTS + ' AND location_label=?'
        query_stability_pool_events_with_address = QUERY_STABILITY_POOL_EVENTS + ' AND location_label=?'  # noqa: E501
        query_stability_pool_deposits = QUERY_STABILITY_POOL_DEPOSITS + ' AND location_label=?'
        for address in addresses:
            result['by_address'][address] = _get_amount_and_value_stats(
                cursor=cursor,
                history_events_db=history_events_db,
                query_staking=query_staking_events_with_address,
                bindings_staking=[*BINDINGS_STAKING_EVENTS, address],
                query_stability_pool=query_stability_pool_events_with_address,
                bindings_stability_pool=[*BINDINGS_STABILITY_POOL_EVENTS, address],
                query_stability_pool_deposits=query_stability_pool_deposits,
                deposit_pool_bindings=[CPT_LIQUITY, A_LUSD.identifier, HistoryEventType.STAKING.serialize(), HistoryEventSubType.DEPOSIT_ASSET.serialize(), address],  # noqa: E501
                withdrawal_pool_bindings=[CPT_LIQUITY, A_LUSD.identifier, HistoryEventType.STAKING.serialize(), HistoryEventSubType.REMOVE_ASSET.serialize(), address],  # noqa: E501
                msg_aggregator=database.msg_aggregator,
            )

    return result
