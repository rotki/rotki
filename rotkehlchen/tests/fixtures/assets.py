
import pytest

from rotkehlchen.assets.resolver import AssetResolver


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
        force_reinitialize_asset_resolver,
        use_clean_caching_directory,
        user_ethereum_tokens,
        generatable_user_ethereum_tokens,
):
    """Run the first initialization of the AssetResolver singleton

    It's an autouse fixture so that it always gets initialized
    """
    # If we need to reinitialize asset resolver, do it. We need to if:
    # (1) test asks for it
    # (2) test uses clean directory, so the previously primed DB no longer exists
    if force_reinitialize_asset_resolver or use_clean_caching_directory:
        AssetResolver._AssetResolver__instance = None

    resolver = AssetResolver()
    # add any custom ethereum tokens given by the fixtures for a test
    if user_ethereum_tokens is not None:
        if generatable_user_ethereum_tokens is False:
            given_user_tokens = user_ethereum_tokens
        else:  # a callable was given
            given_user_tokens = user_ethereum_tokens()
        for entry in given_user_tokens:
            globaldb.add_asset(entry)

    return resolver
