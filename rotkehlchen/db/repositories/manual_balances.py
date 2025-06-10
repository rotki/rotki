"""Repository for managing manually tracked balances in the database."""
import logging
from typing import TYPE_CHECKING

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.constants.misc import ONE  # noqa: F401  # pylint: disable=unused-import
from rotkehlchen.db.utils import (
    deserialize_tags_from_db,
    insert_tag_mappings,
    replace_tag_mappings,
)
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.types import BalanceType, Location

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.user_messages import MessagesAggregator


log = logging.getLogger(__name__)


class ManualBalancesRepository:
    """Repository for handling all manually tracked balance operations."""

    def __init__(self, msg_aggregator: 'MessagesAggregator') -> None:
        """Initialize the manual balances repository."""
        self.msg_aggregator = msg_aggregator

    def get_all(
            self,
            cursor: 'DBCursor',
            balance_type: BalanceType | None = BalanceType.ASSET,
            include_entries_with_missing_assets: bool = False,
    ) -> list[ManuallyTrackedBalance]:
        """Returns the manually tracked balances from the DB"""
        query_balance_type = ''
        if balance_type is not None:
            query_balance_type = f"WHERE A.category='{balance_type.serialize_for_db()}'"
        query = cursor.execute(
            f"SELECT A.asset, A.label, A.amount, A.location, group_concat(B.tag_name,','), "
            f"A.category, A.id FROM manually_tracked_balances as A "
            f"LEFT OUTER JOIN tag_mappings as B on B.object_reference = A.id "
            f"{query_balance_type} GROUP BY label;",
        )

        data = []
        for entry in query:
            tags = deserialize_tags_from_db(entry[4])
            if (
                (asset_is_missing := not Asset(entry[0]).exists()) is True
                and include_entries_with_missing_assets is False
            ):
                continue

            try:
                balance_type = BalanceType.deserialize_from_db(entry[5])
                data.append(ManuallyTrackedBalance(
                    identifier=entry[6],
                    asset=Asset(entry[0]),
                    label=entry[1],
                    amount=FVal(entry[2]),
                    location=Location.deserialize_from_db(entry[3]),
                    tags=tags,
                    balance_type=balance_type,
                    asset_is_missing=asset_is_missing,
                ))
            except (DeserializationError, ValueError) as e:
                # ValueError would be due to FVal failing
                self.msg_aggregator.add_warning(
                    f'Unexpected data in a ManuallyTrackedBalance entry in the DB: {e!s}',
                )

        return data

    def add(self, write_cursor: 'DBCursor', data: list[ManuallyTrackedBalance]) -> None:
        """Adds manually tracked balances in the DB

        May raise:
        - InputError if one of the given balance entries already exist in the DB
        """
        # Insert the manually tracked balances in the DB
        try:
            for entry in data:
                write_cursor.execute(
                    'INSERT INTO manually_tracked_balances(asset, label, amount, location, category) '  # noqa: E501
                    'VALUES (?, ?, ?, ?, ?)', (entry.asset.identifier, entry.label, str(entry.amount), entry.location.serialize_for_db(), entry.balance_type.serialize_for_db()),  # noqa: E501
                )
                entry.identifier = write_cursor.lastrowid
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'One of the manually tracked balance entries already exists in the DB. {e!s}',
            ) from e

        insert_tag_mappings(write_cursor=write_cursor, data=data, object_reference_keys=['identifier'])  # noqa: E501

        # make sure assets are included in the global db user owned assets
        GlobalDBHandler.add_user_owned_assets([x.asset for x in data])

    def edit(self, write_cursor: 'DBCursor', data: list[ManuallyTrackedBalance]) -> None:
        """Edits manually tracked balances

        Edits the manually tracked balances for each of the given balance labels.

        At this point in the calling chain we should already know that:
        - All tags exist in the DB

        May raise:
        - InputError if any of the manually tracked balance labels to edit do not
        exist in the DB
        """
        # Update the manually tracked balance entries in the DB
        tuples = [(
            entry.asset.identifier,
            str(entry.amount),
            entry.location.serialize_for_db(),
            BalanceType.serialize_for_db(entry.balance_type),
            entry.label,
            entry.identifier,
        ) for entry in data]

        write_cursor.executemany(
            'UPDATE manually_tracked_balances SET asset=?, amount=?, location=?, category=?, label=?'  # noqa: E501
            'WHERE id=?;', tuples,
        )
        if write_cursor.rowcount != len(data):
            msg = 'Tried to edit manually tracked balance entry that did not exist in the DB'
            raise InputError(msg)
        replace_tag_mappings(write_cursor=write_cursor, data=data, object_reference_keys=['identifier'])  # noqa: E501

    def remove(self, write_cursor: 'DBCursor', ids: list[int]) -> None:
        """
        Removes manually tracked balances for the given ids

        May raise:
        - InputError if any of the given manually tracked balance labels
        to delete did not exist
        """
        tuples = [(x,) for x in ids]
        write_cursor.executemany(
            'DELETE FROM tag_mappings WHERE object_reference = ?;', tuples,
        )
        write_cursor.executemany(
            'DELETE FROM manually_tracked_balances WHERE id = ?;', tuples,
        )
        affected_rows = write_cursor.rowcount
        if affected_rows != len(ids):
            raise InputError(
                f'Tried to remove {len(ids) - affected_rows} '
                f'manually tracked balance entries that did not exist',
            )
