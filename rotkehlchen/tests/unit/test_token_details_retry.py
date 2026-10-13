"""Tests for the task that retries querying the details of tokens saved without them.

The seam: retry_missing_token_details picks tokens whose name is their identifier, asks the
node inquirer of their chain for the details in chunks and only edits the tokens for which a
name was found. Its cursor decides where the next run continues.
"""
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest
from eth_abi import encode
from eth_utils import to_checksum_address

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.constants import ERC20_PROPERTIES, ERC20_PROPERTIES_CALLDATA
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.concurrency import wait
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.tasks.assets import retry_missing_token_details
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import SPAM_PROTOCOL, ChainID, SupportedBlockchain, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.tasks.manager import TaskManager
    from rotkehlchen.types import ChecksumEvmAddress


def _address(idx: int) -> ChecksumEvmAddress:
    return to_checksum_address(f'0x{idx:040x}')


def _create_placeholder(
        database: DBHandler,
        idx: int,
        chain_id: ChainID = ChainID.ETHEREUM,
        token_kind: TokenKind = TokenKind.ERC20,
        protocol: str | None = None,
) -> EvmToken:
    """Create a token like the ones saved when its details could not be queried"""
    token = get_or_create_evm_token(
        userdb=database,
        evm_address=_address(idx),
        chain_id=chain_id,
        token_kind=token_kind,  # type: ignore[arg-type]  # only evm kinds are used here
        protocol=protocol,
    )
    assert token.name == token.identifier
    return token


def _chains_aggregator(
        database: DBHandler,
        chains_with_accounts: tuple[SupportedBlockchain, ...] = (SupportedBlockchain.ETHEREUM,),
        infos: Any = None,
) -> tuple[MagicMock, MagicMock]:
    chains_aggregator, node_inquirer = MagicMock(), MagicMock()
    chains_aggregator.database = database
    chains_aggregator.accounts.get.side_effect = lambda chain: ['account'] if chain in chains_with_accounts else []  # noqa: E501
    chains_aggregator.get_evm_manager.return_value.node_inquirer = node_inquirer
    node_inquirer.get_multiple_erc20_contracts_info.side_effect = infos
    return chains_aggregator, node_inquirer


def _info(name: str | None, symbol: str = 'SYM', decimals: int = 6) -> dict[str, Any]:
    return {'name': name, 'symbol': symbol, 'decimals': decimals}


def _get_cursor(database: DBHandler) -> str | None:
    with database.conn.read_ctx() as cursor:
        return database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.TOKEN_DETAILS_RETRY_CURSOR,
        )


def test_details_are_updated_only_when_found(database: DBHandler) -> None:
    updated, unconformant, nameless = (_create_placeholder(database, i) for i in (1, 2, 3))
    chains_aggregator, node_inquirer = _chains_aggregator(
        database=database,
        infos=lambda addresses: {
            updated.evm_address: _info('Updated Token'),
            nameless.evm_address: _info(None),  # still without a name. unconformant is missing
        },
    )

    retry_missing_token_details(chains_aggregator)

    node_inquirer.get_multiple_erc20_contracts_info.assert_called_once()
    assert (token := EvmToken(updated.identifier)).name == 'Updated Token'
    assert (token.symbol, token.decimals) == ('SYM', 6)
    for untouched in (unconformant, nameless):
        assert EvmToken(untouched.identifier).name == untouched.identifier
        assert EvmToken(untouched.identifier).decimals == 18
    assert _get_cursor(database) == ''  # reached the end
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.LAST_TOKEN_DETAILS_RETRY_TS,
        ) is not None


def test_remote_error_is_retried_in_the_next_cycle(database: DBHandler) -> None:
    tokens = [_create_placeholder(database, i) for i in (1, 2, 3)]
    chains_aggregator, _ = _chains_aggregator(database=database, infos=RemoteError('nodes down'))

    with patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_BATCH_SIZE', 3):
        retry_missing_token_details(chains_aggregator)

    assert all(EvmToken(x.identifier).name == x.identifier for x in tokens)
    # the failure does not hold the cursor. Otherwise a chunk that always fails would block
    # all the tokens after it
    assert _get_cursor(database) == max(x.identifier for x in tokens)
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(  # and the task is not rescheduled every tick
            cursor=cursor,
            name=DBCacheStatic.LAST_TOKEN_DETAILS_RETRY_TS,
        ) is not None


def test_cursor_advances_and_wraps(database: DBHandler) -> None:
    tokens = sorted((_create_placeholder(database, i) for i in (1, 2, 3)), key=lambda x: x.identifier)  # noqa: E501
    queried: list[list[ChecksumEvmAddress]] = []

    def infos(addresses: list[ChecksumEvmAddress]) -> dict[str, Any]:
        queried.append(addresses)
        return {}  # nothing can be updated, as if the tokens were permanently broken

    chains_aggregator, _ = _chains_aggregator(database=database, infos=infos)
    with patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_BATCH_SIZE', 2):
        retry_missing_token_details(chains_aggregator)
        assert _get_cursor(database) == tokens[1].identifier
        retry_missing_token_details(chains_aggregator)
        assert _get_cursor(database) == ''  # only the last token was left, so it wrapped
        retry_missing_token_details(chains_aggregator)
        assert _get_cursor(database) == tokens[1].identifier

    # broken tokens did not block the ones after them
    assert queried == [
        [tokens[0].evm_address, tokens[1].evm_address],
        [tokens[2].evm_address],
        [tokens[0].evm_address, tokens[1].evm_address],
    ]


