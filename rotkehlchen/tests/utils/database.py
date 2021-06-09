import random
from typing import Any, Dict, List, Optional
from unittest.mock import _patch, patch

from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.db.utils import BlockchainAccounts
from rotkehlchen.tests.utils.constants import DEFAULT_TESTS_MAIN_CURRENCY
from rotkehlchen.typing import (
    ApiKey,
    BlockchainAccountData,
    ExternalService,
    ExternalServiceApiCredentials,
    SupportedBlockchain,
)


def maybe_include_etherscan_key(db: DBHandler, include_etherscan_key: bool) -> None:
    if not include_etherscan_key:
        return
    # Add the tests only etherscan API key
    db.add_external_service_credentials([ExternalServiceApiCredentials(
        service=ExternalService.ETHERSCAN,
        api_key=ApiKey('8JT7WQBB2VQP5C3416Y8X3S8GBA3CVZKP4'),
    )])


def maybe_include_cryptocompare_key(db: DBHandler, include_cryptocompare_key: bool) -> None:
    if not include_cryptocompare_key:
        return
    keys = [
        'a4a36d7fd1835cc1d757186de8e7357b4478b73923933d09d3689140ecc23c03',
        'e929bcf68fa28715fa95f3bfa3baa3b9a6bc8f12112835586c705ab038ee06aa',
        '5159ca00f2579ef634b7f210ad725550572afbfb44e409460dd8a908d1c6416a',
        '6781b638eca6c3ca51a87efcdf0b9032397379a0810c5f8198a25493161c318d',
    ]
    # Add the tests only etherscan API key
    db.add_external_service_credentials([ExternalServiceApiCredentials(
        service=ExternalService.CRYPTOCOMPARE,
        api_key=ApiKey(random.choice(keys)),
    )])


def add_blockchain_accounts_to_db(db: DBHandler, blockchain_accounts: BlockchainAccounts) -> None:
    db.add_blockchain_accounts(
        SupportedBlockchain.ETHEREUM,
        [BlockchainAccountData(address=x) for x in blockchain_accounts.eth],
    )
    db.add_blockchain_accounts(
        SupportedBlockchain.BITCOIN,
        [BlockchainAccountData(address=x) for x in blockchain_accounts.btc],
    )


def add_settings_to_test_db(
        db: DBHandler,
        db_settings: Optional[Dict[str, Any]],
        ignored_assets: Optional[List[Asset]],
) -> None:
    settings = {
        # DO not submit usage analytics during tests
        'submit_usage_analytics': False,
        'main_currency': DEFAULT_TESTS_MAIN_CURRENCY,
    }
    # Set the given db_settings. The pre-set values have priority unless overriden here
    if db_settings is not None:
        for key, value in db_settings.items():
            settings[key] = value
    db.set_settings(ModifiableDBSettings(**settings))  # type: ignore

    if ignored_assets:
        for asset in ignored_assets:
            db.add_to_ignored_assets(asset)


def add_tags_to_test_db(db: DBHandler, tags: List[Dict[str, Any]]) -> None:
    for tag in tags:
        db.add_tag(
            name=tag['name'],
            description=tag.get('description', None),
            background_color=tag['background_color'],
            foreground_color=tag['foreground_color'],
        )


def add_manually_tracked_balances_to_test_db(
        db: DBHandler,
        balances: List[ManuallyTrackedBalance],
) -> None:
    db.add_manually_tracked_balances(balances)


def mock_dbhandler_update_owned_assets() -> _patch:
    """Just make sure update owned assets does nothing for older DB tests"""
    return patch(
        'rotkehlchen.db.dbhandler.DBHandler.update_owned_assets_in_globaldb',
        lambda x: None,
    )


def mock_dbhandler_add_globaldb_assetids() -> _patch:
    """Just make sure add globalds assetids does nothing for older DB tests"""
    return patch(
        'rotkehlchen.db.dbhandler.DBHandler.add_globaldb_assetids',
        lambda x: None,
    )


def mock_dbhandler_ensura_data_integrity() -> _patch:
    """Just make sure ensure_data_integrity oes nothing for older DB tests"""
    return patch(
        'rotkehlchen.db.dbhandler.DBHandler.ensure_data_integrity',
        lambda x: None,
    )
