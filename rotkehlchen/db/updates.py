import json
import logging
from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING, Any, Final, Literal, Union, overload

import requests

from rotkehlchen.assets.spam_assets import update_spam_assets
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import (
    AddressbookEntry,
    AddressbookType,
    OptionalChainAddress,
    SupportedBlockchain,
)
from rotkehlchen.utils.misc import is_production, ts_now
from rotkehlchen.utils.network import query_file

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBCursor, DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

LAST_DATA_UPDATES_KEY: Final = 'last_data_updates_ts'
SPAM_ASSETS_URL = 'https://raw.githubusercontent.com/rotki/data/{branch}/updates/spam_assets/v{version}.json'  # noqa: E501
RPC_NODES_URL = 'https://raw.githubusercontent.com/rotki/data/{branch}/updates/rpc_nodes/v{version}.json'  # noqa: E501
CONTRACTS_URL = 'https://raw.githubusercontent.com/rotki/data/{branch}/updates/contracts/v{version}.json'  # noqa: E501
GLOBAL_ADDRESSBOOK_URL = 'https://raw.githubusercontent.com/rotki/data/{branch}/updates/global_addressbook/v{version}.json'  # noqa: E501


class UpdateType(Enum):
    SPAM_ASSETS = 'spam_assets'
    RPC_NODES = 'rpc_nodes'
    CONTRACTS = 'contracts'
    GLOBAL_ADDRESSBOOK = 'global_addressbook'

    def serialize(self) -> str:
        """Serializes the update type for the DB and API"""
        return f'{self.value}_version'

    @classmethod
    def deserialize(cls: type['UpdateType'], value: str) -> 'UpdateType':
        """Deserialize string from api/DB to UpdateType
        May raise:
        - Deserialization error if value is not a valid UpdateType
        """
        try:
            return cls(value[:-8])  # length of the _version suffix
        except ValueError as e:
            raise DeserializationError(f'Failed to deserialize UpdateTypevalue {value}') from e


