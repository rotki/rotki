"""Tests for querying again the details of tokens that are missing them.

The seam: when the details of an erc20 token can't be fully queried while it is first seen,
_get_or_create_token marks it in the global DB cache. retry_missing_token_details picks the
marked tokens and the ones whose name is their identifier, asks the node inquirer of their chain
for the details in chunks and fills the details that were missing and came back, as long as
nobody else changed them in the meantime.
When the details of a token change, or it gets created, a redecode is recorded for it in the
global DB, which every user DB applies by flagging the transactions of the token for redecoding,
and the periodic decoding task redecodes them.
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
    TOKEN_DETAILS_RETRY_MAX_POSTPONES,
    TokenDetailsRetryMark,
    apply_token_details_redecodes,
    count_token_details_retry_attempt,
    get_token_details_retry_mark,
    get_token_details_retry_marks,
    is_token_details_retry_given_up,
    mark_token_details_retry,
    postpone_token_details_retry,
    settle_created_token_marks,
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
from rotkehlchen.db.constants import TX_DECODED
from rotkehlchen.db.dbhandler import DBHandler
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
from rotkehlchen.tests.utils.database import mock_dbhandler_sync_globaldb_assets
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
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.concurrency import Task
    from rotkehlchen.tasks.manager import TaskManager
    from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash


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


def _token(address: ChecksumEvmAddress) -> EvmToken:
    return EvmToken(evm_address_to_identifier(address=address, chain_id=ChainID.ETHEREUM))


def _see_token(
        database: DBHandler,
        inquirer: EthereumInquirer,
        address: ChecksumEvmAddress,
        multicall: dict[str, Any] | None = None,
        raises: type[Exception] | None = TokenQueryFailed,
        **given: Any,
) -> EvmToken | None:
    """Make the decoding see a token while the multicall fails, or answers as given"""
    inquirer.token_query_failures.remove(address)
    inquirer.contract_info_erc20_cache.remove(address)
    token = None
    with (
        patch.object(inquirer, 'multicall_2', **(multicall or {'side_effect': RemoteError('down')})),  # noqa: E501
        pytest.raises(raises) if raises is not None else nullcontext(),
    ):
        token = get_or_create_evm_token(
            userdb=database,
            evm_address=address,
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=inquirer,
            **given,
        )

    return token  # noqa: RET504  # a return inside the with is unreachable when it raises


def _details(token: EvmToken) -> tuple[str, str | None, int | None]:
    return (token := EvmToken(token.identifier)).name, token.symbol, token.decimals


def _give_up(
        address: ChecksumEvmAddress,
        saved: tuple[str, str | None, int] | None,
        missing: frozenset[str] = frozenset({'name', 'symbol', 'decimals'}),
) -> None:
    """Give up a token as if its attempts ran out"""
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        details_retry._write_mark(
            write_cursor=write_cursor,
            mark=TokenDetailsRetryMark(chain_id=ChainID.ETHEREUM, address=address, attempts=TOKEN_DETAILS_RETRY_MAX_ATTEMPTS, saved=saved, missing=missing),  # noqa: E501
            given_up=True,
        )


def _redecodes() -> dict[ChecksumEvmAddress, bool]:
    """The tokens with a redecode recorded in the global DB, and whether they were created"""
    return {address: created for _, address, created, _ in details_retry._get_pending_redecodes(after_seq=0)}  # noqa: E501


def _redecode_seqs() -> dict[ChecksumEvmAddress, int]:
    return {address: seq for _, address, _, seq in details_retry._get_pending_redecodes(after_seq=0)}  # noqa: E501


def _applied_seq(database: DBHandler) -> int:
    """The sequence number of the last redecode the user DB applied"""
    with database.conn.read_ctx() as cursor:
        return int(database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.TOKEN_DETAILS_REDECODE_CURSOR,
        ) or 0)


def _add_incoming_transfer(
        database: DBHandler,
        user: ChecksumEvmAddress,
        token_address: ChecksumEvmAddress,
) -> EVMTxHash:
    """Add a not yet decoded transaction where the user receives 1500000 units of the token"""
    transaction = EvmTransaction(
        tx_hash=(tx_hash := make_evm_tx_hash()),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1700000000),
        block_number=18000000,
        from_address=make_evm_address(),  # incoming, so no fee event is decoded for the user
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
                bytes(12) + bytes.fromhex(make_evm_address()[2:]),
                bytes(12) + bytes.fromhex(user[2:]),
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

    return tx_hash


def _transfers(
        database: DBHandler,
        tx_hash: EVMTxHash,
) -> list[tuple[HistoryEventType, HistoryEventSubType, str, FVal]]:
    with database.conn.read_ctx() as cursor:
        return [
            (x.event_type, x.event_subtype, x.asset.identifier, x.amount)
            for x in DBHistoryEvents(database).get_history_events_internal(
                cursor=cursor,
                filter_query=EvmEventFilterQuery.make(tx_hashes=[tx_hash]),
            )
            if x.event_type != HistoryEventType.SPEND or x.event_subtype != HistoryEventSubType.FEE
        ]


def _is_decoded(database: DBHandler, tx_hash: EVMTxHash) -> bool:
    with database.conn.read_ctx() as cursor:
        return cursor.execute(
            'SELECT COUNT(*) FROM evm_tx_mappings AS M JOIN evm_transactions AS E '
            'ON E.identifier=M.tx_id WHERE E.tx_hash=? AND M.value=?',
            (tx_hash, TX_DECODED),
        ).fetchone()[0] == 1


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
    token = _token(address)
    assert _details(token) == ('Token', 'TKN', 6)
    assert _marks() == {}


def test_given_up_token_is_never_retried(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """A token whose details stay incomplete is given up when the attempts run out, and is
    not marked again when it is seen again. If it is added later, for example by an asset
    update, a redecode of the transactions where it was seen is recorded once. Tokens given
    up because the user edited them don't need one."""
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
    assert stop_token_details_retry(chain_id=ChainID.ETHEREUM, address=edited.evm_address) is False
    get_or_create_evm_token(  # added later, for example by an asset update
        userdb=database,
        evm_address=address,
        chain_id=ChainID.ETHEREUM,
        name='Added',
        symbol='ADD',
        decimals=6,
    )
    retry_missing_token_details(chains_aggregator)
    assert _redecodes() == {address: True}
    seqs = _redecode_seqs()
    retry_missing_token_details(chains_aggregator)
    assert _redecode_seqs() == seqs  # recorded only once


