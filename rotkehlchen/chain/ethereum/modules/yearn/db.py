from typing import TYPE_CHECKING, List

from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor

from .structures import YearnVault, YearnVaultEvent


def add_yearn_vaults_events(
        write_cursor: 'DBCursor',
        address: ChecksumEvmAddress,
        events: List[YearnVaultEvent],
) -> None:
    serialized_events = [e.serialize_for_db(address) for e in events]
    write_cursor.executemany(
        'INSERT OR IGNORE INTO yearn_vaults_events( '
        'address, '
        'event_type, '
        'from_asset, '
        'from_amount, '
        'from_usd_value, '
        'to_asset, '
        'to_amount, '
        'to_usd_value, '
        'pnl_amount, '
        'pnl_usd_value, '
        'block_number, '
        'timestamp, '
        'tx_hash, '
        'log_index,'
        'version)'
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        serialized_events,
    )


def get_yearn_vaults_events(
        cursor: 'DBCursor',
        address: ChecksumEvmAddress,
        vault: YearnVault,
        msg_aggregator: MessagesAggregator,
) -> List[YearnVaultEvent]:
    events = []
    cursor.execute(
        'SELECT * from yearn_vaults_events WHERE address=? '
        'AND (from_asset=? OR from_asset=?);',
        (address, vault.underlying_token.identifier, vault.token.identifier),
    )
    for result in cursor:
        try:
            events.append(YearnVaultEvent.deserialize_from_db(result))
        except (DeserializationError, UnknownAsset) as e:
            msg = f'Failed to read yearn vault event from database due to {str(e)}'
            msg_aggregator.add_warning(msg)

    return events


def get_yearn_vaults_v2_events(
        cursor: 'DBCursor',
        address: ChecksumEvmAddress,
        from_block: int,
        to_block: int,
        msg_aggregator: MessagesAggregator,
) -> List[YearnVaultEvent]:
    events = []
    cursor.execute(
        'SELECT * from yearn_vaults_events WHERE address=? AND version=2 '
        'AND block_number BETWEEN ? AND ?',
        (address, from_block, to_block),
    )
    for result in cursor:
        try:
            events.append(YearnVaultEvent.deserialize_from_db(result))
        except (DeserializationError, UnknownAsset) as e:
            msg = f'Failed to read yearn vault event from database due to {str(e)}'
            msg_aggregator.add_warning(msg)

    return events
