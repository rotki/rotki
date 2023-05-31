from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
from rotkehlchen.chain.ethereum.modules.aave.aave import Aave
from rotkehlchen.chain.ethereum.modules.aave.common import (
    AaveStats,
    asset_to_aave_reserve_address,
    atoken_to_asset,
)
from rotkehlchen.chain.ethereum.utils import ethaddress_to_asset
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.premium.premium import Premium, PremiumCredentials
from rotkehlchen.tests.utils.aave import ATOKENV1_TO_ASSET, ATOKENV2_ADDRESS_TO_RESERVE_ASSET
from rotkehlchen.types import ChainID, Timestamp, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.price import PriceHistorian
    from rotkehlchen.inquirer import Inquirer


def test_aave_reserve_mapping():
    atokensv1 = GlobalDBHandler().get_evm_tokens(chain_id=ChainID.ETHEREUM, protocol='aave')
    for token in atokensv1:
        underlying_asset = ATOKENV1_TO_ASSET[token].resolve_to_crypto_asset()
        if underlying_asset == A_ETH:
            assert asset_to_aave_reserve_address(underlying_asset) == ETH_SPECIAL_ADDRESS
            continue

        assert ethaddress_to_asset(underlying_asset.evm_address) == underlying_asset
        assert asset_to_aave_reserve_address(underlying_asset) == underlying_asset.evm_address


def test_atoken_to_asset():
    cursor = GlobalDBHandler().conn.cursor()
    result = cursor.execute(
        'SELECT A.identifier from evm_tokens as A LEFT OUTER JOIN common_asset_details as B '
        'WHERE A.identifier=B.identifier AND A.protocol IN (?, ?)',
        ('aave', 'aave-v2'),
    )
    for entry in result:
        atoken = EvmToken(entry[0])
        reserve_asset = atoken_to_asset(atoken)
        if atoken in ATOKENV1_TO_ASSET:
            assert reserve_asset == ATOKENV1_TO_ASSET[atoken]
        else:
            assert reserve_asset == ATOKENV2_ADDRESS_TO_RESERVE_ASSET[atoken.evm_address]

    for atokenv1, reserve_asset in ATOKENV1_TO_ASSET.items():
        assert atoken_to_asset(atokenv1.resolve_to_evm_token()) == reserve_asset


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_aave_v1_events_stats(
        database: 'DBHandler',
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_transaction_decoder: 'EthereumTransactionDecoder',
        rotki_premium_credentials: 'PremiumCredentials',
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
        price_historian: 'PriceHistorian',  # pylint: disable=unused-argument
):
    """
    Test aave stats for v1 events. The transactions have been obtained from
    https://github.com/rotki/rotki/blob/6b1a538ca6a1ec235933b0d3936698be9ebc72ee/rotkehlchen/tests/api/test_aave.py#L181
    """
    tx_hashes = [
        deserialize_evm_tx_hash('0x8b72307967c4f7a486c1cb1b6ebca5e549de06e02930ece0399e2096f1a132c5'),  # supply    102.92 DAI and get same amount of aDAI  # noqa: E501
        deserialize_evm_tx_hash('0x78ae48d93e0284d1f9a5e1cd4a7e5f2e3daf65ab5dafb0c4bd626aa90e783d60'),  # supply    160    DAI  # noqa: E501
        deserialize_evm_tx_hash('0xb9999b06b706dcc973bcf381d69f12620f1bef887082bce9679cf256f7e8023c'),  # supply    390    DAI  # noqa: E501
        deserialize_evm_tx_hash('0x28054d29620515337b8ffb2f7f2dda5b2033beae9844b42359893f4f73d855bc'),  # supply    58.985 DAI  # noqa: E501
        deserialize_evm_tx_hash('0x07ac09cc06c7cd74c7312f3a82c9f77d69ba7a89a4a3b7ded33db07e32c3607c'),  # cast vote interest update  # noqa: E501
        deserialize_evm_tx_hash('0x90b818ba8d3b55f332b64f3df58bf37f33addcbfc1f27bd1ec6102ae4bf2d871'),  # supply    168.84 DAI  # noqa: E501
        deserialize_evm_tx_hash('0xc3a8978418afa1a4f139e9314ac787cacfbed79b1daa28e146bb0bf6fdf79a41'),  # supply    1939.8 DAI  # noqa: E501
        deserialize_evm_tx_hash('0x930879d66d13c37edf25cdbb2d2e85b65c3b2a026529ff4085146bb7a5398410'),  # supply    2507.6 DAI  # noqa: E501
        deserialize_evm_tx_hash('0x4fed67963375a3f90916f0cf7cb9e4d12644629e36233025b36060494ffba486'),  # withdraw  7968.4 DAI  # noqa: E501
    ]
    ethereum_transaction_decoder.decode_transaction_hashes(
        ignore_cache=True,
        tx_hashes=tx_hashes,
    )

    aave = Aave(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
        premium=Premium(rotki_premium_credentials),
        msg_aggregator=database.msg_aggregator,
    )
    stats = aave.get_stats_for_addresses(
        addresses=[string_to_evm_address('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12')],
        from_timestamp=Timestamp(0),
        to_timestamp=ts_now(),
        given_defi_balances={},
    )
    expected_stats = {
        '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12': AaveStats(
            total_earned_interest={
                Asset('eip155:1/erc20:0xfC1E690f61EFd961294b3e1Ce3313fBD8aa4f85d'): Balance(
                    amount=FVal('139.001974573936997356'),
                    usd_value=FVal('139.001974573936997356'),
                ),
            },
            total_lost={
                Asset('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'): Balance(
                    amount=FVal('2640.139017221015985936'),
                    usd_value=FVal('3960.2085258315239789040'),
                ),
            },
            total_earned_liquidations={},
        ),
    }
    assert stats == expected_stats
