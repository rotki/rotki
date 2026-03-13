from collections.abc import Callable
from contextlib import suppress
from functools import partial
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest
from httpx import HTTPStatusError, Response
from solana.exceptions import SolanaRpcException
from solana.rpc.api import Client

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import get_or_create_solana_token, get_solana_token
from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.chain.mixins.rpc_nodes import RPCNode
from rotkehlchen.chain.solana.utils import MetadataInfo, MintInfo, is_solana_token_nft
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.serialization.deserialize import deserialize_tx_signature
from rotkehlchen.tests.utils.makerdao import FVal
from rotkehlchen.types import SolanaAddress, SupportedBlockchain, Timestamp, TokenKind
from rotkehlchen.utils.misc import ts_now

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
    SolanaAddress('FkzRQKW8Mzip4xXHamibLZB28sjqN9ZLFacQdbuVEYxa'),
]])
def test_solana_balances(
        solana_manager: 'SolanaManager',
        solana_accounts: list['SolanaAddress'],
) -> None:
    assert solana_manager.get_multi_balance(accounts=solana_accounts) == {
        solana_accounts[0]: FVal('3.063908962'),
        solana_accounts[1]: FVal('0.564503502'),
    }


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['7pFGok3zuvacRP797Ke3bUZqbq24PbVQNLvwopfErvih']])
def test_solana_token_balances(
        solana_manager: 'SolanaManager',
        solana_accounts: list['SolanaAddress'],
) -> None:
    """Test that the solana token balances are returned correctly.
    The address tested currently holds 3 tokens and 11 NFTs according to solscan.

    1 token (JUPDROP) appears to be a scam token, with a token_standard of 2 (normal token) but
    with zero decimals and is classified as an NFT on solscan. We simply stick to the
    token_standard for this and class it as a normal token.

    1 token (catwifhat) is from the new Token 2022 Program, and the others are from the original
    Token Program.
    """
    balances = solana_manager.get_token_balances(account=solana_accounts[0])
    assert len(balances) == 14
    assert len([x for x in balances if '/token:' in x.identifier]) == 4
    assert len([x for x in balances if '/nft:' in x.identifier]) == 10
    # Check several token and nft balances
    assert balances[Asset('solana/token:Hv69wUkD225TYq111eAar9CtjhNpzBTRFpHkpY3pbonk')] == FVal('233884.967632')  # noqa: E501
    assert balances[Asset('solana/token:7KUZ5CoUZfcxYbjLzXT6sgAqo3CZbHxMvzwKGcUtpump')] == FVal('55689.635733')  # noqa: E501
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
        ('https://bafkreib5jykd5ehlvmi7f253jdjzzknj6eqlnqhzenfmdc6okrwksqfu6a.ipfs.dweb.link/', False),  # catwifhat token  # noqa: E501
    ):
        assert is_solana_token_nft(
            token_address=SolanaAddress('Cg4noWpzmDHhPZZXDwmCLJns43PJpLmd6E8aYL1pRcRJ'),
            mint_info=MintInfo(supply=100, decimals=0, tlv_data=None),
            metadata=MetadataInfo(name='Some Token', symbol='ST', uri=uri, token_standard=None),
        ) == is_nft


