from typing import TYPE_CHECKING, Any
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.liquity.constants import CPT_LIQUITY
from rotkehlchen.constants.assets import A_LQTY, A_LUSD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

# This queries for events having a specific combination of asset + staking type + reward and
# being from liquity. This helps to filter if they are from the stability pool or the LQTY
# staking. Then we need to consider the rewards in other assets that appear in the same
# transaction and this is why we use the IN operator as filter.
QUERY_STAKING_EVENTS = """
WHERE event_identifier IN
(SELECT A.event_identifier FROM history_events AS A JOIN history_events AS B ON A.event_identifier = B.event_identifier
    JOIN evm_events_info AS C ON A.identifier=C.identifier WHERE C.counterparty=? AND A.asset=?
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
WHERE event_identifier IN (
    SELECT A.event_identifier FROM history_events AS A JOIN history_events AS B ON
    A.event_identifier = B.event_identifier JOIN evm_events_info AS C ON A.identifier=C.identifier
    WHERE C.counterparty = "liquity" AND B.asset=? AND B.subtype=?
) AND type=? AND subtype=?
"""
BINDINGS_STABILITY_POOL_EVENTS = [
    A_LQTY.identifier,
    HistoryEventSubType.REWARD.serialize(),
    HistoryEventType.STAKING.serialize(),
    HistoryEventSubType.REWARD.serialize(),
]
QUERY_STABILITY_POOL_DEPOSITS = (
    'SELECT SUM(CAST(amount AS REAL)), SUM(CAST(usd_value AS REAL)) '
    'FROM history_events WHERE asset=? AND type=? AND subtype=?'
)


def _get_stats(
        cursor: 'DBCursor',
        history_events_db: DBHistoryEvents,
        query_staking: str,
        bindings_staking: list[Any],
        query_stability_pool: str,
        bindings_stability_pool: list[Any],
        query_stability_pool_deposits: str,
        deposit_pool_bindings: list[Any],
        withdrawal_pool_bindings: list[Any],
) -> dict[str, Any]:
    """
    Query the database using the given pre-computed filters and create a report
    with all the information related to staking
    """
    total_usd_staking_rewards, staking_rewards_breakdown = history_events_db.get_value_stats(
        cursor=cursor,
        query_filters=query_staking,
        bindings=bindings_staking,
    )
    total_usd_stability_rewards, stability_rewards_breakdown = history_events_db.get_value_stats(  # noqa: E501
        cursor=cursor,
        query_filters=query_stability_pool,
        bindings=bindings_stability_pool,
    )
    # get stats about LUSD deposited in the stability pool
    cursor.execute(query_stability_pool_deposits, deposit_pool_bindings)
    stability_pool_deposits = cursor.fetchone()

    cursor.execute(query_stability_pool_deposits, withdrawal_pool_bindings)
    stability_pool_withdrawals = cursor.fetchone()

    return {
        'total_usd_gains_stability_pool': total_usd_stability_rewards,
        'total_usd_gains_staking': total_usd_staking_rewards,
        'total_deposited_stability_pool': FVal(stability_pool_deposits[0]) if stability_pool_deposits[0] is not None else ZERO,  # noqa: E501
        'total_withdrawn_stability_pool': FVal(stability_pool_withdrawals[0]) if stability_pool_withdrawals[0] is not None else ZERO,  # noqa: E501
        'total_deposited_stability_pool_usd_value': FVal(stability_pool_deposits[1]) if stability_pool_deposits[1] is not None else ZERO,  # noqa: E501
        'total_withdrawn_stability_pool_usd_value': FVal(stability_pool_withdrawals[1]) if stability_pool_withdrawals[1] is not None else ZERO,  # noqa: E501
        'staking_gains': [
            {
                'asset': entry[0],
                'amount': entry[1],
                'usd_value': entry[2],
            } for entry in staking_rewards_breakdown
        ],
        'stability_pool_gains': [
            {
                'asset': entry[0],
                'amount': entry[1],
                'usd_value': entry[2],
            } for entry in stability_rewards_breakdown
        ],
    }


def get_stats(database: 'DBHandler', addresses: list[ChecksumEvmAddress]) -> dict[str, Any]:
    """
    Query staking information for the liquity module related to both the LQTY staking
    and the stability pool. It returns a dictionary combining the information from all
    the addresses and stats per address.
    """
    history_events_db = DBHistoryEvents(database)
    result = {}
    with database.conn.read_ctx() as cursor:
        result['global_stats'] = _get_stats(
            cursor=cursor,
            history_events_db=history_events_db,
            query_staking=QUERY_STAKING_EVENTS,
            bindings_staking=BINDINGS_STAKING_EVENTS,
            query_stability_pool=QUERY_STABILITY_POOL_EVENTS,
            bindings_stability_pool=BINDINGS_STABILITY_POOL_EVENTS,
            query_stability_pool_deposits=QUERY_STABILITY_POOL_DEPOSITS,
            deposit_pool_bindings=[A_LUSD.identifier, HistoryEventType.STAKING.serialize(), HistoryEventSubType.DEPOSIT_ASSET.serialize()],  # noqa: E501
            withdrawal_pool_bindings=[A_LUSD.identifier, HistoryEventType.STAKING.serialize(), HistoryEventSubType.REMOVE_ASSET.serialize()],  # noqa: E501
        )

        if len(addresses) == 0:
            return result

        result['by_address'] = {}
        query_staking_events_with_address = QUERY_STAKING_EVENTS + ' AND location_label=?'
        query_stability_pool_events_with_address = QUERY_STABILITY_POOL_EVENTS + ' AND location_label=?'  # noqa: E501
        query_stability_pool_deposits = QUERY_STABILITY_POOL_DEPOSITS + ' AND location_label=?'
        for address in addresses:
            result['by_address'][address] = _get_stats(
                cursor=cursor,
                history_events_db=history_events_db,
                query_staking=query_staking_events_with_address,
                bindings_staking=[*BINDINGS_STAKING_EVENTS, address],
                query_stability_pool=query_stability_pool_events_with_address,
                bindings_stability_pool=[*BINDINGS_STABILITY_POOL_EVENTS, address],
                query_stability_pool_deposits=query_stability_pool_deposits,
                deposit_pool_bindings=[A_LUSD.identifier, HistoryEventType.STAKING.serialize(), HistoryEventSubType.DEPOSIT_ASSET.serialize(), address],  # noqa: E501
                withdrawal_pool_bindings=[A_LUSD.identifier, HistoryEventType.STAKING.serialize(), HistoryEventSubType.REMOVE_ASSET.serialize(), address],  # noqa: E501
            )

    return result
