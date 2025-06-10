"""Repository for managing Bitcoin xpub operations in the database."""
import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.bitcoin.hdkey import HDKey
from rotkehlchen.chain.bitcoin.xpub import XpubData, XpubDerivedAddressData
from rotkehlchen.db.utils import (
    deserialize_derivation_path_for_db,
    deserialize_tags_from_db,
    replace_tag_mappings,
)
from rotkehlchen.errors.misc import InputError
from rotkehlchen.types import BTCAddress, SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.user_messages import MessagesAggregator


log = logging.getLogger(__name__)


class XpubRepository:
    """Repository for handling all xpub-related operations."""

    def __init__(self, msg_aggregator: 'MessagesAggregator') -> None:
        """Initialize the xpub repository."""
        self.msg_aggregator = msg_aggregator

    def add(self, write_cursor: 'DBCursor', xpub_data: XpubData) -> None:
        """Add the xpub to the DB

        May raise:
        - InputError if the xpub data already exist
        """
        try:
            write_cursor.execute(
                'INSERT INTO xpubs(xpub, derivation_path, label, blockchain) '
                'VALUES (?, ?, ?, ?)',
                (
                    xpub_data.xpub.xpub,
                    xpub_data.serialize_derivation_path_for_db(),
                    xpub_data.label,
                    xpub_data.blockchain.value,
                ),
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'Xpub {xpub_data.xpub.xpub} for {xpub_data.blockchain.value} with '
                f'derivation path {xpub_data.derivation_path} is already tracked',
            ) from e

    def delete(self, write_cursor: 'DBCursor', xpub_data: XpubData) -> None:
        """Deletes an xpub from the DB. Also deletes all derived addresses and mappings

        May raise:
        - InputError if the xpub does not exist in the DB
        """
        write_cursor.execute(
            'SELECT COUNT(*) FROM xpubs WHERE xpub=? AND derivation_path IS ? AND blockchain=?;',
            (
                xpub_data.xpub.xpub,
                xpub_data.serialize_derivation_path_for_db(),
                xpub_data.blockchain.value,
            ),
        )
        if write_cursor.fetchone()[0] == 0:
            derivation_str = (
                'no derivation path' if xpub_data.derivation_path is None else
                f'derivation path {xpub_data.derivation_path}'
            )
            raise InputError(
                f'Tried to remove non existing xpub {xpub_data.xpub.xpub} '
                f'for {xpub_data.blockchain!s} with {derivation_str}',
            )

        # Delete the tag mappings for all derived addresses
        write_cursor.execute(
            'DELETE FROM tag_mappings WHERE '
            'object_reference IN ('
            'SELECT address from xpub_mappings WHERE xpub=? AND derivation_path IS ? AND blockchain IS ?);',  # noqa: E501
            (
                xpub_data.xpub.xpub,
                xpub_data.serialize_derivation_path_for_db(),
                xpub_data.blockchain.value,
            ),
        )
        # Delete the tag mappings for the xpub itself (type ignore is for xpub is not None
        key = xpub_data.xpub.xpub + xpub_data.serialize_derivation_path_for_db()  # type: ignore
        write_cursor.execute('DELETE FROM tag_mappings WHERE object_reference=?', (key,))
        # Delete any derived addresses
        write_cursor.execute(
            'DELETE FROM blockchain_accounts WHERE blockchain=? AND account IN ('
            'SELECT address from xpub_mappings WHERE xpub=? AND derivation_path IS ? AND blockchain=?);',  # noqa: E501
            (
                xpub_data.blockchain.value,
                xpub_data.xpub.xpub,
                xpub_data.serialize_derivation_path_for_db(),
                xpub_data.blockchain.value,
            ),
        )
        # And then finally delete the xpub itself
        write_cursor.execute(
            'DELETE FROM xpubs WHERE xpub=? AND derivation_path IS ? AND blockchain=?;',
            (
                xpub_data.xpub.xpub,
                xpub_data.serialize_derivation_path_for_db(),
                xpub_data.blockchain.value,
            ),
        )

    def edit(self, write_cursor: 'DBCursor', xpub_data: XpubData) -> None:
        """Edit the xpub tags and label

        May raise:
        - InputError if the xpub data already exist
        """
        try:
            write_cursor.execute(
                'SELECT address from xpub_mappings WHERE xpub=? AND derivation_path IS ? AND blockchain=?',  # noqa: E501
                (
                    xpub_data.xpub.xpub,
                    xpub_data.serialize_derivation_path_for_db(),
                    xpub_data.blockchain.value,
                ),
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'Xpub {xpub_data.xpub} for {xpub_data.blockchain.value} with '
                f'derivation path {xpub_data.derivation_path} is not tracked',
            ) from e

        addresses_data = [
            BlockchainAccountData(
                chain=xpub_data.blockchain,
                address=x[0],
                tags=xpub_data.tags,
            )
            for x in write_cursor
        ]
        # Update tag mappings of the derived addresses
        replace_tag_mappings(
            write_cursor=write_cursor,
            data=addresses_data,
            object_reference_keys=['address'],
        )
        key = xpub_data.xpub.xpub + xpub_data.serialize_derivation_path_for_db()  # type: ignore
        # Delete the tag mappings for the xpub itself (type ignore is for xpub is not None)
        write_cursor.execute('DELETE FROM tag_mappings WHERE object_reference=?', (key,))
        replace_tag_mappings(
            # if we got tags add them to the xpub
            write_cursor=write_cursor,
            data=[xpub_data],
            object_reference_keys=['xpub.xpub', 'derivation_path'],
        )
        write_cursor.execute(
            'UPDATE xpubs SET label=? WHERE xpub=? AND derivation_path=? AND blockchain=?',
            (
                xpub_data.label,
                xpub_data.xpub.xpub,
                xpub_data.serialize_derivation_path_for_db(),
                xpub_data.blockchain.value,
            ),
        )

    def get_all(
            self,
            cursor: 'DBCursor',
            blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
    ) -> list[XpubData]:
        query = cursor.execute(
            "SELECT A.xpub, A.blockchain, A.derivation_path, A.label, "
            "group_concat(B.tag_name,',') FROM xpubs as A LEFT OUTER JOIN tag_mappings AS B ON "
            "B.object_reference = A.xpub || A.derivation_path WHERE A.blockchain=? GROUP BY A.xpub || A.derivation_path",  # noqa: E501
            (blockchain.value,),
        )
        result = []
        for entry in query:
            tags = deserialize_tags_from_db(entry[4])
            result.append(XpubData(
                xpub=HDKey.from_xpub(entry[0], path='m'),
                blockchain=SupportedBlockchain.deserialize(entry[1]),  # type: ignore
                derivation_path=deserialize_derivation_path_for_db(entry[2]),
                label=entry[3],
                tags=tags,
            ))

        return result

    def get_last_consecutive_derived_indices(
            self, cursor: 'DBCursor', xpub_data: XpubData,
    ) -> tuple[int, int]:
        """
        Get the last known receiving and change derived indices from the given
        xpub that are consecutive since the beginning.

        For example if we have derived indices 0, 1, 4, 5 then this will return 1.

        This tells us from where to start deriving again safely
        """
        returned_indices = []
        for acc_idx in (0, 1):
            query = cursor.execute(
                'SELECT derived_index from xpub_mappings WHERE xpub=? AND '
                'derivation_path IS ? AND account_index=? AND blockchain = ?;',
                (
                    xpub_data.xpub.xpub,
                    xpub_data.serialize_derivation_path_for_db(),
                    acc_idx,
                    xpub_data.blockchain.value,
                ),
            )
            prev_index = -1
            for result in query:
                index = int(result[0])
                if index != prev_index + 1:
                    break

                prev_index = index

            returned_indices.append(0 if prev_index == -1 else prev_index)

        return tuple(returned_indices)  # type: ignore

    def get_addresses_to_xpub_mapping(
            self,
            cursor: 'DBCursor',
            blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
            addresses: Sequence[BTCAddress],
    ) -> dict[BTCAddress, XpubData]:
        data = {}
        for address in addresses:
            cursor.execute(
                'SELECT B.address, A.xpub, A.derivation_path FROM xpubs as A '
                'LEFT OUTER JOIN xpub_mappings as B '
                'ON B.xpub = A.xpub AND B.derivation_path IS A.derivation_path AND B.blockchain = A.blockchain '  # noqa: E501
                'WHERE B.address=? AND B.blockchain=?;', (address, blockchain.value),
            )
            result = cursor.fetchall()
            if len(result) == 0:
                continue

            data[result[0][0]] = XpubData(
                xpub=HDKey.from_xpub(result[0][1], path='m'),
                blockchain=blockchain,
                derivation_path=deserialize_derivation_path_for_db(result[0][2]),
            )

        return data

    def ensure_mappings_exist(
            self,
            write_cursor: 'DBCursor',
            xpub_data: XpubData,
            derived_addresses_data: list['XpubDerivedAddressData'],
    ) -> None:
        """Create if not existing the mappings between the addresses and the xpub"""
        tuples = [
            (
                x.address,
                xpub_data.xpub.xpub,
                '' if xpub_data.derivation_path is None else xpub_data.derivation_path,
                x.account_index,
                x.derived_index,
                xpub_data.blockchain.value,
            ) for x in derived_addresses_data
        ]
        for entry in tuples:
            try:
                write_cursor.execute(
                    'INSERT INTO xpub_mappings'
                    '(address, xpub, derivation_path, account_index, derived_index, blockchain) '
                    'VALUES (?, ?, ?, ?, ?, ?)',
                    entry,
                )
            except sqlcipher.IntegrityError:  # pylint: disable=no-member
                # mapping already exists
                continue