def test_which_tokens_are_retried(database: DBHandler) -> None:
    """Placeholders of normal erc20 tokens on chains with accounts are queried, also the ones
    with a NULL name that older versions saved, and only updated when all the details were
    found. Marks of tokens found to be spam after being marked are dropped without a query,
    and so are the ones of tokens that could not be created but were added since, whose
    transactions have to be redecoded instead, like the ones of the tokens that were found."""
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
    retry_missing_token_details(chains_aggregator)

    assert sorted(queried) == sorted(x.evm_address for x in (found, not_found, null_name))
    assert _redecodes() == {added: True, found.evm_address: False, null_name.evm_address: False}
    assert _applied_seq(database) == max(_redecode_seqs().values())  # applied by the run
    assert _details(_token(added)) == ('Added', 'ADD', 6)
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
        token = _see_token(database, ethereum_inquirer, _address(1), raises=None, **FALLBACKS)
        assert token is not None
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
    tx_hash = _add_incoming_transfer(database, user=ethereum_accounts[0], token_address=(token_address := _address(1)))  # noqa: E501

    def transfers() -> list[tuple[HistoryEventType, HistoryEventSubType, str, FVal]]:
        return _transfers(database, tx_hash)

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

    def ignored() -> bool:
        with database.conn.read_ctx() as cursor:
            return f'1{tx_hash!s}' in database.get_ignored_action_ids(cursor=cursor)

    if decimals_call == 'unreachable':
        assert transfers() == []
        assert ignored() is True  # decoding to no events ignores the tx
        assert _marks() == {token_address: (0, None)}
    else:  # created with the default decimals
        assert transfers() == [(
            HistoryEventType.RECEIVE,
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
    assert ignored() is False  # or accounting would skip the recovered transfer
    assert transfers() == [(
        HistoryEventType.RECEIVE,
        HistoryEventSubType.NONE,
        token_identifier,
        FVal('1.5'),  # 1500000 with the 6 decimals of the token
    )]
    assert _marks() == {}


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


def test_last_run_is_saved_before_applying_redecodes(database: DBHandler) -> None:
    """Applying the recorded redecodes waits for the decoders and scans the logs, so if it
    fails the last run must be saved already, or the task would be due again at once"""
    chains_aggregator, _ = _chains_aggregator(database=database, infos=lambda _: {})
    with (
        patch('rotkehlchen.tasks.assets.apply_token_details_redecodes', side_effect=ValueError('unexpected')),  # noqa: E501
        pytest.raises(ValueError),
    ):
        retry_missing_token_details(chains_aggregator)

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
        return {}  # nothing can be updated, as if the tokens were permanently broken

    chains_aggregator, _ = _chains_aggregator(database=database, infos=infos)
    with patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_BATCH_SIZE', 2):
        retry_missing_token_details(chains_aggregator)
        assert _get_cursor(database) == tokens[1].identifier
        retry_missing_token_details(chains_aggregator)
        assert _get_cursor(database) == ''  # only the last token was left, so it wrapped
        retry_missing_token_details(chains_aggregator)
        assert _get_cursor(database) == ''  # all are marked now, so none is picked by name

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
        token = _token(address)
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


@pytest.mark.parametrize('poison_range', [slice(2, 4), slice(1, 4)])
def test_tokens_failing_on_their_own_do_not_look_like_an_outage(
        database: DBHandler,
        poison_range: slice,
) -> None:
    """Tokens that each break their own query count an attempt and the rest is still found. Next
    to each other, enough of them reach the limit of failures in a row: a token that answered
    in the run is then queried again, and as it answers the nodes are up and the run goes on."""
    addresses = [_address(i) for i in range(1, 7)]
    poison = addresses[poison_range]
    for address in addresses:
        mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=address, saved=None)

    def infos(queried: list[ChecksumEvmAddress]) -> dict[str, Any]:
        if any(x in poison for x in queried):
            raise RemoteError('out of gas')
        return {address: _info('Found') for address in queried}

    chains_aggregator, node_inquirer = _chains_aggregator(database=database, infos=infos)
    with patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_CHUNK_SIZE', 2):
        retry_missing_token_details(chains_aggregator)

    assert _marks() == dict.fromkeys(poison, (1, None))  # counted, and the rest was found
    for address in set(addresses) - set(poison):
        assert _details(_token(address)) == ('Found', 'SYM', 6)

    if len(poison) == 2:  # below the limit: no probe, and the chunks after them are queried
        assert [x.args[0] for x in node_inquirer.get_multiple_erc20_contracts_info.call_args_list] == [  # noqa: E501
            addresses[:2], addresses[2:4], addresses[2:3], addresses[3:4], addresses[4:],
        ]


def test_decoder_edit_does_not_stop_missing_details_from_being_fixed(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """A token created while only decimals() failed gets the default decimals and a mark that
    remembers that only they are missing, so the symbol given by the caller is kept. A decoder
    giving it a name later does not count as an edit of the decimals, so the retry still fixes
    them and keeps the decoder's name. The stale info cached when the token was first seen is
    dropped by the retry query."""
    token = _see_token(
        database, ethereum_inquirer, address := _address(1),
        multicall={'return_value': _output(decimals=None)}, raises=None, symbol='GIV',
    )
    assert token is not None
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
        given: dict[str, Any],
) -> None:
    """Every collectible id is a new token, so an nft seen while the nodes fail is created
    with empty details, or the given ones, instead of dropping its events. It is not marked."""
    token = _see_token(
        database, ethereum_inquirer, _address(1), raises=None,
        token_kind=TokenKind.ERC721, collectible_id='1', **given,
    )

    assert token is not None
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
    decimals_only = _see_token(
        database, ethereum_inquirer, _address(1),
        multicall={'return_value': _output(decimals=None)}, raises=None, symbol='GIV',
    )
    both = _see_token(
        database, ethereum_inquirer, _address(2),
        multicall={'return_value': _output(decimals=None, symbol=None)}, raises=None, **FALLBACKS,
    )
    assert decimals_only is not None
    assert both is not None
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

    save_found_token_details = details_retry.save_found_token_details

    def save_with_hook(*args: Any, **kwargs: Any) -> Any:
        with patch.object(details_retry, '_read_token_details', side_effect=read_then_start):
            return save_found_token_details(*args, **kwargs)

    with patch('rotkehlchen.tasks.assets.save_found_token_details', side_effect=save_with_hook):
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
    """The redecode of a token whose details changed is recorded in the same transaction that
    writes them, so the mark can go at once. The user DB only saves that it applied it after
    flagging the transactions, so a stop in between makes the next run flag them again, even if
    the nodes don't answer anymore."""
    token = _create_placeholder(database, 1)
    if marked:
        mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=token.evm_address, saved=(token.identifier, None, 18))  # noqa: E501
    chains_aggregator, _ = _chains_aggregator(database=database, infos=lambda _: {token.evm_address: _info('Found')})  # noqa: E501
    with (
        patch.object(details_retry, '_flag_token_transactions', side_effect=RemoteError('interrupted')),  # noqa: E501
        pytest.raises(RemoteError),
    ):
        retry_missing_token_details(chains_aggregator)

    assert _details(token) == ('Found', 'SYM', 6)  # written already
    assert _marks() == {}  # nothing is missing
    assert _redecodes() == {token.evm_address: False}
    assert _applied_seq(database) == 0  # pending

    chains_aggregator, _ = _chains_aggregator(database=database, infos=RemoteError('down'))
    with patch.object(details_retry, '_flag_token_transactions') as flag:
        retry_missing_token_details(chains_aggregator)
        retry_missing_token_details(chains_aggregator)

    assert [x.kwargs['tokens'] for x in flag.call_args_list] == [{token.evm_address: False}]
    assert _applied_seq(database) == _redecode_seqs()[token.evm_address]


