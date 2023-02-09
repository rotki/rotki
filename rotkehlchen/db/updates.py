import json
import logging
import sys
from enum import Enum
from typing import TYPE_CHECKING, Any

import requests

from rotkehlchen.assets.spam_assets import update_spam_assets
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.network import query_file

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

LAST_DATA_UPDATES_KEY = 'last_data_updates_ts'
SPAM_ASSETS_URL = 'https://raw.githubusercontent.com/rotki/data/{branch}/updates/spam_assets/assets_v{version}.json'  # noqa: E501


class UpdateType(Enum):
    SPAM_ASSETS = 'spam_assets'
    RPC_NODES = 'rpc_nodes'
    CONTRACTS = 'contracts'

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
        self.branch = 'main'
        if not getattr(sys, 'frozen', False):
            # not packaged -- must be in develop mode
            self.branch = 'develop'

    def _get_remote_info_json(self) -> dict[str, Any]:
        """Retrieve remote file with information for different updates"""
        url = f'https://raw.githubusercontent.com/rotki/data/{self.branch}/updates/info.json'
        try:
            response = requests.get(url=url, timeout=DEFAULT_TIMEOUT_TUPLE)
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Failed to query {url} during assets update: {str(e)}') from e

        try:
            json_data = response.json()
        except json.decoder.JSONDecodeError as e:
            raise RemoteError(
                f'Could not parse update info from {url} as json: {response.text}',
            ) from e

        return json_data

    def update_spam_assets(self, local_version: int, to_version: int) -> None:
        """
        Check the updates in the inclusive range [local_version + 1, to_version] and update the
        spam assets for those versions. Assets are also added to the globaldb if they don't exist
        locally
        """
        for version in range(local_version + 1, to_version + 1):
            file_url = SPAM_ASSETS_URL.format(branch=self.branch, version=version)
            try:
                updates = query_file(file_url, is_json=True)
            except RemoteError as e:
                log.warning(f'Failed to update spam assets due to {str(e)}')
                break
            updated_assets = updates.get('assets')
            if updated_assets is None:
                log.error(f'Remote update {file_url} does not contain the assets key')
                continue

            log.info(f'Applying update for spam assets from {version}. {len(updates)} tokens to add')  # noqa: E501
            with GlobalDBHandler().conn.critical_section():
                # Use a critical section to avoid another greenlet adding spam assets at
                # the same time
                update_spam_assets(db=self.user_db, assets_info=updates['assets'])

            with self.user_db.conn.write_ctx() as write_cursor:
                write_cursor.execute(
                    'INSERT OR REPLACE INTO settings(name, value) VALUES (?, ?)',
                    (UpdateType.SPAM_ASSETS.serialize(), version),
                )

    def check_for_updates(self) -> None:
        """Retrieve the information about the latest available update"""
        remote_information = self._get_remote_info_json()

        # Get latest applied versions
        with self.user_db.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT value FROM settings WHERE name=?',
                (UpdateType.SPAM_ASSETS.serialize(),),
            )
            last_version = cursor.fetchone()
        local_spam_assets_version = int(last_version[0]) if last_version is not None else 0

        # update spam assets
        latest_spam_assets_version = remote_information[UpdateType.SPAM_ASSETS.value]['latest']
        if local_spam_assets_version < latest_spam_assets_version:
            self.update_spam_assets(local_spam_assets_version, latest_spam_assets_version)
