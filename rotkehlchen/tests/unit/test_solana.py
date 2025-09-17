from contextlib import suppress
from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import get_solana_token
from rotkehlchen.chain.solana.utils import MetadataInfo, MintInfo, is_token_nft
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.errors.misc import InputError
from rotkehlchen.tests.utils.makerdao import FVal
from rotkehlchen.types import SolanaAddress, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.chain.solana.manager import SolanaManager
    from rotkehlchen.globaldb.handler import GlobalDBHandler


def identifier_to_address(identifier: str) -> SolanaAddress:
    """Extract the address from a solana token identifier."""
    return SolanaAddress(identifier.split(':')[1])


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [[
    SolanaAddress('updtkJ8HAhh3rSkBCd3p9Z1Q74yJW4rMhSbScRskDPM'),
    SolanaAddress('EfxpFpET4tvP4jjFEbWLCfkzQ6LozJjsPQD4FbpRk6KX'),
]])
def test_solana_balances(
        solana_manager: 'SolanaManager',
        solana_accounts: list['SolanaAddress'],
) -> None:
    assert solana_manager.get_multi_balance(accounts=solana_accounts) == {
        solana_accounts[0]: FVal('3.432027149'),
        solana_accounts[1]: FVal('1.437765205'),
    }


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['7pFGok3zuvacRP797Ke3bUZqbq24PbVQNLvwopfErvih']])
def test_solana_token_balances(
        solana_manager: 'SolanaManager',
        solana_accounts: list['SolanaAddress'],
) -> None:
    """Test that the solana token balances are returned correctly.
    The address tested currently holds 4 tokens and 11 NFTs according to solscan.

    1 token (JUPDROP) appears to be a scam token, with a token_standard of 2 (normal token) but
    with zero decimals and is classified as an NFT on solscan. We simply stick to the
    token_standard for this and class it as a normal token.

    1 token (catwifhat) is from the new Token 2022 Program, and the others are from the original
    Token Program.
    """
    balances = solana_manager.get_token_balances(account=solana_accounts[0])
    assert len(balances) == 15
    assert len([x for x in balances if '/token:' in x.identifier]) == 5
    assert len([x for x in balances if '/nft:' in x.identifier]) == 10
    # Check several token and nft balances
    assert balances[Asset('solana/token:EG1Y8goUGa7y4iRYRgLgwBmSHc4Lxc91qL35cdDNBiRc')] == FVal('392143.986634')  # noqa: E501
    assert balances[Asset('solana/token:6XLSXS1HDXsTbq53onqAUeCqU6fxuMSgu7JkfZ9kbonk')] == FVal('322811.321023')  # noqa: E501
    assert balances[Asset('solana/token:7atgF8KQo4wJrD5ATGX7t1V2zVvykPJbFfNeVf1icFv1')] == FVal('0.11')  # noqa: E501
    assert balances[Asset('solana/nft:GQqWmmdLGSwDRbN5fRdDfx17ZM55icmHtNyBSKcnLhNm')] == ONE
    assert balances[Asset('solana/nft:ByqVeGqR8VzvJG67E92rijxvuCzkLrbqotx2kPPo6eot')] == ONE
    assert balances[Asset('solana/nft:Cg4noWpzmDHhPZZXDwmCLJns43PJpLmd6E8aYL1pRcRJ')] == ONE


@pytest.mark.vcr
def test_solana_query_token_metadata(
        solana_manager: 'SolanaManager',
        globaldb: 'GlobalDBHandler',
) -> None:
    """Test that the solana token metadata is queried correctly for different types of tokens.
    Also check that get_solana_token can load tokens and nfts from the db using only the address.
    """
    for asset in (
        (a_amep := Asset('solana/token:6XLSXS1HDXsTbq53onqAUeCqU6fxuMSgu7JkfZ9kbonk')),  # legacy token using metaplex  # noqa: E501
        (a_cwif := Asset('solana/token:7atgF8KQo4wJrD5ATGX7t1V2zVvykPJbFfNeVf1icFv1')),  # token 2022 using metaplex  # noqa: E501
        (a_img := Asset('solana/token:znv3FZt2HFAvzYf5LxzVyryh3mBXWuTRRng25gEZAjh')),  # token 2022 using token extensions  # noqa: E501
        (a_pxwl := Asset('solana/nft:Cg4noWpzmDHhPZZXDwmCLJns43PJpLmd6E8aYL1pRcRJ')),  # nft using metaplex  # noqa: E501
    ):
        with suppress(InputError):  # Ensure it's not in the db so it queries the metadata
            globaldb.delete_asset_by_identifier(identifier=asset.identifier)

        solana_manager._create_token(token_address=SolanaAddress(asset.identifier.split(':')[1]))

    amep_token = get_solana_token(identifier_to_address(a_amep.identifier))
    assert amep_token is not None
    assert amep_token.name == 'America Party'
    assert amep_token.symbol == 'AMEP'
    assert amep_token.decimals == 6
    assert amep_token.token_kind == TokenKind.SPL_TOKEN
    cwif_token = get_solana_token(identifier_to_address(a_cwif.identifier))
    assert cwif_token is not None
    assert cwif_token.name == 'catwifhat'
    assert cwif_token.symbol == '$CWIF'
    assert cwif_token.decimals == 2
    assert cwif_token.token_kind == TokenKind.SPL_TOKEN
    img_token = get_solana_token(identifier_to_address(a_img.identifier))
    assert img_token is not None
    assert img_token.name == 'Infinite Money Glitch'
    assert img_token.symbol == 'IMG'
    assert img_token.decimals == 6
    assert img_token.token_kind == TokenKind.SPL_TOKEN
    pxwl_token = get_solana_token(identifier_to_address(a_pxwl.identifier))
    assert pxwl_token is not None
    assert pxwl_token.name == 'Pixie Willie #1089'
    assert pxwl_token.symbol == 'PXWL'
    assert pxwl_token.decimals == ZERO
    assert pxwl_token.token_kind == TokenKind.SPL_NFT


@pytest.mark.vcr
def test_is_nft_via_offchain_metadata() -> None:
    """Test that NFTs are still correctly identified when using the offchain metadata.
    Calls is_token_nft with decimals == 0, supply > 1 and token_standard == None, which forces it
    to use the offchain metadata from the given uri to determine if it's an NFT or not.
    """
    for uri, is_nft in (
        ('https://gateway.pinit.io/ipfs/QmSTAhtdaqJmm9FTxWEdjQwKqvvjf99uGvN3vQaxzhRGqP/1089.json', True),  # Pixie Willie NFT  # noqa: E501
        ('https://bafkreib5jykd5ehlvmi7f253jdjzzknj6eqlnqhzenfmdc6okrwksqfu6a.ipfs.nftstorage.link', False),  # catwifhat token  # noqa: E501
    ):
        assert is_token_nft(
            token_address=SolanaAddress('Cg4noWpzmDHhPZZXDwmCLJns43PJpLmd6E8aYL1pRcRJ'),
            mint_info=MintInfo(supply=100, decimals=0, tlv_data=None),
            metadata=MetadataInfo(name='Some Token', symbol='ST', uri=uri, token_standard=None),
        ) == is_nft