def test_created_tokens_are_redecoded_in_a_single_scan(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """The logs have no index on their address, so the tokens of a run that could not be created
    before, whether created by the retry, added since or given up, are all searched for with one
    scan per chain. Their marks and attempts are cleared in the transaction that records their
    redecode, so an interrupted scan is done again by the next run."""
    created, added, given_up = _address(1), _address(2), _address(3)
    for address in (created, added):
        mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=address, saved=None)

    _give_up(given_up, saved=None)  # before it could be created
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
    with patch.object(details_retry, '_find_transactions', side_effect=RemoteError('interrupted')) as scan:  # noqa: E501
        with pytest.raises(RemoteError):
            retry_missing_token_details(chains_aggregator)

        assert _marks() == {}
        assert _redecodes() == dict.fromkeys((created, added, given_up), True)
        assert _applied_seq(database) == 0

        scan.reset_mock(side_effect=True)
        scan.return_value = {}
        retry_missing_token_details(chains_aggregator)

    logs_scans = [x.kwargs['values'] for x in scan.call_args_list if 'evmtx_receipt_logs' in x.kwargs['select_query']]  # noqa: E501
    assert [sorted(x) for x in logs_scans] == [sorted([created, added, given_up])]
    assert _applied_seq(database) == max(_redecode_seqs().values())
    assert _details(_token(created)) == ('Chain', 'SYM', 6)


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


