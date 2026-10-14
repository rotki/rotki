"""Tests for querying again the details of tokens that are missing them.

The seam: when the details of an erc20 token can't be fully queried while it is first seen,
_get_or_create_token marks it in the global DB cache. retry_missing_token_details picks the
marked tokens and the ones whose name is their identifier, asks the node inquirer of their chain
for the details in chunks and fills the details that were missing and came back, as long as
nobody else changed them in the meantime.
The transactions of tokens that got their details or were created that way are flagged for
redecoding, and the periodic decoding task redecodes them.
"""
import time
from contextlib import contextmanager, nullcontext
from typing import TYPE_CHECKING, Any, Final
from unittest.mock import MagicMock, patch

import pytest
from eth_abi import encode
from eth_utils import to_checksum_address

from rotkehlchen.assets import details_retry
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.details_retry import (
    TOKEN_DETAILS_RETRY_MAX_ATTEMPTS,
    TokenDetailsRetryMark,
    count_token_details_retry_attempt,
    get_token_details_retry_marks,
    is_token_details_retry_given_up,
    mark_token_details_retry,
    stop_token_details_retry,
)
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.utils import (
    edit_token_and_clean_cache,
    get_or_create_evm_token,
)
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.concurrency import exception_of, spawn, wait
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError, TokenQueryFailed
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tasks.assets import (
    TOKEN_DETAILS_RETRY_MAX_FAILED_QUERIES,
    retry_missing_token_details,
)
from rotkehlchen.tests.utils.ethereum import txreceipt_to_data
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import (
    SPAM_PROTOCOL,
    ChainID,
    EvmTransaction,
    SupportedBlockchain,
    Timestamp,
    TokenKind,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.concurrency import Task
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
) -> EvmToken:
    """Create a token like the ones saved without querying its details"""
    token = get_or_create_evm_token(
        userdb=database,
        evm_address=_address(idx),
        chain_id=chain_id,
        token_kind=token_kind,  # type: ignore[arg-type]  # only evm kinds are used here
        protocol=protocol,
        decimals=decimals,
    )
    assert token.name == token.identifier
    return token


def _chains_aggregator(
        database: DBHandler,
        chains_with_accounts: tuple[SupportedBlockchain, ...] = (SupportedBlockchain.ETHEREUM,),
        infos: Any = None,
        node_inquirer: Any = None,
) -> tuple[MagicMock, Any]:
    chains_aggregator = MagicMock()
    if node_inquirer is None:
        node_inquirer = MagicMock()
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


def _get_cursor(database: DBHandler) -> str | None:
    with database.conn.read_ctx() as cursor:
        return database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.TOKEN_DETAILS_RETRY_CURSOR,
        )


def _marks() -> dict[ChecksumEvmAddress, tuple[int, Any]]:
    return {
        mark.address: (mark.attempts, mark.saved)
        for mark in get_token_details_retry_marks(chain_id=ChainID.ETHEREUM, limit=100)
    }


def _details(token: EvmToken) -> tuple[str, str | None, int | None]:
    return (token := EvmToken(token.identifier)).name, token.symbol, token.decimals


@pytest.mark.parametrize(('multicall_kwargs', 'create_kwargs', 'error', 'mark'), [
    pytest.param({'side_effect': RemoteError('down')}, {}, TokenQueryFailed, (0, None), id='unreachable'),  # noqa: E501
    pytest.param({'side_effect': RemoteError('down')}, FALLBACKS, None, (0, ('Fallback', 'FB', 18)), id='unreachable-with-fallbacks'),  # noqa: E501
    pytest.param({'return_value': _output(name=None)}, FALLBACKS, None, (0, ('Fallback', 'TKN', 6)), id='partial'),  # fallbacks only fill what is missing  # noqa: E501
    pytest.param({'return_value': [(False, b'')] * 3}, {}, NotERC20Conformant, None, id='no-methods'),  # noqa: E501
    pytest.param({'return_value': _output(name=None)}, FALLBACKS | {'protocol': SPAM_PROTOCOL}, None, None, id='known-spam'),  # noqa: E501
    pytest.param({'side_effect': RemoteError('down')}, {'protocol': SPAM_PROTOCOL}, TokenQueryFailed, None, id='known-spam-unreachable'),  # noqa: E501
    pytest.param({'return_value': _output(decimals=None, symbol='claim at site.io')}, {}, None, None, id='detected-spam'),  # noqa: E501
])
def test_marking_at_creation(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        multicall_kwargs: dict[str, Any],
        create_kwargs: dict[str, Any],
        error: type[Exception] | None,
        mark: tuple[int, Any] | None,
) -> None:
    """When a token is first seen, only an erc20 token whose query failed or returned some of
    the details is marked, never spam or a contract without any of the methods. A retry that
    can't reach the nodes does not count an attempt, and the mark goes away once the details
    are found."""
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
    assert _marks() == ({} if mark is None else {address: mark})
    if mark is None:
        return

    chains_aggregator, _ = _chains_aggregator(database=database, node_inquirer=ethereum_inquirer)
    with patch.object(ethereum_inquirer, 'multicall_2', side_effect=RemoteError('down')):
        retry_missing_token_details(chains_aggregator)
    assert _marks() == {address: mark}

    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output()):
        retry_missing_token_details(chains_aggregator)
    token = EvmToken(evm_address_to_identifier(address=address, chain_id=ChainID.ETHEREUM))
    assert _details(token) == ('Token', 'TKN', 6)
    assert _marks() == {}


