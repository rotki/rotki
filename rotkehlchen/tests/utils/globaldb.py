import re
from copy import deepcopy
from typing import TYPE_CHECKING, Final, Literal
from unittest.mock import patch

from eth_utils.address import to_checksum_address

from rotkehlchen.assets.asset import EvmToken, UnderlyingToken
from rotkehlchen.constants.assets import A_MKR
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import compute_cache_key
from rotkehlchen.globaldb.upgrades.manager import UPGRADES_LIST
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import CacheType, ChainID, Timestamp, TokenKind

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable
    from contextlib import ExitStack

    from rotkehlchen.db.drivers.sqlite import DBCursor

# the hex lookarounds keep a 40 char window out of a longer hex run from matching, so a
# transaction hash or any other 32 byte hex value is not mistaken for an address
EVM_ADDRESS_RE: Final = re.compile(r'(?<![a-fA-F0-9])0x[a-fA-F0-9]{40}(?![a-fA-F0-9])')
# columns holding an evm address outside of an asset identifier
ADDRESS_COLUMNS: Final = (
    ('evm_tokens', 'address'),
    ('address_book', 'address'),
    ('contract_data', 'address'),
    ('general_cache', 'value'),
    ('unique_cache', 'value'),
)
# columns holding an asset identifier without declaring a foreign key for it
UNLINKED_IDENTIFIER_COLUMNS: Final = (
    ('location_asset_mappings', 'local_id'),
    ('counterparty_asset_mappings', 'local_id'),
)


def find_non_checksummed_addresses(values: Iterable[tuple[str, str]]) -> list[str]:
    """Return a description of every given value holding a non checksummed evm address.

    Values are (description, value) pairs so that a failure names where the address sits.
    """
    return [
        f'{description}: {value}'
        for description, value in values
        for address in EVM_ADDRESS_RE.findall(value)
        if to_checksum_address(address) != address
    ]


def find_non_checksummed_addresses_in_db(
        cursor: DBCursor,
        skip_columns: Collection[tuple[str, str]] = (),
) -> list[str]:
    """Return a description of every non checksummed evm address stored in a globaldb.

    The asset columns are asked of the db rather than listed, so a new one cannot be missed.
    The two holding an identifier without a foreign key, and the ones holding a bare address,
    are named explicitly since nothing in the schema marks them. skip_columns leaves out the
    ones a caller fills from somewhere it does not test.
    """
    columns = [('assets', 'identifier'), *ADDRESS_COLUMNS, *UNLINKED_IDENTIFIER_COLUMNS]
    for (table,) in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'",
    ).fetchall():
        columns.extend(
            (table, fk_entry[3])
            for fk_entry in cursor.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()
            if fk_entry[2] == 'assets' and fk_entry[4] == 'identifier'
        )

    bad_values: list[str] = []
    for table, column in columns:
        if (table, column) in skip_columns:
            continue

        bad_values.extend(find_non_checksummed_addresses(
            (f'{table}.{column}', value)
            for (value,) in cursor.execute(f'SELECT "{column}" FROM "{table}"').fetchall()
            if isinstance(value, str)
        ))

    return bad_values


underlying_address1 = make_evm_address()
underlying_address2 = make_evm_address()
underlying_address3 = make_evm_address()

user_token_address1 = make_evm_address()
user_token_address2 = make_evm_address()


def create_initial_globaldb_test_tokens() -> list[EvmToken]:
    return [
        EvmToken.initialize(
            address=user_token_address1,
            chain_id=ChainID.ETHEREUM,
            token_kind=TokenKind.ERC20,
            decimals=4,
            name='Custom 1',
            symbol='CST1',
            started=Timestamp(0),
            swapped_for=A_MKR.resolve_to_crypto_asset(),
            coingecko='internet-computer',
            cryptocompare='ICP',
            protocol='uniswap',
            underlying_tokens=[
                UnderlyingToken(address=underlying_address1, token_kind=TokenKind.ERC20, weight=FVal('0.5055')),  # noqa: E501
                UnderlyingToken(address=underlying_address2, token_kind=TokenKind.ERC20, weight=FVal('0.1545')),  # noqa: E501
                UnderlyingToken(address=underlying_address3, token_kind=TokenKind.ERC20, weight=FVal('0.34')),  # noqa: E501
            ],
        ),
        EvmToken.initialize(
            address=user_token_address2,
            chain_id=ChainID.ETHEREUM,
            token_kind=TokenKind.ERC20,
            decimals=18,
            name='Custom 2',
            symbol='CST2',
        ),
    ]


def create_initial_expected_globaldb_test_tokens() -> list[EvmToken]:
    initial_tokens = create_initial_globaldb_test_tokens()
    return [initial_tokens[0]] + [
        EvmToken.initialize(underlying_address1, chain_id=ChainID.ETHEREUM, token_kind=TokenKind.ERC20),  # noqa: E501
        EvmToken.initialize(underlying_address2, chain_id=ChainID.ETHEREUM, token_kind=TokenKind.ERC20),  # noqa: E501
        EvmToken.initialize(underlying_address3, chain_id=ChainID.ETHEREUM, token_kind=TokenKind.ERC20),  # noqa: E501
    ] + [initial_tokens[1]]


underlying_address4 = make_evm_address()
user_token_address3 = make_evm_address()
USER_TOKEN3 = EvmToken.initialize(
    address=user_token_address3,
    chain_id=ChainID.ETHEREUM,
    token_kind=TokenKind.ERC20,
    decimals=15,
    name='Custom 3',
    symbol='CST3',
    cryptocompare='ICP',
    protocol='aave',
    underlying_tokens=[
        UnderlyingToken(address=user_token_address1, token_kind=TokenKind.ERC20, weight=FVal('0.55')),  # noqa: E501
        UnderlyingToken(address=underlying_address4, token_kind=TokenKind.ERC20, weight=FVal('0.45')),  # noqa: E501
    ],
)


def patch_for_globaldb_upgrade_to(
        stack: ExitStack,
        version: Literal[2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
) -> ExitStack:
    stack.enter_context(
        patch(
            'rotkehlchen.globaldb.upgrades.manager.GLOBAL_DB_VERSION',
            version,
        ),
    )
    original_list = deepcopy(UPGRADES_LIST)
    stack.enter_context(
        patch(
            'rotkehlchen.globaldb.upgrades.manager.UPGRADES_LIST',
            original_list[:version - 2],
        ),
    )
    return stack


def patch_for_globaldb_migrations(stack: ExitStack, new_list: list) -> ExitStack:
    stack.enter_context(
        patch(
            'rotkehlchen.globaldb.migrations.manager.MIGRATIONS_LIST',
            new_list,
        ),
    )
    stack.enter_context(
        patch(
            'rotkehlchen.globaldb.migrations.manager.LAST_GLOBALDB_DATA_MIGRATION',
            len(new_list),
        ),
    )
    return stack


def globaldb_get_general_cache_last_queried_ts(
        cursor: DBCursor,
        key_parts: Iterable[str | CacheType],
        value: str,
) -> Timestamp | None:
    """Function to get timestamp at which pair key - value was queried last time."""
    cache_key = compute_cache_key(key_parts)
    cursor.execute(
        'SELECT MAX(last_queried_ts) FROM general_cache WHERE key=? AND value=?',
        (cache_key, value),
    )
    result = cursor.fetchone()
    if result is None:
        return None
    return Timestamp(result[0])
