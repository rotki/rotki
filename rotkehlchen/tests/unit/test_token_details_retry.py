"""Tests for querying again the details of tokens that are missing them.

The seam: retry_missing_token_details picks the erc20 tokens whose name is their identifier
or NULL, asks the node inquirer of their chain for the details in chunks and, for the ones
whose query answered, saves what came back and gives a name to the ones without it, as long as
nobody else changed the token in the meantime. Their transactions are not redecoded.
"""
from contextlib import nullcontext
from typing import TYPE_CHECKING, Any, Final
from unittest.mock import MagicMock, patch

import pytest
from eth_abi import encode
from eth_utils import to_checksum_address

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.utils import edit_token_and_clean_cache, get_or_create_evm_token
from rotkehlchen.concurrency import wait
from rotkehlchen.constants import ONE
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError, TokenQueryFailed
from rotkehlchen.globaldb.cache import globaldb_get_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tasks.assets import (
    TOKEN_DETAILS_RETRY_MAX_FAILED_QUERIES,
    retry_missing_token_details,
)
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import (
    SPAM_PROTOCOL,
    CacheType,
    ChainID,
    Location,
    SupportedBlockchain,
    TimestampMS,
    TokenKind,
)

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
        decimals: int | None = None,
        symbol: str | None = None,
) -> EvmToken:
    """Create a token like the ones saved without querying its details"""
    token = get_or_create_evm_token(
        userdb=database,
        evm_address=_address(idx),
        chain_id=chain_id,
        token_kind=token_kind,  # type: ignore[arg-type]  # only evm kinds are used here
        protocol=protocol,
        decimals=decimals,
        symbol=symbol,
    )
    assert token.name == token.identifier
    return token


def _chains_aggregator(
        database: DBHandler,
        chains_with_accounts: tuple[SupportedBlockchain, ...] = (SupportedBlockchain.ETHEREUM,),
        infos: Any = None,
) -> tuple[MagicMock, MagicMock]:
    chains_aggregator, node_inquirer = MagicMock(), MagicMock()
    node_inquirer.get_multiple_erc20_contracts_info.side_effect = infos
    chains_aggregator.database = database
    chains_aggregator.accounts.get.side_effect = lambda chain: ['account'] if chain in chains_with_accounts else []  # noqa: E501
    chains_aggregator.get_evm_manager.return_value.node_inquirer = node_inquirer
    return chains_aggregator, node_inquirer


def _info(name: str, symbol: str = 'SYM', decimals: int = 6) -> dict[str, Any]:
    return {'name': name, 'symbol': symbol, 'decimals': decimals}


def _output(
        decimals: int | None = 6,
        symbol: str | None = 'TKN',
        name: str | None = 'Token',
) -> list[tuple[bool, bytes]]:
    """Multicall output of an erc20 contract. None is a failed call."""
    return [
        (False, b'') if value is None else (True, encode([abi_type], [value]))
        for abi_type, value in (('uint8', decimals), ('string', symbol), ('string', name))
    ]


FALLBACKS: Final[dict[str, Any]] = {'fallback_name': 'Fallback', 'fallback_symbol': 'FB', 'fallback_decimals': 18}  # noqa: E501


def _get_cursor(database: DBHandler, chain_id: ChainID = ChainID.ETHEREUM) -> str | None:
    with database.conn.read_ctx() as cursor:
        return database.get_dynamic_cache(
            cursor=cursor,
            name=DBCacheDynamic.TOKEN_DETAILS_RETRY_CURSOR,
            blockchain=chain_id.to_blockchain().serialize(),
        )


def _without_decimals() -> set[str]:
    """The tokens marked as having no decimals in their contract"""
    with GlobalDBHandler().conn.read_ctx() as cursor:
        return set(globaldb_get_general_cache_values(
            cursor=cursor,
            key_parts=(CacheType.TOKEN_WITHOUT_DECIMALS,),
        ))


def _details(token: EvmToken | ChecksumEvmAddress) -> tuple[str, str | None, int | None]:
    identifier = token.identifier if isinstance(token, EvmToken) else evm_address_to_identifier(
        address=token,
        chain_id=ChainID.ETHEREUM,
    )
    return (token := EvmToken(identifier)).name, token.symbol, token.decimals


