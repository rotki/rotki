"""Tests for querying again the details of tokens that are missing them.

The seam: when the details of an erc20 token can't be fully queried while it is first seen,
_get_or_create_token marks it in the global DB cache, and records the transaction if the
token could not be created at all. retry_missing_token_details picks the marked tokens and the
ones whose name is their identifier, asks the node inquirer of their chain for the details in
chunks and only saves complete details over a token that nobody else changed in the meantime.
Tokens created that way get their recorded transactions redecoded.
"""
from contextlib import nullcontext
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest
from eth_abi import encode
from eth_utils import to_checksum_address

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.details_retry import (
    TOKEN_DETAILS_RETRY_MAX_ATTEMPTS,
    get_token_details_retry_marks,
    get_token_retry_txs,
    mark_token_details_retry,
    record_token_retry_tx,
)
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.utils import (
    TokenEncounterInfo,
    edit_token_and_clean_cache,
    get_or_create_evm_token,
)
from rotkehlchen.chain.evm.constants import ERC20_PROPERTIES, ERC20_PROPERTIES_CALLDATA
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.concurrency import wait
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
    _get_tokens_missing_details,
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
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
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


def test_details_are_updated_only_when_found(database: DBHandler) -> None:
    updated, unconformant = (_create_placeholder(database, i) for i in (1, 2))
    chains_aggregator, node_inquirer = _chains_aggregator(
        database=database,
        infos=lambda addresses: {updated.evm_address: _info('Updated Token')},
    )

    retry_missing_token_details(chains_aggregator)

    node_inquirer.get_multiple_erc20_contracts_info.assert_called_once()
    assert _details(updated) == ('Updated Token', 'SYM', 6)
    assert _details(unconformant) == (unconformant.identifier, '', 18)
    assert _get_cursor(database) == ''  # reached the end
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.LAST_TOKEN_DETAILS_RETRY_TS,
        ) is not None


def test_token_with_null_name_is_retried(database: DBHandler) -> None:
    """Older versions saved a NULL name when repairing a token failed. It shows the
    identifier as name too, so it has to be picked like the other placeholders"""
    token = _create_placeholder(database, 1)
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        write_cursor.execute('UPDATE assets SET name=NULL WHERE identifier=?', (token.identifier,))
    AssetResolver.clean_memory_cache(token.identifier)
    assert EvmToken(token.identifier).name == token.identifier
    chains_aggregator, _ = _chains_aggregator(
        database=database,
        infos=lambda addresses: {token.evm_address: _info('Found')},
    )

    retry_missing_token_details(chains_aggregator)

    assert _details(token) == ('Found', 'SYM', 6)


def test_partial_details_keep_the_token_retryable(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """A placeholder with the right decimals whose name() works but decimals() fails must
    keep its decimals and be picked again"""
    token = _create_placeholder(database, 1, decimals=6)
    chains_aggregator, _ = _chains_aggregator(database=database, node_inquirer=ethereum_inquirer)

    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output(decimals=None)):
        retry_missing_token_details(chains_aggregator)

    assert _details(token) == (token.identifier, '', 6)
    assert _get_tokens_missing_details(chain_ids=[ChainID.ETHEREUM], after_identifier='') == [
        (token.identifier, ChainID.ETHEREUM, token.evm_address),
    ]


@pytest.mark.parametrize('marked', [False, True])
def test_token_changed_while_querying_is_not_overwritten(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        marked: bool,
) -> None:
    """A user edit or asset update that happens while the details are queried wins"""
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

    def edit_while_querying(addresses: list[ChecksumEvmAddress]) -> dict[str, Any]:
        edit_token_and_clean_cache(
            token=EvmToken(token.identifier),
            name='User Name',
            symbol='USR',
            decimals=8,
            started=None,
            chain_inquirer=None,
        )
        return {token.evm_address: _info('Queried')}

    chains_aggregator, _ = _chains_aggregator(database=database, infos=edit_while_querying)
    retry_missing_token_details(chains_aggregator)

    assert _details(token) == ('User Name', 'USR', 8)
    assert _marks() == {}  # nothing to retry, the token was fixed by someone else


