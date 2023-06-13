from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.modules.compound.compound import Compound
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
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.price import PriceHistorian
    from rotkehlchen.inquirer import Inquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', '0xC440f3C87DC4B6843CABc413916220D4f4FeD117', '0xF59D4937BF1305856C3a267bB07791507a3377Ee', '0x65304d6aff5096472519ca86a6a1fea31cb47Ced']])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_compound_events_stats(
        database: 'DBHandler',
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_transaction_decoder: 'EthereumTransactionDecoder',
        rotki_premium_credentials: 'PremiumCredentials',
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
        price_historian: 'PriceHistorian',  # pylint: disable=unused-argument
        ethereum_accounts,
):
    """
    Test aave stats for v1 events. The transactions have been obtained from
    https://github.com/rotki/rotki/blob/6b1a538ca6a1ec235933b0d3936698be9ebc72ee/rotkehlchen/tests/api/test_aave.py#L181
    """
    tx_hashes = [
        deserialize_evm_tx_hash('0xacc2e21f911a4e438966694e9ad16747878a15dae52de62a09f1ebabc8b26c8d'),  # Supply 2,988.4343  # noqa: E501
        deserialize_evm_tx_hash('0xd88138b22ef340f9ce572408b8cef10ea8df91768aee5205d5edbdb6fca76665'),  # withdraw 2,997.387744259127714006 DAI  # noqa: E501
        deserialize_evm_tx_hash('0x0e1b732cd29d65be155dba7675379ce5e63e1902773609b3b15b2d685ff6bc3d'),  # withdraw 2 USDC  # noqa: E501
        deserialize_evm_tx_hash('0x3ddf908ddeba7d95bc4903f5dff9c47a2c79ac517ad3aa4ebf6330ce949e7297'),  # Borrow 0.0108 ether  # noqa: E501
        deserialize_evm_tx_hash('0x301527f6f3c728a298f971d68a5bc917c31ad0ce477d91c0daf653b248e9b072'),  # Borrow 0.0001 ether  # noqa: E501
        deserialize_evm_tx_hash('0x1b4827a2fd4d6fcbf10bdd1a6c845c1a5f294ca39c60c90610b2a4d9fa5f6a33'),  # liquidation lost 38.409 cUSDC  # noqa: E501
        deserialize_evm_tx_hash('0xdc01f2eb8833ac877051900f14b0c5fc99b8b948cb00cfacede84ee8b670a272'),  # borrow 0.00065 Ether  # noqa: E501
        deserialize_evm_tx_hash('0x82806e5f41c31a85c89b0ce096d784002d867df9d7f2d67bf07d47407e1a1225'),  # liquidation lost 22.13 cUSDC  # noqa: E501
        deserialize_evm_tx_hash('0xf051267460d677f794f0d4a9a39e74b1e76733f0956809d7acee2f339a48e6d9'),  # borrow  0.000326 Ether  # noqa: E501
        deserialize_evm_tx_hash('0x160c0e6db0df5ea0c1cc9b1b31bd90c842ef793c9b2ab496efdc62bdd80eeb52'),  # liquidation lost 13.06 cUSDC  # noqa: E501
        deserialize_evm_tx_hash('0xe5f31776ada64cb566c5d8601791aa75a18c72963af29d6646bd6557a4e6a4ae'),  # supply  1275.82 DAI  # noqa: E501
        deserialize_evm_tx_hash('0x63ec8370b29e3ddad6d59f09a161023b5bc0524eb5ca6c4473a5242f40e2129f'),  # withdraw  1275. 96 DAI  # noqa: E501
        deserialize_evm_tx_hash('0x02356347600dc86ba35effba30207277b022b05f5573f4dd66ba667c6656b3f3'),  # liquidation lost 5.48 cUSDC  # noqa: E501
        deserialize_evm_tx_hash('0xaa15bf91ae1db6f981cf72372cbb497bc51cfb750a7e61fdb18719756741c734'),  # liquidation lost 5.88 cUSDC  # noqa: E501
        deserialize_evm_tx_hash('0x2bbb296ebf1d94ad28d54c446cb23709b3463c4a43d8b5b8438ff39b2b985e1c'),  # generate 91971 cDAI and mint 0.002 CMP  # noqa: E501
        deserialize_evm_tx_hash('0x48a3e2ef8a746383deac34d74f2f0ea0451b2047701fbed4b9d769a782888eea'),  # repay  # noqa: E501
    ]
    ethereum_transaction_decoder.decode_transaction_hashes(
        ignore_cache=True,
        tx_hashes=tx_hashes,
    )

    compound = Compound(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
        premium=Premium(rotki_premium_credentials),
        msg_aggregator=database.msg_aggregator,
    )
    stats = compound.get_stats(
        addresses=ethereum_accounts,
        from_timestamp=Timestamp(0),
        to_timestamp=ts_now(),
        given_defi_balances={},
    )
    import pprint
    pprint.pprint(stats)
    assert False