@pytest.mark.parametrize(('multicall_kwargs', 'create_kwargs', 'error', 'details', 'marked'), [
    pytest.param({'side_effect': RemoteError('down')}, {}, TokenQueryFailed, None, False, id='unreachable'),  # noqa: E501
    pytest.param({'return_value': _output(name=None)}, FALLBACKS, None, ('Fallback', 'TKN', 6), False, id='partial'),  # fallbacks only fill what is missing  # noqa: E501
    pytest.param({'return_value': _output(decimals=None)}, FALLBACKS | {'symbol': 'GIV'}, None, ('Token', 'GIV', 18), True, id='partial-given'),  # noqa: E501
    pytest.param({'return_value': _output(decimals=None)}, {}, None, ('Token', 'TKN', 18), True, id='no-decimals'),  # noqa: E501
    pytest.param({'return_value': _output(decimals=None)}, {'decimals': 8}, None, ('Token', 'TKN', 8), False, id='decimals-given'),  # noqa: E501
    pytest.param({'return_value': [(False, b'')] * 3}, {}, NotERC20Conformant, None, False, id='no-methods'),  # noqa: E501
])
def test_token_creation_with_missing_details(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        multicall_kwargs: dict[str, Any],
        create_kwargs: dict[str, Any],
        error: type[Exception] | None,
        details: tuple[str, str, int] | None,
        marked: bool,
) -> None:
    """A failed query is told apart from a non conformant contract, and when the query
    succeeded the fallbacks only fill the details the chain did not return. A token created
    without decimals from the chain or the caller is marked as such."""
    with (
        patch.object(ethereum_inquirer, 'multicall_2', **multicall_kwargs),
        pytest.raises(error) if error is not None else nullcontext() as raised,
    ):
        get_or_create_evm_token(
            userdb=database,
            evm_address=(address := _address(1)),
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
            **create_kwargs,
        )

    assert raised is None or type(raised.value) is error  # a failed query is not non conformant
    if details is not None:
        assert _details(address) == details
    assert _without_decimals() == ({evm_address_to_identifier(address, ChainID.ETHEREUM)} if marked else set())  # noqa: E501


def test_which_tokens_are_retried(database: DBHandler) -> None:
    """Placeholders of normal erc20 tokens on chains with accounts are queried, also the ones
    with a NULL name that older versions saved. An answered query is final: the details found
    are saved, the missing ones keep their value, and a token without a name gets its symbol
    or `<chain_id>:<address>` as name. Spam tokens, nfts and tokens of chains without accounts
    are not queried."""
    found, not_found, partial, null_name = (_create_placeholder(database, i) for i in (1, 2, 3, 4))
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        write_cursor.execute('UPDATE assets SET name=NULL WHERE identifier=?', (null_name.identifier,))  # noqa: E501
    AssetResolver.clean_memory_cache(null_name.identifier)
    _create_placeholder(database, 5, protocol=SPAM_PROTOCOL)
    _create_placeholder(database, 6, token_kind=TokenKind.ERC721)
    other_chain = _create_placeholder(database, 7, ChainID.GNOSIS)
    queried: list[ChecksumEvmAddress] = []

    def infos(addresses: list[ChecksumEvmAddress]) -> dict[ChecksumEvmAddress, Any]:
        queried.extend(addresses)
        return {x.evm_address: _info('Found') for x in (found, null_name)} | {
            partial.evm_address: {'name': 'Partial', 'symbol': 'PRT'},
        }

    chains_aggregator, _ = _chains_aggregator(database=database, infos=infos)
    retry_missing_token_details(chains_aggregator)

    assert sorted(queried) == sorted(x.evm_address for x in (found, not_found, partial, null_name))
    assert _details(found) == _details(null_name) == ('Found', 'SYM', 6)
    assert _details(not_found) == (f'1:{not_found.evm_address}', '', 18)
    assert _details(partial) == ('Partial', 'PRT', 18)  # decimals() reverted, so they are kept
    assert _without_decimals() == {not_found.identifier, partial.identifier}
    assert _details(other_chain)[0] == other_chain.identifier
    assert _get_cursor(database) == ''  # reached the end
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.LAST_TOKEN_DETAILS_RETRY_TS,
        ) is not None


