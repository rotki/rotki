from unittest.mock import patch

import pytest

from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.tests.utils.mock import MockResponse


@pytest.fixture()
def mock_asset_meta_github_response() -> str:
    return '{"md5": "", "version": 0}'


@pytest.fixture()
def mock_asset_github_response() -> str:
    return '{}'


@pytest.fixture()
def query_github_for_assets() -> bool:
    """If True, the default behavior of querying github for latest assets will occur"""
    return False


@pytest.fixture()
def asset_resolver(
        data_dir,
        query_github_for_assets,
        mock_asset_meta_github_response,
        mock_asset_github_response,
):
    """Run the first initialization of the AssetResolver singleton"""
    if query_github_for_assets:
        AssetResolver(data_dir)
        return

    # else mock the github request to return version lower than anything possible
    def mock_get_request(url: str) -> MockResponse:
        if url == 'https://raw.githubusercontent.com/rotki/rotki/develop/rotkehlchen/data/all_assets.meta':  # noqa: E501
            return MockResponse(200, mock_asset_meta_github_response)
        elif url == 'https://raw.githubusercontent.com/rotki/rotki/develop/rotkehlchen/data/all_assets.json':  # noqa: E501
            return MockResponse(200, mock_asset_github_response)

        raise AssertionError('This mock should receive no other urls')

    get_patch = patch('requests.get', side_effect=mock_get_request)
    with get_patch:
        AssetResolver(data_dir)