@pytest.mark.parametrize(('sightings', 'given', 'missing', 'details'), [
    ([{'name': 'Given Name', 'decimals': 2}], {'name': 'Given Name', 'decimals': 2}, {'symbol'}, ('Given Name', 'ONCHAIN', 2)),  # noqa: E501
    # a later sighting that gives nothing, as a plain transfer decoder, keeps what was given
    ([{'name': 'Given Name'}, {}, {'symbol': 'GIV'}], {'name': 'Given Name', 'symbol': 'GIV'}, {'decimals'}, ('Given Name', 'GIV', 6)),  # noqa: E501
])
def test_given_details_are_kept_when_creation_is_deferred(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        sightings: list[dict[str, Any]],
        given: dict[str, Any],
        missing: set[str],
        details: tuple[str, str, int],
) -> None:
    """The details supplied by the callers of a token that can't be created because the query
    failed are kept in its mark, across sightings, and win over the on chain ones when it is
    created. Only the ones that were not supplied are queried."""
    for sighting in sightings:
        _see_token(database, ethereum_inquirer, address := _address(1), **sighting)

    [mark] = get_token_details_retry_marks(chain_id=ChainID.ETHEREUM, limit=10)
    assert (mark.saved, mark.given, mark.missing) == (None, given, frozenset(missing))
    chains_aggregator, _ = _chains_aggregator(database=database, node_inquirer=ethereum_inquirer)
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output(decimals=6, symbol='ONCHAIN', name='On Chain')):  # noqa: E501
        retry_missing_token_details(chains_aggregator)

    assert _details(_token(address)) == details
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


@pytest.mark.parametrize('persisted', [True, False])
def test_stale_mark_does_not_recreate_bookkeeping(database: DBHandler, persisted: bool) -> None:
    """Counting an attempt or postponing writes the mark the run loaded before querying. If the
    token was deleted meanwhile, which removes its bookkeeping, or marked again by a decoder,
    the stale mark must not be written back, nor become a permanent given up entry."""
    token = _create_placeholder(database, 1)
    saved = (token.identifier, '', 18)
    if persisted:
        mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=token.evm_address, saved=saved)
        stale = get_token_details_retry_mark(chain_id=ChainID.ETHEREUM, address=token.evm_address)
        assert stale is not None
        stale = stale._replace(attempts=TOKEN_DETAILS_RETRY_MAX_ATTEMPTS - 1)  # would give up
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            details_retry._write_mark(write_cursor=write_cursor, mark=stale)
    else:  # a placeholder retried without a mark
        stale = TokenDetailsRetryMark(chain_id=ChainID.ETHEREUM, address=token.evm_address, attempts=TOKEN_DETAILS_RETRY_MAX_ATTEMPTS - 1, saved=saved, persisted=False)  # noqa: E501

    def bookkeeping() -> tuple[bool, dict[ChecksumEvmAddress, tuple[int, Any]]]:
        return is_token_details_retry_given_up(ChainID.ETHEREUM, token.evm_address), _marks()

    GlobalDBHandler.delete_asset_by_identifier(token.identifier)
    AssetResolver.clean_memory_cache(token.identifier)
    count_token_details_retry_attempt(stale)
    postpone_token_details_retry([stale])
    assert bookkeeping() == (False, {})

    # seen again by a decoder while its query fails, so marked as a token not created
    mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=token.evm_address, saved=None)
    count_token_details_retry_attempt(stale)
    postpone_token_details_retry([stale])
    assert bookkeeping() == (False, {token.evm_address: (0, None)})

    current = get_token_details_retry_mark(chain_id=ChainID.ETHEREUM, address=token.evm_address)
    assert current is not None
    count_token_details_retry_attempt(current)  # the current mark still counts
    assert bookkeeping() == (False, {token.evm_address: (1, None)})


