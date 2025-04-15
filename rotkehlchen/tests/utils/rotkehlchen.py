from contextlib import ExitStack
from typing import Any, NamedTuple
from unittest.mock import _patch, patch

import requests

from rotkehlchen.accounting.structures.balance import Balance, BalanceType
from rotkehlchen.assets.asset import Asset, AssetWithOracles, EvmToken
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.ethereum.defi.structures import DefiProtocolBalances
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR
from rotkehlchen.db.utils import DBAssetBalance, LocationData
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
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
from rotkehlchen.types import (
    BTCAddress,
    ChecksumEvmAddress,
    Location,
    Price,
    SupportedBlockchain,
    Timestamp,
)


class BalancesTestSetup(NamedTuple):
    eth_balances: list[str]
    btc_balances: list[str]
    token_balances: dict[EvmToken, list[str]]
    binance_balances: dict[AssetWithOracles, FVal]
    poloniex_balances: dict[AssetWithOracles, FVal]
    manually_tracked_balances: list[ManuallyTrackedBalance]
    poloniex_patch: _patch | None
    binance_patch: _patch | None
    etherscan_patch: _patch
    beaconchain_patch: _patch
    evmtokens_max_chunks_patch: _patch
    bitcoin_patch: _patch

    def enter_all_patches(self, stack: ExitStack):
        if self.poloniex_patch:
            stack.enter_context(self.poloniex_patch)
        if self.binance_patch:
            stack.enter_context(self.binance_patch)
        self.enter_blockchain_patches(stack)
        return stack

    def enter_blockchain_patches(self, stack: ExitStack):
        self.enter_ethereum_patches(stack)
        stack.enter_context(self.bitcoin_patch)
        return stack

    def enter_ethereum_patches(self, stack: ExitStack):
        stack.enter_context(self.etherscan_patch)
        stack.enter_context(self.evmtokens_max_chunks_patch)
        stack.enter_context(self.beaconchain_patch)
        return stack


def setup_balances(
        rotki,
        ethereum_accounts: list[ChecksumEvmAddress] | None,
        btc_accounts: list[BTCAddress] | None,
        eth_balances: list[str] | None = None,
        token_balances: dict[EvmToken, list[str]] | None = None,
        populate_detected_tokens: bool = True,
        liabilities: dict[EvmToken, list[str]] | None = None,
        btc_balances: list[str] | None = None,
        manually_tracked_balances: list[ManuallyTrackedBalance] | None = None,
        manual_current_prices: list[tuple[Asset, Asset, Price]] | None = None,
        original_queries: list[str] | None = None,
        extra_flags: list[str] | None = None,
        defi_balances: dict[ChecksumEvmAddress, list[DefiProtocolBalances]] | None = None,
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
    elif len(ethereum_accounts) != 0:  # Default test values
        eth_balances = ['1000000', '2000000']
    else:
        eth_balances = []

    if token_balances is not None:
        msg = 'token balances length does not match number of owned eth tokens'
        for balances in token_balances.values():
            msg = (
                'The token balances should be a list with each '
                'element representing balance of an account'
            )
            assert len(balances) == len(ethereum_accounts), msg
    elif len(ethereum_accounts) != 0:  # default test values
        token_balances = {A_RDN.resolve_to_evm_token(): ['0', '4000000']}
    else:
        token_balances = {}

    if btc_balances is not None:
        msg = (
            'The btc balances should be a list with each '
            'element representing balance of an account'
        )
        assert len(btc_balances) == len(btc_accounts)
    elif len(btc_accounts) != 0:  # default test values
        btc_balances = ['3000000', '5000000']
    else:
        btc_balances = []

    eth_map: dict[ChecksumEvmAddress, dict[str | EvmToken, Any]] = {}
    with rotki.data.db.user_write() as write_cursor:
        for idx, acc in enumerate(ethereum_accounts):
            eth_map[acc] = {}
            eth_map[acc]['ETH'] = eth_balances[idx]
            for token in token_balances:
                eth_map[acc][token] = token_balances[token][idx]
            if populate_detected_tokens is True:
                rotki.data.db.save_tokens_for_address(write_cursor, acc, SupportedBlockchain.ETHEREUM, list(token_balances.keys()))  # noqa: E501

    if liabilities is not None:
        def mock_add_defi_balances_to_account():
            # super hacky way of mocking this but well fuck it
            if len(rotki.chains_aggregator.balances.eth) == 4:
                d_liabilities = liabilities.copy()
            else:  # we know the only test this is used removes index 0 and 2
                msg = 'Should be at removal of accounts and only have 2 left'
                assert len(rotki.chains_aggregator.balances.eth) == 2, msg
                d_liabilities = {
                    k: [
                        x for idx, x in enumerate(v) if idx not in {0, 2}
                    ] for k, v in liabilities.items()
                }

            for token, balances in d_liabilities.items():
                for idx, raw_balance in enumerate(balances):
                    balance = FVal(raw_balance)
                    if balance == ZERO:
                        continue

                    account = rotki.chains_aggregator.accounts.eth[idx]
                    rotki.chains_aggregator.balances.eth[account].liabilities[token] = Balance(balance)  # noqa: E501

            # need this to not get randomized behaviour when defi balances are added or not
            # depending on whether liabilities are mocked
            if rotki.chains_aggregator.defi_balances is not None:
                for account, single_defi_balances in rotki.chains_aggregator.defi_balances.items():
                    rotki.chains_aggregator._add_account_defi_balances_to_token(
                        account=account,
                        balances=single_defi_balances,
                    )

    btc_map: dict[BTCAddress, str] = {}
    for idx, btc_acc in enumerate(btc_accounts):
        btc_map[btc_acc] = btc_balances[idx]

    binance = try_get_first_exchange(rotki.exchange_manager, Location.BINANCE)
    binance_patch = patch_binance_balances_query(binance) if binance else None
    poloniex = try_get_first_exchange(rotki.exchange_manager, Location.POLONIEX)
    poloniex_patch = patch_poloniex_balances_query(poloniex) if poloniex else None
    etherscan_patch = mock_etherscan_query(
        eth_map=eth_map,
        etherscan=rotki.chains_aggregator.ethereum.node_inquirer.etherscan,
        ethereum=rotki.chains_aggregator.ethereum.node_inquirer,
        original_queries=original_queries,
        original_requests_get=requests.get,
        extra_flags=extra_flags,
    )
    beaconchain_patch = mock_beaconchain(
        beaconchain=rotki.chains_aggregator.beaconchain,
        original_queries=original_queries,
        original_requests_get=requests.get,
    )
    # For evmtoken detection we can have bigger chunk length during tests since it's mocked anyway
    evmtokens_max_chunks_patch = patch(
        'rotkehlchen.chain.evm.tokens.ETHERSCAN_MAX_ARGUMENTS_TO_CONTRACT',
        new=800,
    )

    bitcoin_patch = mock_bitcoin_balances_query(
        btc_map=btc_map,
        original_requests_get=requests.get,
    )
    # Taken from BINANCE_BALANCES_RESPONSE from tests.utils.exchanges
    binance_balances: dict[AssetWithOracles, FVal] = {
        A_ETH.resolve_to_asset_with_oracles(): FVal('4763368.68006011'),
        A_BTC.resolve_to_asset_with_oracles(): FVal('4723846.89208129'),
    }
    # Taken from POLONIEX_BALANCES_RESPONSE from tests.utils.exchanges
    poloniex_balances: dict[AssetWithOracles, FVal] = {
        A_ETH.resolve_to_asset_with_oracles(): FVal('11.0'),
        A_BTC.resolve_to_asset_with_oracles(): FVal('5.5'),
    }

    if manually_tracked_balances is None:
        manually_tracked_balances = []
    with rotki.data.db.user_write() as cursor:
        rotki.data.db.add_manually_tracked_balances(cursor, manually_tracked_balances)

    if manual_current_prices is not None:
        for current_price in manual_current_prices:
            GlobalDBHandler.add_manual_latest_price(
                from_asset=current_price[0],
                to_asset=current_price[1],
                price=current_price[2],
            )

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
        evmtokens_max_chunks_patch=evmtokens_max_chunks_patch,
        bitcoin_patch=bitcoin_patch,
        beaconchain_patch=beaconchain_patch,
    )


