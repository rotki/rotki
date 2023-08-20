import json
import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import requests

from packaging import version as pversion
from rotkehlchen.assets.spam_assets import update_spam_assets
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.settings import CachedSettings
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
from rotkehlchen.utils.version_check import get_current_version

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBCursor, DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

from .constants import LAST_DATA_UPDATES_KEY, UpdateType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


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
        self.update_type_mappings = {  # better than dynamic getattr. More explicit, negligible memory overhead if any  # noqa: E501
            UpdateType.SPAM_ASSETS: self.update_spam_assets,
            UpdateType.RPC_NODES: self.update_rpc_nodes,
            UpdateType.CONTRACTS: self.update_contracts,
            UpdateType.GLOBAL_ADDRESSBOOK: self.update_global_addressbook,
        }  # If we ever change this also change tests/unit/test_data_updates::reset_update_type_mappings  # noqa: E501
        self.version = pversion.parse(get_current_version().our_version)

    def update_single(
            self,
            update_type: UpdateType,
            from_version: int,
            to_version: int,
            limits: dict[str, dict],
    ) -> None:
        """Common code to update a single type of data

        Check the updates in the inclusive range [from_version + 1, to_version] and apply
        the needed updates if any. Also save latest applied update type in the DB.
        """
        for update_version in range(from_version + 1, to_version + 1):
            version_info = limits.get(str(update_version), {})  # json treats keys as string
            min_version = version_info.get('min_version', None)
            if min_version is not None:
                p_min_version = pversion.parse(min_version)
                if p_min_version > self.version:
                    log.warning(f'Not updating {update_type.value} to {update_version=} due to {min_version=}')  # noqa: E501
                    break  # stop iteration since all next versions will also hit this. User needs to update  # noqa: E501

            max_version = version_info.get('max_version', None)
            if max_version is not None:
                p_max_version = pversion.parse(max_version)
                if p_max_version < self.version:
                    log.warning(f'Not updating {update_type.value} to {update_version=} due to {max_version=}')  # noqa: E501
                    continue  # probably can never apply this update. Check next one

            file_url = f'https://raw.githubusercontent.com/rotki/data/{self.branch}/updates/{update_type.value}/v{update_version}.json'  # noqa: E501
            try:
                updates = query_file(file_url, True)
            except RemoteError as e:
                log.warning(f'Failed to update {update_type.value} due to {e!s}')
                continue  # perhaps broken file? Skipping

            updated_data = updates.get(update_type.value)
            if updated_data is None:
                log.error(f'Remote update {file_url} does not contain {update_type.value} key')
                continue  # perhaps broken file? Skipping

            # At this point we can apply the update. Type ignore is due to different sigs of data
            self.update_type_mappings[update_type](updated_data, update_version)  # type: ignore
            with self.user_db.conn.write_ctx() as write_cursor:
                write_cursor.execute(  # this was the last update to be applied for this data type, so remember it  # noqa: E501
                    'INSERT OR REPLACE INTO settings(name, value) VALUES (?, ?)',
                    (update_type.serialize(), update_version),
                )

    def _get_remote_info_json(self) -> dict[str, Any]:
        """Retrieve remote file with information for different updates

        May raise RemoteError if anything is wrong contacting github
        """
        url = f'https://raw.githubusercontent.com/rotki/data/{self.branch}/updates/info.json'
        try:
            response = requests.get(url=url, timeout=CachedSettings().get_timeout_tuple())
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Failed to query {url} during assets update: {e!s}') from e

        try:
            json_data = response.json()
        except json.decoder.JSONDecodeError as e:
            raise RemoteError(
                f'Could not parse update info from {url} as json: {response.text}',
            ) from e

        return json_data

    def update_spam_assets(self, data: list[dict[str, Any]], version: int) -> None:
        """
        Spam assets update code. Assets are also added to the globaldb if they don't exist
        locally
        """
        log.info(f'Applying update for spam assets to v{version}. {len(data)} tokens to add')  # noqa: E501
        with GlobalDBHandler().conn.critical_section():
            # Use a critical section to avoid another greenlet adding spam assets at
            # the same time
            update_spam_assets(db=self.user_db, assets_info=data)

    def update_rpc_nodes(self, data: list[dict[str, Any]], version: int) -> None:
        """RPC nodes update code. It also updates the user db with these default nodes."""
        log.info(f'Applying update for rpc nodes to v{version}')
        new_default_nodes: list[tuple[Any, ...]] = [
            (
                node['name'],
                node['endpoint'],
                node['owned'],
                node['active'],
                str(FVal(node['weight'])),
                node['blockchain'],
            )
            for node in data
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

        self._update_user_nodes(
            existing_default_nodes=existing_default_nodes,
            new_default_nodes=new_default_nodes,
        )

    def update_contracts(self, data: dict[str, Any], version: int) -> None:
        """
        Updates evm contracts and ABIs in globaldb.
        If an ABI already exists in the db, it is reused.
        If a contract (address + chain id) exists, it is replaced by the remote counterpart.
        """
        log.info(f'Applying update for contracts to v{version}')
        remote_id_to_local_id = {}
        for single_abi_data in data['abis_data']:
            # store a mapping of the virtual id to the id in the user's globaldb
            abi_id = GlobalDBHandler().get_or_write_abi(
                serialized_abi=single_abi_data['value'],
                abi_name=single_abi_data.get('name'),
            )
            remote_id_to_local_id[single_abi_data['id']] = abi_id

        new_contracts_data = []
        for single_contract_data in data['contracts_data']:
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

    def update_global_addressbook(self, data: list[dict[str, Any]], version: int) -> None:
        """Applies global addressbook updates"""
        log.info(f'Applying update for addressbook to v{version}')
        db_addressbook = DBAddressbook(self.user_db)
        entries_to_add = []
        for raw_entry in data:
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
            # skip updates, but write last data update to not spam periodic tasks
        else:
            for update_type in updates:
                try:
                    info = remote_information[update_type.value]
                    latest_version = info['latest']
                except KeyError as e:
                    log.error(f'Could not find key {e} in remote update info file for {update_type.value}')  # noqa: E501
                    continue
                limits = info.get('limits', {})

                # Get latest applied version
                with self.user_db.conn.read_ctx() as cursor:
                    local_version = self._check_for_last_version(
                        cursor=cursor,
                        update_type=update_type,
                    )

                # Update all remote data
                if local_version < latest_version:
                    self.update_single(
                        update_type=update_type,
                        from_version=local_version,
                        to_version=latest_version,
                        limits=limits,
                    )

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
