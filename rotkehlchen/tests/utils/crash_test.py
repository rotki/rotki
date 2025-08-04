"""
This file is executed from `rotkehlchen/tests/unit/test_search.py::test_db_persistence_after_search
as a logic in a subprocess. This is done to simulate the behavior of crashing the application.
"""
from uuid import uuid4

from rotkehlchen.assets.asset import Asset, CustomAsset
from rotkehlchen.config import default_data_directory
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.db.filtering import AssetsFilterQuery
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import TRACE, add_logging_level
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.args import default_args
from rotkehlchen.types import Price


def subprocess_sequence_for_test_db_persistence_after_search() -> None:
    """
    - Add a new custom asset
    - Search for the custom asset
    - Add a manual price for the custom asset
    - Crash the application
    """
    add_logging_level('TRACE', TRACE)
    data_dir = default_data_directory().parent / 'test_data'
    rotki = Rotkehlchen(default_args(data_dir=data_dir))  # type: ignore
    create_new = (data_dir / 'users' / 'testuser' / 'rotkehlchen.db').exists() is False
    rotki.unlock_user(
        user='testuser',
        password='123',
        create_new=create_new,
        sync_approval='no',
        premium_credentials=None,
        resume_from_backup=False,
    )

    # check manual price of a newly added custom asset
    custom_asset_identifier = str(uuid4())
    GlobalDBHandler.add_asset(CustomAsset.initialize(
        identifier=custom_asset_identifier,
        name='Test Asset',
        custom_asset_type='test',
    ))

    # search the Test Asset
    GlobalDBHandler.search_assets(
        filter_query=AssetsFilterQuery.make(substring_search='Test Asset'),
        db=rotki.data.db,
    )

    # add a manual price for the custom asset
    GlobalDBHandler.add_manual_latest_price(
        from_asset=Asset(custom_asset_identifier),
        to_asset=A_USD,
        price=Price(FVal(123)),
    )

    # using print to send the identifier in stdout to be parsed in get_identifier_from_stdout
    print(f'Identifier: {custom_asset_identifier}')  # noqa: T201


if __name__ == '__main__':
    subprocess_sequence_for_test_db_persistence_after_search()