@pytest.mark.parametrize(('has_events', 'found_decimals', 'warns'), [
    (True, 6, True),
    (False, 6, False),
    (True, 18, False),
])
def test_warns_when_found_decimals_change(
        database: DBHandler,
        has_events: bool,
        found_decimals: int,
        warns: bool,
) -> None:
    """Events of a placeholder were calculated with its default decimals and its transactions
    are not redecoded, so the user is told to redecode them when the decimals change"""
    token = _create_placeholder(database, 1)
    if has_events:
        with database.user_write() as write_cursor:
            DBHistoryEvents(database).add_history_event(write_cursor, HistoryEvent(
                group_identifier='1',
                sequence_index=0,
                timestamp=TimestampMS(1),
                location=Location.EXTERNAL,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=token,
                amount=ONE,
            ))
    database.msg_aggregator.consume_warnings()
    chains_aggregator, _ = _chains_aggregator(
        database=database,
        infos=lambda _: {token.evm_address: _info('Found', decimals=found_decimals)},
    )
    retry_missing_token_details(chains_aggregator)

    assert _details(token) == ('Found', 'SYM', found_decimals)
    assert database.msg_aggregator.consume_warnings() == ([(
        f'The decimals of token SYM ({token.identifier}) were found to be 6 instead of 18. '
        'Redecode its transactions to fix the amounts of its existing events.'
    )] if warns else [])


@pytest.mark.parametrize('keep_name', [False, True])
def test_token_changed_while_querying_is_not_overwritten(
        database: DBHandler,
        keep_name: bool,
) -> None:
    """A user edit, asset update or decoder that changes the token while the details are
    queried wins, even if the name is still the placeholder one. The token is read again
    under the token lock before writing."""
    token = _create_placeholder(database, 1)

    def edit_while_querying(addresses: list[ChecksumEvmAddress]) -> dict[str, Any]:
        edit_token_and_clean_cache(
            token=EvmToken(token.identifier),
            name=token.identifier if keep_name else 'User Name',
            symbol='USR',
            decimals=8,
            started=None,
            chain_inquirer=None,
        )
        return {token.evm_address: _info('Queried')}

    chains_aggregator, _ = _chains_aggregator(database=database, infos=edit_while_querying)
    retry_missing_token_details(chains_aggregator)

    assert _details(token) == (token.identifier if keep_name else 'User Name', 'USR', 8)


@pytest.mark.parametrize(('output', 'details', 'marked'), [
    (_output(decimals=None), ('Token', 'TKN', 6), True),
    (_output(name=None, decimals=8), ('TKN', 'TKN', 8), False),
    (_output(decimals=None, symbol=None, name=None), (f'1:{_address(1)}', '', 6), True),
])
def test_repair_on_access_saves_what_came_back(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        output: list[tuple[bool, bytes]],
        details: tuple[str, str, int],
        marked: bool,
) -> None:
    """Accessing a placeholder with an inquirer queries it. A failed query changes nothing.
    An answered one is final: what came back is saved, the missing decimals keep their value
    and are never replaced by the default, and a missing name is replaced by the symbol or
    `<chain_id>:<address>`, so the token is no longer a placeholder."""
    token = _create_placeholder(database, 1, decimals=6)

    def access(multicall_kwargs: dict[str, Any]) -> tuple[str, str | None, int | None]:
        ethereum_inquirer.contract_info_erc20_cache.remove(token.evm_address)
        ethereum_inquirer.forget_token_query_failures(token.evm_address)
        with patch.object(ethereum_inquirer, 'multicall_2', **multicall_kwargs):
            get_or_create_evm_token(
                userdb=database,
                evm_address=token.evm_address,
                chain_id=ChainID.ETHEREUM,
                evm_inquirer=ethereum_inquirer,
            )
        return _details(token)

    assert access({'side_effect': RemoteError('down')}) == (token.identifier, '', 6)
    assert _without_decimals() == set()  # a failed query says nothing about the decimals
    assert access({'return_value': output}) == details
    assert _without_decimals() == ({token.identifier} if marked else set())


