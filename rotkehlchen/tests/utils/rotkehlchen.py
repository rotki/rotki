from contextlib import ExitStack
from typing import Any, Dict, List, NamedTuple, Optional, Union
from unittest.mock import _patch

import requests

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR
from rotkehlchen.db.utils import AssetBalance, LocationData
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.blockchain import (
    mock_alethio_balances_query,
    mock_bitcoin_balances_query,
    mock_etherscan_balances_query,
)
from rotkehlchen.tests.utils.constants import A_RDN, A_XMR
from rotkehlchen.tests.utils.exchanges import (
    patch_binance_balances_query,
    patch_poloniex_balances_query,
)
from rotkehlchen.typing import BTCAddress, ChecksumEthAddress, Location, Timestamp


class BalancesTestSetup(NamedTuple):
    eth_balances: List[str]
    btc_balances: List[str]
    fiat_balances: Dict[str, FVal]
    token_balances: Dict[EthereumToken, List[str]]
    binance_balances: Dict[str, FVal]
    poloniex_balances: Dict[str, FVal]
    manually_tracked_balances: List[ManuallyTrackedBalance]
    poloniex_patch: _patch
    binance_patch: _patch
    etherscan_patch: _patch
    alethio_patch: _patch
    bitcoin_patch: _patch

    def enter_all_patches(self, stack: ExitStack):
        stack.enter_context(self.poloniex_patch)
        stack.enter_context(self.binance_patch)
        stack.enter_context(self.etherscan_patch)
        stack.enter_context(self.alethio_patch)
        stack.enter_context(self.bitcoin_patch)
        return stack

    def enter_blockchain_patches(self, stack: ExitStack):
        stack.enter_context(self.etherscan_patch)
        stack.enter_context(self.alethio_patch)
        stack.enter_context(self.bitcoin_patch)
        return stack


def setup_balances(
        rotki,
        ethereum_accounts: Optional[List[ChecksumEthAddress]],
        btc_accounts: Optional[List[BTCAddress]],
        eth_balances: Optional[List[str]] = None,
        token_balances: Optional[Dict[EthereumToken, List[str]]] = None,
        btc_balances: Optional[List[str]] = None,
        use_alethio: bool = False,
        manually_tracked_balances: Optional[List[ManuallyTrackedBalance]] = None,
) -> BalancesTestSetup:
    """Setup the blockchain, exchange and fiat balances for some tests

    When eth_balances, token_balances and btc_balances are not provided some
    default values are provided.

    If use_alethio is not True the alethio queries are properly tested. If not
    then an error is returned with each query so the tests revert to etherscan
    """
    if ethereum_accounts is None:
        ethereum_accounts = []
    if btc_accounts is None:
        btc_accounts = []

    # Sanity checks for setup input
    if eth_balances is not None:
        msg = (
            'The eth balances should be a list with each '
            'element representing balance of an account'
        )
        assert len(eth_balances) == len(ethereum_accounts)
    else:
        # Default test values
        if len(ethereum_accounts) != 0:
            eth_balances = ['1000000', '2000000']
        else:
            eth_balances = []
    if token_balances is not None:
        msg = 'token balances length does not match number of owned eth tokens'
        # We use >= here since the test may add more tokens to the owned eth tokens
        # at later points after setup
        assert len(token_balances) >= len(rotki.chain_manager.owned_eth_tokens), msg
        for _, balances in token_balances.items():
            msg = (
                'The token balances should be a list with each '
                'element representing balance of an account'
            )
            assert len(balances) == len(ethereum_accounts), msg
    else:
        # Default test values
        if len(ethereum_accounts) != 0:
            token_balances = {A_RDN: ['0', '4000000']}
        else:
            token_balances = {}
    if btc_balances is not None:
        msg = (
            'The btc balances should be a list with each '
            'element representing balance of an account'
        )
        assert len(btc_balances) == len(btc_accounts)
    else:
        # Default test values
        if len(btc_accounts) != 0:
            btc_balances = ['3000000', '5000000']
        else:
            btc_balances = []

    eth_map: Dict[ChecksumEthAddress, Dict[Union[str, EthereumToken], Any]] = {}
    for idx, acc in enumerate(ethereum_accounts):
        eth_map[acc] = {}
        eth_map[acc]['ETH'] = eth_balances[idx]
        for token in token_balances:
            eth_map[acc][token] = token_balances[token][idx]

    btc_map: Dict[BTCAddress, str] = {}
    for idx, btc_acc in enumerate(btc_accounts):
        btc_map[btc_acc] = btc_balances[idx]

    eur_balance = FVal('1550')

    rotki.data.db.add_fiat_balance(A_EUR, eur_balance)
    binance = rotki.exchange_manager.connected_exchanges.get('binance', None)
    binance_patch = patch_binance_balances_query(binance) if binance else None
    poloniex = rotki.exchange_manager.connected_exchanges.get('poloniex', None)
    poloniex_patch = patch_poloniex_balances_query(poloniex) if poloniex else None
    etherscan_patch = mock_etherscan_balances_query(
        eth_map=eth_map,
        etherscan=rotki.etherscan,
        original_requests_get=requests.get,
    )
    alethio_patch = mock_alethio_balances_query(
        eth_map=eth_map,
        alethio=rotki.chain_manager.alethio,
        use_alethio=use_alethio,
    )
    bitcoin_patch = mock_bitcoin_balances_query(
        btc_map=btc_map,
        original_requests_get=requests.get,
    )
    # Taken from BINANCE_BALANCES_RESPONSE from tests.utils.exchanges
    binance_balances = {'ETH': FVal('4763368.68006011'), 'BTC': FVal('4723846.89208129')}
    # Taken from POLONIEX_BALANCES_RESPONSE from tests.utils.exchanges
    poloniex_balances = {'ETH': FVal('11.0'), 'BTC': FVal('5.5')}

    if manually_tracked_balances is None:
        manually_tracked_balances = []
    return BalancesTestSetup(
        eth_balances=eth_balances,
        btc_balances=btc_balances,
        token_balances=token_balances,
        fiat_balances={'EUR': eur_balance},
        binance_balances=binance_balances,
        poloniex_balances=poloniex_balances,
        manually_tracked_balances=manually_tracked_balances,
        poloniex_patch=poloniex_patch,
        binance_patch=binance_patch,
        etherscan_patch=etherscan_patch,
        alethio_patch=alethio_patch,
        bitcoin_patch=bitcoin_patch,
    )


