import abc
import logging
import re
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from rotkehlchen.assets.types import AssetType
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChainID, ChecksumEvmAddress, Timestamp, TokenKind

from .types import VersionRange

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.db.drivers.gevent import DBConnection

T = TypeVar('T')

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BaseAssetParser(abc.ABC, Generic[T]):
    """Base assets parser with common parsing functionality.

    This was introduced to handle asset updates that need to be applied
    before global db schema version changes. By having dedicated parser classes for different
    data types (assets, collections, mappings), we can ensure compatible updates
    are applied before the schema transitions to a new version.
    """
    def __init__(self) -> None:
        self._double_quotes_re = re.compile(r'\"(.*?)\"')
        self._string_re = re.compile(r'.*([\'"])(.*?)\1.*')
        self._version_parsers: list[tuple[VersionRange, Callable]] = []

    def parse(self, insert_text: str, version: int, connection: 'DBConnection') -> T:
        for version_range, parser in self._version_parsers:
            if version_range.contains(version):
                return parser(insert_text=insert_text, connection=connection)

        assert False, f'No parser found for version {version}. One needs to be implemented and configured'  # noqa: E501, PT015, B011

    def _parse_value(self, value: str) -> str | int | None:
        match = self._string_re.match(value)
        if match is not None:
            return match.group(2)

        value = value.strip()
        if value == 'NULL':
            return None

        try:
            return int(value)
        except ValueError:
            return value

    def _parse_str(self, value: str, name: str, insert_text: str) -> str:
        result = self._parse_value(value)
        if not isinstance(result, str):
            raise DeserializationError(
                f'Got invalid {name} {value} from {insert_text}',
            )
        return result

    def _parse_optional_str(self, value: str, name: str, insert_text: str) -> str | None:
        result = self._parse_value(value)
        if result is not None and not isinstance(result, str):
            raise DeserializationError(
                f'Got invalid {name} {value} from {insert_text}',
            )
        return result

    def _parse_optional_int(self, value: str, name: str, insert_text: str) -> int | None:
        result = self._parse_value(value)
        if result is not None and not isinstance(result, int):
            raise DeserializationError(
                f'Got invalid {name} {value} from {insert_text}',
            )
        return result

    def standardize_quotes(self, text: str) -> str:
        """Convert double quotes to single quotes for consistency.

        We enforce single quotes for all SQL values. If any old updates
        come with double quotes, we convert them here.
        """
        def replace_double_quotes(match_result: re.Match[str]) -> str:
            content = match_result.group(1).replace("'", "''")
            return f"'{content}'"

        return self._double_quotes_re.sub(replace_double_quotes, text)


