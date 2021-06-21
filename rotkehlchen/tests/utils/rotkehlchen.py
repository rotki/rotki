from contextlib import ExitStack
from typing import Any, Dict, List, NamedTuple, Optional, Union
from unittest.mock import _patch, patch

import requests

from rotkehlchen.accounting.structures import Balance, BalanceType
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.utils import DBAssetBalance, LocationData
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.blockchain import (
    mock_beaconchain,
    mock_bitcoin_balances_query,
    mock_etherscan_query,
)
from rotkehlchen.tests.utils.constants import A_RDN, A_XMR
from rotkehlchen.tests.utils.exchanges import (
    patch_binance_balances_query,
    patch_poloniex_balances_query,
    try_get_first_exchange,
)
from rotkehlchen.typing import BTCAddress, ChecksumEthAddress, Location, Timestamp


class BalancesTestSetup(NamedTuple):
    eth_balances: List[str]
    btc_balances: List[str]
    token_balances: Dict[EthereumToken, List[str]]
    binance_balances: Dict[Asset, FVal]
    poloniex_balances: Dict[Asset, FVal]
    manually_tracked_balances: List[ManuallyTrackedBalance]
    poloniex_patch: _patch
    binance_patch: _patch
    etherscan_patch: _patch
    beaconchain_patch: _patch
    ethtokens_max_chunks_patch: _patch
    bitcoin_patch: _patch
    defi_balances_patch: Optional[_patch]

    def enter_all_patches(self, stack: ExitStack):
        stack.enter_context(self.poloniex_patch)
        stack.enter_context(self.binance_patch)
        self.enter_blockchain_patches(stack)
        return stack

    def enter_blockchain_patches(self, stack: ExitStack):
        self.enter_ethereum_patches(stack)
        stack.enter_context(self.bitcoin_patch)
        return stack

    def enter_ethereum_patches(self, stack: ExitStack):
        stack.enter_context(self.etherscan_patch)
        stack.enter_context(self.ethtokens_max_chunks_patch)
        stack.enter_context(self.beaconchain_patch)
        if self.defi_balances_patch is not None:
            stack.enter_context(self.defi_balances_patch)
        return stack