def add_starting_balances(datahandler) -> List[AssetBalance]:
    """Adds some starting balances and other data to a testing instance"""
    balances = [
        AssetBalance(
            time=Timestamp(1488326400),
            asset=A_BTC,
            amount='1',
            usd_value='1222.66',
        ), AssetBalance(
            time=Timestamp(1488326400),
            asset=A_ETH,
            amount='10',
            usd_value='4517.4',
        ), AssetBalance(
            time=Timestamp(1488326400),
            asset=A_EUR,
            amount='100',
            usd_value='61.5',
        ), AssetBalance(
            time=Timestamp(1488326400),
            asset=A_XMR,
            amount='5',
            usd_value='135.6',
        ),
    ]
    datahandler.db.add_multiple_balances(balances)
    # Also add an unknown/invalid asset. This will generate a warning
    cursor = datahandler.db.conn.cursor()
    cursor.execute(
        'INSERT INTO timed_balances('
        '    time, currency, amount, usd_value) '
        ' VALUES(?, ?, ?, ?)',
        (1469326500, 'ADSADX', '10.1', '100.5'),
    )
    datahandler.db.conn.commit()

    location_data = [
        LocationData(
            time=Timestamp(1451606400),
            location=Location.KRAKEN.serialize_for_db(),
            usd_value='100',
        ),
        LocationData(
            time=Timestamp(1451606400),
            location=Location.BANKS.serialize_for_db(),
            usd_value='1000',
        ),
        LocationData(
            time=Timestamp(1461606500),
            location=Location.POLONIEX.serialize_for_db(),
            usd_value='50',
        ),
        LocationData(
            time=Timestamp(1461606500),
            location=Location.KRAKEN.serialize_for_db(),
            usd_value='200',
        ),
        LocationData(
            time=Timestamp(1461606500),
            location=Location.BANKS.serialize_for_db(),
            usd_value='50000',
        ),
        LocationData(
            time=Timestamp(1491607800),
            location=Location.POLONIEX.serialize_for_db(),
            usd_value='100',
        ),
        LocationData(
            time=Timestamp(1491607800),
            location=Location.KRAKEN.serialize_for_db(),
            usd_value='2000',
        ),
        LocationData(
            time=Timestamp(1491607800),
            location=Location.BANKS.serialize_for_db(),
            usd_value='10000',
        ),
        LocationData(
            time=Timestamp(1491607800),
            location=Location.BLOCKCHAIN.serialize_for_db(),
            usd_value='200000',
        ),
        LocationData(
            time=Timestamp(1451606400),
            location=Location.TOTAL.serialize_for_db(),
            usd_value='1500',
        ),
        LocationData(
            time=Timestamp(1461606500),
            location=Location.TOTAL.serialize_for_db(),
            usd_value='4500',
        ),
        LocationData(
            time=Timestamp(1491607800),
            location=Location.TOTAL.serialize_for_db(),
            usd_value='10700.5',
        ),
    ]
    datahandler.db.add_multiple_location_data(location_data)

    return balances