def test_placeholder_named_by_a_decoder_is_repaired(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """A decoder giving the name of a placeholder still gets the rest of its details queried,
    since once renamed it is no longer a placeholder and they would never be. While the query
    fails the name is not saved either, so it stays a placeholder that is queried again."""
    token = _create_placeholder(database, 1)
    assert token.decimals == 18

    def access(multicall_kwargs: dict[str, Any]) -> tuple[str, str | None, int | None]:
        ethereum_inquirer.contract_info_erc20_cache.remove(token.evm_address)
        ethereum_inquirer.forget_token_query_failures(token.evm_address)
        with patch.object(ethereum_inquirer, 'multicall_2', **multicall_kwargs):
            get_or_create_evm_token(
                userdb=database,
                evm_address=token.evm_address,
                chain_id=ChainID.ETHEREUM,
                evm_inquirer=ethereum_inquirer,
                name='Decoder Name',
                protocol='some-protocol',
            )
        return _details(token)

    assert access({'side_effect': RemoteError('down')}) == (token.identifier, '', 18)
    assert EvmToken(token.identifier).protocol == 'some-protocol'  # the rest is still saved
    with GlobalDBHandler().conn.read_ctx() as cursor:  # it is still selected to be queried
        assert cursor.execute(
            'SELECT COUNT(*) FROM assets WHERE identifier=? AND name=identifier',
            (token.identifier,),
        ).fetchone()[0] == 1

    assert access({'return_value': _output(decimals=6)}) == ('Decoder Name', 'TKN', 6)


@pytest.mark.parametrize(('error', 'raises'), [
    (RemoteError('nodes down'), None),
    (ValueError('unexpected'), ValueError),
])
def test_progress_is_saved_when_the_query_fails(
        database: DBHandler,
        error: Exception,
        raises: type[Exception] | None,
) -> None:
    """When the nodes are down, or the query fails unexpectedly, the placeholders are left as
    they are, but the cursor moves past them and the last run is saved before querying, so a
    chunk that always fails can't block the tokens after it nor repeat forever."""
    tokens = [_create_placeholder(database, i) for i in (1, 2, 3)]
    chains_aggregator, _ = _chains_aggregator(database=database, infos=error)

    with (
        patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_BATCH_SIZE', 3),
        pytest.raises(raises) if raises is not None else nullcontext(),
    ):
        retry_missing_token_details(chains_aggregator)

    assert all(EvmToken(x.identifier).name == x.identifier for x in tokens)
    assert _get_cursor(database) == max(x.identifier for x in tokens)
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.LAST_TOKEN_DETAILS_RETRY_TS,
        ) is not None


def test_cursor_advances_and_wraps(database: DBHandler) -> None:
    tokens = sorted((_create_placeholder(database, i) for i in (1, 2, 3)), key=lambda x: x.identifier)  # noqa: E501
    queried: list[list[ChecksumEvmAddress]] = []

    def infos(addresses: list[ChecksumEvmAddress]) -> dict[str, Any]:
        queried.append(addresses)
        return {}

    chains_aggregator, _ = _chains_aggregator(database=database, infos=infos)
    with (  # nothing is saved, so the tokens stay placeholders as if they always failed
        patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_BATCH_SIZE', 2),
        patch('rotkehlchen.tasks.assets._save_found_token_details'),
    ):
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


def test_cursor_wraps_after_an_exactly_full_batch(database: DBHandler) -> None:
    """When the last batch of a chain is exactly full, the next run finds nothing after the
    cursor and wraps it, so the tokens are queried again in the run after it"""
    tokens = sorted((_create_placeholder(database, i) for i in (1, 2)), key=lambda x: x.identifier)
    chains_aggregator, node_inquirer = _chains_aggregator(database=database, infos=lambda _: {})
    with (  # nothing is saved, so the tokens stay placeholders as if they always failed
        patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_BATCH_SIZE', 2),
        patch('rotkehlchen.tasks.assets._save_found_token_details'),
    ):
        retry_missing_token_details(chains_aggregator)
        assert _get_cursor(database) == tokens[1].identifier
        retry_missing_token_details(chains_aggregator)
        assert _get_cursor(database) == ''
        retry_missing_token_details(chains_aggregator)

    assert [x.args[0] for x in node_inquirer.get_multiple_erc20_contracts_info.call_args_list] == [
        [x.evm_address for x in tokens],
        [x.evm_address for x in tokens],
    ]