def test_given_up_token_is_never_retried(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """A token whose details stay incomplete is given up when the attempts run out, and is
    not marked again when it is seen again. If it is added later, for example by an asset
    update, the transactions where it was seen are flagged for redecoding once. Tokens given
    up because the user edited them are not."""
    def see_token() -> None:
        ethereum_inquirer.contract_info_erc20_cache.remove(address)
        with pytest.raises(NotERC20Conformant):
            get_or_create_evm_token(
                userdb=database,
                evm_address=address,
                chain_id=ChainID.ETHEREUM,
                evm_inquirer=ethereum_inquirer,
            )

    address = _address(1)
    chains_aggregator, _ = _chains_aggregator(database=database, node_inquirer=ethereum_inquirer)
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output(name=None)) as multicall:  # noqa: E501
        see_token()
        for attempt in range(1, TOKEN_DETAILS_RETRY_MAX_ATTEMPTS + 1):
            retry_missing_token_details(chains_aggregator)
            assert _marks() == (
                {address: (attempt, None)} if attempt < TOKEN_DETAILS_RETRY_MAX_ATTEMPTS else {}
            )

        multicall.reset_mock()
        see_token()  # seen again after giving up
        retry_missing_token_details(chains_aggregator)

    assert _marks() == {}
    assert multicall.call_count == 1  # only the query of the new sighting

    edited = _create_placeholder(database, 2)
    stop_token_details_retry(chain_id=ChainID.ETHEREUM, address=edited.evm_address)
    get_or_create_evm_token(  # added later, for example by an asset update
        userdb=database,
        evm_address=address,
        chain_id=ChainID.ETHEREUM,
        name='Added',
        symbol='ADD',
        decimals=6,
    )
    with patch('rotkehlchen.tasks.assets.redecode_created_tokens_txs') as redecode:
        retry_missing_token_details(chains_aggregator)
        retry_missing_token_details(chains_aggregator)  # flagged only once

    assert [x.kwargs for x in redecode.call_args_list] == [
        {'database': database, 'chain_id': ChainID.ETHEREUM, 'addresses': [address]},
    ]


def test_which_tokens_are_retried(database: DBHandler) -> None:
    """Placeholders of normal erc20 tokens on chains with accounts are queried, also the ones
    with a NULL name that older versions saved, and only updated when all the details were
    found. Marks of tokens found to be spam after being marked are dropped without a query,
    and so are the ones of tokens that could not be created but were added since, whose
    transactions are flagged for redecoding instead."""
    found, not_found, null_name = (_create_placeholder(database, i) for i in (1, 2, 3))
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        write_cursor.execute('UPDATE assets SET name=NULL WHERE identifier=?', (null_name.identifier,))  # noqa: E501
    AssetResolver.clean_memory_cache(null_name.identifier)
    _create_placeholder(database, 4, protocol=SPAM_PROTOCOL)
    _create_placeholder(database, 5, token_kind=TokenKind.ERC721)
    other_chain = _create_placeholder(database, 6, ChainID.GNOSIS)
    spam = _create_placeholder(database, 7, protocol=SPAM_PROTOCOL)  # marked before found spam
    mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=spam.evm_address, saved=(spam.identifier, '', 18))  # noqa: E501
    mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=(added := _address(8)), saved=None)
    get_or_create_evm_token(  # added after it could not be created, for example by an update
        userdb=database,
        evm_address=added,
        chain_id=ChainID.ETHEREUM,
        name='Added',
        symbol='ADD',
        decimals=6,
    )
    queried: list[ChecksumEvmAddress] = []

    def infos(addresses: list[ChecksumEvmAddress]) -> dict[str, Any]:
        queried.extend(addresses)
        return {x.evm_address: _info('Found') for x in (found, null_name)}

    chains_aggregator, _ = _chains_aggregator(database=database, infos=infos)
    with (
        patch('rotkehlchen.tasks.assets.redecode_token_txs'),
        patch('rotkehlchen.tasks.assets.redecode_created_tokens_txs') as redecode,
    ):
        retry_missing_token_details(chains_aggregator)

    assert sorted(queried) == sorted(x.evm_address for x in (found, not_found, null_name))
    assert [x.kwargs for x in redecode.call_args_list] == [
        {'database': database, 'chain_id': ChainID.ETHEREUM, 'addresses': [added]},
    ]
    assert _details(EvmToken(evm_address_to_identifier(address=added, chain_id=ChainID.ETHEREUM))) == ('Added', 'ADD', 6)  # noqa: E501
    assert _details(found) == _details(null_name) == ('Found', 'SYM', 6)
    assert _details(not_found) == (not_found.identifier, '', 18)
    assert _details(other_chain)[0] == other_chain.identifier
    # the placeholder that answered without details counts an attempt to be given up some day
    assert _marks() == {not_found.evm_address: (1, (not_found.identifier, None, 18))}
    assert _get_cursor(database) == ''  # reached the end
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.LAST_TOKEN_DETAILS_RETRY_TS,
        ) is not None


