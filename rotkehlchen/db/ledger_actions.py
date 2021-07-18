import logging
from sqlite3 import Cursor
from typing import TYPE_CHECKING, Dict, List, NamedTuple, Optional, Tuple, Union

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.ledger_actions import LedgerAction
from rotkehlchen.chain.ethereum.gitcoin.constants import GITCOIN_GRANTS_PREFIX
from rotkehlchen.db.utils import form_query_to_filter_timestamps
from rotkehlchen.errors import DeserializationError, UnknownAsset
from rotkehlchen.typing import Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class GitcoinGrantMetadata(NamedTuple):
    grant_id: int
    name: str
    created_on: Timestamp


def _add_gitcoin_extra_data(cursor: Cursor, actions: List[LedgerAction]) -> None:
    """May raise sqlcipher.IntegrityError"""
    db_tuples = []
    for action in actions:
        if action.extra_data is not None:
            db_tuples.append(
                action.extra_data.serialize_for_db(parent_id=action.identifier),
            )

    if len(db_tuples) == 0:
        return

    query = """INSERT INTO ledger_actions_gitcoin_data(
        parent_id, tx_id, grant_id, clr_round, tx_type
    )
    VALUES (?, ?, ?, ?, ?);"""
    cursor.executemany(query, db_tuples)


class DBLedgerActions():

    def __init__(self, database: 'DBHandler', msg_aggregator: MessagesAggregator):
        self.db = database
        self.msg_aggregator = msg_aggregator

    def get_ledger_actions(
            self,
            from_ts: Optional[Timestamp],
            to_ts: Optional[Timestamp],
            location: Optional[Location],
            link: Optional[str] = None,
            notes: Optional[str] = None,
    ) -> List[LedgerAction]:
        bindings = []
        cursor = self.db.conn.cursor()
        query_selection = 'SELECT * '
        query = 'FROM ledger_actions '
        if location is not None:
            query += f'WHERE location="{location.serialize_for_db()}" '

        if link is not None:
            if 'WHERE' not in query:
                query += ' WHERE '
            else:
                query += ' AND '
            query += 'link=? '
            bindings.append(link)

        if notes is not None:
            if 'WHERE' not in query:
                query += ' WHERE '
            else:
                query += ' AND '
            query += 'notes=? '
            bindings.append(notes)

        query, time_bindings = form_query_to_filter_timestamps(query, 'timestamp', from_ts, to_ts)
        full_query = query_selection + query
        results = cursor.execute(full_query, bindings + list(time_bindings)).fetchall()  # type: ignore  # noqa: E501

        original_query = 'SELECT identifier ' + query[:-1]
        gitcoin_query = f'SELECT * from ledger_actions_gitcoin_data WHERE parent_id IN ({original_query});'  # noqa: E501
        gitcoin_results = cursor.execute(gitcoin_query, bindings + list(time_bindings))  # type: ignore  # noqa: E501
        gitcoin_map = {x[0]: x for x in gitcoin_results}

        actions = []
        for result in results:
            try:
                action = LedgerAction.deserialize_from_db(result, gitcoin_map)
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

    def get_gitcoin_grant_metadata(
            self,
            grant_id: Optional[int] = None,
    ) -> Dict[int, GitcoinGrantMetadata]:
        cursor = self.db.conn.cursor()
        querystr = 'SELECT * from gitcoin_grant_metadata'
        bindings: Union[Tuple, Tuple[int]] = ()
        if grant_id is not None:
            querystr += ' WHERE grant_id=?'
            bindings = (grant_id,)

        response = cursor.execute(querystr, bindings)
        results = {}
        for entry in response:
            results[entry[0]] = GitcoinGrantMetadata(
                grant_id=entry[0],
                name=entry[1],
                created_on=entry[2],
            )

        return results

    def set_gitcoin_grant_metadata(
            self,
            grant_id: int,
            name: str,
            created_on: Timestamp,
    ) -> None:
        """Inserts new grant metadata entry if they don't exist or update entry if it does"""
        cursor = self.db.conn.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO gitcoin_grant_metadata(grant_id, grant_name, created_on) '
            'VALUES(?, ?, ?);',
            (grant_id, name, created_on),
        )
        if cursor.rowcount != 1:
            cursor.execute(
                'UPDATE gitcoin_grant_metadata SET grant_name=?, created_on=? WHERE grant_id=?;',
                (name, created_on, grant_id),
            )

    def get_gitcoin_grant_events(
            self,
            grant_id: Optional[int],
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
    ) -> List[LedgerAction]:
        ledger_actions = self.get_ledger_actions(
            from_ts=from_ts,
            to_ts=to_ts,
            location=Location.GITCOIN,
        )
        if grant_id is None:
            return ledger_actions
        # else
        return [x for x in ledger_actions if x.extra_data.grant_id == grant_id]  # type: ignore

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
        _add_gitcoin_extra_data(cursor, [action])
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

    def delete_gitcoin_ledger_actions(self, grant_id: Optional[int]) -> None:
        cursor = self.db.conn.cursor()
        query1str = (
            'DELETE FROM ledger_actions WHERE identifier IN ('
            'SELECT parent_id from ledger_actions_gitcoin_data '
        )
        query2str = 'DELETE FROM used_query_ranges WHERE name '
        query3str = 'DELETE FROM gitcoin_grant_metadata '
        if grant_id:
            query1str += 'WHERE grant_id = ?);'
            bindings1 = (grant_id,)
            query2str += '= ?;'
            bindings2 = (f'{GITCOIN_GRANTS_PREFIX}_{grant_id}',)
            query3str += 'WHERE grant_id=?;'
        else:
            query1str += ');'
            bindings1 = ()  # type: ignore
            query2str += 'LIKE ? ESCAPE ?'
            bindings2 = (f'{GITCOIN_GRANTS_PREFIX}_%', '\\')  # type: ignore
            query3str += ';'

        cursor.execute(query1str, bindings1)
        cursor.execute(query2str, bindings2)
        cursor.execute(query3str, bindings1)
        self.db.conn.commit()