def test_failed_chunk_does_not_block_following_tokens(database: DBHandler) -> None:
    tokens = sorted((_create_placeholder(database, i) for i in (1, 2, 3, 4, 5)), key=lambda x: x.identifier)  # noqa: E501
    calls = []

    def infos(addresses: list[ChecksumEvmAddress]) -> dict[str, Any]:
        calls.append(addresses)
        if len(calls) == 2:
            raise RemoteError('nodes down')
        return {address: _info('Found') for address in addresses}

    chains_aggregator, _ = _chains_aggregator(database=database, infos=infos)
    with (
        patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_BATCH_SIZE', 4),
        patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_CHUNK_SIZE', 2),
    ):
        retry_missing_token_details(chains_aggregator)
        # the nodes were considered unavailable so the rest of the batch was left out
        assert [EvmToken(x.identifier).name for x in tokens] == [
            'Found', 'Found', tokens[2].identifier, tokens[3].identifier, tokens[4].identifier,
        ]
        assert _get_cursor(database) == tokens[3].identifier

        retry_missing_token_details(chains_aggregator)  # continues after the skipped tokens

    assert calls[-1] == [tokens[4].evm_address]
    assert EvmToken(tokens[4].identifier).name == 'Found'
    assert _get_cursor(database) == ''  # wrapped. The skipped ones come back in the next cycle


def test_only_normal_erc20_tokens_of_chains_with_accounts_are_queried(database: DBHandler) -> None:
    normal = _create_placeholder(database, 1)
    _create_placeholder(database, 2, protocol=SPAM_PROTOCOL)
    _create_placeholder(database, 3, token_kind=TokenKind.ERC721)
    other_chain = _create_placeholder(database, 4, ChainID.GNOSIS)
    queried: list[list[ChecksumEvmAddress]] = []

    def infos(addresses: list[ChecksumEvmAddress]) -> dict[str, Any]:
        queried.append(addresses)
        return {}

    chains_aggregator, _ = _chains_aggregator(database=database, infos=infos)

    retry_missing_token_details(chains_aggregator)

    assert queried == [[normal.evm_address]]
    assert EvmToken(other_chain.identifier).name == other_chain.identifier


def test_get_multiple_erc20_contracts_info(ethereum_inquirer: EthereumInquirer) -> None:
    """Failed calls make the token non conformant instead of failing the whole query"""
    good, broken = _address(1), _address(2)
    output = [
        (True, encode(['uint8'], [6])),
        (True, encode(['string'], ['TKN'])),
        (True, encode(['string'], ['Token'])),
        (False, b''),  # the contract has none of the methods
        (False, b''),
        (False, b''),
    ]
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=output) as multicall:
        result = ethereum_inquirer.get_multiple_erc20_contracts_info([good, broken])

    assert result[good] == {'decimals': 6, 'symbol': 'TKN', 'name': 'Token'}
    assert result[broken] == {'decimals': 18, 'symbol': None, 'name': None}
    assert len(multicall.call_args.kwargs['calls']) == 6
    assert multicall.call_args.kwargs['require_success'] is False


def test_erc20_properties_calldata(ethereum_inquirer: EthereumInquirer) -> None:
    contract = EvmContract(
        address=_address(1),
        abi=ethereum_inquirer.contracts.erc20_abi,
        deployed_block=0,
    )
    assert tuple(contract.encode(x) for x in ERC20_PROPERTIES) == ERC20_PROPERTIES_CALLDATA


def test_undecodable_token_does_not_discard_its_chunk(ethereum_inquirer: EthereumInquirer) -> None:
    """A bytes32 name that is not utf-8 only leaves out its own token"""
    good, undecodable = _address(1), _address(2)
    output = [
        (True, encode(['uint8'], [6])),
        (True, encode(['string'], ['TKN'])),
        (True, encode(['string'], ['Token'])),
        (True, encode(['uint8'], [6])),
        (True, b'\xff' * 32),
        (True, b'\xff' * 32),
    ]
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=output):
        result = ethereum_inquirer.get_multiple_erc20_contracts_info([good, undecodable])

    assert result == {good: {'decimals': 6, 'symbol': 'TKN', 'name': 'Token'}}


def test_unexpected_error_still_saves_progress(database: DBHandler) -> None:
    """The cursor and last run are saved before querying so a failure can't repeat forever"""
    token = _create_placeholder(database, 1)
    chains_aggregator, _ = _chains_aggregator(database=database, infos=ValueError('unexpected'))

    with patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_BATCH_SIZE', 1), pytest.raises(ValueError):  # noqa: E501
        retry_missing_token_details(chains_aggregator)

    assert _get_cursor(database) == token.identifier
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.LAST_TOKEN_DETAILS_RETRY_TS,
        ) is not None


@pytest.mark.parametrize('max_tasks_num', [5])
@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address()]])
def test_task_is_scheduled_with_real_chains_aggregator(
        task_manager: TaskManager,
        database: DBHandler,
) -> None:
    token = _create_placeholder(database, 1)
    ethereum_inquirer = task_manager.chains_aggregator.get_evm_manager(ChainID.ETHEREUM).node_inquirer  # noqa: E501
    task_manager.potential_tasks = [task_manager._maybe_retry_missing_token_details]
    with patch.object(
        ethereum_inquirer,
        'get_multiple_erc20_contracts_info',
        return_value={token.evm_address: _info('Scheduled Token')},
    ):
        task_manager.schedule()
        wait(task_manager.running_tasks[task_manager._maybe_retry_missing_token_details])

    assert EvmToken(token.identifier).name == 'Scheduled Token'
    assert task_manager._maybe_retry_missing_token_details() is None  # just ran, not due again