@pytest.mark.parametrize(('decoder_given', 'raises', 'details', 'marks'), [
    ({'name': 'Decoder Name', 'decimals': 2}, TokenQueryFailed, ('Decoder Name', 'ONCHAIN', 2), {}),  # noqa: E501
    # created with fallbacks: its new mark tracks the details only they gave, so it must stay
    (FALLBACKS, None, ('Fallback', 'FB', 18), {_address(1): (0, ('Fallback', 'FB', 18))}),
])
def test_token_seen_by_a_decoder_while_querying(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        decoder_given: dict[str, Any],
        raises: type[Exception] | None,
        details: tuple[str, str, int],
        marks: dict[ChecksumEvmAddress, tuple[int, Any]],
) -> None:
    """A decoder can see a token that could not be created while the retry is querying it. The
    mark is read again right before creating, so what it gave wins, and the transactions that
    skipped the token are redecoded either way without losing the mark it may have created."""
    _see_token(database, ethereum_inquirer, address := _address(1))

    def query(*args: Any, **kwargs: Any) -> list[tuple[bool, bytes]]:
        _see_token(database, ethereum_inquirer, address, raises=raises, **decoder_given)
        return _output(decimals=6, symbol='ONCHAIN', name='On Chain')

    chains_aggregator, _ = _chains_aggregator(database=database, node_inquirer=ethereum_inquirer)
    with patch.object(ethereum_inquirer, 'multicall_2', side_effect=query):
        retry_missing_token_details(chains_aggregator)

    assert _redecodes() == {address: True}
    assert _details(_token(address)) == details
    assert _marks() == marks


def test_settling_a_created_token_keeps_the_mark_of_one_deleted_and_seen_again(
        database: DBHandler,
) -> None:
    """The mark of a token not created when marked is removed once the token exists, recording
    the redecode of the transactions that skipped it. If the token was deleted and seen again
    with its query failing, the new mark of the token that does not exist is the only way to
    recover it, so it is kept and nothing is recorded."""
    token = _create_placeholder(database, 1)
    GlobalDBHandler.delete_asset_by_identifier(token.identifier)
    AssetResolver.clean_memory_cache(token.identifier)  # what the endpoints do
    mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=token.evm_address, saved=None)
    settle_created_token_marks(chain_id=ChainID.ETHEREUM, addresses=[token.evm_address])
    assert _marks() == {token.evm_address: (0, None)}
    assert _redecodes() == {}

    _create_placeholder(database, 1)  # exists now: the mark is the one of a created token
    settle_created_token_marks(chain_id=ChainID.ETHEREUM, addresses=[token.evm_address])
    assert _marks() == {}
    assert _redecodes() == {token.evm_address: True}


def test_marked_placeholder_outside_the_marks_page_keeps_its_mark(database: DBHandler) -> None:
    """A placeholder that has a mark is retried with that mark, also when the mark is beyond
    the page of marks loaded for the chain, instead of with a fresh one that has no attempts
    and has every detail considered missing."""
    token = _create_placeholder(database, 1)
    mark_token_details_retry(
        chain_id=ChainID.ETHEREUM,
        address=token.evm_address,
        saved=(token.identifier, None, 18),
        missing=frozenset({'symbol'}),
    )
    count_token_details_retry_attempt(get_token_details_retry_marks(ChainID.ETHEREUM, 1)[0])
    for idx in range(2, 5):  # older marks fill the page before the one of the placeholder
        mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=_address(idx), saved=None)
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            write_cursor.execute('UPDATE unique_cache SET last_queried_ts=? WHERE key LIKE ?', (idx, f'%{_address(idx)}'))  # noqa: E501

    chains_aggregator, node_inquirer = _chains_aggregator(database=database, infos=lambda _: {})
    with patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_BATCH_SIZE', 2):
        retry_missing_token_details(chains_aggregator)

    queried = [a for call in node_inquirer.get_multiple_erc20_contracts_info.call_args_list for a in call.args[0]]  # noqa: E501
    assert queried.count(token.evm_address) <= 1
    mark = next(m for m in get_token_details_retry_marks(ChainID.ETHEREUM, 100) if m.address == token.evm_address)  # noqa: E501
    assert mark.missing == frozenset({'symbol'})  # not reset to every detail
    assert mark.attempts >= 1  # kept the attempt that was counted


