from unittest.mock import patch

import pytest

from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.tests.utils.mock import MockResponse


@pytest.fixture(name='mock_asset_meta_github_response')
def fixture_mock_asset_meta_github_response() -> str:
    return '{"md5": "", "version": 0}'


@pytest.fixture(name='mock_asset_github_response')
def fixture_mock_asset_github_response() -> str:
    return '{}'


@pytest.fixture(name='query_github_for_assets')
def fixture_query_github_for_assets() -> bool:
    """If True, the default behavior of querying github for latest assets will occur"""
    return False


@pytest.fixture(name='force_reinitialize_asset_resolver')
def fixture_force_reinitialize_asset_resolver() -> bool:
    """If True, the asset resolver instance will be force to start frm scratch"""
    return False


# We need auto-use here since the fixture needs to be included
# everywhere so as to not have Asset() calls use a Resolver not
# initialized from here which would take more time
@pytest.fixture(autouse=True)
def asset_resolver(
        data_dir,
        query_github_for_assets,
        mock_asset_meta_github_response,
        mock_asset_github_response,
        force_reinitialize_asset_resolver,
):
    """Run the first initialization of the AssetResolver singleton

    It's an autouse fixture so that it always gets initialized
    """
    if force_reinitialize_asset_resolver:
        AssetResolver._AssetResolver__instance = None

    if query_github_for_assets:
        AssetResolver(data_dir)
        return

    # else mock the github request to return version lower than anything possible
    def mock_get_request(url: str) -> MockResponse:
        if url == 'https://raw.githubusercontent.com/rotki/rotki/develop/rotkehlchen/data/all_assets.meta':  # noqa: E501
            return MockResponse(200, mock_asset_meta_github_response)
        if url == 'https://raw.githubusercontent.com/rotki/rotki/develop/rotkehlchen/data/all_assets.json':  # noqa: E501
            return MockResponse(200, mock_asset_github_response)
        # else
        raise AssertionError('This mock should receive no other urls')

    get_patch = patch('requests.get', side_effect=mock_get_request)
    with get_patch:
        AssetResolver(data_dir)
