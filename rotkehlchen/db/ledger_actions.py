import logging
from typing import TYPE_CHECKING, List, Optional, Tuple

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.ledger_actions import LedgerAction
from rotkehlchen.constants.limits import FREE_LEDGER_ACTIONS_LIMIT
from rotkehlchen.db.filtering import LedgerActionsFilterQuery
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class DBLedgerActions():

    def __init__(self, database: 'DBHandler', msg_aggregator: MessagesAggregator):
        self.db = database
        self.msg_aggregator = msg_aggregator

    def get_ledger_actions_and_limit_info(
            self,
            filter_query: LedgerActionsFilterQuery,
            has_premium: bool,
    ) -> Tuple[List[LedgerAction], int]:
        """Gets all ledger actions for the query from the DB

        Also returns how many are the total found for the filter
        """
        actions = self.get_ledger_actions(filter_query=filter_query, has_premium=has_premium)
        cursor = self.db.conn.cursor()
        query, bindings = filter_query.prepare(with_pagination=False)
        query = 'SELECT COUNT(*) from ledger_actions ' + query
        total_found_result = cursor.execute(query, bindings)
        return actions, total_found_result.fetchone()[0]

    def get_ledger_actions(
            self,
            filter_query: LedgerActionsFilterQuery,
            has_premium: bool,
    ) -> List[LedgerAction]:
        """Returns a list of ledger actions optionally filtered by the given filter.

        Returned list is ordered according to the passed filter query
        """
        cursor = self.db.conn.cursor()
        query_filter, bindings = filter_query.prepare()
        if has_premium:
            query = 'SELECT * from ledger_actions ' + query_filter
            results = cursor.execute(query, bindings)
        else:
            query = 'SELECT * FROM (SELECT * from ledger_actions ORDER BY timestamp DESC LIMIT ?) ' + query_filter  # noqa: E501
            results = cursor.execute(query, [FREE_LEDGER_ACTIONS_LIMIT] + bindings)

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
        """Adds a new ledger action to the DB and returns its identifier for success

        May raise:
        - sqlcipher.IntegrityError if there is a conflict at addition in  _add_gitcoin_extra_data.
         If this error is raised connection needs to be rolled back by the caller.
        """
        cursor = self.db.conn.cursor()
        query = """
        INSERT INTO ledger_actions(
            timestamp, type, location, amount, asset, rate, rate_asset, link, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);"""
        cursor.execute(query, action.serialize_for_db())
        identifier = cursor.lastrowid
        action.identifier = identifier
        self.db.conn.commit()
        return identifier

    def add_ledger_actions(self, actions: List[LedgerAction]) -> None:
        """Adds multiple ledger action to the DB

        Is slow due to not using executemany since the ledger actions table
        utilized an auto generated primary key.
        """
        for action in actions:
            try:
                self.add_ledger_action(action)
            except sqlcipher.IntegrityError:  # pylint: disable=no-member
                self.db.msg_aggregator.add_warning('Did not add ledger action to DB due to it already existing')  # noqa: E501
                log.warning(f'Did not add ledger action {action} to the DB due to it already existing')  # noqa: E501
                self.db.conn.rollback()  # undo the addition and rollack to last commit

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

        Does not edit the extra data at the moment

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
