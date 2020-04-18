from typing import Any, Dict, List, Optional

from rotkehlchen.assets.asset import Asset
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.db.utils import BlockchainAccounts, ManuallyTrackedBalance
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
    # Add the tests only etherscan API key
    db.add_external_service_credentials([ExternalServiceApiCredentials(
        service=ExternalService.CRYPTOCOMPARE,
        api_key=ApiKey('e929bcf68fa28715fa95f3bfa3baa3b9a6bc8f12112835586c705ab038ee06aa'),
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