@pytest.mark.parametrize('marked', [False, True])
@pytest.mark.parametrize('keep_name', [False, True])
def test_token_changed_while_querying_keeps_the_changes(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        marked: bool,
        keep_name: bool,
) -> None:
    """A user edit or asset update that happens while the details are queried wins. Only the
    details it did not change are filled, so a name it kept, which is the placeholder or
    fallback one, still gets the queried one."""
    if marked:  # created with fallbacks after a failed query
        with patch.object(ethereum_inquirer, 'multicall_2', side_effect=RemoteError('down')):
            token = get_or_create_evm_token(
                userdb=database,
                evm_address=_address(1),
                chain_id=ChainID.ETHEREUM,
                evm_inquirer=ethereum_inquirer,
                fallback_name='Fallback',
                fallback_symbol='FB',
                fallback_decimals=18,
            )
        assert _marks() == {token.evm_address: (0, ('Fallback', 'FB', 18))}
    else:
        token = _create_placeholder(database, 1)

    name = _details(token)[0] if keep_name else 'User Name'

    def edit_while_querying(addresses: list[ChecksumEvmAddress]) -> dict[str, Any]:
        edit_token_and_clean_cache(
            token=EvmToken(token.identifier),
            name=name,
            symbol='USR',
            decimals=8,
            started=None,
            chain_inquirer=None,
        )
        return {token.evm_address: _info('Queried')}

    chains_aggregator, _ = _chains_aggregator(database=database, infos=edit_while_querying)
    retry_missing_token_details(chains_aggregator)

    assert _details(token) == ('Queried' if keep_name else name, 'USR', 8)
    assert _marks() == {}  # nothing to retry, the token was fixed by someone else


@pytest.mark.parametrize('marked', [False, True])
def test_user_edit_while_querying_is_never_overwritten(
        database: DBHandler,
        marked: bool,
) -> None:
    """A user edit stops the retry of the token. If it happens while the details are queried,
    not even the details the user left as they were are filled, and no mark is created."""
    token = _create_placeholder(database, 1)
    if marked:
        mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=token.evm_address, saved=(token.identifier, None, 18))  # noqa: E501

    def edit_while_querying(addresses: list[ChecksumEvmAddress]) -> dict[str, Any]:
        edit_token_and_clean_cache(  # what the edit endpoint does
            token=EvmToken(token.identifier),
            name=None,
            symbol='USR',
            decimals=None,
            started=None,
            chain_inquirer=None,
        )
        stop_token_details_retry(chain_id=ChainID.ETHEREUM, address=token.evm_address)
        return {token.evm_address: _info('Queried')}

    chains_aggregator, _ = _chains_aggregator(database=database, infos=edit_while_querying)
    retry_missing_token_details(chains_aggregator)

    assert _details(token) == (token.identifier, 'USR', 18)
    assert _marks() == {}


def test_repair_on_access_does_not_overwrite_with_defaults(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """Accessing a placeholder with an inquirer queries it, but a failed or partial query
    must not write None or the default decimals over what the token has"""
    token = _create_placeholder(database, 1, decimals=6)
    for multicall_kwargs in (
        {'side_effect': RemoteError('down')},
        {'return_value': _output(decimals=None, symbol=None)},
    ):
        ethereum_inquirer.token_query_failures.remove(token.evm_address)
        ethereum_inquirer.contract_info_erc20_cache.remove(token.evm_address)
        with patch.object(ethereum_inquirer, 'multicall_2', **multicall_kwargs):
            get_or_create_evm_token(
                userdb=database,
                evm_address=token.evm_address,
                chain_id=ChainID.ETHEREUM,
                evm_inquirer=ethereum_inquirer,
            )
        assert _details(token) == (token.identifier, '', 6)

    ethereum_inquirer.contract_info_erc20_cache.remove(token.evm_address)
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output()):
        get_or_create_evm_token(
            userdb=database,
            evm_address=token.evm_address,
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
        )
    assert _details(token) == ('Token', 'TKN', 6)


