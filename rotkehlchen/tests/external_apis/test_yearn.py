import datetime
import json
import logging
from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
import requests
from eth_abi import encode
from freezegun import freeze_time

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
from rotkehlchen.chain.ethereum.modules.yearn.constants import (
    CPT_YEARN_STAKING,
    CPT_YEARN_V2,
    CPT_YEARN_V3,
)
from rotkehlchen.chain.ethereum.modules.yearn.decoder import YearnDecoder
from rotkehlchen.chain.ethereum.modules.yearn.utils import (
    KONG_API,
    _query_yearn_vaults,
    query_yearn_vaults,
)
from rotkehlchen.chain.evm.decoding.yearn import decoder as yearn_decoder_module
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.constants.timing import WEEK_IN_SECONDS
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_last_queried_ts_by_key,
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tasks.assets import retry_missing_token_details
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import CacheType, ChainID, SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.ethereum.transactions import EthereumTransactions
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.inquirer import Inquirer


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['v4_global_before_migration1.db'])
def test_yearn_api_addresses_are_checksummed(database, ethereum_inquirer):
    """A vault the api reports with a non-checksummed address is still stored canonically.

    Identifiers are compared exactly, so a token created from a lowercased address builds an
    identifier that never matches the canonical one for the same token.
    """
    vault_address = '0x4c2dF8adB2B14e1d5FDBD9d11A2cf7562b67adC9'
    underlying_address = '0x9b77bd0a665F05995b68e36fC1053AFFfAf0d4B5'

    def mock_yearn_api(url, timeout):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.OK, json.dumps([{
            'address': vault_address.lower(),
            'apiVersion': '0.4.6',
            'decimals': 18,
            'name': 'Curve mevETHfrxE-f Factory yVault',
            'symbol': 'yvCurve-mevETHfrxE-f',
            'asset': {
                'address': underlying_address.lower(),
                'decimals': 18,
                'name': 'Curve.fi Factory Crypto Pool: mevETH/frxETH',
                'symbol': 'mevETHfrxE-f',
            },
        }]))

    with patch.object(requests, 'get', wraps=mock_yearn_api):
        query_yearn_vaults(db=database, node_inquirer=ethereum_inquirer)

    # queried by the checksummed address, which the address column only matches exactly
    assert (token := GlobalDBHandler.get_evm_token(
        address=string_to_evm_address(vault_address),
        chain_id=ChainID.ETHEREUM,
    )) is not None
    assert token.protocol == CPT_YEARN_V2
    assert token.underlying_tokens[0].address == underlying_address


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['v4_global_before_migration1.db'])
def test_kong_vaults_without_api_version_are_skipped_silently(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        caplog: pytest.LogCaptureFixture,
) -> None:
    """Kong lists non-yearn ERC4626 vaults without an apiVersion. They are not yearn
    vaults, so they are skipped without an error log while the rest are still stored."""
    vault_address, non_yearn_address = make_evm_address(), make_evm_address()
    caplog.set_level(logging.DEBUG)
    with patch.object(requests, 'get', return_value=MockResponse(HTTPStatus.OK, json.dumps([{
        'address': non_yearn_address,
        'apiVersion': None,
        'decimals': 18,
        'name': 'Savings Dai',
        'symbol': 'sDAI',
        'asset': {'address': make_evm_address(), 'decimals': 18, 'name': 'Dai', 'symbol': 'DAI'},
    }, {
        'address': vault_address,
        'apiVersion': '3.0.4',
        'decimals': 6,
        'name': 'USDC yVault',
        'symbol': 'yvUSDC',
        'asset': {'address': make_evm_address(), 'decimals': 6, 'name': 'USD Coin', 'symbol': 'USDC'},  # noqa: E501
        'staking': None,
    }]))):
        query_yearn_vaults(db=database, node_inquirer=ethereum_inquirer)

    assert GlobalDBHandler.get_evm_token(address=non_yearn_address, chain_id=ChainID.ETHEREUM) is None  # noqa: E501
    assert (token := GlobalDBHandler.get_evm_token(address=vault_address, chain_id=ChainID.ETHEREUM)) is not None  # noqa: E501
    assert token.protocol == CPT_YEARN_V3
    assert [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR] == []


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['v4_global_before_migration1.db'])
@pytest.mark.parametrize('missing_asset', [{'asset': None}, {}])
def test_kong_vaults_without_asset_are_skipped_with_info_log(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        caplog: pytest.LogCaptureFixture,
        missing_asset: dict[str, None],
) -> None:
    """Kong serves vaults whose underlying asset it has not indexed yet with a null or
    absent asset. They are skipped with an info log and the rest are still stored."""
    no_asset_address, vault_address = make_evm_address(), make_evm_address()
    caplog.set_level(logging.DEBUG)
    with patch.object(requests, 'get', return_value=MockResponse(HTTPStatus.OK, json.dumps([{
        'address': no_asset_address,
        'apiVersion': '3.1.0',
        'decimals': 18,
        'name': 'yvUSD Fixed',
        'symbol': 'yvUSD',
        'staking': None,
    } | missing_asset, {
        'address': vault_address,
        'apiVersion': '3.0.4',
        'decimals': 6,
        'name': 'USDC yVault',
        'symbol': 'yvUSDC',
        'asset': {'address': make_evm_address(), 'decimals': 6, 'name': 'USD Coin', 'symbol': 'USDC'},  # noqa: E501
        'staking': None,
    }]))):
        query_yearn_vaults(db=database, node_inquirer=ethereum_inquirer)

    assert GlobalDBHandler.get_evm_token(address=no_asset_address, chain_id=ChainID.ETHEREUM) is None  # noqa: E501
    assert (token := GlobalDBHandler.get_evm_token(address=vault_address, chain_id=ChainID.ETHEREUM)) is not None  # noqa: E501
    assert token.protocol == CPT_YEARN_V3
    assert [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING] == []
    assert [
        r.getMessage() for r in caplog.records
        if r.levelno == logging.INFO and 'without underlying asset' in r.getMessage()
    ] == [f'MainThread: Skipping yearn {CPT_YEARN_V3} vault {no_asset_address} without underlying asset']  # noqa: E501


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['v4_global_before_migration1.db'])
def test_malformed_staking_skips_only_that_vault(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        caplog: pytest.LogCaptureFixture,
) -> None:
    """A vault whose staking entry is not an object (the old yDaemon string shape) is
    logged and skipped, and the vaults after it in the response are still processed."""
    malformed_vault, staking_address, next_vault = (make_evm_address() for _ in range(3))
    with patch.object(requests, 'get', return_value=MockResponse(HTTPStatus.OK, json.dumps([{
        'address': address,
        'apiVersion': '0.4.6',
        'decimals': 18,
        'name': f'yVault {idx}',
        'symbol': f'yv{idx}',
        'asset': {'address': make_evm_address(), 'decimals': 18, 'name': 'Dai', 'symbol': 'DAI'},
        'staking': staking,
    } for idx, (address, staking) in enumerate(((malformed_vault, staking_address), (next_vault, None)))]))):  # noqa: E501
        query_yearn_vaults(db=database, node_inquirer=ethereum_inquirer)

    assert GlobalDBHandler.get_evm_token(address=staking_address, chain_id=ChainID.ETHEREUM) is None  # noqa: E501
    assert (token := GlobalDBHandler.get_evm_token(address=next_vault, chain_id=ChainID.ETHEREUM)) is not None  # noqa: E501
    assert token.protocol == CPT_YEARN_V2
    assert any(
        r.levelno == logging.ERROR and 'Unexpected staking metadata' in r.getMessage()
        for r in caplog.records
    )