class AssetParser(BaseAssetParser[dict[str, Any]]):
    """Parser for assets introduced in global db v3 (assets v15+)."""

    def __init__(self) -> None:
        super().__init__()
        self._assets_re = re.compile(r'.*INSERT +INTO +assets *\( *identifier *, *name *, *type *\) *VALUES *\(([^,]*?),([^,]*?),([^,]*?)\).*?')  # noqa: E501
        self._common_details_re = re.compile(r'.*INSERT +INTO +common_asset_details *\( *identifier *, *symbol *, *coingecko *, *cryptocompare *, *forked *, *started *, *swapped_for *\) *VALUES *\((.*?),(.*?),(.*?),(.*?),(.*?),([^,]*?),([^,]*?)\).*')  # noqa: E501
        self._evm_tokens_re = re.compile(r'.*INSERT +INTO +evm_tokens *\( *identifier *, *token_kind *, *chain *, *address *, *decimals *, *protocol *\) *VALUES *\(([^,]*?),([^,]*?),([^,]*?),([^,]*?),([^,]*?),([^,]*?)\).*')  # noqa: E501
        self._version_parsers = [
            (VersionRange(15, None), self._parse),
        ]

    def _parse(self, connection: 'DBConnection', insert_text: str) -> dict[str, Any]:
        asset_data = self._parse_asset_data(insert_text)
        address = decimals = protocol = chain_id = token_kind = None
        if asset_data['asset_type'] == AssetType.EVM_TOKEN:
            address, decimals, protocol, chain_id, token_kind = self._parse_evm_token_data(insert_text)  # noqa: E501

        return {
            'identifier': asset_data['identifier'],
            'name': asset_data['name'],
            'symbol': asset_data['symbol'],
            'asset_type': asset_data['asset_type'],
            'started': asset_data['started'],
            'forked': asset_data['forked'],
            'swapped_for': asset_data['swapped_for'],
            'address': address,
            'chain_id': chain_id,
            'token_kind': token_kind,
            'decimals': decimals,
            'cryptocompare': asset_data['cryptocompare'],
            'coingecko': asset_data['coingecko'],
            'protocol': protocol,
        }

    def _parse_asset_data(self, insert_text: str) -> dict[str, Any]:
        """Parse basic asset data for format"""
        assets_match = self._assets_re.match(insert_text)
        if assets_match is None:
            raise DeserializationError(
                f'At asset DB update could not parse asset data out of {insert_text}',
            )
        if len(assets_match.groups()) != 3:
            raise DeserializationError(
                f'At asset DB update could not parse asset data out of {insert_text}',
            )

        raw_type = self._parse_str(assets_match.group(3), 'asset type', insert_text)
        asset_type = AssetType.deserialize_from_db(raw_type)
        common_details_match = self._common_details_re.match(insert_text)
        if common_details_match is None:
            raise DeserializationError(
                f'At asset DB update could not parse common asset '
                f'details data out of {insert_text}',
            )

        raw_started = self._parse_optional_int(common_details_match.group(6), 'started', insert_text)  # noqa: E501
        started = Timestamp(raw_started) if raw_started else None
        return {
            'identifier': self._parse_str(common_details_match.group(1), 'identifier', insert_text),  # noqa: E501
            'asset_type': asset_type,
            'name': self._parse_str(assets_match.group(2), 'name', insert_text),
            'symbol': self._parse_str(common_details_match.group(2), 'symbol', insert_text),
            'started': started,
            'swapped_for': self._parse_optional_str(
                common_details_match.group(7),
                'swapped_for',
                insert_text,
            ),
            'coingecko': self._parse_optional_str(
                common_details_match.group(3),
                'coingecko',
                insert_text,
            ),
            'cryptocompare': self._parse_optional_str(
                common_details_match.group(4),
                'cryptocompare',
                insert_text,
            ),
            'forked': self._parse_optional_str(
                common_details_match.group(5),
                'forked',
                insert_text,
            ),
            'chain_id': None,
            'address': None,
            'token_kind': None,
            'decimals': None,
            'protocol': None,
        }

    def _parse_evm_token_data(
            self,
            insert_text: str,
    ) -> tuple[ChecksumEvmAddress, int | None, str | None, ChainID | None, TokenKind | None]:
        """Read information related to evm assets from the insert line.
        May raise:
            - DeserializationError: if the regex didn't work or we failed to deserialize any value
        """
        match = self._evm_tokens_re.match(insert_text)
        if match is None:
            raise DeserializationError(
                f'At asset DB update could not parse evm token data out '
                f'of {insert_text}',
            )

        if len(match.groups()) != 6:
            raise DeserializationError(
                f'At asset DB update could not parse evm token data out of {insert_text}',
            )

        chain_value = self._parse_optional_int(
            value=match.group(3),
            name='chain',
            insert_text=insert_text,
        )
        chain_id = ChainID.deserialize(chain_value) if chain_value is not None else None
        token_kind_value = self._parse_optional_str(
            value=match.group(2),
            name='token_kind',
            insert_text=insert_text,
        )
        token_kind = (
            TokenKind.deserialize_evm_from_db(token_kind_value)
            if token_kind_value is not None
            else None
        )
        return (
            deserialize_evm_address(self._parse_str(match.group(4), 'address', insert_text)),
            self._parse_optional_int(match.group(5), 'decimals', insert_text),
            self._parse_optional_str(match.group(6), 'protocol', insert_text),
            chain_id,
            token_kind,
        )