@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address()]])
@pytest.mark.parametrize('decimals_call', ['unreachable', 'failing'])
def test_transfer_is_redecoded_with_found_details(
        database: DBHandler,
        ethereum_accounts: list[ChecksumEvmAddress],
        ethereum_inquirer: EthereumInquirer,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        decimals_call: str,
) -> None:
    """A transfer of a new token decoded while the nodes fail is missing from history, and
    one decoded while only decimals() fails has the amount of the default decimals. Once the
    token details are found the transaction is redecoded with them."""
    token_address = _address(1)
    transaction = EvmTransaction(
        tx_hash=(tx_hash := make_evm_tx_hash()),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1700000000),
        block_number=18000000,
        from_address=(user := ethereum_accounts[0]),
        to_address=token_address,
        value=0,
        gas=45000,
        gas_price=10000000000,
        gas_used=45000,
        input_data=b'',
        nonce=0,
    )
    receipt = EvmTxReceipt(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[EvmTxReceiptLog(
            log_index=0,
            data=(1500000).to_bytes(32, 'big'),
            address=token_address,
            topics=[
                ERC20_OR_ERC721_TRANSFER,
                bytes(12) + bytes.fromhex(user[2:]),
                bytes(12) + bytes.fromhex(make_evm_address()[2:]),
            ],
        )],
    )
    with database.user_write() as write_cursor:
        DBEvmTx(database).add_transactions(write_cursor, [transaction], relevant_address=user)
        DBEvmTx(database).add_or_ignore_receipt_data(
            write_cursor,
            ChainID.ETHEREUM,
            txreceipt_to_data(receipt),
        )

    def transfers() -> list[tuple[HistoryEventType, HistoryEventSubType, str, FVal]]:
        with database.conn.read_ctx() as cursor:
            return [
                (x.event_type, x.event_subtype, x.asset.identifier, x.amount)
                for x in DBHistoryEvents(database).get_history_events_internal(
                    cursor=cursor,
                    filter_query=EvmEventFilterQuery.make(tx_hashes=[tx_hash]),
                )
                if x.event_type != HistoryEventType.SPEND or x.event_subtype != HistoryEventSubType.FEE  # noqa: E501
            ]

    token_identifier = evm_address_to_identifier(address=token_address, chain_id=ChainID.ETHEREUM)
    with patch.object(
        ethereum_inquirer,
        'multicall_2',
        **({'side_effect': RemoteError('down')} if decimals_call == 'unreachable' else {'return_value': _output(decimals=None)}),  # noqa: E501
    ):
        ethereum_transaction_decoder.decode_transaction_hashes(
            ignore_cache=False,
            tx_hashes=[tx_hash],
        )

    if decimals_call == 'unreachable':
        assert transfers() == []
        assert _marks() == {token_address: (0, None)}
    else:  # created with the default decimals
        assert transfers() == [(
            HistoryEventType.SPEND,
            HistoryEventSubType.NONE,
            token_identifier,
            FVal('1.5E-12'),
        )]
        assert _marks() == {token_address: (0, ('Token', 'TKN', 18))}

    chains_aggregator, _ = _chains_aggregator(database=database, node_inquirer=ethereum_inquirer)
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output()):
        retry_missing_token_details(chains_aggregator)

    # flagged for the periodic decoding task, which redecodes it with the found details
    assert ethereum_transaction_decoder.get_and_decode_undecoded_transactions() == [tx_hash]
    assert transfers() == [(
        HistoryEventType.SPEND,
        HistoryEventSubType.NONE,
        token_identifier,
        FVal('1.5'),  # 1500000 with the 6 decimals of the token
    )]
    assert _marks() == {}


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

    # broken tokens did not block the ones after them. They got marked when their details
    # were not found, so they are also retried from the marks until they are given up.
    assert queried == [
        [tokens[0].evm_address, tokens[1].evm_address],
        [tokens[2].evm_address, tokens[0].evm_address, tokens[1].evm_address],
        [tokens[0].evm_address, tokens[1].evm_address],  # the marks are least recently tried
    ]
    assert {address: attempts for address, (attempts, _) in _marks().items()} == {
        tokens[0].evm_address: 3, tokens[1].evm_address: 3, tokens[2].evm_address: 1,
    }


def test_failed_chunk_does_not_block_following_tokens(database: DBHandler) -> None:
    """A chunk of placeholders that fails after an earlier chunk worked is queried one by
    one. The nodes answered in this run, so the failures don't stop it and the chunks after
    it are still queried."""
    tokens = sorted((_create_placeholder(database, i) for i in range(1, 7)), key=lambda x: x.identifier)  # noqa: E501
    failing = {tokens[2].evm_address, tokens[3].evm_address}
    calls = []

    def infos(addresses: list[ChecksumEvmAddress]) -> dict[str, Any]:
        calls.append(addresses)
        if failing.intersection(addresses):
            raise RemoteError('out of gas')
        return {address: _info('Found') for address in addresses}

    chains_aggregator, _ = _chains_aggregator(database=database, infos=infos)
    with patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_CHUNK_SIZE', 2):
        retry_missing_token_details(chains_aggregator)

    assert calls == [[x.evm_address for x in chunk] for chunk in (
        tokens[:2], tokens[2:4], tokens[2:3], tokens[3:4], tokens[4:],
    )]
    assert [EvmToken(x.identifier).name for x in tokens] == [
        'Found', 'Found', tokens[2].identifier, tokens[3].identifier, 'Found', 'Found',
    ]


def test_remote_error_is_retried_in_the_next_cycle(database: DBHandler) -> None:
    """When the nodes are down the placeholders are left as they are, and the cursor still
    moves past them so a chunk that always fails can't block the tokens after it"""
    tokens = [_create_placeholder(database, i) for i in (1, 2, 3)]
    chains_aggregator, _ = _chains_aggregator(database=database, infos=RemoteError('nodes down'))

    with patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_BATCH_SIZE', 3):
        retry_missing_token_details(chains_aggregator)

    assert all(EvmToken(x.identifier).name == x.identifier for x in tokens)
    assert _get_cursor(database) == max(x.identifier for x in tokens)


def test_token_failing_its_chunk_does_not_block_the_marks(database: DBHandler) -> None:
    """A token that makes the query of its whole chunk fail while the nodes work is isolated:
    the rest of its chunk is still found and it counts attempts until it is given up, instead
    of failing the chunk of the least recently tried marks forever"""
    poison, *others = (addresses := [_address(i) for i in (1, 2, 3)])
    for address in addresses:
        mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=address, saved=None)

    def infos(queried: list[ChecksumEvmAddress]) -> dict[str, Any]:
        if poison in queried:
            raise RemoteError('out of gas')
        return {address: _info('Found') for address in queried}

    chains_aggregator, _ = _chains_aggregator(database=database, infos=infos)
    retry_missing_token_details(chains_aggregator)

    assert _marks() == {poison: (1, None)}
    for address in others:
        token = EvmToken(evm_address_to_identifier(address=address, chain_id=ChainID.ETHEREUM))
        assert _details(token) == ('Found', 'SYM', 6)

    for idx in range(TOKEN_DETAILS_RETRY_MAX_ATTEMPTS - 1):
        # another token answering in the same run shows the nodes work
        _create_placeholder(database, 10 + idx)
        retry_missing_token_details(chains_aggregator)
    assert _marks() == {}  # given up