def test_staking_token_saved_when_the_nodes_fail(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """A staking token whose details can't be queried is still saved as a yearn staking
    token, with the decimals of its vault and the identifier as name, so its transactions
    decode as staking. The token details retry task fills in its details later."""
    vault_address, underlying_address, staking_address = (make_evm_address() for _ in range(3))

    def mock_yearn_api(url, timeout):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.OK, json.dumps([{
            'address': vault_address,
            'apiVersion': '0.4.6',
            'decimals': 6,
            'name': 'USDC yVault',
            'symbol': 'yvUSDC',
            'asset': {'address': underlying_address, 'decimals': 6, 'name': 'USD Coin', 'symbol': 'USDC'},  # noqa: E501
            'staking': {'address': staking_address, 'available': True},
        }]))

    with (
        patch.object(requests, 'get', wraps=mock_yearn_api),
        patch.object(ethereum_inquirer, 'multicall_2', side_effect=RemoteError('nodes down')),
    ):
        query_yearn_vaults(db=database, node_inquirer=ethereum_inquirer)

    token = EvmToken(identifier := evm_address_to_identifier(staking_address, ChainID.ETHEREUM))
    assert (token.name, token.decimals, token.protocol) == (identifier, 6, CPT_YEARN_STAKING)
    assert [x.address for x in token.underlying_tokens or []] == [vault_address]

    chains_aggregator = MagicMock()
    chains_aggregator.database = database
    chains_aggregator.accounts.get.side_effect = lambda chain: ['account'] if chain == SupportedBlockchain.ETHEREUM else []  # noqa: E501
    chains_aggregator.get_evm_manager.return_value.node_inquirer = ethereum_inquirer
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=[
        (True, encode([abi_type], [value]))
        for abi_type, value in (('uint8', 6), ('string', 'yvUSDC-gauge'), ('string', 'yvUSDC gauge'))  # noqa: E501
    ]):
        retry_missing_token_details(chains_aggregator)

    token = EvmToken(identifier)
    assert (token.name, token.symbol, token.decimals) == ('yvUSDC gauge', 'yvUSDC-gauge', 6)
    assert token.protocol == CPT_YEARN_STAKING


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['v4_global_before_migration1.db'])
def test_yearn_api(database, ethereum_inquirer):
    """Test that vaults are queried correctly

    Since they are already in the globalDB we check with an older globalDB
    """
    # mock coingecko response
    original_request = requests.get
    yearn_vaults_cache_key = (CacheType.YEARN_VAULTS, str(ChainID.ETHEREUM.serialize_for_db()))

    def mock_yearn_api(url, timeout):
        """Return Kong vault metadata for the API response"""
        if url == f'{KONG_API}/list/vaults/1':
            return MockResponse(HTTPStatus.OK, """[
    {
        "address": "0xBfBC4acAE2ceC91A5bC80eCA1C9290F92959f7c3",
        "name": "Curve eUSDUSDC Factory yVault",
        "symbol": "yvCurve-eUSDUSDC-f",
        "decimals": 18,
        "apiVersion": "0.4.6",
        "asset": {
            "address": "0x08BfA22bB3e024CDfEB3eca53c0cb93bF59c4147",
            "name": "eUSD/USDC",
            "symbol": "eUSDUSDC",
            "decimals": 18
        },
        "staking": {"address": null, "available": false}
    },
    {
        "address": "0x4c2dF8adB2B14e1d5FDBD9d11A2cf7562b67adC9",
        "name": "Curve mevETHfrxE-f Factory yVault",
        "symbol": "yvCurve-mevETHfrxE-f",
        "decimals": 18,
        "apiVersion": "0.4.6",
        "asset": {
            "address": "0x9b77bd0a665F05995b68e36fC1053AFFfAf0d4B5",
            "name": "Curve.fi Factory Crypto Pool: mevETH/frxETH",
            "symbol": "mevETHfrxE-f",
            "decimals": 18
        },
        "staking": null
    },
    {
        "address": "0x341bb10D8f5947f3066502DC8125d9b8949FD3D6",
        "name": "Curve STG-USDC Pool yVault",
        "symbol": "yvCurve-STG-USDC",
        "decimals": 18,
        "apiVersion": "0.4.3",
        "asset": {
            "address": "0xdf55670e27bE5cDE7228dD0A6849181891c9ebA1",
            "name": "Curve.fi Factory Crypto Pool: STG/USDC",
            "symbol": "STGUSDC-f",
            "decimals": 18
        },
        "staking": null,
        "isRetired": true
    },
    {
        "address": "0x04AeBe2e4301CdF5E9c57B01eBdfe4Ac4B48DD13",
        "name": "mkUSD yVault-A",
        "symbol": "yvmkUSD-A",
        "decimals": 18,
        "apiVersion": "~3.0.1",
        "asset": {
            "address": "0x4591DBfF62656E7859Afe5e45f6f47D3669fBB28",
            "name": "Prisma mkUSD",
            "symbol": "mkUSD",
            "decimals": 18
        },
        "staking": null,
        "isHidden": true
    }
]""")
        nonlocal original_request
        return original_request(url, timeout)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        state_before = globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=yearn_vaults_cache_key,
        )

    with patch.object(requests, 'get', wraps=mock_yearn_api):
        query_yearn_vaults(db=database, node_inquirer=ethereum_inquirer)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        state_after = globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=yearn_vaults_cache_key,
        )

        last_queried_ts = globaldb_get_unique_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=yearn_vaults_cache_key,
        )
        assert last_queried_ts is not None

    assert state_after != state_before
    assert state_before is None
    assert int(state_after) == 4

    # check that a new vault was added
    token = GlobalDBHandler.get_evm_token(
        address=string_to_evm_address('0x341bb10D8f5947f3066502DC8125d9b8949FD3D6'),
        chain_id=ChainID.ETHEREUM,
    )

    assert token is not None
    assert token.name == 'Curve STG-USDC Pool yVault'
    assert token.symbol == 'yvCurve-STG-USDC'
    assert token.protocol == CPT_YEARN_V2

    # vault underlying token metadata
    token = GlobalDBHandler.get_evm_token(
        address=string_to_evm_address('0x4c2dF8adB2B14e1d5FDBD9d11A2cf7562b67adC9'),
        chain_id=ChainID.ETHEREUM,
    )
    assert token.name == 'Curve mevETHfrxE-f Factory yVault'
    assert token.symbol == 'yvCurve-mevETHfrxE-f'
    assert token.protocol == CPT_YEARN_V2
    assert len(token.underlying_tokens) == 1
    assert token.underlying_tokens[0].address == '0x9b77bd0a665F05995b68e36fC1053AFFfAf0d4B5'

    # v3 vault token
    token = GlobalDBHandler.get_evm_token(
        address=string_to_evm_address('0x04AeBe2e4301CdF5E9c57B01eBdfe4Ac4B48DD13'),
        chain_id=ChainID.ETHEREUM,
    )
    assert token.name == 'mkUSD yVault-A'
    assert token.symbol == 'yvmkUSD-A'
    assert token.protocol == CPT_YEARN_V3
    assert len(token.underlying_tokens) == 1
    assert token.underlying_tokens[0].address == '0x4591DBfF62656E7859Afe5e45f6f47D3669fBB28'

    # trigger the query again and check that the timestamp was updated
    future_timestamp = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(seconds=WEEK_IN_SECONDS)  # noqa: E501
    with freeze_time(future_timestamp), patch.object(requests, 'get', wraps=mock_yearn_api):
        query_yearn_vaults(db=database, node_inquirer=ethereum_inquirer)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        new_queried_ts = globaldb_get_unique_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=yearn_vaults_cache_key,
        )
    assert new_queried_ts is not None
    assert new_queried_ts > last_queried_ts