def test_token_failing_its_chunk_does_not_block_the_rest(database: DBHandler) -> None:
    """A token that makes the query of its whole chunk fail while the nodes work is isolated:
    the chunk is queried one token at a time and the rest of it is still found"""
    poison, *others = (tokens := [_create_placeholder(database, i) for i in (1, 2, 3)])

    def infos(queried: list[ChecksumEvmAddress]) -> dict[str, Any]:
        if poison.evm_address in queried:
            raise RemoteError('out of gas')
        return {address: _info('Found') for address in queried}

    chains_aggregator, node_inquirer = _chains_aggregator(database=database, infos=infos)
    retry_missing_token_details(chains_aggregator)

    assert _details(poison)[0] == poison.identifier
    for token in others:
        assert _details(token) == ('Found', 'SYM', 6)

    assert [x.args[0] for x in node_inquirer.get_multiple_erc20_contracts_info.call_args_list] == [
        [x.evm_address for x in tokens],
        *([x.evm_address] for x in tokens),
    ]


def test_tokens_not_queried_are_first_in_the_next_run(database: DBHandler) -> None:
    """When querying stops early because single queries fail in a row, the cursor only moves
    past the tokens that were queried, so the ones after them are queried in the next run
    instead of starting again with the same failing tokens"""
    *broken, healthy = [_create_placeholder(database, i) for i in (1, 2, 3, 4)]

    def infos(queried: list[ChecksumEvmAddress]) -> dict[str, Any]:
        if any(x.evm_address in queried for x in broken):
            raise RemoteError('out of gas')
        return {address: _info('Found') for address in queried}

    chains_aggregator, node_inquirer = _chains_aggregator(database=database, infos=infos)
    retry_missing_token_details(chains_aggregator)
    assert _details(healthy)[0] == healthy.identifier  # not queried, the run stopped before it
    assert _get_cursor(database) == broken[-1].identifier

    retry_missing_token_details(chains_aggregator)
    assert _details(healthy) == ('Found', 'SYM', 6)
    assert _get_cursor(database) == ''  # it reached the end, so it wraps
    assert [x.args[0] for x in node_inquirer.get_multiple_erc20_contracts_info.call_args_list] == [
        [x.evm_address for x in (*broken, healthy)],
        *([x.evm_address] for x in broken),
        [healthy.evm_address],
    ]


def test_failing_chain_does_not_hold_back_the_others(database: DBHandler) -> None:
    """Each chain goes through its own tokens with its own cursor, so a chain whose nodes fail
    and that has more placeholders than a batch does not keep the tokens of the chains sorted
    after it from being queried while its cursor only moves past the few it queried."""
    failing = [_create_placeholder(database, i).evm_address for i in range(1, 7)]
    other_chain = _create_placeholder(database, 7, ChainID.GNOSIS)
    assert all(evm_address_to_identifier(x, ChainID.ETHEREUM) < other_chain.identifier for x in failing)  # noqa: E501

    def infos(queried: list[ChecksumEvmAddress]) -> dict[str, Any]:
        if any(x in failing for x in queried):
            raise RemoteError('down')
        return {address: _info('Found') for address in queried}

    chains_aggregator, _ = _chains_aggregator(
        database=database,
        chains_with_accounts=(SupportedBlockchain.ETHEREUM, SupportedBlockchain.GNOSIS),
        infos=infos,
    )
    with patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_BATCH_SIZE', 5):
        retry_missing_token_details(chains_aggregator)

    assert _details(other_chain) == ('Found', 'SYM', 6)
    assert _get_cursor(database) == evm_address_to_identifier(failing[2], ChainID.ETHEREUM)
    assert _get_cursor(database, ChainID.GNOSIS) == ''