def test_marks_failing_while_nodes_are_down_go_to_the_back(database: DBHandler) -> None:
    """When the nodes don't answer, the marks queried one by one don't count an attempt but
    move behind the ones not tried, so they can't stay in front if they were the problem"""
    addresses = [_address(i) for i in (1, 2, 3, 4, 5)]
    for address in addresses:
        mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=address, saved=None)

    chains_aggregator, node_inquirer = _chains_aggregator(database=database, infos=RemoteError('down'))  # noqa: E501
    with patch('rotkehlchen.globaldb.cache.ts_now', return_value=ts_now() + 100):
        retry_missing_token_details(chains_aggregator)

    assert [x.args[0] for x in node_inquirer.get_multiple_erc20_contracts_info.call_args_list] == [
        addresses,  # the chunk
        *([x] for x in addresses[:TOKEN_DETAILS_RETRY_MAX_FAILED_QUERIES]),  # one by one
    ]
    marks = get_token_details_retry_marks(chain_id=ChainID.ETHEREUM, limit=10)
    assert [x.address for x in marks] == addresses[3:] + addresses[:3]
    assert all(x.attempts == 0 for x in marks)


def test_outage_in_the_middle_of_a_run_counts_no_attempts(database: DBHandler) -> None:
    """When the nodes stop answering after a chunk of the run was queried, the run stops
    after TOKEN_DETAILS_RETRY_MAX_FAILED_QUERIES single token queries fail in a row. Their
    marks are postponed instead of counting an attempt and the rest are not queried."""
    addresses = [_address(i) for i in range(1, 7)]
    for address in addresses:
        mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=address, saved=None)

    def infos(queried: list[ChecksumEvmAddress]) -> dict[str, Any]:
        if queried == addresses[:2]:
            return {}  # the nodes answered, but these tokens have no details
        raise RemoteError('down')

    chains_aggregator, node_inquirer = _chains_aggregator(database=database, infos=infos)
    with patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_CHUNK_SIZE', 2):
        retry_missing_token_details(chains_aggregator)

    assert [x.args[0] for x in node_inquirer.get_multiple_erc20_contracts_info.call_args_list] == [
        addresses[:2],
        addresses[2:4], [addresses[2]], [addresses[3]],
        addresses[4:], [addresses[4]],  # third failure in a row
        [addresses[1]],  # probe with the token that answered: it fails too, so the nodes are down
    ]
    assert _marks() == {
        addresses[0]: (1, None), addresses[1]: (1, None),  # answered without details
        **dict.fromkeys(addresses[2:], (0, None)),
    }


def test_tokens_failing_on_their_own_do_not_look_like_an_outage(database: DBHandler) -> None:
    """Tokens that each break their own query, next to each other, reach the limit of failures
    in a row. A token that answered in the run is queried again: as it answers the nodes are up,
    so those tokens count an attempt, they can be given up, and the run goes on to the rest."""
    healthy, *poison, last_a, last_b = (addresses := [_address(i) for i in range(1, 7)])
    poison = poison[:3]
    for address in addresses:
        mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=address, saved=None)

    def infos(queried: list[ChecksumEvmAddress]) -> dict[str, Any]:
        if any(x in poison for x in queried):
            raise RemoteError('out of gas')
        return {address: _info('Found') for address in queried}

    chains_aggregator, _ = _chains_aggregator(database=database, infos=infos)
    with patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_CHUNK_SIZE', 2):
        retry_missing_token_details(chains_aggregator)

    assert _marks() == dict.fromkeys(poison, (1, None))  # counted, and the rest was found
    for address in (healthy, last_a, last_b):
        token = EvmToken(evm_address_to_identifier(address=address, chain_id=ChainID.ETHEREUM))
        assert _details(token) == ('Found', 'SYM', 6)


def test_decoder_edit_does_not_stop_missing_details_from_being_fixed(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """A token created while only decimals() failed gets the default decimals and a mark that
    remembers that only they are missing, so the symbol given by the caller is kept. A decoder
    giving it a name later does not count as an edit of the decimals, so the retry still fixes
    them and keeps the decoder's name. The stale info cached when the token was first seen is
    dropped by the retry query."""
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output(decimals=None)):
        token = get_or_create_evm_token(
            userdb=database,
            evm_address=(address := _address(1)),
            chain_id=ChainID.ETHEREUM,
            symbol='GIV',
            evm_inquirer=ethereum_inquirer,
        )
    assert _details(token) == ('Token', 'GIV', 18)
    assert [x.missing for x in get_token_details_retry_marks(chain_id=ChainID.ETHEREUM, limit=10)] == [frozenset({'decimals'})]  # noqa: E501

    get_or_create_evm_token(  # what a protocol decoder does
        userdb=database,
        evm_address=address,
        chain_id=ChainID.ETHEREUM,
        name='Decoder Name',
        protocol='some-protocol',
    )
    chains_aggregator, _ = _chains_aggregator(database=database, node_inquirer=ethereum_inquirer)
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output()) as multicall:
        retry_missing_token_details(chains_aggregator)
        # what the refresh of the asset edit form shows, not the info cached when first seen
        assert ethereum_inquirer.get_erc20_contract_info(address=address, ignore_failure_cooldown=True)['decimals'] == 6  # noqa: E501
        assert multicall.call_count == 2

    assert _details(token) == ('Decoder Name', 'GIV', 6)
    assert _marks() == {}