def test_renamed_placeholder_keeps_its_other_details_retryable(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """A decoder giving a name to an unmarked placeholder takes it out of the ones the task
    picks by name, so the details that were not given have to be marked for retrying."""
    token = _create_placeholder(database, 1)
    assert _marks() == {}

    get_or_create_evm_token(
        userdb=database,
        evm_address=token.evm_address,
        chain_id=ChainID.ETHEREUM,
        name='Decoder Name',
        evm_inquirer=ethereum_inquirer,
    )

    assert _details(token)[0] == 'Decoder Name'
    assert _marks() == {token.evm_address: (0, ('Decoder Name', '', 18))}
    assert next(iter(get_token_details_retry_marks(ChainID.ETHEREUM, 1))).missing == frozenset({'symbol', 'decimals'})  # noqa: E501


def test_asset_update_replacing_a_token_clears_its_retry_bookkeeping(
        database: DBHandler,
        tmp_path: Path,
) -> None:
    """The asset update replaces the evm tokens in bulk, so the given up key of a token that
    it removes has to go too, or the token seen again could not be marked."""
    from rotkehlchen.globaldb.asset_updates.manager import _replace_assets_from_db

    kept, removed = _create_placeholder(database, 1), _create_placeholder(database, 2)
    for token in (kept, removed):
        stop_token_details_retry(chain_id=ChainID.ETHEREUM, address=token.evm_address)

    source = tmp_path / 'source.db'
    with GlobalDBHandler().conn.read_ctx() as cursor:
        cursor.execute(f"VACUUM INTO '{source}'")
    import sqlite3
    with sqlite3.connect(source) as connection:  # the update drops one of the tokens
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute('DELETE FROM assets WHERE identifier=?', (removed.identifier,))

    _replace_assets_from_db(connection=GlobalDBHandler().conn, sourcedb_path=source)

    assert is_token_details_retry_given_up(ChainID.ETHEREUM, removed.evm_address) is False
    assert is_token_details_retry_given_up(ChainID.ETHEREUM, kept.evm_address) is True


def test_renaming_a_marked_placeholder_keeps_its_mark(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """The mark of a placeholder says which details are protected, so a rename by a decoder
    must not make them retryable again."""
    token = _create_placeholder(database, 1, decimals=6)
    mark_token_details_retry(
        chain_id=ChainID.ETHEREUM,
        address=token.evm_address,
        saved=(token.identifier, None, 6),
        missing=frozenset({'symbol'}),
    )

    get_or_create_evm_token(
        userdb=database,
        evm_address=token.evm_address,
        chain_id=ChainID.ETHEREUM,
        name='Decoder Name',
        evm_inquirer=ethereum_inquirer,
    )

    assert next(iter(get_token_details_retry_marks(ChainID.ETHEREUM, 1))).missing == frozenset({'symbol'})  # noqa: E501


def test_asset_update_changing_a_token_keeps_its_retry_mark(
        database: DBHandler,
        tmp_path: Path,
) -> None:
    """An update that corrects a retained token keeps its pending recovery, which is what
    flags its transactions for redecoding."""
    import sqlite3

    from rotkehlchen.globaldb.asset_updates.manager import _replace_assets_from_db

    token = _create_placeholder(database, 1)
    mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=token.evm_address, saved=(token.identifier, None, 18))  # noqa: E501
    source = tmp_path / 'source.db'
    with GlobalDBHandler().conn.read_ctx() as cursor:
        cursor.execute(f"VACUUM INTO '{source}'")
    with sqlite3.connect(source) as connection:
        connection.execute('UPDATE evm_tokens SET decimals=6 WHERE identifier=?', (token.identifier,))  # noqa: E501

    _replace_assets_from_db(connection=GlobalDBHandler().conn, sourcedb_path=source)

    assert set(_marks()) == {token.evm_address}


def test_lone_token_failing_on_its_own_is_given_up_after_many_postponed_runs(
        database: DBHandler,
) -> None:
    """With no other token to answer, a token that always fails looks like an outage, so a run
    only postpones it. After TOKEN_DETAILS_RETRY_MAX_POSTPONES runs it counts an attempt, and
    after enough of those it is given up."""
    mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=(address := _address(1)), saved=None)  # noqa: E501
    chains_aggregator, _ = _chains_aggregator(database=database, infos=RemoteError('fails'))

    for _ in range(TOKEN_DETAILS_RETRY_MAX_POSTPONES - 1):
        retry_missing_token_details(chains_aggregator)
    assert _marks() == {address: (0, None)}  # still not an attempt

    retry_missing_token_details(chains_aggregator)
    assert _marks() == {address: (1, None)}

    for _ in range((TOKEN_DETAILS_RETRY_MAX_ATTEMPTS - 1) * TOKEN_DETAILS_RETRY_MAX_POSTPONES):
        retry_missing_token_details(chains_aggregator)
    assert _marks() == {}
    assert is_token_details_retry_given_up(ChainID.ETHEREUM, address) is True


