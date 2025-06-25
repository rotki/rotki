import json
from collections.abc import Callable
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.types import AssetData, AssetType
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.asset_updates.manager import (
    ASSETS_VERSION_KEY,
    AssetsUpdater,
    UpdateFileType,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.utils import GLOBAL_DB_VERSION
from rotkehlchen.tests.api.test_assets_updates import mock_asset_updates
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ChainID, Timestamp, TokenKind

VALID_ASSET_MAPPINGS = """INSERT INTO multiasset_mappings(collection_id, asset) VALUES (5, "ETH");
    *
    INSERT INTO multiasset_mappings(collection_id, asset) VALUES (5, "BTC");
    *
"""
VALID_ASSET_COLLECTIONS = """INSERT INTO asset_collections(id, name, symbol, main_asset) VALUES (99999999, "My custom ETH", "ETHS", "ETHS")
    *
"""  # noqa: E501
VALID_ASSETS = """INSERT INTO assets(identifier, name, type) VALUES("MYBONK", "Bonk", "Y"); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES("MYBONK", "BONK", "bonk", "BONK", NULL, 1672279200, NULL);
    *
UPDATE common_asset_details SET coingecko="coingecko-id" where identifier="new-asset";
INSERT INTO assets(identifier, name, type) VALUES("new-asset", "New Asset", "Y"); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES("new-asset", "NEW", "coingecko-id", "", NULL, 1672279200, NULL);
"""  # noqa: E501


@pytest.fixture(name='assets_updater')
def fixture_assets_updater(messages_aggregator, globaldb):
    return AssetsUpdater(
        globaldb=globaldb,
        msg_aggregator=messages_aggregator,
    )


def get_mock_github_assets_response(
        assets_exists: bool,
        collections_exists: bool,
        mappings_exists: bool,
) -> Callable[..., MockResponse]:
    """Return mocked response from github for assets updates.
    Each of the boolean parameters indicates if the mocked response should return
    corresponding update files' content or 404 error."""

    def mocked_response_fn(url, timeout):  # pylint: disable=unused-argument
        if 'mappings' in url:
            return MockResponse(200, VALID_ASSET_MAPPINGS) if mappings_exists else MockResponse(404, '')  # noqa: E501
        if 'collections' in url:
            return MockResponse(200, VALID_ASSET_COLLECTIONS) if collections_exists else MockResponse(404, '')  # noqa: E501
        if 'info' in url:
            local_schema = GlobalDBHandler.get_schema_version()
            data = json.dumps({
                'updates': {
                    '998': {'min_schema_version': 4, 'max_schema_version': 4, 'changes': 1},
                    '999': {'min_schema_version': local_schema, 'max_schema_version': local_schema, 'changes': 1},  # noqa: E501
                },
                'latest': 999,
            })
            return MockResponse(200, data)

        if 'updates' in url:
            return MockResponse(200, VALID_ASSETS) if assets_exists else MockResponse(404, '')

        raise AssertionError(f'Unknown url {url}')

    return mocked_response_fn


@pytest.mark.parametrize(('text', 'expected_data', 'error_msg'), [
    (
        """
        INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol)
        VALUES(
            "eip155:1/erc20:0xD178b20c6007572bD1FD01D205cC20D32B4A6015",
            "A",
            1,
            "0xD178b20c6007572bD1FD01D205cC20D32B4A6015",
            18,
            NULL
        );
        INSERT INTO assets(identifier, name, type)
        VALUES(
            "eip155:1/erc20:0xD178b20c6007572bD1FD01D205cC20D32B4A6015",
            "Aidus",
            "C"
        );
        INSERT INTO common_asset_details(identifier, symbol, coingecko,
        cryptocompare, forked, started, swapped_for)
        VALUES(
            "eip155:1/erc20:0xD178b20c6007572bD1FD01D205cC20D32B4A6015",
            "AID",
            NULL,
            "AIDU",
            NULL,
            123,
            NULL
        );
        """,
        AssetData(
            identifier='eip155:1/erc20:0xD178b20c6007572bD1FD01D205cC20D32B4A6015',
            name='Aidus',
            symbol='AID',
            asset_type=AssetType.EVM_TOKEN,
            started=Timestamp(123),
            forked=None,
            swapped_for=None,
            address=string_to_evm_address('0xD178b20c6007572bD1FD01D205cC20D32B4A6015'),
            chain_id=ChainID.ETHEREUM,
            token_kind=TokenKind.ERC20,
            decimals=18,
            cryptocompare='AIDU',
            coingecko=None,
            protocol=None,
        ),
        None,
    ),
    (
        """
        INSERT INTO assets(identifier, name, type)
        VALUES(
            "121-ada-FADS-as",
            "A name",
            "F"
        );
        INSERT INTO common_asset_details(identifier, symbol, coingecko,
        cryptocompare, forked, started, swapped_for)
        VALUES(
            "121-ada-FADS-as",
            "SYMBOL",
            "",
            "",
            "421-bbc-FADS-ks",
            NULL,
            NULL
        );
        """,
        AssetData(
            identifier='121-ada-FADS-as',
            name='A name',
            symbol='SYMBOL',
            asset_type=AssetType.COUNTERPARTY_TOKEN,
            started=None,
            forked='421-bbc-FADS-ks',
            swapped_for=None,
            address=None,
            chain_id=None,
            token_kind=None,
            decimals=None,
            cryptocompare='',
            coingecko='',
            protocol=None,
        ),
        None,
    ),
    (
        """
        INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol)
        VALUES(
            "eip155:1/erc20:0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            "A",
            1,
            "0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            18,
            "uniswap"
        );
        INSERT INTO assets(identifier, name, type)
        VALUES(
            "eip155:1/erc20:0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            "Test token",
            "C"
        );
        INSERT INTO common_asset_details(identifier, symbol, coingecko,
        cryptocompare, forked, started, swapped_for)
        VALUES(
            "eip155:1/erc20:0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            "TEST",
            "test-token",
            "",
            NULL,
            123,
            "eip155:1/erc20:0xD178b20c6007572bD1FD01D205cC20D32B4A6015"
        );
""",
        AssetData(
            identifier='eip155:1/erc20:0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C',
            name='Test token',
            symbol='TEST',
            asset_type=AssetType.EVM_TOKEN,
            started=Timestamp(123),
            forked=None,
            swapped_for='eip155:1/erc20:0xD178b20c6007572bD1FD01D205cC20D32B4A6015',
            address=string_to_evm_address('0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C'),
            chain_id=ChainID.ETHEREUM,
            token_kind=TokenKind.ERC20,
            decimals=18,
            cryptocompare='',
            coingecko='test-token',
            protocol='uniswap',
        ),
        None,
    ),
    (
        """
        INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol)
        VALUES(
            "eip155:1/erc20:0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            "A",
            1,
            "0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            18,
            "uniswap"
        );
        INSERT INTO assets(identifier, name, type)
        VALUES(
            "eip155:1/erc20:0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            "Test token",
            "C"
        );
        INSERT INTO common_asset_details(identifier, symbol, coingecko,
        cryptocompare, forked, started, swapped_for)
        VALUES(
            "eip155:1/erc20:0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            "TEST",
                        "test-token",
            "",
            NULL,
            123,
            "eip155:1/erc20:0xD178b20c6007572bD1FD01D205cC20D32B4A6015"
        );
""",
        AssetData(
            identifier='eip155:1/erc20:0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C',
            name='Test token',
            symbol='TEST',
            asset_type=AssetType.EVM_TOKEN,
            started=Timestamp(123),
            forked=None,
            swapped_for='eip155:1/erc20:0xD178b20c6007572bD1FD01D205cC20D32B4A6015',
            address=string_to_evm_address('0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C'),
            chain_id=ChainID.ETHEREUM,
            token_kind=TokenKind.ERC20,
            decimals=18,
            cryptocompare='',
            coingecko='test-token',
            protocol='uniswap',
        ),
        None,
    ),
    (
        """
        INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol)
        VALUES(
            "eip155:1/erc20:0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            "A",
            1,
            18,
            "uniswap"
        );
        INSERT INTO assets(identifier, name, type)
        VALUES(
            "eip155:1/erc20:0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            "Test token",
            "C"
        );
        INSERT INTO common_asset_details(identifier, symbol, coingecko,
        cryptocompare, forked, started, swapped_for)
        VALUES(
            "eip155:1/erc20:0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            "TEST",
                        "test-token",
            "",
            NULL,
            123,
            "eip155:1/erc20:0xD178b20c6007572bD1FD01D205cC20D32B4A6015"
        );
""",
        None,
        'At asset DB update could not parse evm token data out of',
    ),
    (
        """
        INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol)
        VALUES(
            "eip155:1/erc20:0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            "A",
            1,
            "0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            18,
            "uniswap"
        );
        INSERT INTO assets(identifier, name, type)
        VALUES(
            "eip155:1/erc20:0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            "Test token",
            "C"
        );
        INSERT INTO common_asset_details(identifier, symbol, coingecko,
        cryptocompare, forked, started, swapped_for)
        VALUES(
            "eip155:1/erc20:0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            "TEST" ,
            "test-token",
            "",
            NULL,
            "eip155:1/erc20:0xD178b20c6007572bD1FD01D205cC20D32B4A6015"
        );
        """,
        None,
        'At asset DB update could not parse common asset details data out of',
    ),
    (
        """
        INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol)
        VALUES(
            "eip155:1/erc20:0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            "A",
            1,
            "0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            18,
            "uniswap"
        );
        INSERT INTO assets(identifier, name, type)
        VALUES(
            "eip155:1/erc20:0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            "Test token",
            "C"
        );
        INSERT INTO common_asset_details(identifier, symbol, coingecko,
        cryptocompare, forked, started, swapped_for)
        VALUES(
            "eip155:1/erc20:0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            "TEST",
            "",
            NULL,
            123,
            "eip155:1/erc20:0xD178b20c6007572bD1FD01D205cC20D32B4A6015"
        );
        """,
        None,
        'At asset DB update could not parse common asset details data out of',
    ),
])
def test_parse_full_insert_assets(
        assets_updater: AssetsUpdater,
        text: str,
        expected_data: AssetData | None,
        error_msg: str,
        globaldb,
) -> None:
    text = text.replace('\n', '')
    if expected_data is not None:
        assert expected_data == assets_updater.asset_parser.parse(
            insert_text=text,
            connection=globaldb.conn,
            version=15,  # any version works for assets since no change has happened.
        )
    else:
        with pytest.raises(DeserializationError) as excinfo:
            assets_updater.asset_parser.parse(
                insert_text=text,
                connection=globaldb.conn,
                version=15,  # any version works for assets since no change has happened.
            )

        assert error_msg in str(excinfo.value)


def test_some_updates_are_malformed(assets_updater: AssetsUpdater) -> None:
    """
    Checks the following cases:
    1. If some of the updates are broken, others are not affected.
    2. If an update is broken, info about asset stays the same in all tables as before the update.

    Checks both insertion of a new asset and an update of an existing one.
    """
    # In "ETH" update swapped_for is incorrect
    # In "BTC" update everything is good
    # In "NEW-ASSET-1" insertion swapped_for is incorrect
    # In "NEW-ASSET-2" insertion everything is good
    update_text = """INSERT INTO assets(identifier, name, type) VALUES('ETH', 'name1', 'B'); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES('ETH', 'symbol1', '', '', NULL, NULL, 'NONEXISTENT');
*
INSERT INTO assets(identifier, name, type) VALUES('BTC', 'name2', 'B'); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES('BTC', 'symbol2', '', '', NULL, NULL, NULL);
*
INSERT INTO assets(identifier, name, type) VALUES('NEW-ASSET-1', 'name3', 'B'); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES('NEW-ASSET-1', 'symbol3', '', '', NULL, NULL, 'LOLKEK');
*
INSERT INTO assets(identifier, name, type) VALUES('NEW-ASSET-2', 'name4', 'B'); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES('NEW-ASSET-2', 'symbol4', '', '', NULL, NULL, NULL);
*
"""  # noqa: E501
    connection = GlobalDBHandler().conn
    assets_updater._apply_single_version_update(
        connection=connection,
        version=999,  # doesn't matter
        text=update_text,
        assets_conflicts={A_ETH: 'remote', A_BTC: 'remote'},
        update_file_type=UpdateFileType.ASSETS,
    )

    # Should have stayed unchanged since one of the insertions was incorrect
    assert connection.execute("SELECT name FROM assets WHERE identifier='ETH'").fetchone()[0] == 'Ethereum'  # noqa: E501
    assert connection.execute("SELECT symbol FROM common_asset_details WHERE identifier='ETH'").fetchone()[0] == 'ETH'  # noqa: E501
    # BTC should have been updated since the insertion were correct
    assert connection.execute("SELECT name FROM assets WHERE identifier='BTC'").fetchone()[0] == 'name2'  # noqa: E501
    assert connection.execute("SELECT symbol FROM common_asset_details WHERE identifier='BTC'").fetchone()[0] == 'symbol2'  # noqa: E501
    # NEW-ASSET-1 should have not been added since the insertions were incorrect
    assert connection.execute("SELECT * FROM assets WHERE identifier='NEW-ASSET-1'").fetchone() is None  # noqa: E501
    # NEW-ASSET-2 should have been added since the insertions were correct
    assert connection.execute("SELECT name FROM assets WHERE identifier='NEW-ASSET-2'").fetchone()[0] == 'name4'  # noqa: E501
    assert connection.execute("SELECT symbol FROM common_asset_details WHERE identifier='NEW-ASSET-2'").fetchone()[0] == 'symbol4'  # noqa: E501


def test_updates_assets_collections_errors(assets_updater: AssetsUpdater):
    """
    Check that assets collections can be created and edited correctly.

    - Try to create a collection with missing fields
    - Try to add an Unknown asset
    - Try to add to a collection that doesn't exists
    - Add an asset that was newly introduced to a collection
    """
    update_text_assets = """INSERT INTO assets(identifier, name, type) VALUES('MYBONK', 'Bonk', 'Y'); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES('MYBONK', 'BONK', 'bonk', 'BONK', NULL, 1672279200, NULL);
    *
    """  # noqa: E501
    update_text_collection = """INSERT INTO asset_collections(id, name) VALUES (99999999, 'My custom ETH')
    *
    """  # noqa: E501
    update_mapping_collection = """INSERT INTO multiasset_mappings(collection_id, asset) VALUES (1, 'ETH99999');
    *
    INSERT INTO multiasset_mappings(collection_id, asset) VALUES (99999999, 'eip155:1/erc20:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84');
    *
    INSERT INTO multiasset_mappings(collection_id, asset) VALUES (1, 'MYBONK');
    *
    """  # noqa: E501

    # consume warnings to remove any warning that might have been kept in the object
    assets_updater.msg_aggregator.consume_warnings()
    connection = GlobalDBHandler().conn
    assets_updater._apply_single_version_update(
        connection=connection,
        version=999,  # doesn't matter
        text=update_text_assets,
        assets_conflicts={},
        update_file_type=UpdateFileType.ASSETS,
    )
    assets_updater._apply_single_version_update(
        connection=connection,
        version=999,  # doesn't matter
        text=update_text_collection,
        assets_conflicts={},
        update_file_type=UpdateFileType.ASSET_COLLECTIONS,
    )
    assets_updater._apply_single_version_update(
        connection=connection,
        version=999,  # doesn't matter
        text=update_mapping_collection,
        assets_conflicts={},
        update_file_type=UpdateFileType.ASSET_COLLECTIONS_MAPPINGS,
    )
    with connection.read_ctx() as cursor:
        cursor.execute('SELECT COUNT(*) FROM asset_collections WHERE id = 99999999')
        assert cursor.fetchone()[0] == 0

    warnings = assets_updater.msg_aggregator.consume_warnings()
    assert warnings == [
        "Skipping entry during assets collection update to v999 due to a deserialization error. At asset DB update could not parse asset collection data out of INSERT INTO asset_collections(id, name) VALUES (99999999, 'My custom ETH')",  # noqa: E501
        'Tried to add unknown asset ETH99999 to collection of assets. Skipping',
        'Skipping entry during assets collection multimapping update due to a deserialization error. Tried to add asset to collection with id 99999999 but it does not exist',  # noqa: E501
    ]


@pytest.mark.parametrize('update_assets', [True, False])
@pytest.mark.parametrize('update_collections', [True, False])
@pytest.mark.parametrize('update_mappings', [True, False])
def test_asset_update(
        assets_updater: AssetsUpdater,
        update_assets: bool,
        update_collections: bool,
        update_mappings: bool,
):
    """
    Check that globaldb updates work properly when getting information from github
    and assets collections are applied correctly in the process
    """
    # consume warnings from other tests
    assets_updater.msg_aggregator.consume_warnings()
    # set a high version of the globaldb to avoid conflicts with future changes
    GlobalDBHandler.add_setting_value(ASSETS_VERSION_KEY, 997)
    with patch('requests.get', wraps=get_mock_github_assets_response(update_assets, update_collections, update_mappings)):  # noqa: E501
        assets_updater.perform_update(up_to_version=999, conflicts={})

    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert cursor.execute("SELECT * FROM assets WHERE identifier = 'MYBONK'").fetchall() == ([
            ('MYBONK', 'Bonk', 'Y'),
        ] if update_assets else [])
        assert cursor.execute("SELECT * FROM assets WHERE identifier = 'new-asset'").fetchall() == ([  # noqa: E501
            ('new-asset', 'New Asset', 'Y'),
        ] if update_assets else [])

        cursor.execute('SELECT * FROM asset_collections WHERE id = 99999999')
        assert cursor.fetchall() == ([
            (99999999, 'My custom ETH', 'ETHS', 'ETHS'),
        ] if update_collections else [])

        cursor.execute('SELECT * FROM multiasset_mappings WHERE collection_id = 5')
        assert cursor.fetchall() == ([(5, 'BTC'), (5, 'ETH')] if update_mappings else []) + [  # plus the already existing ones  # noqa: E501
            (5, 'eip155:1/erc20:0xa1faa113cbE53436Df28FF0aEe54275c13B40975'),
            (5, 'eip155:43114/erc20:0x2147EFFF675e4A4eE1C2f918d181cDBd7a8E208f'),
        ]

        # check that we skip versions with wrong schema and that all the versions
        # required are correctly queried.
        warnings = assets_updater.msg_aggregator.consume_warnings()
        assert warnings == [
            f'Skipping assets update 998 since it requires a min schema of 4 and max schema of 4 while the local DB schema version is {GlobalDBHandler().get_schema_version()}. You will have to follow an alternative method to obtain the assets of this update. Easiest would be to reset global DB.',  # noqa: E501
        ]


def test_conflict_updates(assets_updater: AssetsUpdater, globaldb: GlobalDBHandler):
    """Test that the logic doesn't add duplicates for assets that were inserted twice
    in the globaldb assets updates. Also test a bug in asset updates where the foreign key entries
    are removed when an asset update conflict is resolved through 'remote' option.
    """
    with globaldb.conn.write_ctx() as write_cursor:
        assert write_cursor.execute(
            'SELECT COUNT(*) FROM underlying_tokens_list WHERE parent_token_entry=?;',
            ('eip155:42161/erc20:0xA5EDBDD9646f8dFF606d7448e414884C7d905dCA',),
        ).fetchone()[0] == 1
        assert write_cursor.execute(
            'SELECT COUNT(*) FROM multiasset_mappings WHERE asset=?;',
            ('eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8',),
        ).fetchone()[0] == 1

    update_1 = """INSERT INTO assets(identifier, name, type) VALUES("eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8", "Bridged USDC", "C"); INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol) VALUES("eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8", "A", 42161, "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8", 6, ""); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES("eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8", "USDC.e", "usd-coin", "USDC", NULL, 1623868379, NULL);
*"""  # noqa: E501
    update_2 = """INSERT INTO assets(identifier, name, type) VALUES("eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8", "Bridged USDC", "C"); INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol) VALUES("eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8", "A", 42161, "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8", 6, NULL); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES("eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8", "USDC.e", "usd-coin-ethereum-bridged", "USDC", NULL, 1623868379, NULL);
*"""  # noqa: E501
    update_patch = mock_asset_updates(
        original_requests_get=requests.get,
        latest=16,
        updates={'15': {
            'changes': 1,
            'min_schema_version': GLOBAL_DB_VERSION,
            'max_schema_version': GLOBAL_DB_VERSION,
        }, '16': {
            'changes': 1,
            'min_schema_version': GLOBAL_DB_VERSION,
            'max_schema_version': GLOBAL_DB_VERSION,
        }},
        sql_actions={'15': {'assets': update_1, 'collections': '', 'mappings': ''}, '16': {'assets': update_2, 'collections': '', 'mappings': ''}},  # noqa: E501
    )
    cursor = globaldb.conn.cursor()
    cursor.execute(f"DELETE FROM settings WHERE name='{ASSETS_VERSION_KEY}'")
    with update_patch:
        conflicts = assets_updater.perform_update(
            up_to_version=16,
            conflicts=None,
        )
    assert conflicts is not None
    assert len(conflicts) == 1
    assert conflicts[0]['remote'] == {'name': 'Bridged USDC', 'symbol': 'USDC.e', 'asset_type': 'evm token', 'started': 1623868379, 'forked': None, 'swapped_for': None, 'address': '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8', 'token_kind': 'erc20', 'decimals': 6, 'cryptocompare': 'USDC', 'coingecko': 'usd-coin-ethereum-bridged', 'protocol': None, 'evm_chain': 'arbitrum_one'}  # noqa: E501

    # resolve with all the remote updates and check if the multiasset and underlying_asset mappings still exists  # noqa: E501
    with update_patch:
        assets_updater.perform_update(
            up_to_version=16,
            conflicts={
                Asset(conflict['identifier']): 'remote'
                for conflict in conflicts
            },
        )
    assert cursor.execute("SELECT value FROM settings WHERE name='assets_version'").fetchone()[0] == '16'  # noqa: E501
    with globaldb.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM underlying_tokens_list WHERE parent_token_entry=?;',
            ('eip155:42161/erc20:0xA5EDBDD9646f8dFF606d7448e414884C7d905dCA',),
        ).fetchone()[0] == 1
        assert cursor.execute(
            'SELECT COUNT(*) FROM multiasset_mappings WHERE asset=?;',
            ('eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8',),
        ).fetchone()[0] == 1