def test_seeing_a_marked_token_again_keeps_its_place(database: DBHandler) -> None:
    """Every sighting of a token that could not be created marks it, so marking it again as it
    already is must not move it to the back of the queue"""
    mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=(first := _address(1)), saved=None)
    mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=_address(2), saved=None)
    with patch('rotkehlchen.globaldb.cache.ts_now', return_value=ts_now() + 100):
        mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=first, saved=None)

    assert get_token_details_retry_marks(chain_id=ChainID.ETHEREUM, limit=10)[0].address == first


@pytest.mark.parametrize('given', [{}, {'name': 'name.eth', 'symbol': 'ENS'}])
def test_nft_is_created_when_the_nodes_fail(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        given: dict[str, str],
) -> None:
    """Every collectible id is a new token, so an nft seen while the nodes fail is created
    with empty details, or the given ones, instead of dropping its events. It is not marked."""
    with patch.object(ethereum_inquirer, 'multicall_2', side_effect=RemoteError('down')):
        token = get_or_create_evm_token(
            userdb=database,
            evm_address=_address(1),
            chain_id=ChainID.ETHEREUM,
            token_kind=TokenKind.ERC721,
            collectible_id='1',
            evm_inquirer=ethereum_inquirer,
            **given,  # type: ignore[arg-type]  # only name and symbol are given
        )

    assert _details(token) == (given.get('name', ''), given.get('symbol', ''), 0)
    assert _marks() == {}


def test_unrelated_failing_property_does_not_block_the_needed_ones(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """A mark only needs the properties it recorded as missing. A decimals only mark gets its
    decimals even if the optional symbol() keeps reverting, and a mark that needs both keeps
    only the symbol as missing, instead of losing the decimals. A run that made progress does
    not count an attempt, a later one that did not does."""
    chains_aggregator, _ = _chains_aggregator(database=database, node_inquirer=ethereum_inquirer)
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output(decimals=None)):
        decimals_only = get_or_create_evm_token(
            userdb=database,
            evm_address=_address(1),
            chain_id=ChainID.ETHEREUM,
            symbol='GIV',
            evm_inquirer=ethereum_inquirer,
        )
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output(decimals=None, symbol=None)):  # noqa: E501
        both = get_or_create_evm_token(
            userdb=database,
            evm_address=_address(2),
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
            **FALLBACKS,
        )
    assert {x.address: x.missing for x in get_token_details_retry_marks(chain_id=ChainID.ETHEREUM, limit=10)} == {  # noqa: E501
        decimals_only.evm_address: frozenset({'decimals'}),
        both.evm_address: frozenset({'decimals', 'symbol'}),
    }

    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output(symbol=None) * 2):
        retry_missing_token_details(chains_aggregator)

    assert _details(decimals_only) == ('Token', 'GIV', 6)
    assert _details(both) == ('Token', 'FB', 6)  # the symbol is still the fallback one
    marks = {x.address: (x.attempts, x.missing) for x in get_token_details_retry_marks(chain_id=ChainID.ETHEREUM, limit=10)}  # noqa: E501
    assert marks == {both.evm_address: (0, frozenset({'symbol'}))}

    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output(symbol=None)):
        retry_missing_token_details(chains_aggregator)

    marks = {x.address: (x.attempts, x.missing) for x in get_token_details_retry_marks(chain_id=ChainID.ETHEREUM, limit=10)}  # noqa: E501
    assert marks == {both.evm_address: (1, frozenset({'symbol'}))}


@contextmanager
def _during_retry_transaction(func: Callable[[], None]) -> Iterator[None]:
    """Run func in another task from inside the global DB transaction of the retry, after it
    read the token and before it writes it, where a gap would let it in. It has to wait."""
    tasks: list[Task] = []
    read_token_details = details_retry._read_token_details

    def read_then_start(*args: Any, **kwargs: Any) -> Any:
        result = read_token_details(*args, **kwargs)
        if len(tasks) == 0:
            tasks.append(spawn(func))
            time.sleep(0.5)  # enough for it to finish if nothing stopped it
            assert tasks[0].dead is False

        return result

    with patch.object(details_retry, '_read_token_details', side_effect=read_then_start):
        yield

    wait(tasks)
    assert exception_of(tasks[0]) is None


@pytest.mark.parametrize('marked', [False, True])
def test_user_edit_cannot_land_between_the_check_and_the_write(
        database: DBHandler,
        marked: bool,
) -> None:
    """The retry checks the given up key, reads the token and writes in one global DB
    transaction. An edit like the one of the user, which does not take the token lock, that
    starts after the read has to wait for the transaction and wins."""
    token = _create_placeholder(database, 1)
    if marked:
        mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=token.evm_address, saved=(token.identifier, None, 18))  # noqa: E501
    user_token = EvmToken.initialize(
        address=token.evm_address,
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        name='User Name',
        symbol='USR',
        decimals=8,
    )

    def edit_like_the_user() -> None:
        with GlobalDBHandler().conn.write_ctx():  # what the edit endpoint does
            GlobalDBHandler.edit_user_asset(user_token)
            stop_token_details_retry(chain_id=ChainID.ETHEREUM, address=token.evm_address)

    chains_aggregator, _ = _chains_aggregator(database=database, infos=lambda _: {token.evm_address: _info('Queried')})  # noqa: E501
    with _during_retry_transaction(edit_like_the_user):
        retry_missing_token_details(chains_aggregator)

    assert _details(token) == ('User Name', 'USR', 8)
    assert is_token_details_retry_given_up(chain_id=ChainID.ETHEREUM, address=token.evm_address)
    assert _marks() == {}