def setup_balances(
        rotki,
        ethereum_accounts: Optional[List[ChecksumEthAddress]],
        btc_accounts: Optional[List[BTCAddress]],
        eth_balances: Optional[List[str]] = None,
        token_balances: Optional[Dict[EthereumToken, List[str]]] = None,
        liabilities: Optional[Dict[EthereumToken, List[str]]] = None,
        btc_balances: Optional[List[str]] = None,
        manually_tracked_balances: Optional[List[ManuallyTrackedBalance]] = None,
        original_queries: Optional[List[str]] = None,
        extra_flags: Optional[List[str]] = None,
) -> BalancesTestSetup:
    """Setup the blockchain, exchange and fiat balances for some tests

    When eth_balances, token_balances and btc_balances are not provided some
    default values are provided.
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

    defi_balances_patch = None
    if liabilities is not None:
        def mock_add_defi_balances_to_token_and_totals():
            # super hacky way of mocking this but well fuck it
            if len(rotki.chain_manager.balances.eth) == 4:
                d_liabilities = liabilities.copy()
            else:  # we know the only test this is used removes index 0 and 2
                msg = 'Should be at removal of accounts and only have 2 left'
                assert len(rotki.chain_manager.balances.eth) == 2, msg
                d_liabilities = {
                    k: [
                        x for idx, x in enumerate(v) if idx not in (0, 2)
                    ] for k, v in liabilities.items()
                }

            for token, balances in d_liabilities.items():
                for idx, balance in enumerate(balances):
                    balance = FVal(balance)
                    if balance == ZERO:
                        continue

                    account = ethereum_accounts[idx]
                    rotki.chain_manager.balances.eth[account].liabilities[token] = Balance(balance)
                    rotki.chain_manager.totals.liabilities[token] += Balance(balance)

        defi_balances_patch = patch.object(
            rotki.chain_manager,
            'add_defi_balances_to_token_and_totals',
            side_effect=mock_add_defi_balances_to_token_and_totals,
        )

    btc_map: Dict[BTCAddress, str] = {}
    for idx, btc_acc in enumerate(btc_accounts):
        btc_map[btc_acc] = btc_balances[idx]

    binance = try_get_first_exchange(rotki.exchange_manager, Location.BINANCE)
    binance_patch = patch_binance_balances_query(binance) if binance else None  # type: ignore
    poloniex = try_get_first_exchange(rotki.exchange_manager, Location.POLONIEX)
    poloniex_patch = patch_poloniex_balances_query(poloniex) if poloniex else None  # type: ignore
    etherscan_patch = mock_etherscan_query(
        eth_map=eth_map,
        etherscan=rotki.etherscan,
        original_queries=original_queries,
        original_requests_get=requests.get,
        extra_flags=extra_flags,
    )
    beaconchain_patch = mock_beaconchain(
        beaconchain=rotki.chain_manager.beaconchain,
        original_queries=original_queries,
        original_requests_get=requests.get,
    )
    # For ethtoken detection we can have bigger chunk length during tests since it's mocked anyway
    ethtokens_max_chunks_patch = patch(
        'rotkehlchen.chain.ethereum.tokens.ETHERSCAN_MAX_TOKEN_CHUNK_LENGTH',
        new=800,
    )

    bitcoin_patch = mock_bitcoin_balances_query(
        btc_map=btc_map,
        original_requests_get=requests.get,
    )
    # Taken from BINANCE_BALANCES_RESPONSE from tests.utils.exchanges
    binance_balances = {A_ETH: FVal('4763368.68006011'), A_BTC: FVal('4723846.89208129')}
    # Taken from POLONIEX_BALANCES_RESPONSE from tests.utils.exchanges
    poloniex_balances = {A_ETH: FVal('11.0'), A_BTC: FVal('5.5')}

    if manually_tracked_balances is None:
        manually_tracked_balances = []
    rotki.data.db.add_manually_tracked_balances(manually_tracked_balances)

    return BalancesTestSetup(
        eth_balances=eth_balances,
        btc_balances=btc_balances,
        token_balances=token_balances,
        binance_balances=binance_balances,
        poloniex_balances=poloniex_balances,
        manually_tracked_balances=manually_tracked_balances,
        poloniex_patch=poloniex_patch,
        binance_patch=binance_patch,
        etherscan_patch=etherscan_patch,
        ethtokens_max_chunks_patch=ethtokens_max_chunks_patch,
        bitcoin_patch=bitcoin_patch,
        beaconchain_patch=beaconchain_patch,
        defi_balances_patch=defi_balances_patch,
    )


def add_starting_balances(datahandler) -> List[DBAssetBalance]:
    """Adds some starting balances and other data to a testing instance"""
    balances = [
        DBAssetBalance(
            category=BalanceType.ASSET,
            time=Timestamp(1488326400),
            asset=A_BTC,
            amount='1',
            usd_value='1222.66',
        ), DBAssetBalance(
            category=BalanceType.ASSET,
            time=Timestamp(1488326400),
            asset=A_ETH,
            amount='10',
            usd_value='4517.4',
        ), DBAssetBalance(
            category=BalanceType.ASSET,
            time=Timestamp(1488326400),
            asset=A_EUR,
            amount='100',
            usd_value='61.5',
        ), DBAssetBalance(
            category=BalanceType.ASSET,
            time=Timestamp(1488326400),
            asset=A_XMR,
            amount='5',
            usd_value='135.6',
        ),
    ]
    datahandler.db.add_multiple_balances(balances)
    datahandler.db.conn.commit()

    location_data = [
        LocationData(
            time=Timestamp(1451606400),
            location=Location.KRAKEN.serialize_for_db(),  # pylint: disable=no-member
            usd_value='100',
        ),
        LocationData(
            time=Timestamp(1451606400),
            location=Location.BANKS.serialize_for_db(),  # pylint: disable=no-member
            usd_value='1000',
        ),
        LocationData(
            time=Timestamp(1461606500),
            location=Location.POLONIEX.serialize_for_db(),  # pylint: disable=no-member
            usd_value='50',
        ),
        LocationData(
            time=Timestamp(1461606500),
            location=Location.KRAKEN.serialize_for_db(),  # pylint: disable=no-member
            usd_value='200',
        ),
        LocationData(
            time=Timestamp(1461606500),
            location=Location.BANKS.serialize_for_db(),  # pylint: disable=no-member
            usd_value='50000',
        ),
        LocationData(
            time=Timestamp(1491607800),
            location=Location.POLONIEX.serialize_for_db(),  # pylint: disable=no-member
            usd_value='100',
        ),
        LocationData(
            time=Timestamp(1491607800),
            location=Location.KRAKEN.serialize_for_db(),  # pylint: disable=no-member
            usd_value='2000',
        ),
        LocationData(
            time=Timestamp(1491607800),
            location=Location.BANKS.serialize_for_db(),  # pylint: disable=no-member
            usd_value='10000',
        ),
        LocationData(
            time=Timestamp(1491607800),
            location=Location.BLOCKCHAIN.serialize_for_db(),  # pylint: disable=no-member
            usd_value='200000',
        ),
        LocationData(
            time=Timestamp(1451606400),
            location=Location.TOTAL.serialize_for_db(),  # pylint: disable=no-member
            usd_value='1500',
        ),
        LocationData(
            time=Timestamp(1461606500),
            location=Location.TOTAL.serialize_for_db(),  # pylint: disable=no-member
            usd_value='4500',
        ),
        LocationData(
            time=Timestamp(1491607800),
            location=Location.TOTAL.serialize_for_db(),  # pylint: disable=no-member
            usd_value='10700.5',
        ),
    ]
    datahandler.db.add_multiple_location_data(location_data)

    return balances