@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address()]])
def test_redecode_waits_for_the_decoder(
        database: DBHandler,
        ethereum_accounts: list[ChecksumEvmAddress],
        ethereum_inquirer: EthereumInquirer,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
) -> None:
    """A decoder may have loaded the old details of a token without having saved the
    transaction as decoded yet. Flagging it then would do nothing, and the decoder would save
    events calculated with the old details. So the redecode waits for the lock that every
    decoding holds, and flags the transaction once the decoder saved it."""
    tx_hash = _add_incoming_transfer(database, user=ethereum_accounts[0], token_address=(token_address := _address(1)))  # noqa: E501
    _see_token(  # created with the default decimals
        database, ethereum_inquirer, token_address,
        multicall={'return_value': _output(decimals=None)}, raises=None,
    )
    chains_aggregator, _ = _chains_aggregator(database=database, node_inquirer=ethereum_inquirer)
    chains_aggregator.get_evm_manager.return_value.transactions_decoder = ethereum_transaction_decoder  # noqa: E501
    decoder_lock = ethereum_transaction_decoder.undecoded_tx_query_lock
    decoder_lock.acquire()  # a decoder is decoding the transaction
    try:
        with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output()):
            task = spawn(retry_missing_token_details, chains_aggregator)
            time.sleep(0.5)  # enough for it to finish if nothing stopped it

        assert task.dead is False
        assert _details(_token(token_address)) == ('Token', 'TKN', 6)  # written already
        # what the decoder holding the lock saves, after having loaded the old details
        ethereum_transaction_decoder.decode_transaction_hashes(ignore_cache=False, tx_hashes=[tx_hash])  # noqa: E501
        assert _is_decoded(database, tx_hash) is True
    finally:
        decoder_lock.release()

    wait([task])
    assert exception_of(task) is None
    assert _is_decoded(database, tx_hash) is False  # flagged after the decoder saved it
    assert ethereum_transaction_decoder.get_and_decode_undecoded_transactions() == [tx_hash]
    assert _transfers(database, tx_hash) == [(
        HistoryEventType.RECEIVE,
        HistoryEventSubType.NONE,
        evm_address_to_identifier(address=token_address, chain_id=ChainID.ETHEREUM),
        FVal('1.5'),
    )]


@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address()]])
def test_redecode_reaches_every_user(
        database: DBHandler,
        ethereum_accounts: list[ChecksumEvmAddress],
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        user_data_dir: Path,
        db_password: str,
        sql_vm_instructions_cb: int,
) -> None:
    """The bookkeeping is in the global DB, shared by the users of the machine, while the
    transactions of each are in their own user DB. A token fixed by the run of another user
    still has its transactions redecoded for this user, when this user next applies the
    recorded redecodes."""
    token = _create_placeholder(database, 1)  # with the default decimals
    tx_hash = _add_incoming_transfer(database, user=ethereum_accounts[0], token_address=token.evm_address)  # noqa: E501
    ethereum_transaction_decoder.decode_transaction_hashes(ignore_cache=False, tx_hashes=[tx_hash])
    assert [x[3] for x in _transfers(database, tx_hash)] == [FVal('1.5E-12')]

    (other_user_dir := user_data_dir.parent / 'other_user').mkdir()
    with mock_dbhandler_sync_globaldb_assets():
        other_db = DBHandler(
            user_data_dir=other_user_dir,
            password=db_password,
            msg_aggregator=MessagesAggregator(),
            initial_settings=None,
            sql_vm_instructions_cb=sql_vm_instructions_cb,
            resume_from_backup=False,
        )
    try:
        other_chains_aggregator, _ = _chains_aggregator(database=other_db, infos=lambda _: {token.evm_address: _info('Found')})  # noqa: E501
        retry_missing_token_details(other_chains_aggregator)
        assert _applied_seq(other_db) == _redecode_seqs()[token.evm_address]
    finally:
        other_db.logout()

    assert _details(token) == ('Found', 'SYM', 6)
    assert _is_decoded(database, tx_hash) is True  # not applied to this user yet
    chains_aggregator, _ = _chains_aggregator(database=database)
    chains_aggregator.get_evm_manager.return_value.transactions_decoder = ethereum_transaction_decoder  # noqa: E501
    apply_token_details_redecodes(chains_aggregator)

    assert ethereum_transaction_decoder.get_and_decode_undecoded_transactions() == [tx_hash]
    assert [x[3] for x in _transfers(database, tx_hash)] == [FVal('1.5')]