def test_decoder_with_an_older_token_cannot_overwrite_the_found_details(
        database: DBHandler,
) -> None:
    """A decoder that loaded the token before the retry wrote it, and saves it after, would
    write its older decimals back with the mark gone. The retry takes the token lock like
    get_or_create_evm_token does, so the decoder only loads the token after the retry."""
    token = _create_placeholder(database, 1)
    assert EvmToken(token.identifier).decimals == 18  # in the memory cache with the old decimals

    def decode() -> None:
        get_or_create_evm_token(
            userdb=database,
            evm_address=token.evm_address,
            chain_id=ChainID.ETHEREUM,
            name='Decoder Name',
            protocol='some-protocol',
        )

    chains_aggregator, _ = _chains_aggregator(database=database, infos=lambda _: {token.evm_address: _info('Queried', decimals=6)})  # noqa: E501
    with _during_retry_transaction(decode):
        retry_missing_token_details(chains_aggregator)

    assert _details(token) == ('Decoder Name', 'SYM', 6)
    assert _marks() == {}


@pytest.mark.parametrize('marked', [False, True])
def test_interrupted_redecode_is_done_in_the_next_run(
        database: DBHandler,
        marked: bool,
) -> None:
    """The mark is only removed once the transactions of a token whose details changed are
    redecoded, and an unmarked token gets one with its old details for that, so that a stop
    in between does not leave events calculated with the old decimals for good."""
    token = _create_placeholder(database, 1)
    if marked:
        mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=token.evm_address, saved=(token.identifier, None, 18))  # noqa: E501
    chains_aggregator, _ = _chains_aggregator(database=database, infos=lambda _: {token.evm_address: _info('Found')})  # noqa: E501
    with (
        patch('rotkehlchen.tasks.assets.redecode_token_txs', side_effect=RemoteError('interrupted')),  # noqa: E501
        pytest.raises(RemoteError),
    ):
        retry_missing_token_details(chains_aggregator)

    assert _details(token) == ('Found', 'SYM', 6)  # written already
    assert _marks() == {token.evm_address: (0, (token.identifier, None, 18))}  # pending

    with patch('rotkehlchen.tasks.assets.redecode_token_txs') as redecode:
        retry_missing_token_details(chains_aggregator)

    assert [x.kwargs['address'] for x in redecode.call_args_list] == [token.evm_address]
    assert _details(token) == ('Found', 'SYM', 6)
    assert _marks() == {}


def test_created_tokens_are_redecoded_in_a_single_scan(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """The logs have no index on their address, so the tokens of a run that could not be created
    before, whether created by the retry, added since or given up, are all searched for with one
    scan per chain. Their marks and attempts are cleared only after it, so an interruption
    makes the next run do it again."""
    created, added, given_up = _address(1), _address(2), _address(3)
    for address in (created, added):
        mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=address, saved=None)

    for _ in range(TOKEN_DETAILS_RETRY_MAX_ATTEMPTS):  # given up before it could be created
        count_token_details_retry_attempt(TokenDetailsRetryMark(chain_id=ChainID.ETHEREUM, address=given_up, attempts=_, saved=None))  # noqa: E501
    for address in (added, given_up):  # added since, for example by an asset update
        get_or_create_evm_token(
            userdb=database,
            evm_address=address,
            chain_id=ChainID.ETHEREUM,
            name='Added',
            symbol='ADD',
            decimals=6,
        )
    chains_aggregator, _ = _chains_aggregator(database=database, infos=lambda addresses: {x: _info('Chain') for x in addresses})  # noqa: E501
    with patch('rotkehlchen.tasks.assets.redecode_created_tokens_txs', side_effect=RemoteError('interrupted')) as redecode:  # noqa: E501
        with pytest.raises(RemoteError):
            retry_missing_token_details(chains_aggregator)

        assert set(_marks()) == {created, added}  # not cleared yet
        assert details_retry.get_given_up_tokens_added_since(ChainID.ETHEREUM) == [given_up]

        redecode.side_effect = None
        retry_missing_token_details(chains_aggregator)

    assert [sorted(x.kwargs['addresses']) for x in redecode.call_args_list] == [
        sorted([created, added, given_up]),
        sorted([created, added, given_up]),
    ]
    assert _marks() == {}
    assert details_retry.get_given_up_tokens_added_since(ChainID.ETHEREUM) == []
    assert _details(EvmToken(evm_address_to_identifier(address=created, chain_id=ChainID.ETHEREUM))) == ('Chain', 'SYM', 6)  # noqa: E501


