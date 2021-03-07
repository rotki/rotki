import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.typing import CustomEthereumToken
from rotkehlchen.constants.resolver import ETHEREUM_DIRECTIVE
from rotkehlchen.errors import InputError
from rotkehlchen.tests.utils.constants import A_BAT
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.tests.utils.globaldb import INITIAL_TOKENS
from rotkehlchen.typing import AssetType


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('custom_ethereum_tokens', [INITIAL_TOKENS])
def test_get_ethereum_token_identifier(globaldb):
    assert globaldb.get_ethereum_token_identifier('0xnotexistingaddress') is None
    token_0_id = globaldb.get_ethereum_token_identifier(INITIAL_TOKENS[0].address)
    assert token_0_id == ETHEREUM_DIRECTIVE + INITIAL_TOKENS[0].address


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_add_edit_token_with_wrong_swapped_for(globaldb):
    """Test that giving a non-existing swapped_for token in the DB raises InputError

    This can only be unit tested since via the API, marshmallow checks for Asset existence already
    """
    # To unit test it we need to even hack it a bit. Make a new token, add it in the DB
    # then delete it and then try to add a new one referencing the old one. Since we
    # need to obtain a valid CustomEthereumToken object
    address_to_delete = make_ethereum_address()
    token_to_delete = CustomEthereumToken(
        address=address_to_delete,
        decimals=18,
        name='willdell',
        symbol='DELME',
    )
    token_to_delete_id = 'DELMEID1'
    globaldb.add_asset(
        asset_id=token_to_delete_id,
        asset_type=AssetType.ETHEREUM_TOKEN,
        data=token_to_delete,
    )
    asset_to_delete = Asset(token_to_delete_id)
    assert globaldb.delete_ethereum_token(address_to_delete) == token_to_delete_id

    # now try to add a new token with swapped_for pointing to a non existing token in the DB
    with pytest.raises(InputError):
        globaldb.add_asset(
            asset_id='NEWID',
            asset_type=AssetType.ETHEREUM_TOKEN,
            data=CustomEthereumToken(
                address=make_ethereum_address(),
                swapped_for=asset_to_delete,
            ),
        )

    # now edit a new token with swapped_for pointing to a non existing token in the DB
    bat_custom = A_BAT.to_custom_ethereum_token()
    bat_custom = CustomEthereumToken(
        address=A_BAT.ethereum_address,
        decimals=A_BAT.decimals,
        name=A_BAT.name,
        symbol=A_BAT.symbol,
        started=A_BAT.started,
        swapped_for=asset_to_delete,
        coingecko=A_BAT.coingecko,
        cryptocompare=A_BAT.cryptocompare,
        protocol=None,
        underlying_tokens=None,
    )
    with pytest.raises(InputError):
        globaldb.edit_ethereum_token(bat_custom)
