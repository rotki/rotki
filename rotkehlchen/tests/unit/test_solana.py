from contextlib import suppress
from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import get_or_create_solana_token, get_solana_token
from rotkehlchen.chain.solana.utils import MetadataInfo, MintInfo, is_solana_token_nft
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.errors.misc import InputError
from rotkehlchen.serialization.deserialize import deserialize_tx_signature
from rotkehlchen.tests.utils.makerdao import FVal
from rotkehlchen.types import SolanaAddress, Timestamp, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.chain.solana.manager import SolanaManager
    from rotkehlchen.chain.solana.node_inquirer import SolanaInquirer
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
        solana_inquirer: 'SolanaInquirer',
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

        get_or_create_solana_token(
            userdb=solana_inquirer.database,
            address=SolanaAddress(asset.identifier.split(':')[1]),
            solana_inquirer=solana_inquirer,
        )

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
    Calls is_solana_token_nft with decimals == 0, supply > 1 and token_standard == None, which
    forces it to use the offchain metadata from the given uri to determine if it's an NFT or not.
    """
    for uri, is_nft in (
        ('https://gateway.pinit.io/ipfs/QmSTAhtdaqJmm9FTxWEdjQwKqvvjf99uGvN3vQaxzhRGqP/1089.json', True),  # Pixie Willie NFT  # noqa: E501
        ('https://bafkreib5jykd5ehlvmi7f253jdjzzknj6eqlnqhzenfmdc6okrwksqfu6a.ipfs.nftstorage.link', False),  # catwifhat token  # noqa: E501
    ):
        assert is_solana_token_nft(
            token_address=SolanaAddress('Cg4noWpzmDHhPZZXDwmCLJns43PJpLmd6E8aYL1pRcRJ'),
            mint_info=MintInfo(supply=100, decimals=0, tlv_data=None),
            metadata=MetadataInfo(name='Some Token', symbol='ST', uri=uri, token_standard=None),
        ) == is_nft


@pytest.mark.vcr
def test_query_tx_from_rpc(solana_inquirer: 'SolanaInquirer') -> None:
    tx = solana_inquirer.get_transaction_for_signature(
        signature=(signature := deserialize_tx_signature('58F9fNP78FiBCbVc2Gdy6on2d6pZiJcTbqib4MsTfNcgAXqS7UGp3a3eeEy7fRWnLiXaJjncUHdqtpCnEFuVsVEM')),  # noqa: E501
    )
    assert tx is not None
    assert tx.signature == signature
    assert tx.fee == 15001
    assert tx.slot == 344394079
    assert tx.block_time == Timestamp(1748974662)
    assert tx.success is True
    assert len(tx.account_keys) == 25
    assert tx.account_keys[12:] == [  # Check that addresses from the address lookup tables (ALTs) are correct.  # noqa: E501
        'src5qyZHqTqecJV4aY6Cb6zDZLMDzrDKKezs22MPHr4',  # last key from the tx's account keys
        '81MPQqJY58rgT83sy99MkRHs2g3dyy6uWKHD24twV62F',  # first writable from ALT 1
        '7ixaquirw9k3VNkxJ5zpbx9GTAbAvUrrNeZovw7TBqyu',
        '2JwKVhEeJZn8bHsHVK1rFuATHni3wDft3UFAsrKKMKfP',
        'CdaNdGvQ1mCz9kKushqgkoKy2DwETQscJuBZEP9E2sMM',
        '8djrA5qrjHMExDfau983kZjpNdhPVLHedvjJcrjTEwkD',
        '9yfN3qv6tKxhniWcrQi7bP1kZgXmdd4dLm84rostKvQG',  # one writable from ALT 2
        'So11111111111111111111111111111111111111112',  # first readonly from ALT 1
        'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
        'LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo',
        'D1ZN9Wj1fRSUQfCjhvnu1hqDMT7hzjzBBpi12nVniYD6',
        'HJEPgYkbqjetrphNHG2W33SjG9mB4PrXorW358MzfggY',  # first readonly from ALT 2
        '12hWR4XhwfmjMcJ2ykfwcVVbP1mW7Cdu7LUqdzzYar8m',
    ]
    assert len(tx.instructions) == 23
    assert len([x for x in tx.instructions if x.parent_execution_index is None]) == 8
    assert len([x for x in tx.instructions if x.parent_execution_index == 2]) == 4
    assert len([x for x in tx.instructions if x.parent_execution_index == 5]) == 5
    assert len([x for x in tx.instructions if x.parent_execution_index == 7]) == 6


@pytest.mark.vcr
def test_query_signatures_for_address(solana_inquirer: 'SolanaInquirer') -> None:
    signatures = solana_inquirer.query_tx_signatures_for_address(
        address=SolanaAddress('7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY'),
    )
    assert len(signatures) == 64
    assert signatures[0] == deserialize_tx_signature('4awgHCjCD2Da2UbaKitSfUWExW2eVSA1x5PBrdHBi61NdCpWWxG1JbCDRbKUsQYSPZfPzMKLGrJw2XhajUUvz2Tc')  # noqa: E501
    assert signatures[63] == deserialize_tx_signature('Ars2bdNxYNVRDmWsGCwr9j8jHgRkb6gq7giaritpLw9yj6kiefwEUZpqz4Hr6SxRnJLTLtNnQaVNjuX6jjMAL7T')  # noqa: E501