@pytest.mark.vcr
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_process_staked_vaults(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        globaldb: GlobalDBHandler,
        inquirer_defi: Inquirer,
):
    data = """[{
        "address": "0x790a60024bC3aea28385b60480f15a0771f26D09",
        "name": "Curve YFI-ETH Pool yVault",
        "symbol": "yvCurve-YFIETH",
        "decimals": 18,
        "apiVersion": "0.4.3",
        "icon": "https://assets.smold.app/api/token/1/0x790a60024bC3aea28385b60480f15a0771f26D09/logo-128.png",
        "type": "Yearn Vault",
        "asset": {
        "address": "0x29059568bB40344487d62f7450E78b8E6C74e0e5",
        "name": "Curve.fi Factory Crypto Pool: YFI/ETH",
        "symbol": "YFIETH-f",
        "decimals": 18,
        "icon": "https://assets.smold.app/api/token/1/0x29059568bB40344487d62f7450E78b8E6C74e0e5/logo-128.png"
        },
        "staking": {"address": "0x7Fd8Af959B54A677a1D8F92265Bd0714274C56a3", "available": true}
    }]"""
    original_request = requests.get
    with globaldb.conn.write_ctx() as write_cursor:
        write_cursor.execute('DELETE FROM unique_cache WHERE key=?', ('YEARN_VAULTS1',))

    def mock_yearn_api(url, timeout):
        """Return Kong vault metadata for the API response"""
        if url == f'{KONG_API}/list/vaults/1':
            return MockResponse(HTTPStatus.OK, data)
        nonlocal original_request
        return original_request(url, timeout)

    evm_manager = inquirer_defi.get_evm_manager(chain_id=ChainID.ETHEREUM)
    with patch.object(requests, 'get', wraps=mock_yearn_api):
        query_yearn_vaults(db=database, node_inquirer=ethereum_inquirer)

    token = EvmToken('eip155:1/erc20:0x7Fd8Af959B54A677a1D8F92265Bd0714274C56a3')
    underlying_tokens = token.underlying_tokens
    assert len(underlying_tokens) == 1
    assert underlying_tokens[0].address == string_to_evm_address('0x790a60024bC3aea28385b60480f15a0771f26D09')  # noqa: E501
    assert token.protocol == CPT_YEARN_STAKING
    with patch.object(evm_manager, 'assure_curve_cache_is_queried_and_decoder_updated'):
        assert inquirer_defi.find_usd_price(token).is_close(FVal('8776.098257'), max_diff='1e6')