@pytest.mark.parametrize('fallbacks', [False, True])
def test_query_failure_at_creation_is_retried(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        fallbacks: bool,
) -> None:
    """A token whose query failed is marked, with or without fallbacks, and gets the real
    details once the nodes answer"""
    with (
        patch.object(ethereum_inquirer, 'multicall_2', side_effect=RemoteError('down')),
        pytest.raises(TokenQueryFailed) if not fallbacks else nullcontext(),
    ):
        get_or_create_evm_token(
            userdb=database,
            evm_address=(address := _address(1)),
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
            fallback_name='Fallback' if fallbacks else None,
            fallback_symbol='FB' if fallbacks else None,
            fallback_decimals=18 if fallbacks else None,
        )
    assert _marks() == {address: (0, ('Fallback', 'FB', 18) if fallbacks else None)}

    chains_aggregator, _ = _chains_aggregator(database=database, node_inquirer=ethereum_inquirer)
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output()):
        retry_missing_token_details(chains_aggregator)

    token = EvmToken(evm_address_to_identifier(address=address, chain_id=ChainID.ETHEREUM))
    assert _details(token) == ('Token', 'TKN', 6)
    assert _marks() == {}


def test_partial_details_at_creation(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """Fallbacks only fill the details the chain did not return, the token is marked and
    the mark is dropped after the attempts run out"""
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output(name=None)):
        token = get_or_create_evm_token(
            userdb=database,
            evm_address=_address(1),
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
            fallback_name='Fallback',
            fallback_symbol='FB',
            fallback_decimals=18,
        )
    assert _details(token) == ('Fallback', 'TKN', 6)
    assert _marks() == {token.evm_address: (0, ('Fallback', 'TKN', 6))}

    chains_aggregator, _ = _chains_aggregator(database=database, node_inquirer=ethereum_inquirer)
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output(name=None)) as multicall:  # noqa: E501
        for attempt in range(1, TOKEN_DETAILS_RETRY_MAX_ATTEMPTS + 1):
            retry_missing_token_details(chains_aggregator)
            assert _marks() == (
                {token.evm_address: (attempt, ('Fallback', 'TKN', 6))}
                if attempt < TOKEN_DETAILS_RETRY_MAX_ATTEMPTS else {}
            )

        retry_missing_token_details(chains_aggregator)  # not queried anymore

    assert multicall.call_count == TOKEN_DETAILS_RETRY_MAX_ATTEMPTS
    assert _details(token) == ('Fallback', 'TKN', 6)


