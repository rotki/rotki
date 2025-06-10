"""Repository for managing blockchain accounts in the database."""
import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.accounts import (
    BlockchainAccountData,
    BlockchainAccounts,
    SingleBlockchainAccountData,
)
from rotkehlchen.chain.evm.types import ChecksumEvmAddress
from rotkehlchen.db.constants import (
    EVM_ACCOUNTS_DETAILS_LAST_QUERIED_TS,
    EVM_ACCOUNTS_DETAILS_TOKENS,
)
from rotkehlchen.db.utils import (
    insert_tag_mappings,
    is_valid_db_blockchain_account,
    replace_tag_mappings,
)
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import (
    ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE,
    SUPPORTED_EVM_CHAINS,
    BlockchainAddress,
    ListOfBlockchainAddresses,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.user_messages import MessagesAggregator

log = logging.getLogger(__name__)


class AccountsRepository:
    """Repository for handling all blockchain account operations."""

    def __init__(self, msg_aggregator: 'MessagesAggregator') -> None:
        """Initialize the accounts repository."""
        self.msg_aggregator = msg_aggregator

    def add(
            self,
            write_cursor: 'DBCursor',
            account_data: list[BlockchainAccountData],
    ) -> None:
        """Add blockchain accounts to the database."""
        # Insert the blockchain account addresses and labels to the DB
        blockchain_accounts_query, bindings_to_insert = [], []
        for entry in account_data:
            blockchain_accounts_query.append((entry.chain.value, entry.address))
            if entry.label:
                bindings_to_insert.append((entry.address, entry.chain.value, entry.label))
        try:
            write_cursor.executemany(
                'INSERT INTO blockchain_accounts(blockchain, account) VALUES (?, ?)',
                blockchain_accounts_query,
            )
            if len(bindings_to_insert) > 0:
                write_cursor.executemany(
                    'INSERT OR REPLACE INTO address_book(address, blockchain, name) VALUES (?, ?, ?)',  # noqa: E501
                    bindings_to_insert,
                )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'Blockchain account/s {[x.address for x in account_data]} already exist',
            ) from e

        insert_tag_mappings(write_cursor=write_cursor, data=account_data, object_reference_keys=['address'])  # noqa: E501

    def edit(
            self,
            write_cursor: 'DBCursor',
            account_data: list[BlockchainAccountData],
    ) -> None:
        """Edit the given blockchain accounts.

        At this point in the calling chain we should already know that:
        - All tags exist in the DB
        - All accounts exist in the DB
        """
        # Update the blockchain account labels in the DB
        bindings_to_update, bindings_to_delete = [], []
        for entry in account_data:
            if entry.label:
                bindings_to_update.append((entry.address, entry.chain.value, entry.label))
            else:
                bindings_to_delete.append((entry.address, entry.chain.value))

        modified_count, deleted_count = 0, 0
        if len(bindings_to_update) > 0:
            write_cursor.executemany(
                'INSERT OR REPLACE INTO address_book(address, blockchain, name) VALUES (?, ?, ?);',
                bindings_to_update,
            )
            modified_count += write_cursor.rowcount

        if len(bindings_to_delete) > 0:
            write_cursor.executemany(
                'DELETE FROM address_book WHERE address=? AND blockchain=?;',
                bindings_to_delete,
            )
            deleted_count += write_cursor.rowcount

        if modified_count != len(bindings_to_update):
            msg = (
                f'When updating blockchain accounts expected {len(bindings_to_update)} '
                f'modified, but instead there were {modified_count}. Should not happen.'
            )
            log.error(msg)
            raise InputError(msg)

        if deleted_count != len(bindings_to_delete):
            msg = (
                f'When updating blockchain accounts expected {len(bindings_to_delete)} '
                f'deleted, but instead there were {deleted_count}. Should not happen.'
            )
            log.error(msg)
            raise InputError(msg)

        replace_tag_mappings(
            write_cursor=write_cursor,
            data=account_data,
            object_reference_keys=['address'],
        )

    def remove_single_blockchain(
            self,
            write_cursor: 'DBCursor',
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
    ) -> None:
        """Removes the given blockchain accounts from the DB.

        May raise:
        - InputError if any of the given accounts to delete did not exist
        """
        # Assure all are there
        accounts_number = write_cursor.execute(
            f'SELECT COUNT(*) from blockchain_accounts WHERE blockchain = ? '
            f'AND account IN ({",".join("?" * len(accounts))})',
            (blockchain.value, *accounts),
        ).fetchone()[0]
        if accounts_number != len(accounts):
            raise InputError(
                f'Tried to remove {len(accounts) - accounts_number} '
                f'{blockchain.value} accounts that do not exist',
            )

        tuples = [(blockchain.value, x) for x in accounts]

        write_cursor.executemany(
            'DELETE FROM tag_mappings WHERE object_reference = ?;',
            [(account,) for account in accounts],
        )
        write_cursor.executemany(
            'DELETE FROM blockchain_accounts WHERE '
            'blockchain = ? and account = ?;', tuples,
        )

    def get_tokens_for_address(
            self,
            cursor: 'DBCursor',
            address: ChecksumEvmAddress,
            blockchain: SupportedBlockchain,
            token_exceptions: set[ChecksumEvmAddress],
    ) -> tuple[list[EvmToken] | None, Timestamp | None]:
        """Gets the detected tokens for the given address if the given current time
        is recent enough.

        If not, or if there is no saved entry, return None.
        """
        last_queried_ts = None
        querystr = (
            "SELECT key, value FROM evm_accounts_details WHERE account=? AND chain_id=? "
            "AND (key=? OR key=?) AND value NOT IN "
            "(SELECT value FROM multisettings WHERE name='ignored_asset')"
        )
        bindings = (address, blockchain.to_chain_id().serialize_for_db(), EVM_ACCOUNTS_DETAILS_LAST_QUERIED_TS, EVM_ACCOUNTS_DETAILS_TOKENS)  # noqa: E501
        cursor.execute(querystr, bindings)

        returned_list = []
        for (key, value) in cursor:
            if key == EVM_ACCOUNTS_DETAILS_LAST_QUERIED_TS:
                # At the moment last_queried_timestamp is not used. It used to be a cache for the
                # query but since we made token detection not run it is no longer used, but is
                # written. This will probably change in the future again. Related issue:
                # https://github.com/rotki/rotki/issues/5252
                last_queried_ts = deserialize_timestamp(value)
            else:  # should be EVM_ACCOUNTS_DETAILS_TOKENS
                try:
                    # This method is used directly when querying the balances and it is easier
                    # to resolve the token here
                    token = EvmToken(value)
                except (DeserializationError, UnknownAsset):
                    self.msg_aggregator.add_warning(
                        f'Could not deserialize {value} as a token when reading latest '
                        f'tokens list of {address}',
                    )
                    continue

                if token.evm_address not in token_exceptions:
                    returned_list.append(token)

        if len(returned_list) == 0 and last_queried_ts is None:
            return None, None

        return returned_list, last_queried_ts

    def save_tokens_for_address(
            self,
            write_cursor: 'DBCursor',
            address: ChecksumEvmAddress,
            blockchain: SupportedBlockchain,
            tokens: Sequence[Asset],
    ) -> None:
        """Saves detected tokens for an address"""
        now = ts_now()
        chain_id = blockchain.to_chain_id().serialize_for_db()
        insert_rows: list[tuple[ChecksumEvmAddress, int, str, str | Timestamp]] = [
            (
                address,
                chain_id,
                EVM_ACCOUNTS_DETAILS_TOKENS,
                x.identifier,
            )
            for x in tokens
        ]
        # Also add the update row for the timestamp
        insert_rows.append(
            (
                address,
                chain_id,
                EVM_ACCOUNTS_DETAILS_LAST_QUERIED_TS,
                now,
            ),
        )
        # Delete previous entries for tokens
        write_cursor.execute(
            'DELETE FROM evm_accounts_details WHERE account=? AND chain_id=? AND KEY IN(?, ?)',
            (address, chain_id, EVM_ACCOUNTS_DETAILS_TOKENS, EVM_ACCOUNTS_DETAILS_LAST_QUERIED_TS),
        )
        # Insert new values
        write_cursor.executemany(
            'INSERT OR REPLACE INTO evm_accounts_details '
            '(account, chain_id, key, value) VALUES (?, ?, ?, ?)',
            insert_rows,
        )

    def _deserialize_account_blockchain_from_db(
            self,
            chain_str: str,
            account: str,
    ) -> SupportedBlockchain | None:
        try:
            blockchain = SupportedBlockchain.deserialize(chain_str)
        except DeserializationError:
            log.warning(f'Unsupported blockchain {chain_str} found in DB. Ignoring...')
            return None

        if blockchain is None or is_valid_db_blockchain_account(blockchain=blockchain, account=account) is False:  # noqa: E501
            self.msg_aggregator.add_warning(
                f'Invalid {chain_str} account in DB: {account}. '
                f'This should not happen unless the DB was manually modified. '
                f'Skipping entry. This needs to be fixed manually. If you '
                f'can not do that alone ask for help in the issue tracker',
            )
            return None

        return blockchain

    def get_blockchains_for_accounts(
            self,
            cursor: 'DBCursor',
            accounts: list[BlockchainAddress],
    ) -> list[tuple[BlockchainAddress, SupportedBlockchain]]:
        """Gets all blockchains for the specified accounts.
        Returns a list of tuples containing the address and blockchain entries.
        """
        return [
            (account, blockchain)
            for entry in cursor.execute(
                'SELECT blockchain, account FROM blockchain_accounts '
                f"WHERE account IN ({','.join(['?'] * len(accounts))});",
                accounts,
            )
            if (blockchain := self._deserialize_account_blockchain_from_db(
                chain_str=entry[0],
                account=(account := entry[1]),
            )) is not None
        ]

    def get_evm_accounts(self, cursor: 'DBCursor') -> list[ChecksumEvmAddress]:
        """Returns a list of unique EVM accounts from all EVM chains."""
        placeholders = ','.join('?' * len(SUPPORTED_EVM_CHAINS))
        cursor.execute(
            f'SELECT DISTINCT account FROM blockchain_accounts WHERE blockchain IN ({placeholders});',  # noqa: E501
            [chain.value for chain in SUPPORTED_EVM_CHAINS],
        )
        return [entry[0] for entry in cursor]

    def get_all(self, cursor: 'DBCursor') -> BlockchainAccounts:
        """Returns a Blockchain accounts instance containing all blockchain account addresses"""
        cursor.execute(
            'SELECT blockchain, account FROM blockchain_accounts;',
        )
        accounts_lists = defaultdict(list)
        for entry in cursor:
            if (blockchain := self._deserialize_account_blockchain_from_db(
                chain_str=entry[0],
                account=(account := entry[1]),
            )) is not None:
                accounts_lists[blockchain.get_key()].append(account)

        return BlockchainAccounts(**{x: tuple(y) for x, y in accounts_lists.items()})

    def get_account_data(
            self,
            cursor: 'DBCursor',
            blockchain: SupportedBlockchain,
    ) -> list[SingleBlockchainAccountData]:
        """Returns account data for a particular blockchain.

        Each account entry contains address and potentially label and tags
        """
        query = cursor.execute(
            "SELECT A.account, C.name, group_concat(B.tag_name,',') "
            "FROM blockchain_accounts AS A "
            "LEFT OUTER JOIN tag_mappings AS B ON B.object_reference = A.account "
            "LEFT OUTER JOIN address_book AS C ON C.address = A.account AND (A.blockchain IS C.blockchain OR C.blockchain IS ?) "  # noqa: E501
            "WHERE A.blockchain = ? GROUP BY account;",
            (ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE, blockchain.value),
        )
        data = []
        for address, label, tags_string in query:
            tags = tags_string.split(',') if tags_string else None
            data.append(SingleBlockchainAccountData(address=address, label=label, tags=tags))

        return data

    def get_single_addresses(
            self,
            cursor: 'DBCursor',
            blockchain: SupportedBlockchain,
    ) -> ListOfBlockchainAddresses:
        """Returns a list of addresses for a single blockchain

        May raise:
        - DeserializationError if there is an issue with address deserialization
        """
        cursor.execute(
            'SELECT account FROM blockchain_accounts WHERE blockchain = ?;',
            (blockchain.value,),
        )
        return [entry[0] for entry in cursor]
