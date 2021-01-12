from typing import Optional

from rotkehlchen.accounting.structures import LedgerAction, LedgerActionType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.utils import form_query_to_filter_timestamps
from rotkehlchen.errors import DeserializationError, InputError, UnknownAsset
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_ledger_action_type_from_db,
    deserialize_location_from_db,
    deserialize_timestamp,
)
from rotkehlchen.typing import AssetAmount, Location, Timestamp


class DBLedgerActions():

    def __init__(self, database: DBHandler):
        self.db = database

    def get_ledger_actions(
            self,
            from_ts: Optional[Timestamp],
            to_ts: Optional[Timestamp],
            location: Optional[Location],
    ):
        cursor = self.db.conn.cursor()
        query = (
            'SELECT identifier,'
            '  timestamp,'
            '  type,'
            '  location,'
            '  amount,'
            '  asset,'
            '  link,'
            '  notes FROM ledger_actions '
        )
        if location is not None:
            query += f'WHERE location="{location.serialize_for_db()}" '
        query, bindings = form_query_to_filter_timestamps(query, 'time', from_ts, to_ts)
        results = cursor.execute(query, bindings)
        actions = []
        for result in results:
            try:
                action = LedgerAction(
                    identifier=result[0],
                    timestamp=deserialize_timestamp(result[1]),
                    action_type=deserialize_ledger_action_type_from_db(result[2]),
                    location=deserialize_location_from_db(result[3]),
                    amount=deserialize_asset_amount(result[4]),
                    asset=Asset(result[5]),
                    link=result[6],
                    notes=result[7],
                )
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing Ledger Action from the DB. Skipping it.'
                    f'Error was: {str(e)}',
                )
                continue
            except UnknownAsset as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing Ledger Action from the DB. Skipping it. '
                    f'Unknown asset {e.asset_name} found',
                )
                continue
            actions.append(action)

        return actions

    def add_ledger_action(
            self,
            timestamp: Timestamp,
            action_type: LedgerActionType,
            location: Location,
            amount: AssetAmount,
            asset: Asset,
            link: str,
            notes: str,
    ) -> int:
        """Adds a new ledger action to the DB and returns its identifier for success"""
        cursor = self.db.conn.cursor()
        query = """
        INSERT INTO ledger_actions(timestamp, type, location, amount, asset, link, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?);"""
        cursor.execute(
            query,
            (
                timestamp,
                action_type.serialize_for_db(),
                location.serialize_for_db(),
                amount,
                asset.identifier,
                link,
                notes,
            ),
        )
        identifier = cursor.lastrowid
        return identifier

    def remove_ledger_action(self, identifier: int) -> Optional[str]:
        """Removes a ledger action from the DB by identifier

        Returns None for success or an error message for error
        """
        error_msg = None
        cursor = self.db.conn.cursor()
        cursor.execute(
            'DELETE from ledger_actions WHERE identifier = ?;', (identifier,),
        )
        if cursor.rowcount < 1:
            error_msg = (
                f'Tried to delete ledger action with identifier {identifier} but '
                f'it was not found in the DB',
            )
        return error_msg

    def edit_ledger_action(self, action: LedgerAction) -> Optional[str]:
        """Edits a ledger action from the DB by identifier

        Returns None for success or an error message for error
        """
        error_msg = None
        cursor = self.db.conn.cursor()
        query = """
        UPDATE ledger_actions SET timestamp=?, action_type=?, location=?, amount=?,
        asset=?, link=?, notes=? WHERE identifier=?"""
        cursor.execute(query, (*action.serialize_for_db(), action.identifier))
        if cursor.rowcount != 1:
            error_msg = (
                f'Tried to edit ledger action with identifier {action.identifier} '
                f'but it was not found in the DB',
            )
        return error_msg