def test_given_up_token_keeps_what_it_has_and_is_not_retried(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """When the attempts run out nothing is deleted: the recorded transactions stay, so they
    are redecoded if the token is added later, and the token is never retried again, even
    when it is seen in another transaction"""
    def see_token(tx_hash: EVMTxHash) -> None:
        with (
            patch.object(ethereum_inquirer, 'multicall_2', return_value=_output(name=None)),
            pytest.raises(NotERC20Conformant),
        ):
            get_or_create_evm_token(
                userdb=database,
                evm_address=address,
                chain_id=ChainID.ETHEREUM,
                evm_inquirer=ethereum_inquirer,
                encounter=TokenEncounterInfo(tx_ref=tx_hash),
            )
        ethereum_inquirer.contract_info_erc20_cache.remove(address)

    address = _address(1)
    see_token(first_tx := make_evm_tx_hash())
    chains_aggregator, node_inquirer = _chains_aggregator(database=database, infos=lambda addresses: {})  # noqa: E501
    for _ in range(TOKEN_DETAILS_RETRY_MAX_ATTEMPTS):
        retry_missing_token_details(chains_aggregator)
    assert _marks() == {}
    assert node_inquirer.get_multiple_erc20_contracts_info.call_count == TOKEN_DETAILS_RETRY_MAX_ATTEMPTS  # noqa: E501

    see_token(second_tx := make_evm_tx_hash())  # seen again after giving up
    retry_missing_token_details(chains_aggregator)
    assert _marks() == {}  # not marked again
    assert node_inquirer.get_multiple_erc20_contracts_info.call_count == TOKEN_DETAILS_RETRY_MAX_ATTEMPTS  # noqa: E501
    with database.conn.read_ctx() as cursor:
        assert {x.tx_hash for x in get_token_retry_txs(cursor)} == {first_tx, second_tx}

    get_or_create_evm_token(  # added later, for example by the user
        userdb=database,
        evm_address=address,
        chain_id=ChainID.ETHEREUM,
        name='Added',
        symbol='ADD',
        decimals=6,
    )
    decoder = chains_aggregator.get_evm_manager.return_value.transactions_decoder
    retry_missing_token_details(chains_aggregator)
    assert {x.kwargs['tx_hashes'][0] for x in decoder.decode_and_get_transaction_hashes.call_args_list} == {first_tx, second_tx}  # noqa: E501


def test_contract_without_methods_is_not_marked(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """A contract that has none of the methods is not an erc20 token, so it is not retried"""
    with (
        patch.object(ethereum_inquirer, 'multicall_2', return_value=[(False, b'')] * 3),
        pytest.raises(NotERC20Conformant) as e,
    ):
        get_or_create_evm_token(
            userdb=database,
            evm_address=_address(1),
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
            encounter=None,
        )

    assert not isinstance(e.value, TokenQueryFailed)
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
        with database.conn.read_ctx() as cursor:
            assert [(x.address, x.tx_hash) for x in get_token_retry_txs(cursor)] == [
                (token_address, tx_hash),
            ]
    else:  # created with the default decimals
        assert transfers() == [(
            HistoryEventType.SPEND,
            HistoryEventSubType.NONE,
            token_identifier,
            FVal('1.5E-12'),
        )]
        assert _marks() == {token_address: (0, ('Token', 'TKN', 18))}

    chains_aggregator, _ = _chains_aggregator(database=database, node_inquirer=ethereum_inquirer)
    chains_aggregator.get_evm_manager.return_value.transactions_decoder = ethereum_transaction_decoder  # noqa: E501
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output()):
        retry_missing_token_details(chains_aggregator)

    assert transfers() == [(
        HistoryEventType.SPEND,
        HistoryEventSubType.NONE,
        token_identifier,
        FVal('1.5'),  # 1500000 with the 6 decimals of the token
    )]
    with database.conn.read_ctx() as cursor:
        assert get_token_retry_txs(cursor) == []
    assert _marks() == {}


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


def test_remote_error_does_not_count_an_attempt(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    with patch.object(ethereum_inquirer, 'multicall_2', side_effect=RemoteError('down')), pytest.raises(TokenQueryFailed):  # noqa: E501
        get_or_create_evm_token(
            userdb=database,
            evm_address=(address := _address(1)),
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
        )

    chains_aggregator, _ = _chains_aggregator(database=database, infos=RemoteError('nodes down'))
    retry_missing_token_details(chains_aggregator)

    assert _marks() == {address: (0, None)}


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
    nodes_down = False

    def infos(addresses: list[ChecksumEvmAddress]) -> dict[str, Any]:
        nonlocal nodes_down
        calls.append(addresses)
        if nodes_down:
            raise RemoteError('nodes down')
        nodes_down = len(calls) == 1  # the nodes go down after the first chunk
        return {address: _info('Found') for address in addresses}

    chains_aggregator, _ = _chains_aggregator(database=database, infos=infos)
    with (
        patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_BATCH_SIZE', 4),
        patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_CHUNK_SIZE', 2),
    ):
        retry_missing_token_details(chains_aggregator)
        # the failed chunk was queried again one by one, which failed too
        assert calls[1:] == [
            [tokens[2].evm_address, tokens[3].evm_address],
            [tokens[2].evm_address],
            [tokens[3].evm_address],
        ]
        assert [EvmToken(x.identifier).name for x in tokens] == [
            'Found', 'Found', tokens[2].identifier, tokens[3].identifier, tokens[4].identifier,
        ]
        assert _get_cursor(database) == tokens[3].identifier

        nodes_down = False
        retry_missing_token_details(chains_aggregator)  # continues after the skipped tokens

    assert calls[-1] == [tokens[4].evm_address]
    assert EvmToken(tokens[4].identifier).name == 'Found'
    assert _get_cursor(database) == ''  # wrapped. The skipped ones come back in the next cycle


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
    with patch('rotkehlchen.assets.details_retry.ts_now', return_value=ts_now() + 100):
        retry_missing_token_details(chains_aggregator)

    assert [x.args[0] for x in node_inquirer.get_multiple_erc20_contracts_info.call_args_list] == [
        addresses,  # the chunk
        *([x] for x in addresses[:TOKEN_DETAILS_RETRY_MAX_FAILED_QUERIES]),  # one by one
    ]
    marks = get_token_details_retry_marks(chain_id=ChainID.ETHEREUM, limit=10)
    assert [x.address for x in marks] == addresses[3:] + addresses[:3]
    assert all(x.attempts == 0 for x in marks)


def test_spam_tokens_are_not_marked(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """Spam tokens are not worth querying again, whether they are known spam when seen or
    found to be spam after being marked"""
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=_output(name=None)):
        get_or_create_evm_token(
            userdb=database,
            evm_address=_address(1),
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
            protocol=SPAM_PROTOCOL,
            fallback_name='Fallback',
            fallback_symbol='FB',
            fallback_decimals=18,
        )
    with patch.object(  # detected as spam from the details that were returned
        ethereum_inquirer,
        'multicall_2',
        return_value=_output(decimals=None, symbol='claim at site.io'),
    ):
        get_or_create_evm_token(
            userdb=database,
            evm_address=_address(4),
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
        )
    with (
        patch.object(ethereum_inquirer, 'multicall_2', side_effect=RemoteError('down')),
        pytest.raises(TokenQueryFailed),
    ):
        get_or_create_evm_token(
            userdb=database,
            evm_address=_address(2),
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
            protocol=SPAM_PROTOCOL,
            encounter=TokenEncounterInfo(tx_ref=make_evm_tx_hash()),
        )
    assert _marks() == {}
    with database.conn.read_ctx() as cursor:
        assert get_token_retry_txs(cursor) == []

    spam = _create_placeholder(database, 3, protocol=SPAM_PROTOCOL)  # marked before found spam
    mark_token_details_retry(chain_id=ChainID.ETHEREUM, address=spam.evm_address, saved=(spam.identifier, '', 18))  # noqa: E501
    chains_aggregator, node_inquirer = _chains_aggregator(database=database, infos=lambda x: {})
    retry_missing_token_details(chains_aggregator)

    assert node_inquirer.get_multiple_erc20_contracts_info.call_count == 0
    assert _marks() == {}


def test_failing_redecodes_do_not_block_the_rest(database: DBHandler) -> None:
    """Transactions that fail to be redecoded move to the back of the queue"""
    token = get_or_create_evm_token(
        userdb=database,
        evm_address=_address(1),
        chain_id=ChainID.ETHEREUM,
        name='Token',
        symbol='TKN',
        decimals=6,
    )
    for tx_hash in (tx_hashes := [make_evm_tx_hash() for _ in range(3)]):
        record_token_retry_tx(
            database=database,
            chain_id=ChainID.ETHEREUM,
            address=token.evm_address,
            tx_hash=tx_hash,
        )

    decoded: list[EVMTxHash] = []

    def decode(tx_hashes: list[EVMTxHash], **kwargs: Any) -> list:
        if tx_hashes[0] in failing:
            raise RemoteError('receipt not found')
        decoded.extend(tx_hashes)
        return []

    failing = set(tx_hashes[:2])
    chains_aggregator, _ = _chains_aggregator(database=database, infos=lambda x: {})
    chains_aggregator.get_evm_manager.return_value.transactions_decoder.decode_and_get_transaction_hashes.side_effect = decode  # noqa: E501
    with patch('rotkehlchen.tasks.assets.TOKEN_DETAILS_RETRY_BATCH_SIZE', 2):
        retry_missing_token_details(chains_aggregator)
        assert decoded == []
        retry_missing_token_details(chains_aggregator)  # the failed ones went to the back

    assert decoded == [tx_hashes[2]]
    with database.conn.read_ctx() as cursor:
        assert [x.tx_hash for x in get_token_retry_txs(cursor)] == tx_hashes[1:2] + tx_hashes[:1]


def test_failing_redecode_is_tried_once_per_run(database: DBHandler) -> None:
    """A transaction recorded for two tokens that fails to be redecoded is not tried again
    in the same run, and stays recorded for both"""
    tx_hash = make_evm_tx_hash()
    for idx in (1, 2):
        token = get_or_create_evm_token(
            userdb=database,
            evm_address=_address(idx),
            chain_id=ChainID.ETHEREUM,
            name='Token',
            symbol='TKN',
            decimals=6,
        )
        record_token_retry_tx(
            database=database,
            chain_id=ChainID.ETHEREUM,
            address=token.evm_address,
            tx_hash=tx_hash,
        )

    chains_aggregator, _ = _chains_aggregator(database=database, infos=lambda x: {})
    (decode := chains_aggregator.get_evm_manager.return_value.transactions_decoder.decode_and_get_transaction_hashes).side_effect = RemoteError('receipt not found')  # noqa: E501
    retry_missing_token_details(chains_aggregator)

    assert decode.call_count == 1
    with database.conn.read_ctx() as cursor:
        assert {x.address for x in get_token_retry_txs(cursor)} == {_address(1), _address(2)}


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
    """Only tokens that returned all their details are in the result"""
    good, broken, partial = _address(1), _address(2), _address(3)
    output = _output() + [(False, b'')] * 3 + _output(decimals=None)
    with patch.object(ethereum_inquirer, 'multicall_2', return_value=output) as multicall:
        result = ethereum_inquirer.get_multiple_erc20_contracts_info([good, broken, partial])

    assert result == {good: {'decimals': 6, 'symbol': 'TKN', 'name': 'Token'}}
    assert len(multicall.call_args.kwargs['calls']) == 9
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
    output = _output() + [
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


@pytest.mark.parametrize('max_tasks_num', [5])
@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address()]])
def test_task_is_not_scheduled_while_history_is_fetched(task_manager: TaskManager) -> None:
    with task_manager.history_processing_coordinator.history_fetch():
        assert task_manager._maybe_retry_missing_token_details() is None

    assert (tasks := task_manager._maybe_retry_missing_token_details()) is not None
    wait(tasks)  # don't leave the spawned task running into other tests
