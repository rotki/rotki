import pytest

from rotkehlchen.assets.types import AssetData, AssetType
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.updates import AssetsUpdater
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
def test_parse_full_insert(assets_updater, text, expected_data, error_msg):
    text = text.replace('\n', '')
    if expected_data is not None:
        assert expected_data == assets_updater._parse_full_insert(text)
    else:
        with pytest.raises(DeserializationError) as excinfo:
            assets_updater._parse_full_insert(text)

        assert error_msg in str(excinfo.value)