@pytest.mark.parametrize('remove', ['delete', 'replace', 'hard_reset'])
def test_deleting_a_token_clears_its_retry_bookkeeping(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        remove: str,
) -> None:
    """The given up key of a token is permanent, so it has to go with the token, however it is
    removed. Otherwise the token, if seen again after being deleted, replaced or dropped by a
    hard reset while its query fails, could not be marked again and its transfers would never be
    recovered."""
    with patch.object(ethereum_inquirer, 'multicall_2', side_effect=RemoteError('down')):
        token = get_or_create_evm_token(
            userdb=database,
            evm_address=_address(1),
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
            **FALLBACKS,
        )
        assert set(_marks()) == {token.evm_address}
        marked_only = _address(2)  # a mark of a token that was never created has no asset row
        mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=marked_only, saved=None)
        stop_token_details_retry(chain_id=ChainID.ETHEREUM, address=token.evm_address)

        if remove == 'delete':
            GlobalDBHandler.delete_asset_by_identifier(token.identifier)
        elif remove == 'hard_reset':
            assert GlobalDBHandler().hard_reset_assets_list(database, True)[0]
        else:
            database.replace_asset_identifier(token.identifier, A_ETH.resolve_to_asset_with_oracles())  # noqa: E501

        AssetResolver.clean_memory_cache(token.identifier)  # what the endpoints do
        assert is_token_details_retry_given_up(chain_id=ChainID.ETHEREUM, address=token.evm_address) is False  # noqa: E501
        assert set(_marks()) == {marked_only}  # only the bookkeeping of the removed token went

        ethereum_inquirer.token_query_failures.remove(token.evm_address)
        ethereum_inquirer.contract_info_erc20_cache.remove(token.evm_address)
        get_or_create_evm_token(  # seen again
            userdb=database,
            evm_address=token.evm_address,
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
            **FALLBACKS,
        )

    assert set(_marks()) == {token.evm_address, marked_only}


def test_given_details_are_kept_when_creation_is_deferred(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """The details supplied by the caller of a token that can't be created because the query
    failed are kept in its mark and win over the on chain ones when it is created. Only the ones
    that were not supplied are queried."""
    with (
        patch.object(ethereum_inquirer, 'multicall_2', side_effect=RemoteError('down')),
        pytest.raises(TokenQueryFailed),
    ):
        get_or_create_evm_token(
            userdb=database,
            evm_address=(address := _address(1)),
            chain_id=ChainID.ETHEREUM,
            name='Given Name',
            decimals=2,
            evm_inquirer=ethereum_inquirer,
        )

    [mark] = get_token_details_retry_marks(chain_id=ChainID.ETHEREUM, limit=10)
    assert (mark.saved, mark.given, mark.missing) == (None, {'name': 'Given Name', 'decimals': 2}, frozenset({'symbol'}))  # noqa: E501
    chains_aggregator, _ = _chains_aggregator(database=database, node_inquirer=ethereum_inquirer)
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output(decimals=6, symbol='ONCHAIN', name='On Chain')):  # noqa: E501
        retry_missing_token_details(chains_aggregator)

    token = EvmToken(evm_address_to_identifier(address=address, chain_id=ChainID.ETHEREUM))
    assert _details(token) == ('Given Name', 'ONCHAIN', 2)
    assert _marks() == {}


def test_later_sightings_keep_the_given_details(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """A protocol decoder gives a name when it sees a token that can't be created, and a plain
    transfer decoder seeing it later gives nothing. The mark keeps what was given."""
    def see_token(**given: Any) -> None:
        ethereum_inquirer.token_query_failures.remove(address)
        with (
            patch.object(ethereum_inquirer, 'multicall_2', side_effect=RemoteError('down')),
            pytest.raises(TokenQueryFailed),
        ):
            get_or_create_evm_token(
                userdb=database,
                evm_address=address,
                chain_id=ChainID.ETHEREUM,
                evm_inquirer=ethereum_inquirer,
                **given,
            )

    address = _address(1)
    see_token(name='Given Name')
    see_token()
    [mark] = get_token_details_retry_marks(chain_id=ChainID.ETHEREUM, limit=10)
    assert (mark.given, mark.missing) == ({'name': 'Given Name'}, frozenset({'symbol', 'decimals'}))  # noqa: E501
    see_token(symbol='GIV')  # more is given later
    [mark] = get_token_details_retry_marks(chain_id=ChainID.ETHEREUM, limit=10)
    assert (mark.given, mark.missing) == ({'name': 'Given Name', 'symbol': 'GIV'}, frozenset({'decimals'}))  # noqa: E501

    chains_aggregator, _ = _chains_aggregator(database=database, node_inquirer=ethereum_inquirer)
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output(decimals=6, symbol='ONCHAIN', name='On Chain')):  # noqa: E501
        retry_missing_token_details(chains_aggregator)

    token = EvmToken(evm_address_to_identifier(address=address, chain_id=ChainID.ETHEREUM))
    assert _details(token) == ('Given Name', 'GIV', 6)
    assert _marks() == {}


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


def test_user_requested_query_ignores_failure_cooldown(ethereum_inquirer: EthereumInquirer) -> None:  # noqa: E501
    """After a failure the address is not queried again for a while, unless the user asks"""
    with (
        patch.object(ethereum_inquirer, 'multicall_2', side_effect=RemoteError('down')),
        pytest.raises(TokenQueryFailed),
    ):
        ethereum_inquirer.get_erc20_contract_info(address := _address(1))

    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output()) as multicall:
        with pytest.raises(TokenQueryFailed):  # in the cooldown
            ethereum_inquirer.get_erc20_contract_info(address)
        assert multicall.call_count == 0

        assert ethereum_inquirer.get_erc20_contract_info(
            address=address,
            ignore_failure_cooldown=True,
        ) == {'decimals': 6, 'symbol': 'TKN', 'name': 'Token'}
        # the success cleared the failure, so the next query reaches the nodes again
        ethereum_inquirer.contract_info_erc20_cache.remove(address)
        assert ethereum_inquirer.get_erc20_contract_info(address)['name'] == 'Token'
        assert multicall.call_count == 2


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
