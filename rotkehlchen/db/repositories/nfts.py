"""Repository for managing NFT operations in the database."""
from typing import TYPE_CHECKING

from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants.misc import NFT_DIRECTIVE

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


class NFTRepository:
    """Repository for handling all NFT-related operations."""

    def get_nft_mappings(
            self,
            cursor: 'DBCursor',
            identifiers: list[str],
    ) -> dict[str, dict]:
        """
        Given a list of nft identifiers, return a list of nft info (id, name, collection_name)
        for those identifiers.
        """
        cursor.execute(
            f'SELECT identifier, name, collection_name, image_url FROM nfts WHERE '
            f'identifier IN ({",".join("?" * len(identifiers))})',
            identifiers,
        )

        serialized_nft_type = AssetType.NFT.serialize()
        return {
            entry[0]: {
                'name': entry[1],
                'asset_type': serialized_nft_type,
                'collection_name': entry[2],
                'image_url': entry[3],
            } for entry in cursor
        }

    def add_nft_data(
            self,
            write_cursor: 'DBCursor',
            identifier: str,
            name: str | None,
            collection_name: str | None,
            image_url: str | None,
    ) -> None:
        """Add NFT data to the database."""
        write_cursor.execute(
            'INSERT OR IGNORE INTO nfts(identifier, name, collection_name, image_url) '
            'VALUES (?, ?, ?, ?)',
            (identifier, name, collection_name, image_url),
        )

    def get_owned_nfts(
            self,
            cursor: 'DBCursor',
    ) -> dict[str, list[dict[str, str]]]:
        """Get all owned NFTs from the database."""
        cursor.execute(
            'SELECT B.address, A.identifier FROM evm_tokens AS A JOIN blockchain_accounts AS B '
            'ON A.address = B.account WHERE A.token_kind="erc721"',
        )
        # Address to NFT id list mapping
        mapping: dict[str, list[dict[str, str]]] = {}
        for address, identifier in cursor:
            address = address.lower()
            identifier_without_chain = identifier.removeprefix(NFT_DIRECTIVE)
            if address in mapping:
                mapping[address].append({'id': identifier_without_chain})
            else:
                mapping[address] = [{'id': identifier_without_chain}]

        return mapping