class AssetCollectionParser(BaseAssetParser[tuple[int, str, str] | tuple[int, str, str, str]]):
    """Parser for asset collections introduced in global db v4 (assets v16+).

    Uses new format after global db v10 which adds main_asset field.
    """

    def __init__(self) -> None:
        super().__init__()
        self._latest_collection_re = re.compile(r'.*INSERT +INTO +asset_collections\( *id *, *name *, *symbol, *main_asset *\) *VALUES +\(([^,]*?),([^,]*?),([^,]*?),([^,]*?)\).*?')  # noqa: E501
        self._legacy_collection_re = re.compile(r'.*INSERT +INTO +asset_collections\( *id *, *name *, *symbol *\) *VALUES +\(([^,]*?),([^,]*?),([^,]*?)\).*?')  # noqa: E501
        self._version_parsers = [
            (VersionRange(16, 32), self._parse_legacy_format),
            (VersionRange(33, None), self._parse_latest_format),
        ]

    def _parse_latest_format(self, connection: 'DBConnection', insert_text: str) -> tuple[int, str, str, str]:  # noqa: E501
        collection_match = self._latest_collection_re.match(insert_text)
        if collection_match is None:
            log.error(f'Failed to match asset collection {insert_text}')
            raise DeserializationError(
                f'At asset DB update could not parse asset collection data out of {insert_text}',
            )

        groups = collection_match.groups()
        if len(groups) != 4:
            log.error(f'Asset collection {insert_text} does not have the expected elements')
            raise DeserializationError(
                f'At asset DB update could not parse asset collection data out of {insert_text}',
            )

        collection_id = self._parse_value(collection_match.group(1))
        if not isinstance(collection_id, int):
            raise DeserializationError(
                f'At asset DB update invalid collection ID {collection_id} from {insert_text}',
            )

        name = self._parse_str(collection_match.group(2), 'name', insert_text)
        symbol = self._parse_str(collection_match.group(3), 'symbol', insert_text)
        main_asset = self._parse_str(collection_match.group(4), 'main_asset', insert_text)
        return collection_id, name, symbol, main_asset

    def _parse_legacy_format(self, connection: 'DBConnection', insert_text: str) -> tuple[int, str, str]:  # noqa: E501
        collection_match = self._legacy_collection_re.match(insert_text)
        if collection_match is None:
            log.error(f'Failed to match asset collection {insert_text}')
            raise DeserializationError(
                f'At asset DB update could not parse asset collection data out of {insert_text}',
            )

        groups = collection_match.groups()
        if len(groups) != 3:
            log.error(f'Asset collection {insert_text} does not have the expected elements')
            raise DeserializationError(
                f'At asset DB update could not parse asset collection data out of {insert_text}',
            )

        collection_id = self._parse_value(collection_match.group(1))
        if not isinstance(collection_id, int):
            raise DeserializationError(
                f'At asset DB update invalid collection ID {collection_id} from {insert_text}',
            )

        name = self._parse_str(collection_match.group(2), 'name', insert_text)
        symbol = self._parse_str(collection_match.group(3), 'symbol', insert_text)
        return collection_id, name, symbol


class MultiAssetMappingsParser(BaseAssetParser[tuple[int, str]]):
    """Parser for assets introduced in global db v4 (assets v16+)."""

    def __init__(self) -> None:
        super().__init__()
        self._mappings_re = re.compile(r'.*INSERT +INTO +multiasset_mappings\( *collection_id *, *asset *\) *VALUES +\(([^,]*?), *([\'"])([^,]+?)\2\).*?')  # noqa: E501
        self._version_parsers = [
            (VersionRange(16, None), self._parse),
        ]

    def _parse(self, connection: 'DBConnection', insert_text: str) -> tuple[int, str]:
        mapping_match = self._mappings_re.match(insert_text)
        if mapping_match is None:
            log.error(f'Failed to match asset collection mapping {insert_text}')
            raise DeserializationError(
                f'At asset DB update could not parse asset collection data out of {insert_text}',
            )

        groups = mapping_match.groups()
        if len(groups) != 3:
            log.error(f'Failed to find all elements in asset collection mapping {insert_text}')
            raise DeserializationError(
                f'At asset DB update could not parse asset collection data out of {insert_text}',
            )

        collection_id = self._parse_value(mapping_match.group(1))
        if not isinstance(collection_id, int):
            raise DeserializationError(
                f'At asset DB update invalid collection ID {collection_id} from {insert_text}',
            )

        asset_identifier = mapping_match.group(3)
        # check that the asset exists and so does the collection
        with connection.read_ctx() as cursor:
            cursor.execute('SELECT COUNT(*) FROM assets where identifier=?', (asset_identifier,))
            if cursor.fetchone()[0] == 0:
                raise UnknownAsset(asset_identifier)

            cursor.execute(
                'SELECT COUNT(*) FROM asset_collections WHERE id=?',
                (collection_id,),
            )
            if cursor.fetchone()[0] != 1:
                raise DeserializationError(
                    f'Tried to add asset to collection with id {collection_id} but it does not exist',  # noqa: E501
                )

        return collection_id, asset_identifier
