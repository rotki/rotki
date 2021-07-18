from unittest.mock import patch

import pytest

from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.typing import AssetType
from rotkehlchen.constants.resolver import ETHEREUM_DIRECTIVE
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
        globaldb,
        query_github_for_assets,
        mock_asset_meta_github_response,
        mock_asset_github_response,
        force_reinitialize_asset_resolver,
        use_clean_caching_directory,
        custom_ethereum_tokens,
):
    """Run the first initialization of the AssetResolver singleton

    It's an autouse fixture so that it always gets initialized
    """
    # If we need to reinitialize asset resolver, do it. We need to if:
    # (1) test asks for it
    # (2) test uses clean directory, so the previously primed DB no longer exists
    if force_reinitialize_asset_resolver or use_clean_caching_directory:
        AssetResolver._AssetResolver__instance = None

    if query_github_for_assets:
        resolver = AssetResolver()
    else:
        # mock the github request to return version lower than anything possible
        def mock_get_request(url: str) -> MockResponse:
            if url == 'https://raw.githubusercontent.com/rotki/rotki/develop/rotkehlchen/data/all_assets.meta':  # noqa: E501
                return MockResponse(200, mock_asset_meta_github_response)
            if url == 'https://raw.githubusercontent.com/rotki/rotki/develop/rotkehlchen/data/all_assets.json':  # noqa: E501
                return MockResponse(200, mock_asset_github_response)
            # else
            raise AssertionError('This mock should receive no other urls')

        get_patch = patch('requests.get', side_effect=mock_get_request)
        with get_patch:
            resolver = AssetResolver()

    # add any custom ethereum tokens given by the fixtures for a test
    if custom_ethereum_tokens is not None:
        for entry in custom_ethereum_tokens:
            asset_id = ETHEREUM_DIRECTIVE + entry.ethereum_address
            globaldb.add_asset(asset_id=asset_id, asset_type=AssetType.ETHEREUM_TOKEN, data=entry)

    return resolver