def test_querying_stops_when_the_nodes_are_down(database: DBHandler) -> None:
    """When TOKEN_DETAILS_RETRY_MAX_FAILED_QUERIES single token queries fail in a row, even
    across chunks, the nodes are considered down and the rest of the chain is not queried"""
    addresses = [_create_placeholder(database, i).evm_address for i in range(1, 7)]

    def infos(queried: list[ChecksumEvmAddress]) -> dict[str, Any]:
        if queried == addresses[:2]:
            return {}  # the nodes answered, but these tokens have no details
        raise RemoteError('down')

    chains_aggregator, node_inquirer = _chains_aggregator(database=database, infos=infos)
    with patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_CHUNK_SIZE', 2):
        retry_missing_token_details(chains_aggregator)

    # only the tokens whose query answered are done, not the ones of the outage
    assert [_details(x)[0] for x in addresses] == [
        *(f'1:{x}' for x in addresses[:2]),
        *(evm_address_to_identifier(x, ChainID.ETHEREUM) for x in addresses[2:]),
    ]
    assert TOKEN_DETAILS_RETRY_MAX_FAILED_QUERIES == 3
    assert [x.args[0] for x in node_inquirer.get_multiple_erc20_contracts_info.call_args_list] == [
        addresses[:2],
        addresses[2:4], [addresses[2]], [addresses[3]],
        addresses[4:], [addresses[4]],  # third failure in a row
    ]


@pytest.mark.parametrize(('found', 'saved_symbol', 'details', 'marked'), [
    ({'name': 'Token', 'symbol': 'TKN'}, None, ('Token', 'TKN', 6), True),  # decimals() failed
    ({'symbol': 'TKN', 'decimals': 8}, None, ('TKN', 'TKN', 8), False),  # name() failed
    ({'decimals': 8}, None, (f'1:{_address(1)}', '', 8), False),  # name() and symbol() failed
    ({'decimals': 8}, 'SAV', ('SAV', 'SAV', 8), False),  # the saved symbol is kept and used as name  # noqa: E501
])
def test_answered_query_is_final(
        database: DBHandler,
        found: dict[str, Any],
        saved_symbol: str | None,
        details: tuple[str, str, int],
        marked: bool,
) -> None:
    """The details found are saved and the missing decimals and symbol keep their value, never
    the default. A missing name is replaced by the symbol or `<chain_id>:<address>`, so the
    token is no longer a placeholder and is not queried again."""
    token = _create_placeholder(database, 1, decimals=6, symbol=saved_symbol)
    chains_aggregator, node_inquirer = _chains_aggregator(
        database=database,
        infos=lambda _: {token.evm_address: found},
    )
    retry_missing_token_details(chains_aggregator)
    assert _details(token) == details
    assert _without_decimals() == ({token.identifier} if marked else set())

    retry_missing_token_details(chains_aggregator)
    assert node_inquirer.get_multiple_erc20_contracts_info.call_count == 1


def test_get_multiple_erc20_contracts_info(ethereum_inquirer: EthereumInquirer) -> None:
    """Each property is decoded on its own: the result has the ones that were returned and
    could be decoded, and a token with none is not in it"""
    good, broken, partial, undecodable = (_address(i) for i in (1, 2, 3, 4))
    output = _output() + [(False, b'')] * 3 + _output(decimals=None) + [
        (True, encode(['uint8'], [6])),
        (True, b'\xff' * 32),  # a bytes32 symbol and name that are not utf-8
        (True, b'\xff' * 32),
    ]
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=output) as multicall:
        result = ethereum_inquirer.get_multiple_erc20_contracts_info([good, broken, partial, undecodable])  # noqa: E501

    assert result == {
        good: {'decimals': 6, 'symbol': 'TKN', 'name': 'Token'},
        partial: {'symbol': 'TKN', 'name': 'Token'},
        undecodable: {'decimals': 6},
    }
    assert multicall.call_args.kwargs['calls'] == [  # decimals(), symbol(), name() of each
        (address, selector)
        for address in (good, broken, partial, undecodable)
        for selector in ('0x313ce567', '0x95d89b41', '0x06fdde03')
    ]
    assert multicall.call_args.kwargs['require_success'] is False


@pytest.mark.parametrize('max_tasks_num', [5])
@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address()]])
def test_task_scheduling(task_manager: TaskManager, database: DBHandler) -> None:
    """Not scheduled while history is fetched. Otherwise it runs with the real chains
    aggregator and is not due again until the period passes."""
    token = _create_placeholder(database, 1)
    ethereum_inquirer = task_manager.chains_aggregator.get_evm_manager(ChainID.ETHEREUM).node_inquirer  # noqa: E501
    with task_manager.history_processing_coordinator.history_fetch():
        assert task_manager._maybe_retry_missing_token_details() is None

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
