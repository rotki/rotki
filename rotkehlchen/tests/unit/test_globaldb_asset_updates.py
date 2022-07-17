import pytest

from rotkehlchen.assets.types import AssetData, AssetType
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.resolver import ChainID
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.updates import AssetsUpdater
from rotkehlchen.types import EvmTokenKind, Timestamp


@pytest.fixture(name='assets_updater')
def fixture_assets_updater(messages_aggregator):
    return AssetsUpdater(messages_aggregator)


@pytest.mark.parametrize('text,expected_data,error_msg', [
    (
        """
        INSERT INTO ethereum_tokens(address, decimals, protocol) VALUES(
        "0xD178b20c6007572bD1FD01D205cC20D32B4A6015", 18, NULL
        );
        INSERT INTO assets(identifier,type, name, symbol,
        started, swapped_for, coingecko, cryptocompare, details_reference)
        VALUES("_ceth_0xD178b20c6007572bD1FD01D205cC20D32B4A6015", "C", "Aidus", "AID"   ,
        123, NULL,   NULL, "AIDU", "0xD178b20c6007572bD1FD01D205cC20D32B4A6015");
        """,
        AssetData(
            identifier='_ceth_0xD178b20c6007572bD1FD01D205cC20D32B4A6015',
            name='Aidus',
            symbol='AID',
            asset_type=AssetType.ETHEREUM_TOKEN,
            started=Timestamp(123),
            forked=None,
            swapped_for=None,
            evm_address=string_to_evm_address('0xD178b20c6007572bD1FD01D205cC20D32B4A6015'),  # noqa: E501
            chain=ChainID.ETHEREUM,
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
        INSERT INTO assets(identifier,type, name, symbol,
        started, swapped_for, coingecko, cryptocompare, details_reference)
        VALUES("121-ada-FADS-as", "F", "A name", "SYMBOL"   ,
        NULL, NULL,   "", "", "121-ada-FADS-as");
        INSERT INTO common_asset_details(asset_id, forked) VALUES(
        "121-ada-FADS-as", "421-bbc-FADS-ks"
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
            evm_address=None,
            chain=None,
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
        INSERT INTO ethereum_tokens(address, decimals, protocol) VALUES(
        "0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C", 18, "uniswap"
        );
        INSERT INTO assets(identifier,type, name, symbol,
        started, swapped_for, coingecko, cryptocompare, details_reference)
        VALUES("_ceth_0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C", "C", "Test token", "TEST"   ,
        123, "_ceth_0xD178b20c6007572bD1FD01D205cC20D32B4A6015",   "test-token",
        "", "0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C");
""",
        AssetData(
            identifier='_ceth_0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C',
            name='Test token',
            symbol='TEST',
            asset_type=AssetType.ETHEREUM_TOKEN,
            started=Timestamp(123),
            forked=None,
            swapped_for='_ceth_0xD178b20c6007572bD1FD01D205cC20D32B4A6015',
            evm_address=string_to_evm_address('0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C'),  # noqa: E501
            chain=ChainID.ETHEREUM,
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
        INSERT INTO ethereum_tokens(address, decimals, protocol) VALUES(
        "0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C", 18, "uniswap"
        );
        INSERT INTO assets(identifier,type, name, symbol,
        started, swapped_for, coingecko, cryptocompare, details_reference)
        VALUES("_ceth_0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C", "C", "Test token", "TEST"   ,
        123, "_ceth_0xD178b20c6007572bD1FD01D205cC20D32B4A6015",   "test-token",
        "", "0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C");
""",
        AssetData(
            identifier='_ceth_0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C',
            name='Test token',
            symbol='TEST',
            asset_type=AssetType.ETHEREUM_TOKEN,
            started=Timestamp(123),
            forked=None,
            swapped_for='_ceth_0xD178b20c6007572bD1FD01D205cC20D32B4A6015',
            evm_address=string_to_evm_address('0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C'),  # noqa: E501
            chain=ChainID.ETHEREUM,
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
        INSERT INTO ethereum_tokens(address, decimals, protocol)
        , 18, "uniswap"
        );
        INSERT INTO assets(identifier,type, name, symbol,
        started, swapped_for, coingecko, cryptocompare, details_reference)
        VALUES("_ceth_0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C", "C", "Test token", "TEST"   ,
        123, "_ceth_0xD178b20c6007572bD1FD01D205cC20D32B4A6015",   "test-token",
        "", "0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C");
""",
        None,
        'At asset DB update could not parse ethereum token data out of',
    ),
    (
        """
        INSERT INTO ethereum_tokens(address, decimals, protocol) VALUES(
        "0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C", 18, "uniswap"
        );
        INSERT INTO assets(identifier,type, name, symbol,
        started, coingecko, cryptocompare, details_reference)
        VALUES(", "C", "Test token", "TEST"   ,
        123, "_ceth_0xD178b20c6007572bD1FD01D205cC20D32B4A6015",   "test-token",
        "", "0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C");
        """,
        None,
        'At asset DB update could not parse asset data out of',
    ),
    (
        """
        INSERT INTO assets(identifier,type, name, symbol,
        started, swapped_for, coingecko, cryptocompare, details_reference)
        VALUES("121-ada-FADS-as", "F", "A name", "SYMBOL"   ,
        NULL, NULL,   "", "", "121-ada-FADS-as");
        INSERT INTO common_asset_details(asset_id, forked) VALUES(
        "421-bbc-FADS-ks"
        );
        """,
        None,
        'At asset DB update could not parse common asset details data out of',
    ),
])
def test_parse_full_insert(assets_updater, text, expected_data, error_msg):
    text = text.replace('\n', '')
    if expected_data is not None:
        assert expected_data == assets_updater._parse_full_insert(text)
    else:
        with pytest.raises(DeserializationError) as excinfo:
            assets_updater._parse_full_insert(text)

        assert error_msg in str(excinfo.value)