@pytest.mark.vcr
def test_query_tx_from_rpc(solana_inquirer: 'SolanaInquirer') -> None:
    tx, token_account_mapping = solana_inquirer.get_transaction_for_signature(
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
    assert token_account_mapping == {
        'F54yhxDkhsprqQoRV5L1dCQKKFSY1WBzFQ6YaVRuW42T': (
            '9rJ4QzDLYm5VARnuWcMFMzB4Nr1hKprGQWb8LTfsU6Q2',
            'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
        ),
        '7ixaquirw9k3VNkxJ5zpbx9GTAbAvUrrNeZovw7TBqyu': (
            '81MPQqJY58rgT83sy99MkRHs2g3dyy6uWKHD24twV62F',
            'So11111111111111111111111111111111111111112',
        ),
        '2JwKVhEeJZn8bHsHVK1rFuATHni3wDft3UFAsrKKMKfP': (
            '81MPQqJY58rgT83sy99MkRHs2g3dyy6uWKHD24twV62F',
            'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
        ),
        '9yfN3qv6tKxhniWcrQi7bP1kZgXmdd4dLm84rostKvQG': (
            '6p6RCUtoXDvrwqx9AJmyM3wCFd9nDvMaLs3Fwif6QeXH',
            'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
        ),
        '9PzW3acuWjfCb74AKRK7BsZq9tjBxvwqPoTLSeXonGLu': (
            'EEne7rPNgqPXLEK3Hv74KwkxJKPgaMHUd39LNx9yXbiK',
            'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
        ),
    }


@pytest.mark.vcr
def test_query_signatures_for_address(solana_inquirer: 'SolanaInquirer') -> None:
    signatures = solana_inquirer.query_tx_signatures_for_address(
        address=SolanaAddress('7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY'),
    )
    assert len(signatures) == 312
    assert signatures[0] == deserialize_tx_signature('5gJFZweW8EsTQCNWH2EyjJA3vm2VcT91vQtrNAcx7YXeq4zHmqXzSqxxnhb9GxiLvecWJJZv8xxW6opHSnJME643')  # noqa: E501
    assert signatures[63] == deserialize_tx_signature('63u9VxkLKDSBs2nH7Knv4MwX7dU9BKx8WEMGXquWkzVkCm9McGrDcbhhfw8TRm7LgRzXDvutdX74pNMRmo7L2TbL')  # noqa: E501


@pytest.mark.parametrize('solana_accounts', [[SolanaAddress('7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY')]])  # noqa: E501
@pytest.mark.parametrize('solana_nodes_connect_at_start', [(
    WeightedNode(node_info=NodeName(name='therpc', endpoint='https://solana-rpc.publicnode.com/', blockchain=SupportedBlockchain.SOLANA, owned=False), weight=ONE, active=True),  # noqa: E501
    WeightedNode(node_info=NodeName(name='solana.com', endpoint='https://api.mainnet-beta.solana.com', blockchain=SupportedBlockchain.SOLANA, owned=False), weight=ONE, active=True),  # noqa: E501
)])
def test_only_archive_nodes(
        solana_manager: 'SolanaManager',
        solana_accounts: list[SolanaAddress],
) -> None:
    """Test that non-archive nodes are skipped when making a request for historical data.
    solana_nodes_connect_at_start sets the call order to be first a non-archive node and then an
    archive node, so it always tries the non-archive node first unless explicitly skipped.
    """
    client_to_endpoint: dict[int, str] = {}
    original_query = solana_manager.node_inquirer.query

    def mock_client_creation(endpoint: str, timeout: int) -> Client:
        client = MagicMock(spec=Client)
        client.is_connected.return_value = True
        client.get_signatures_for_address.return_value = SimpleNamespace(value=[SimpleNamespace(
            signature=deserialize_tx_signature('5gJFZweW8EsTQCNWH2EyjJA3vm2VcT91vQtrNAcx7YXeq4zHmqXzSqxxnhb9GxiLvecWJJZv8xxW6opHSnJME643'),
        )])
        client.get_multiple_accounts.return_value = SimpleNamespace(
            value=[SimpleNamespace(lamports=1_000_000_000)],
        )
        client_to_endpoint[id(client)] = endpoint
        return client

    def check_client(client: Client, method: Callable, expected_endpoint: str) -> Any:
        assert client_to_endpoint[id(client)] == expected_endpoint
        return method(client)

    for query_func, expected_endpoint, expected_result_len in ((
        lambda: solana_manager.node_inquirer.query_tx_signatures_for_address(address=solana_accounts[0]),  # noqa: E501
        'https://api.mainnet-beta.solana.com',  # archive node
        1,
    ), (
        lambda: solana_manager.get_multi_balance(accounts=solana_accounts),
        'https://solana-rpc.publicnode.com/',  # non-archive node
        1,
    )):
        with (
            patch('rotkehlchen.chain.mixins.rpc_nodes.Client', side_effect=mock_client_creation),
            patch(
                'rotkehlchen.chain.mixins.rpc_nodes.SolanaRPCMixin._is_archive',
                side_effect=lambda client: client_to_endpoint[id(client)] == 'https://api.mainnet-beta.solana.com',
            ),
            patch.object(
                target=solana_manager.node_inquirer,
                attribute='query',
                side_effect=lambda method, call_order=None, only_archive_nodes=False, endpoint=expected_endpoint: original_query(  # noqa: E501
                    method=partial(check_client, method=method, expected_endpoint=endpoint),
                    call_order=call_order,
                    only_archive_nodes=only_archive_nodes,
                ),
            ) as query_mock,
        ):
            assert len(query_func()) == expected_result_len
            assert query_mock.call_count == 1


def test_rate_limit_handling(
        solana_inquirer: 'SolanaInquirer',
) -> None:
    """Test that rate limits are properly handled so that other non-rate limited nodes are used
    instead of blocking until the rate limit backoff time is over.

    1. First query: node1 returns 429, falls back to node2 which succeeds
    2. Second query (within backoff): skips node1, uses node2 directly
    3. Third query (after backoff expires): tries node1 again

    Mocks the nodes and rpc clients to avoid actual network calls and for easier tracking of
    which node is queried.
    """
    call_order = [WeightedNode(
        node_info=(node1_info := NodeName(name='node1', endpoint='https://node1.example.com', blockchain=SupportedBlockchain.SOLANA, owned=False)),  # noqa: E501
        weight=ONE,
        active=True,
    ), WeightedNode(
        node_info=(node2_info := NodeName(name='node2', endpoint='https://node2.example.com', blockchain=SupportedBlockchain.SOLANA, owned=False)),  # noqa: E501
        weight=ONE,
        active=True,
    )]
    mock_client1 = MagicMock(spec=Client)
    mock_client1.name = 'node1'  # For tracking which client is called
    mock_client2 = MagicMock(spec=Client)
    mock_client2.name = 'node2'
    solana_inquirer.rpc_mapping = {
        node1_info: RPCNode(rpc_client=mock_client1, is_pruned=False, is_archive=False),
        node2_info: RPCNode(rpc_client=mock_client2, is_pruned=False, is_archive=False),
    }
    call_log, do_rate_limit = [], True

    def mock_method(client: Client) -> None:
        """Mock RPC method that rate limits node1 when flag is set."""
        client_name = client.name  # type: ignore[attr-defined]  # name was added via MagicMock
        call_log.append(client_name)

        if client_name == 'node1' and do_rate_limit:
            raise SolanaRpcException(MagicMock(), MagicMock(), '', client) from HTTPStatusError(
                message='Rate Limit',
                request=MagicMock(),
                response=Response(status_code=429, headers={'retry-after': '5'}),
            )

    # Query 1: node1 rate limits, falls back to node2
    solana_inquirer.query(method=mock_method, call_order=call_order)
    assert call_log == ['node1', 'node2']  # node1 rate limited, fell back to node2
    assert 'node1' in solana_inquirer.node_backoff_info
    assert 'node2' not in solana_inquirer.node_backoff_info
    backoff_end_ts, attempts, _ = solana_inquirer.node_backoff_info['node1']
    assert attempts == 1
    assert backoff_end_ts is not None
    assert backoff_end_ts > ts_now()

    # Query 2: skips node1 even though do_rate_limit is false since the backoff time is not up yet
    do_rate_limit = False
    call_log.clear()
    solana_inquirer.query(method=mock_method, call_order=call_order)
    assert call_log == ['node2']

    # Query 3: simulate backoff expiry by setting the end ts to now
    solana_inquirer.node_backoff_info['node1'] = (ts_now(), 1, 0)
    call_log.clear()
    solana_inquirer.query(method=mock_method, call_order=call_order)
    assert call_log == ['node1']

    # Query 4: require archive nodes (neither of the current nodes are marked as archive) to make
    # sure we don't loop forever if the query fails for non-rate-limit reasons.
    with pytest.raises(RemoteError):
        solana_inquirer.query(method=mock_method, call_order=call_order, only_archive_nodes=True)
