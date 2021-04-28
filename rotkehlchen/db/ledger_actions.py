from typing import TYPE_CHECKING, List, Optional

from rotkehlchen.accounting.ledger_actions import LedgerAction
from rotkehlchen.db.utils import form_query_to_filter_timestamps
from rotkehlchen.errors import DeserializationError, UnknownAsset
from rotkehlchen.typing import Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class DBLedgerActions():

    def __init__(self, database: 'DBHandler', msg_aggregator: MessagesAggregator):
        self.db = database
        self.msg_aggregator = msg_aggregator

    def get_ledger_actions(
            self,
            from_ts: Optional[Timestamp],
            to_ts: Optional[Timestamp],
            location: Optional[Location],
    ) -> List[LedgerAction]:
        cursor = self.db.conn.cursor()
        query = (
            'SELECT identifier,'
            '  timestamp,'
            '  type,'
            '  location,'
            '  amount,'
            '  asset,'
            '  rate,'
            '  rate_asset,'
            '  link,'
            '  notes FROM ledger_actions '
        )
        if location is not None:
            query += f'WHERE location="{location.serialize_for_db()}" '
        query, bindings = form_query_to_filter_timestamps(query, 'timestamp', from_ts, to_ts)
        results = cursor.execute(query, bindings)
        actions = []
        for result in results:
            try:
                action = LedgerAction.deserialize_from_db(result)
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

    def add_ledger_action(self, action: LedgerAction) -> int:
        """Adds a new ledger action to the DB and returns its identifier for success"""
        cursor = self.db.conn.cursor()
        query = """
        INSERT INTO ledger_actions(
            timestamp, type, location, amount, asset, rate, rate_asset, link, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);"""
        cursor.execute(query, action.serialize_for_db())
        identifier = cursor.lastrowid
        self.db.conn.commit()
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
                f'it was not found in the DB'
            )
        self.db.conn.commit()
        return error_msg

    def edit_ledger_action(self, action: LedgerAction) -> Optional[str]:
        """Edits a ledger action from the DB by identifier

        Returns None for success or an error message for error
        """
        error_msg = None
        cursor = self.db.conn.cursor()
        query = """
        UPDATE ledger_actions SET timestamp=?, type=?, location=?, amount=?,
        asset=?, rate=?, rate_asset=?, link=?, notes=? WHERE identifier=?"""
        db_action_tuple = action.serialize_for_db()
        cursor.execute(query, (*db_action_tuple, action.identifier))
        if cursor.rowcount != 1:
            error_msg = (
                f'Tried to edit ledger action with identifier {action.identifier} '
                f'but it was not found in the DB'
            )
        self.db.conn.commit()
        return error_msg
