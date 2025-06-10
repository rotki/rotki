"""Repository for data management operations."""
import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.gnosis.constants import BRIDGE_QUERIED_ADDRESS_PREFIX
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.constants import EXTRAINTERNALTXPREFIX
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.loopring import DBLoopring
from rotkehlchen.types import (
    SUPPORTED_EVM_CHAINS_TYPE,
    SUPPORTED_EVMLIKE_CHAINS_TYPE,
    ChecksumEvmAddress,
    Location,
    SupportedBlockchain,
)
from rotkehlchen.utils.misc import get_chunks

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

log = logging.getLogger(__name__)


class DataManagementRepository:
    """Repository for handling data management operations."""

    def __init__(self, db_handler: 'DBHandler') -> None:
        """Initialize the data management repository."""
        self.db = db_handler

    def delete_data_for_evm_address(
            self,
            write_cursor: 'DBCursor',
            address: ChecksumEvmAddress,
            blockchain: SUPPORTED_EVM_CHAINS_TYPE,
    ) -> None:
        """Deletes all evm related data from the DB for a single evm address"""
        if blockchain == SupportedBlockchain.ETHEREUM:  # mainnet only behaviour
            write_cursor.execute('DELETE FROM used_query_ranges WHERE name = ?', (f'aave_events_{address}',))  # noqa: E501
            write_cursor.execute(  # queried addresses per module
                'DELETE FROM multisettings WHERE name LIKE ? ESCAPE ? AND value = ?',
                ('queried\\_address\\_%', '\\', address),
            )
            loopring = DBLoopring(self.db)
            loopring.remove_accountid_mapping(write_cursor, address)
            # Delete withdrawals related data
            self.db.delete_dynamic_cache(write_cursor=write_cursor, name=DBCacheDynamic.WITHDRAWALS_TS, address=address)  # noqa: E501
            self.db.delete_dynamic_cache(write_cursor=write_cursor, name=DBCacheDynamic.WITHDRAWALS_IDX, address=address)  # noqa: E501

        write_cursor.execute(
            'DELETE FROM evm_accounts_details WHERE account=? AND chain_id=?',
            (address, blockchain.to_chain_id().serialize_for_db()),
        )

        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name LIKE ? ESCAPE ? AND value = ?',
            (f'{EXTRAINTERNALTXPREFIX}\\_{blockchain.to_chain_id().value}%', '\\', address),
        )

        dbtx = DBEvmTx(self.db)
        dbtx.delete_transactions(write_cursor=write_cursor, address=address, chain=blockchain)
        if blockchain == SupportedBlockchain.GNOSIS:
            write_cursor.execute(
                'DELETE FROM used_query_ranges WHERE name=?',
                (f'{BRIDGE_QUERIED_ADDRESS_PREFIX}{address}',),
            )

    def delete_data_for_evmlike_address(
            self,
            write_cursor: 'DBCursor',
            address: ChecksumEvmAddress,
            blockchain: SUPPORTED_EVMLIKE_CHAINS_TYPE,  # pylint: disable=unused-argument
    ) -> None:
        """Deletes all evmlike chain related data from the DB for a single evm address

        For now it's always gonna be only zksync lite.
        """
        other_addresses = self.db.get_single_blockchain_addresses(
            cursor=write_cursor,
            blockchain=SupportedBlockchain.ZKSYNC_LITE,
        )
        other_addresses.remove(address)  # exclude the address in question so it's only the others

        # delete events by tx_hash
        write_cursor.execute(
            'SELECT tx_hash, from_address, to_address FROM zksynclite_transactions WHERE '
            'from_address=? OR to_address=?',
            (address, address),
        )
        hashes_to_remove = [
            x[0] for x in write_cursor
            if x[1] not in other_addresses and x[2] not in other_addresses  # pylint: disable=unsupported-membership-test
        ]
        for hashes_chunk in get_chunks(hashes_to_remove, n=1000):  # limit num of hashes in a query
            write_cursor.execute(  # delete transactions themselves
                f'DELETE FROM zksynclite_transactions WHERE tx_hash IN '
                f'({",".join("?" * len(hashes_chunk))})',
                hashes_chunk,
            )
            write_cursor.execute(
                f'DELETE FROM history_events WHERE identifier IN (SELECT H.identifier '
                f'FROM history_events H INNER JOIN evm_events_info E '
                f'ON H.identifier=E.identifier AND E.tx_hash IN '
                f'({", ".join(["?"] * len(hashes_chunk))}) AND H.location=?)',
                hashes_chunk + [Location.ZKSYNC_LITE.serialize_for_db()],
            )