@pytest.mark.parametrize(('status', 'data'), [
    (HTTPStatus.SERVICE_UNAVAILABLE, '{}'),
    (HTTPStatus.TOO_MANY_REQUESTS, '{}'),
    (HTTPStatus.OK, 'invalid json'),
    (HTTPStatus.OK, '{}'),
    (HTTPStatus.OK, '[null]'),
])
def test_yearn_kong_invalid_response(status, data):
    with (
        patch.object(requests, 'get', return_value=MockResponse(status, data)),
        pytest.raises(RemoteError),
    ):
        _query_yearn_vaults(chain_id=ChainID.ETHEREUM)


@pytest.mark.parametrize('chain_id', [ChainID.ETHEREUM, ChainID.OPTIMISM, ChainID.BASE])
def test_yearn_kong_chain_list(chain_id):
    with patch.object(requests, 'get', return_value=MockResponse(HTTPStatus.OK, '[]')) as request:
        assert _query_yearn_vaults(chain_id=chain_id) == []

    assert request.call_count == 1
    assert request.call_args.args == (f'{KONG_API}/list/vaults/{chain_id.value}',)


def test_ethereum_decoder_reads_chain_scoped_cache_key(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        eth_transactions: EthereumTransactions,
) -> None:
    """The ethereum yearn decoder checks the same cache key query_yearn_vaults writes, so a
    fresh cache does not trigger a new query of the yearn API on every decoder reload.

    The decoder is built directly since the ethereum_transaction_decoder fixture stubs the
    cache staleness check of every decoder to False."""
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_unique_cache_value(
            write_cursor=write_cursor,
            key_parts=(CacheType.YEARN_VAULTS, str(ChainID.ETHEREUM.serialize_for_db())),
            value='1322',
        )

    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    assert isinstance(yearn_decoder := decoder.decoders['Yearn'], YearnDecoder)
    with patch.object(yearn_decoder_module, 'query_yearn_vaults') as patched_query_yearn_vaults:
        yearn_decoder.reload_data()

    assert patched_query_yearn_vaults.call_count == 0