def add_starting_balances(datahandler) -> list[DBAssetBalance]:
    """Adds some starting balances and other data to a testing instance"""
    balances = [
        DBAssetBalance(
            category=BalanceType.ASSET,
            time=Timestamp(1488326400),
            asset=A_BTC,
            amount=FVal('1'),
            usd_value=FVal('1222.66'),
        ), DBAssetBalance(
            category=BalanceType.ASSET,
            time=Timestamp(1488326400),
            asset=A_ETH,
            amount=FVal('10'),
            usd_value=FVal('4517.4'),
        ), DBAssetBalance(
            category=BalanceType.ASSET,
            time=Timestamp(1488326400),
            asset=A_EUR,
            amount=FVal('100'),
            usd_value=FVal('61.5'),
        ), DBAssetBalance(
            category=BalanceType.ASSET,
            time=Timestamp(1488326400),
            asset=A_XMR,
            amount=FVal('5'),
            usd_value=FVal('135.6'),
        ),
    ]
    with datahandler.db.user_write() as cursor:
        datahandler.db.add_multiple_balances(cursor, balances)

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
    with datahandler.db.user_write() as cursor:
        datahandler.db.add_multiple_location_data(cursor, location_data)

    return balances


def add_starting_nfts(datahandler):
    """Adds a time series for an account owning a NFT"""
    balances = [
        DBAssetBalance(
            category=BalanceType.ASSET,
            time=Timestamp(1488326400),
            asset=Asset('_nft_pickle'),
            amount='1',
            usd_value='1000',
        ), DBAssetBalance(
            category=BalanceType.ASSET,
            time=Timestamp(1488426400),
            asset=Asset('_nft_pickle'),
            amount='1',
            usd_value='1000',
        ), DBAssetBalance(
            category=BalanceType.ASSET,
            time=Timestamp(1488526400),
            asset=Asset('_nft_pickle'),
            amount='2',
            usd_value='2000',
        ), DBAssetBalance(
            category=BalanceType.ASSET,
            time=Timestamp(1488626400),
            asset=Asset('_nft_pickle'),
            amount='1',
            usd_value='1000',
        ),
    ]
    with datahandler.db.user_write() as cursor:
        datahandler.db.add_asset_identifiers(cursor, ['_nft_pickle'])
        datahandler.db.add_multiple_balances(cursor, balances)

        location_data = [
            LocationData(
                time=Timestamp(1488326400),
                location=Location.TOTAL.serialize_for_db(),  # pylint: disable=no-member
                usd_value='3000',
            ),
            LocationData(
                time=Timestamp(1488426400),
                location=Location.TOTAL.serialize_for_db(),  # pylint: disable=no-member
                usd_value='4000',
            ),
            LocationData(
                time=Timestamp(1488526400),
                location=Location.TOTAL.serialize_for_db(),  # pylint: disable=no-member
                usd_value='5000',
            ),
            LocationData(
                time=Timestamp(1488626400),
                location=Location.TOTAL.serialize_for_db(),  # pylint: disable=no-member
                usd_value='5500',
            ),
        ]
        datahandler.db.add_multiple_location_data(cursor, location_data)
