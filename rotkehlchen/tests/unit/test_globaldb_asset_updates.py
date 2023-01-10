from typing import Optional
import pytest

from rotkehlchen.assets.types import AssetData, AssetType
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.updates import AssetsUpdater, UpdateFileType
from rotkehlchen.types import ChainID, EvmTokenKind, Timestamp


@pytest.fixture(name='assets_updater')
def fixture_assets_updater(messages_aggregator):
    return AssetsUpdater(messages_aggregator)


@pytest.mark.parametrize('text,expected_data,error_msg', [
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
            address=string_to_evm_address('0xD178b20c6007572bD1FD01D205cC20D32B4A6015'),  # noqa: E501
            chain_id=ChainID.ETHEREUM,
            token_kind=EvmTokenKind.ERC20,
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
            address=string_to_evm_address('0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C'),  # noqa: E501
            chain_id=ChainID.ETHEREUM,
            token_kind=EvmTokenKind.ERC20,
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
            address=string_to_evm_address('0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C'),  # noqa: E501
            chain_id=ChainID.ETHEREUM,
            token_kind=EvmTokenKind.ERC20,
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
        expected_data: Optional[AssetData],
        error_msg: str,
) -> None:
    text = text.replace('\n', '')
    if expected_data is not None:
        assert expected_data == assets_updater._parse_full_insert_assets(text)
    else:
        with pytest.raises(DeserializationError) as excinfo:
            assets_updater._parse_full_insert_assets(text)

        assert error_msg in str(excinfo.value)


def test_some_updates_are_malformed(assets_updater: AssetsUpdater) -> None:
    """
    Checks the folowing cases:
    1. If some of the updates are broken, others are not affected.
    2. If an update is broken, info about asset stays the same in all tables as before the update.

    Checks both insertion of a new asset and an update of an existing one.
    """
    # In "ETH" update swapped_for is incorrect
    # In "BTC" update everything is good
    # In "NEW-ASSET-1" insertion swapped_for is incorrect
    # In "NEW-ASSET-2" insertion everything is good
    update_text = """INSERT INTO assets(identifier, name, type) VALUES("ETH", "name1", "B"); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES("ETH", "symbol1", "", "", NULL, NULL, "NONEXISTENT");
*
INSERT INTO assets(identifier, name, type) VALUES("BTC", "name2", "B"); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES("BTC", "symbol2", "", "", NULL, NULL, NULL);
*
INSERT INTO assets(identifier, name, type) VALUES("NEW-ASSET-1", "name3", "B"); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES("NEW-ASSET-1", "symbol3", "", "", NULL, NULL, "LOLKEK");
*
INSERT INTO assets(identifier, name, type) VALUES("NEW-ASSET-2", "name4", "B"); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES("NEW-ASSET-2", "symbol4", "", "", NULL, NULL, NULL);
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
    assert connection.execute('SELECT name FROM assets WHERE identifier="ETH"').fetchone()[0] == 'Ethereum'  # noqa: E501
    assert connection.execute('SELECT symbol FROM common_asset_details WHERE identifier="ETH"').fetchone()[0] == 'ETH'  # noqa: E501
    # BTC should have been updated since the insertion were correct
    assert connection.execute('SELECT name FROM assets WHERE identifier="BTC"').fetchone()[0] == 'name2'  # noqa: E501
    assert connection.execute('SELECT symbol FROM common_asset_details WHERE identifier="BTC"').fetchone()[0] == 'symbol2'  # noqa: E501
    # NEW-ASSET-1 should have not been added since the insertions were incorrect
    assert connection.execute('SELECT * FROM assets WHERE identifier="NEW-ASSET-1"').fetchone() is None  # noqa: E501
    # NEW-ASSET-2 should have been added since the insertions were correct
    assert connection.execute('SELECT name FROM assets WHERE identifier="NEW-ASSET-2"').fetchone()[0] == 'name4'  # noqa: E501
    assert connection.execute('SELECT symbol FROM common_asset_details WHERE identifier="NEW-ASSET-2"').fetchone()[0] == 'symbol4'  # noqa: E501


def test_updates_assets_collections(assets_updater: AssetsUpdater) -> None:
    """
    Check that assets collections can be created and edited correctly
    """
    update_text_asset_collections = """INSERT INTO asset_collections(id, name, symbol) VALUES (99999999, "My custom ETH", "ETHS")
    *
    """  # noqa: E501
    update_text_mappings = """INSERT INTO multiasset_mappings(collection_id, asset) VALUES (99999999, "ETH");
    *
    INSERT INTO multiasset_mappings(collection_id, asset) VALUES (99999999, "eip155:1/erc20:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84");
    *
    """  # noqa: E501

    connection = GlobalDBHandler().conn
    assets_updater._apply_single_version_update(
        connection=connection,
        version=999,  # doesn't matter
        text=update_text_asset_collections,
        assets_conflicts={},
        update_file_type=UpdateFileType.ASSET_COLLECTIONS,
    )
    assets_updater._apply_single_version_update(
        connection=connection,
        version=999,  # doesn't matter
        text=update_text_mappings,
        assets_conflicts={},
        update_file_type=UpdateFileType.ASSET_COLLECTIONS_MAPPINGS,
    )
    with connection.read_ctx() as cursor:
        cursor.execute('SELECT * FROM asset_collections WHERE id = 99999999')
        assert cursor.fetchall() == [(99999999, 'My custom ETH', 'ETHS')]
        cursor.execute('SELECT * FROM multiasset_mappings WHERE collection_id = 99999999')
        assert cursor.fetchall() == [(99999999, 'ETH'), (99999999, 'eip155:1/erc20:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84')]  # noqa: E501


def test_updates_assets_collections_errors(assets_updater: AssetsUpdater):
    """
    Check that assets collections can be created and edited correctly.

    - Try to create a collection with missing fields
    - Try to add an Unknown asset
    - Try to add to a collection that doesn't exists
    """
    update_text_collection = """INSERT INTO asset_collections(id, name) VALUES (99999999, "My custom ETH")
    *
    """  # noqa: E501
    update_mapping_collection = """INSERT INTO multiasset_mappings(collection_id, asset) VALUES (1, "ETH99999");
    *
    INSERT INTO multiasset_mappings(collection_id, asset) VALUES (99999999, "eip155:1/erc20:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84");
    *
    """  # noqa: E501

    # consume warnings to remove any warning that might have been kept in the object
    assets_updater.msg_aggregator.consume_warnings()
    connection = GlobalDBHandler().conn
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
        'Skipping entry during assets collection update to v999 due to a deserialization error. At asset DB update could not parse asset collection data out of INSERT INTO asset_collections(id, name) VALUES (99999999, "My custom ETH")',  # noqa: E501
        'Tried to add unknown asset ETH99999 to collection of assets. Unknown asset ETH99999 provided.. Skipping',  # noqa: E501
        'Skipping entry during assets collection multimapping update to v999 due to a deserialization error. Tried to add asset to collection with id 99999999 but it does not exist',  # noqa: E501
    ]