class RotkiDataUpdater:
    """
    Handle updates from the rotki repository related to data that needs to be provided to
    the users. It includes:
    - Spam assets
    - RPC nodes
    - Contracts
    """

    def __init__(self, msg_aggregator: 'MessagesAggregator', user_db: 'DBHandler') -> None:
        self.msg_aggregator = msg_aggregator
        self.user_db = user_db
        self.branch = 'develop'
        if is_production():
            self.branch = 'main'

    def _get_remote_info_json(self) -> dict[str, Any]:
        """Retrieve remote file with information for different updates

        May raise RemoteError if anything is wrong contacting github
        """
        url = f'https://raw.githubusercontent.com/rotki/data/{self.branch}/updates/info.json'
        try:
            response = requests.get(url=url, timeout=DEFAULT_TIMEOUT_TUPLE)
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Failed to query {url} during assets update: {e!s}') from e

        try:
            json_data = response.json()
        except json.decoder.JSONDecodeError as e:
            raise RemoteError(
                f'Could not parse update info from {url} as json: {response.text}',
            ) from e

        return json_data

    def update_spam_assets(self, from_version: int, to_version: int) -> None:
        """
        Check the updates in the inclusive range [from_version + 1, to_version] and update the
        spam assets for those versions. Assets are also added to the globaldb if they don't exist
        locally
        """
        for version in range(from_version + 1, to_version + 1):
            success, updated_assets = self._get_file_content(
                file_url=SPAM_ASSETS_URL.format(branch=self.branch, version=version),
                update_type=UpdateType.SPAM_ASSETS,
            )
            if success is False:
                continue

            log.info(f'Applying update for spam assets from v{version}. {len(updated_assets)} tokens to add')  # noqa: E501
            with GlobalDBHandler().conn.critical_section():
                # Use a critical section to avoid another greenlet adding spam assets at
                # the same time
                update_spam_assets(db=self.user_db, assets_info=updated_assets)

            with self.user_db.conn.write_ctx() as write_cursor:
                write_cursor.execute(
                    'INSERT OR REPLACE INTO settings(name, value) VALUES (?, ?)',
                    (UpdateType.SPAM_ASSETS.serialize(), version),
                )

    def update_rpc_nodes(self, from_version: int, to_version: int) -> None:  # pylint: disable=unused-argument  # noqa: E501
        """Checks the update for the latest version and update the default rpc nodes in the global db.

        It also updates the user db with these default nodes.
        """  # noqa: E501
        success, updated_rpc_nodes = self._get_file_content(
            file_url=RPC_NODES_URL.format(branch=self.branch, version=to_version),
            update_type=UpdateType.RPC_NODES,
        )
        if success is False:
            return

        log.info(f'Applying update for rpc nodes from v{to_version}')
        new_default_nodes: list[tuple[Any, ...]] = [
            (
                node['name'],
                node['endpoint'],
                node['owned'],
                node['active'],
                str(FVal(node['weight'])),
                node['blockchain'],
            )
            for node in updated_rpc_nodes
        ]
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            # Update the default nodes, stored in the global DB
            existing_default_nodes = write_cursor.execute('SELECT * FROM default_rpc_nodes').fetchall()  # noqa: E501
            write_cursor.execute('DELETE FROM default_rpc_nodes')
            write_cursor.executemany(
                'INSERT OR IGNORE INTO default_rpc_nodes(name, endpoint, owned, active, weight, blockchain) '  # noqa: E501
                'VALUES (?, ?, ?, ?, ?, ?)',
                new_default_nodes,
            )

        with self.user_db.conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'INSERT OR REPLACE INTO settings(name, value) VALUES (?, ?)',
                (UpdateType.RPC_NODES.serialize(), to_version),
            )

        self._update_user_nodes(
            existing_default_nodes=existing_default_nodes,
            new_default_nodes=new_default_nodes,
        )

    def update_contracts(self, from_version: int, to_version: int) -> None:
        """
        Updates evm contracts and ABIs in globaldb.
        If an ABI already exists in the db, it is reused.
        If a contract (address + chain id) exists, it is replaced by the remote counterpart.
        """
        for version in range(from_version + 1, to_version + 1):
            success, updated_contracts = self._get_file_content(
                file_url=CONTRACTS_URL.format(branch=self.branch, version=version),
                update_type=UpdateType.CONTRACTS,
            )
            if success is False:
                return

            log.info(f'Applying update for contracts to v{version}')
            remote_id_to_local_id = {}
            for single_abi_data in updated_contracts['abis_data']:
                # store a mapping of the virtual id to the id in the user's globaldb
                abi_id = GlobalDBHandler().get_or_write_abi(
                    serialized_abi=single_abi_data['value'],
                    abi_name=single_abi_data.get('name'),
                )
                remote_id_to_local_id[single_abi_data['id']] = abi_id

            new_contracts_data = []
            for single_contract_data in updated_contracts['contracts_data']:
                if single_contract_data['abi'] not in remote_id_to_local_id:
                    self.msg_aggregator.add_error(
                        f'ABI with id {single_contract_data["abi"]} was missing in a contracts '
                        f'update. Please report it to the rotki team.',
                    )
                    continue
                new_contracts_data.append((
                    single_contract_data['address'],
                    single_contract_data['chain_id'],
                    remote_id_to_local_id[single_contract_data['abi']],
                    single_contract_data['deployed_block'],
                ))

            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                write_cursor.executemany(
                    'INSERT OR REPLACE INTO contract_data(address, chain_id, abi, deployed_block) VALUES(?, ?, ?, ?)',  # noqa: E501
                    new_contracts_data,
                )

            with self.user_db.conn.write_ctx() as write_cursor:
                write_cursor.execute(
                    'INSERT OR REPLACE INTO settings(name, value) VALUES (?, ?)',
                    (UpdateType.CONTRACTS.serialize(), version),
                )

    def update_global_addressbook(self, from_version: int, to_version: int) -> None:
        """Downloads and applies global addressbook updates from from_version to to_version"""
        db_addressbook = DBAddressbook(self.user_db)
        for version in range(from_version + 1, to_version + 1):
            log.debug(f'Applying global address book update version {version}')
            success, new_raw_entries = self._get_file_content(
                file_url=GLOBAL_ADDRESSBOOK_URL.format(branch=self.branch, version=version),
                update_type=UpdateType.GLOBAL_ADDRESSBOOK,
            )
            if success is False:
                log.error(f'Failed to download globaldb addressbook for version {version}')
                continue

            entries_to_add = []
            for raw_entry in new_raw_entries:
                try:
                    address = deserialize_evm_address(raw_entry['address'])
                    blockchain = SupportedBlockchain.deserialize(raw_entry['blockchain']) if raw_entry['blockchain'] else None  # noqa: E501
                except DeserializationError as e:
                    self.msg_aggregator.add_error(
                        f'Could not deserialize address {raw_entry["address"]} or blockchain '
                        f'{raw_entry["blockchain"]} that was seen in a global addressbook update. '
                        f'Please report it to the rotki team. {e!s}',
                    )
                    continue

                entry = AddressbookEntry(
                    address=address,
                    name=raw_entry['new_name'],
                    blockchain=blockchain,
                )
                existing_name = db_addressbook.get_addressbook_entry_name(
                    book_type=AddressbookType.GLOBAL,
                    chain_address=OptionalChainAddress(
                        address=address,
                        blockchain=blockchain,
                    ),
                )
                if existing_name is None:
                    entries_to_add.append(entry)
                elif raw_entry.get('old_name') is not None and existing_name == raw_entry['old_name']:  # noqa: E501
                    # If old_name is specified, replace the entry with the old name.
                    db_addressbook.delete_addressbook_entries(
                        book_type=AddressbookType.GLOBAL,
                        chain_addresses=[OptionalChainAddress(
                            address=address,
                            blockchain=blockchain,
                        )],
                    )
                    entries_to_add.append(entry)
                else:
                    log.debug(
                        f'Global address book entry for address {address} and blockchain '
                        f'{blockchain} already exists (probably was input by the user). '
                        f'Update for this entry will not be applied.',
                    )
                    continue

            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                db_addressbook.add_addressbook_entries(
                    write_cursor=write_cursor,
                    entries=entries_to_add,
                )

    def check_for_updates(self, updates: Sequence[UpdateType] = tuple(UpdateType)) -> None:
        """Retrieve the information about the latest available update"""
        try:
            remote_information = self._get_remote_info_json()
        except RemoteError as e:
            log.error(f'Could not retrieve json update information due to {e!s}')
            # skip updates, but write last date update to not spam periodic tasks
        else:
            for update_type in updates:
                # Get latest applied version
                with self.user_db.conn.read_ctx() as cursor:
                    local_version = self._check_for_last_version(
                        cursor=cursor,
                        update_type=update_type,
                    )

                # Update all remote data
                latest_version = remote_information[update_type.value]['latest']
                if local_version < latest_version:
                    update_function = getattr(self, f'update_{update_type.value}')
                    update_function(from_version=local_version, to_version=latest_version)

        with self.user_db.user_write() as cursor:
            cursor.execute(  # remember last time data updates were detected
                'INSERT OR REPLACE INTO settings (name, value) VALUES (?, ?)',
                (LAST_DATA_UPDATES_KEY, str(ts_now())),
            )

    @staticmethod
    def _check_for_last_version(cursor: 'DBCursor', update_type: UpdateType) -> int:
        """This method checks the database for the last local version of `update_type`"""
        found_version = cursor.execute(
            'SELECT value FROM settings WHERE name=?',
            (update_type.serialize(),),
        ).fetchone()
        return int(found_version[0]) if found_version is not None else 0

    @staticmethod
    @overload
    def _get_file_content(
            file_url: str,
            update_type: Literal[
                UpdateType.SPAM_ASSETS,
                UpdateType.RPC_NODES,
                UpdateType.GLOBAL_ADDRESSBOOK,
            ],
    ) -> tuple[bool, list[dict[str, Any]]]:
        ...

    @staticmethod
    @overload
    def _get_file_content(
            file_url: str,
            update_type: Literal[UpdateType.CONTRACTS],
    ) -> tuple[bool, dict[str, Any]]:
        ...

    @staticmethod
    def _get_file_content(
            file_url: str,
            update_type: UpdateType,
    ) -> tuple[bool, Union[list[dict[str, Any]], dict[str, Any]]]:
        """Retrieves the content of data to be updated.

        Returns True/False for success along with the content.
        """
        try:
            updates = query_file(file_url, is_json=True)
        except RemoteError as e:
            log.warning(f'Failed to update {update_type.value} due to {e!s}')
            return False, []

        update_content = updates.get(update_type.value)
        if update_content is None:
            log.error(f'Remote update {file_url} does not contain {update_type.value} key')
            return False, []

        return True, update_content

    def _update_user_nodes(
            self,
            existing_default_nodes: list[tuple[Any, ...]],
            new_default_nodes: list[tuple[Any, ...]],
    ) -> None:
        """Updates the user nodes using the default nodes from the global db.

        This function does the following:
        1. Compares the previous default rpc nodes to the new ones,
        and the difference is deleted from the user db.
        2. Adds the new default rpc nodes to the user db.

        indexes 1 & 2 -> endpoint of node
        indexes 5 & 6 -> blockchain of node
        """
        # check for nodes to delete for the user
        nodes_to_delete = (
            {(node[2], node[6]) for node in existing_default_nodes} -
            {(node[1], node[5]) for node in new_default_nodes}
        )
        if len(nodes_to_delete) != 0:
            log.debug(f'Deleting {nodes_to_delete} nodes from user database...')
            with self.user_db.user_write() as write_cursor:
                write_cursor.executemany(
                    'DELETE FROM rpc_nodes WHERE endpoint=? AND blockchain=?',
                    list(nodes_to_delete),
                )

        with self.user_db.conn.read_ctx() as cursor:
            user_rpc_nodes = {
                (entry[2], entry[6])
                for entry in cursor.execute('SELECT * FROM rpc_nodes')
            }

        # determine the nodes to add to the user db by
        # checking if it's not already present in the user db.
        nodes_to_add = [
            node_to_add
            for node_to_add in new_default_nodes
            if (node_to_add[1], node_to_add[5]) not in user_rpc_nodes
        ]
        with self.user_db.user_write() as write_cursor:
            log.debug(f'Adding {nodes_to_add} nodes to the user database...')
            write_cursor.executemany(
                'INSERT INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) '  # noqa: E501
                'VALUES(?, ?, ?, ?, ?, ?)',
                nodes_to_add,
            )
