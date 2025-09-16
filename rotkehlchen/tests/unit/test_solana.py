from contextlib import suppress
from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.solana.utils import MetadataInfo, MintInfo, is_token_nft
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.errors.misc import InputError
from rotkehlchen.tests.utils.makerdao import FVal
from rotkehlchen.types import SolanaAddress, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.chain.solana.manager import SolanaManager
    from rotkehlchen.globaldb.handler import GlobalDBHandler


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
    """Test that the solana token metadata is queried correctly for different types of tokens."""
    for asset in (
        (a_amep := Asset('solana/token:6XLSXS1HDXsTbq53onqAUeCqU6fxuMSgu7JkfZ9kbonk')),
        (a_cwif := Asset('solana/token:7atgF8KQo4wJrD5ATGX7t1V2zVvykPJbFfNeVf1icFv1')),
        (a_img := Asset('solana/token:znv3FZt2HFAvzYf5LxzVyryh3mBXWuTRRng25gEZAjh')),
        (a_pxwl := Asset('solana/nft:Cg4noWpzmDHhPZZXDwmCLJns43PJpLmd6E8aYL1pRcRJ')),
    ):
        with suppress(InputError):  # Ensure it's not in the db so it queries the metadata
            globaldb.delete_asset_by_identifier(identifier=asset.identifier)

        solana_manager._create_token(token_address=SolanaAddress(asset.identifier.split(':')[1]))

    a_amep = a_amep.resolve_to_solana_token()  # legacy token using metaplex
    assert a_amep.name == 'America Party'
    assert a_amep.symbol == 'AMEP'
    assert a_amep.decimals == 6
    assert a_amep.token_kind == TokenKind.SPL_TOKEN
    a_cwif = a_cwif.resolve_to_solana_token()  # token 2022 using metaplex
    assert a_cwif.name == 'catwifhat'
    assert a_cwif.symbol == '$CWIF'
    assert a_cwif.decimals == 2
    assert a_cwif.token_kind == TokenKind.SPL_TOKEN
    a_img = a_img.resolve_to_solana_token()  # token 2022 using token extensions
    assert a_img.name == 'Infinite Money Glitch'
    assert a_img.symbol == 'IMG'
    assert a_img.decimals == 6
    assert a_img.token_kind == TokenKind.SPL_TOKEN
    a_pxwl = a_pxwl.resolve_to_solana_token()  # nft using metaplex
    assert a_pxwl.name == 'Pixie Willie #1089'
    assert a_pxwl.symbol == 'PXWL'
    assert a_pxwl.decimals == ZERO
    assert a_pxwl.token_kind == TokenKind.SPL_NFT


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