@pytest.mark.parametrize('before_creation', [False, True])
def test_editing_a_given_up_token_redecodes_it(
        database: DBHandler,
        before_creation: bool,
) -> None:
    """A token given up when its attempts ran out may have events calculated with defaults or
    fallbacks, which its given up entry records. A user edit replacing that entry records a
    redecode of its transactions, searching its logs if it was given up before it could be
    created. Nothing is pending afterwards, so a second edit records nothing."""
    address = _address(1)
    if not before_creation:
        token = _create_placeholder(database, 1)
    saved = None if before_creation else (token.identifier, None, 18)
    _give_up(address, saved=saved)
    assert is_token_details_retry_given_up(chain_id=ChainID.ETHEREUM, address=address)
    if before_creation:  # added since, and edited before a run noticed it
        _create_placeholder(database, 1)

    assert stop_token_details_retry(chain_id=ChainID.ETHEREUM, address=address) is True
    assert _redecodes() == {address: before_creation}
    seqs = _redecode_seqs()
    assert stop_token_details_retry(chain_id=ChainID.ETHEREUM, address=address) is False
    assert _redecode_seqs() == seqs


def test_given_up_token_corrected_by_an_asset_update_is_redecoded(
        database: DBHandler,
        tmp_path: Path,
) -> None:
    """A token given up with details that are only defaults is not queried again, but an asset
    update may correct them. Its events were calculated with the defaults, so a run records a
    redecode of its transactions, once. A change of a detail that was not missing does not."""
    import sqlite3

    from rotkehlchen.globaldb.asset_updates.manager import _replace_assets_from_db

    token = _create_placeholder(database, 1, decimals=6)
    _give_up(token.evm_address, saved=(token.identifier, None, 6), missing=frozenset({'symbol'}))
    chains_aggregator, _ = _chains_aggregator(database=database, infos=lambda _: {})

    def update(statement: str) -> None:
        source = tmp_path / f'source_{statement.split()[1]}.db'  # the updated table
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(f"VACUUM INTO '{source}'")
        with sqlite3.connect(source) as connection:
            connection.execute(statement, (token.identifier,))
        _replace_assets_from_db(connection=GlobalDBHandler().conn, sourcedb_path=source)
        AssetResolver.clean_memory_cache(token.identifier)

    update("UPDATE assets SET name='Updated Name' WHERE identifier=?")
    retry_missing_token_details(chains_aggregator)
    assert _redecodes() == {}

    update("UPDATE common_asset_details SET symbol='UPD' WHERE identifier=?")
    retry_missing_token_details(chains_aggregator)
    assert _redecodes() == {token.evm_address: False}
    seqs = _redecode_seqs()
    retry_missing_token_details(chains_aggregator)
    assert _redecode_seqs() == seqs  # recorded once
    assert is_token_details_retry_given_up(chain_id=ChainID.ETHEREUM, address=token.evm_address)


def test_marked_token_corrected_meanwhile_is_redecoded_without_the_nodes(
        database: DBHandler,
) -> None:
    """A marked token whose missing decimals someone else corrected, for example an asset
    update, had its events calculated with the defaults. A run settles it before querying, so
    the redecode is recorded and the decimals stop being missing even if the nodes never answer
    for it, instead of the token running out of attempts with stale events."""
    token = _create_placeholder(database, 1)
    mark_token_details_retry(
        chain_id=ChainID.ETHEREUM,
        address=token.evm_address,
        saved=(token.identifier, None, 18),
        missing=frozenset({'symbol', 'decimals'}),
    )
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        write_cursor.execute('UPDATE evm_tokens SET decimals=6 WHERE identifier=?', (token.identifier,))  # noqa: E501
    AssetResolver.clean_memory_cache(token.identifier)

    chains_aggregator, _ = _chains_aggregator(database=database, infos=lambda _: {})
    retry_missing_token_details(chains_aggregator)

    assert _redecodes() == {token.evm_address: False}
    [mark] = get_token_details_retry_marks(chain_id=ChainID.ETHEREUM, limit=10)
    assert (mark.saved, mark.missing) == ((token.identifier, None, 6), frozenset({'symbol'}))
    assert mark.attempts == 1  # the symbol still came back missing
