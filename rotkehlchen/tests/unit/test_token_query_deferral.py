"""Tests for leaving a transaction undecoded when a token query fails to reach the nodes.

The seam: while EVMTransactionDecoder._decode_transaction decodes a transaction, a token query
that raises TokenQueryFailed because of a RemoteError is recorded, and the decoder then writes
nothing for that transaction, records it as deferred in the PendingTransactionsTracker and
leaves it for the periodic decoding, which skips it until a cooldown passes. Explicit user
requests retry it right away, and after TOKEN_QUERY_DEFERRAL_MAX_DURATION it is decoded
anyway, as it was before the deferral existed.
"""
from contextlib import suppress
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import requests
from eth_abi import encode
from eth_utils import to_checksum_address

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import get_evm_token, get_or_create_evm_token
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_EVM_DECODING_OUTPUT
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.token_query_failures import track_token_query_failures
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.constants import TX_DECODED
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.pending_transactions import (
    TOKEN_QUERY_DEFERRAL_MAX_DURATION,
    TOKEN_QUERY_DEFERRAL_RETRY_AFTER,
)
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError, TokenQueryFailed
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response_with_result
from rotkehlchen.tests.utils.ethereum import txreceipt_to_data
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import (
    ChainID,
    EvmTransaction,
    SupportedBlockchain,
    Timestamp,
    TokenKind,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext, EvmDecodingOutput
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash

TOKEN_ADDRESS = to_checksum_address('0x' + '1' * 40)
FALLBACKS: dict[str, Any] = {'fallback_name': 'Fallback', 'fallback_symbol': 'FB', 'fallback_decimals': 18}  # noqa: E501
NODES_DOWN: dict[str, Any] = {'side_effect': RemoteError('nodes down')}


def _erc20_output(decimals: int = 6) -> list[tuple[bool, bytes]]:
    return [
        (True, encode(['uint8'], [decimals])),
        (True, encode(['string'], ['TKN'])),
        (True, encode(['string'], ['Token'])),
    ]


def _transfer_log(user: ChecksumEvmAddress, nft: bool = False) -> EvmTxReceiptLog:
    """A transfer of TOKEN_ADDRESS from the user. 1500000 units of an erc20, or nft id 5"""
    topics = [
        ERC20_OR_ERC721_TRANSFER,
        bytes(12) + bytes.fromhex(user[2:]),
        bytes(12) + bytes.fromhex(make_evm_address()[2:]),
    ]
    return EvmTxReceiptLog(
        log_index=1,
        data=b'' if nft else (1500000).to_bytes(32, 'big'),
        address=TOKEN_ADDRESS,
        topics=[*topics, (5).to_bytes(32, 'big')] if nft else topics,
    )


def _add_transaction(
        database: DBHandler,
        user: ChecksumEvmAddress,
        logs: list[EvmTxReceiptLog],
) -> EVMTxHash:
    transaction = EvmTransaction(
        tx_hash=(tx_hash := make_evm_tx_hash()),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1700000000),
        block_number=18000000,
        from_address=user,
        to_address=TOKEN_ADDRESS,
        value=0,
        gas=45000,
        gas_price=10000000000,
        gas_used=45000,
        input_data=b'',
        nonce=0,
    )
    with database.user_write() as write_cursor:
        DBEvmTx(database).add_transactions(write_cursor, [transaction], relevant_address=user)
        DBEvmTx(database).add_or_ignore_receipt_data(
            write_cursor,
            ChainID.ETHEREUM,
            txreceipt_to_data(EvmTxReceipt(
                tx_hash=tx_hash,
                chain_id=ChainID.ETHEREUM,
                contract_address=None,
                status=True,
                tx_type=0,
                logs=logs,
            )),
        )
    return tx_hash


def _transfers(database: DBHandler, tx_hash: EVMTxHash) -> list[tuple[str, FVal]]:
    """The events of the transaction other than the gas fee"""
    with database.conn.read_ctx() as cursor:
        return [
            (x.asset.identifier, x.amount)
            for x in DBHistoryEvents(database).get_history_events_internal(
                cursor=cursor,
                filter_query=EvmEventFilterQuery.make(tx_hashes=[tx_hash]),
            )
            if x.event_subtype != HistoryEventSubType.FEE
        ]


def _is_decoded(database: DBHandler, tx_hash: EVMTxHash) -> bool:
    with database.conn.read_ctx() as cursor:
        return cursor.execute(
            'SELECT COUNT(*) FROM evm_tx_mappings AS A JOIN evm_transactions AS B '
            'ON A.tx_id=B.identifier WHERE B.tx_hash=? AND A.value=?',
            (tx_hash, TX_DECODED),
        ).fetchone()[0] == 1


def _has_events(database: DBHandler, tx_hash: EVMTxHash) -> bool:
    with database.conn.read_ctx() as cursor:
        return cursor.execute(
            'SELECT COUNT(*) FROM history_events WHERE group_identifier=?',
            (str(tx_hash),),
        ).fetchone()[0] != 0


def _is_ignored(database: DBHandler) -> bool:
    with database.conn.read_ctx() as cursor:
        return cursor.execute('SELECT COUNT(*) FROM ignored_actions').fetchone()[0] != 0


def _deferred(database: DBHandler) -> list[EVMTxHash]:
    return database.pending_txs_tracker.get_token_query_deferred_hashes(SupportedBlockchain.ETHEREUM)  # noqa: E501


def _decode_periodically(
        decoder: EthereumTransactionDecoder,
        inquirer: EthereumInquirer,
        now: Timestamp,
        multicall: dict[str, Any],
) -> list[EVMTxHash]:
    """Run the periodic decoding at the given time while the nodes answer as given"""
    inquirer.contract_info_erc20_cache.remove(TOKEN_ADDRESS)
    with (
        patch.object(inquirer, 'multicall_2', **multicall),
        patch('rotkehlchen.chain.evm.decoding.decoder.ts_now', return_value=now),
    ):
        return decoder.get_and_decode_undecoded_transactions()


def _repair_token_rule(
        database: DBHandler,
        inquirer: EthereumInquirer,
) -> Any:
    """A decoder that gets the token with get_or_create_evm_token and ignores it when it is
    not conformant, as about 30 decoders do"""
    def rule(context: DecoderContext) -> EvmDecodingOutput:  # pylint: disable=unused-argument
        with suppress(NotERC20Conformant):
            get_or_create_evm_token(
                userdb=database,
                evm_address=TOKEN_ADDRESS,
                chain_id=ChainID.ETHEREUM,
                evm_inquirer=inquirer,
            )
        return DEFAULT_EVM_DECODING_OUTPUT

    return rule


@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address()]])
def test_transfer_is_deferred_until_the_nodes_respond(
        database: DBHandler,
        ethereum_accounts: list[ChecksumEvmAddress],
        ethereum_inquirer: EthereumInquirer,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
) -> None:
    """A transfer of a new token seen while the nodes fail leaves the transaction undecoded,
    without events and not ignored, and the token is not created. The periodic decoding skips
    it during the cooldown, and once the nodes respond it is decoded with the right decimals.
    The nodes are not reached for a while just because one query failed."""
    tx_hash = _add_transaction(database, (user := ethereum_accounts[0]), [_transfer_log(user)])
    decoder = ethereum_transaction_decoder
    assert _decode_periodically(decoder, ethereum_inquirer, (now := ts_now()), NODES_DOWN) == [tx_hash]  # noqa: E501
    assert not _is_decoded(database, tx_hash)
    assert not _has_events(database, tx_hash)  # not even the gas fee
    assert not _is_ignored(database)
    assert get_evm_token(evm_address=TOKEN_ADDRESS, chain_id=ChainID.ETHEREUM) is None
    assert _deferred(database) == [tx_hash]

    # during the cooldown the periodic decoding leaves it out, and does not count it
    with patch('rotkehlchen.chain.evm.decoding.decoder.ts_now', return_value=now + TOKEN_QUERY_DEFERRAL_RETRY_AFTER):  # noqa: E501
        assert decoder.count_undecoded_transactions() == 0
    assert _decode_periodically(decoder, ethereum_inquirer, Timestamp(now + TOKEN_QUERY_DEFERRAL_RETRY_AFTER), {'return_value': _erc20_output()}) == []  # noqa: E501

    # deferred again by another failure after the cooldown
    later = Timestamp(now + TOKEN_QUERY_DEFERRAL_RETRY_AFTER + 1)
    assert _decode_periodically(decoder, ethereum_inquirer, later, NODES_DOWN) == [tx_hash]
    assert not _is_decoded(database, tx_hash)

    with patch('rotkehlchen.chain.evm.decoding.decoder.ts_now', return_value=later + TOKEN_QUERY_DEFERRAL_RETRY_AFTER + 1):  # noqa: E501
        assert decoder.count_undecoded_transactions() == 1
    assert _decode_periodically(decoder, ethereum_inquirer, Timestamp(later + TOKEN_QUERY_DEFERRAL_RETRY_AFTER + 1), {'return_value': _erc20_output()}) == [tx_hash]  # noqa: E501
    assert _is_decoded(database, tx_hash)
    assert _transfers(database, tx_hash) == [(
        evm_address_to_identifier(address=TOKEN_ADDRESS, chain_id=ChainID.ETHEREUM),
        FVal('1.5'),  # 1500000 with the 6 decimals of the token
    )]
    assert _deferred(database) == []


@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address()]])
def test_decoder_catching_non_conformant_still_defers(
        database: DBHandler,
        ethereum_accounts: list[ChecksumEvmAddress],
        ethereum_inquirer: EthereumInquirer,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
) -> None:
    """TokenQueryFailed is a NotERC20Conformant, so a decoder catching it would decode the
    transaction without the token. The failure is still recorded and the tx deferred."""
    protocol_address = make_evm_address()
    tx_hash = _add_transaction(database, ethereum_accounts[0], [EvmTxReceiptLog(
        log_index=0,
        data=b'',
        address=protocol_address,
        topics=[b'\x01' * 32],
    )])
    with patch.dict(ethereum_transaction_decoder.rules.address_mappings, {
        protocol_address: (_repair_token_rule(database, ethereum_inquirer),),
    }):
        _decode_periodically(ethereum_transaction_decoder, ethereum_inquirer, ts_now(), NODES_DOWN)

    assert not _is_decoded(database, tx_hash)
    assert _deferred(database) == [tx_hash]


@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address()]])
def test_placeholder_repair_failure_defers(
        database: DBHandler,
        ethereum_accounts: list[ChecksumEvmAddress],
        ethereum_inquirer: EthereumInquirer,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
) -> None:
    """A placeholder in the DB is queried again when a decoder gets it with an inquirer. If
    that fails the tx is deferred and the placeholder is left as it is, instead of decoding
    with its default 18 decimals. Once the nodes answer it is repaired and the tx decoded with
    the right decimals."""
    placeholder = get_or_create_evm_token(
        userdb=database,
        evm_address=TOKEN_ADDRESS,
        chain_id=ChainID.ETHEREUM,
    )
    assert (placeholder.name, placeholder.decimals) == (placeholder.identifier, 18)
    user = ethereum_accounts[0]
    tx_hash = _add_transaction(database, user, [_transfer_log(user)])
    decoder = ethereum_transaction_decoder
    with patch.dict(decoder.rules.address_mappings, {
        TOKEN_ADDRESS: (_repair_token_rule(database, ethereum_inquirer),),
    }):
        _decode_periodically(decoder, ethereum_inquirer, (now := ts_now()), NODES_DOWN)
        assert not _is_decoded(database, tx_hash)
        assert _deferred(database) == [tx_hash]
        token = EvmToken(placeholder.identifier)
        assert (token.name, token.symbol, token.decimals) == (placeholder.identifier, '', 18)

        _decode_periodically(decoder, ethereum_inquirer, Timestamp(now + TOKEN_QUERY_DEFERRAL_RETRY_AFTER + 1), {'return_value': _erc20_output()})  # noqa: E501

    token = EvmToken(placeholder.identifier)
    assert (token.name, token.symbol, token.decimals) == ('Token', 'TKN', 6)
    assert _transfers(database, tx_hash) == [(placeholder.identifier, FVal('1.5'))]


@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address()]])
def test_known_token_decodes_during_an_outage(
        database: DBHandler,
        ethereum_accounts: list[ChecksumEvmAddress],
        ethereum_inquirer: EthereumInquirer,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
) -> None:
    """A token in the DB with its details never queries the chain, so it is never deferred"""
    token = get_or_create_evm_token(
        userdb=database,
        evm_address=TOKEN_ADDRESS,
        chain_id=ChainID.ETHEREUM,
        name='Token',
        symbol='TKN',
        decimals=6,
    )
    user = ethereum_accounts[0]
    tx_hash = _add_transaction(database, user, [_transfer_log(user)])
    with patch.object(ethereum_inquirer, 'multicall_2', **NODES_DOWN) as multicall:
        ethereum_transaction_decoder.get_and_decode_undecoded_transactions()

    assert multicall.call_count == 0
    assert _transfers(database, tx_hash) == [(token.identifier, FVal('1.5'))]
    assert _deferred(database) == []


@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address()]])
def test_nft_transfer_is_deferred(
        database: DBHandler,
        ethereum_accounts: list[ChecksumEvmAddress],
        ethereum_inquirer: EthereumInquirer,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
) -> None:
    """An nft seen while the nodes fail is not created with empty details, its tx is
    deferred like an erc20 one"""
    user = ethereum_accounts[0]
    tx_hash = _add_transaction(database, user, [_transfer_log(user, nft=True)])
    _decode_periodically(ethereum_transaction_decoder, ethereum_inquirer, ts_now(), NODES_DOWN)

    assert not _is_decoded(database, tx_hash)
    assert _deferred(database) == [tx_hash]
    assert get_evm_token(
        evm_address=TOKEN_ADDRESS,
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC721,
        collectible_id='5',
    ) is None


@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address()]])
@pytest.mark.parametrize('nft', [False, True])
def test_decoded_as_before_after_the_cap(
        database: DBHandler,
        ethereum_accounts: list[ChecksumEvmAddress],
        ethereum_inquirer: EthereumInquirer,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        nft: bool,
) -> None:
    """A single token that keeps failing, alone on its chain, still stops deferring its tx
    once TOKEN_QUERY_DEFERRAL_MAX_DURATION passes since the first deferral. It is then
    decoded as before the deferral existed: the erc20 transfer is dropped, and the nft is
    created with empty details."""
    user = ethereum_accounts[0]
    tx_hash = _add_transaction(database, user, [_transfer_log(user, nft=nft)])
    decoder = ethereum_transaction_decoder
    _decode_periodically(decoder, ethereum_inquirer, (now := ts_now()), NODES_DOWN)
    _decode_periodically(decoder, ethereum_inquirer, Timestamp(now + TOKEN_QUERY_DEFERRAL_MAX_DURATION), NODES_DOWN)  # noqa: E501
    assert not _is_decoded(database, tx_hash)  # within the cap, which counts from the first

    _decode_periodically(decoder, ethereum_inquirer, Timestamp(now + TOKEN_QUERY_DEFERRAL_MAX_DURATION + TOKEN_QUERY_DEFERRAL_RETRY_AFTER + 1), NODES_DOWN)  # noqa: E501
    assert _is_decoded(database, tx_hash)
    assert _deferred(database) == []
    if nft:
        identifier = evm_address_to_identifier(
            address=TOKEN_ADDRESS,
            chain_id=ChainID.ETHEREUM,
            token_type=TokenKind.ERC721,
            collectible_id='5',
        )
        token = EvmToken(identifier)
        assert (token.name, token.symbol, token.decimals) == ('', '', 0)
        assert _transfers(database, tx_hash) == [(identifier, FVal(1))]
    else:
        assert _transfers(database, tx_hash) == []
        assert get_evm_token(evm_address=TOKEN_ADDRESS, chain_id=ChainID.ETHEREUM) is None


@pytest.mark.parametrize('token_kind', [TokenKind.ERC20, TokenKind.ERC721])
@pytest.mark.parametrize('forced', [None, False, True])
def test_failed_query_never_saves_a_token(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        token_kind: TokenKind,
        forced: bool | None,
) -> None:
    """Outside of decoding (None) or while decoding, a failed query does not save the token,
    even with fallbacks. Otherwise the retry would find it and never query it again. A forced
    decoding does what was done before: fallbacks for erc20, empty details for erc721."""
    with patch.object(ethereum_inquirer, 'multicall_2', **NODES_DOWN):
        if forced is None:
            with pytest.raises(TokenQueryFailed):
                get_or_create_evm_token(
                    userdb=database,
                    evm_address=TOKEN_ADDRESS,
                    chain_id=ChainID.ETHEREUM,
                    token_kind=token_kind,  # type: ignore[arg-type]  # only evm kinds
                    evm_inquirer=ethereum_inquirer,
                    **FALLBACKS,
                )
        else:
            with track_token_query_failures(forced=forced) as failures:
                try:
                    get_or_create_evm_token(
                        userdb=database,
                        evm_address=TOKEN_ADDRESS,
                        chain_id=ChainID.ETHEREUM,
                        token_kind=token_kind,  # type: ignore[arg-type]  # only evm kinds
                        evm_inquirer=ethereum_inquirer,
                        **FALLBACKS,
                    )
                except TokenQueryFailed:
                    assert not forced
                else:
                    assert forced
            assert failures.addresses == {TOKEN_ADDRESS}

    token = get_evm_token(evm_address=TOKEN_ADDRESS, chain_id=ChainID.ETHEREUM, token_kind=token_kind)  # type: ignore[arg-type]  # noqa: E501
    if forced is True:
        assert token is not None
        assert (token.name, token.symbol, token.decimals) == (
            ('Fallback', 'FB', 18) if token_kind == TokenKind.ERC20 else ('', '', 0)
        )
    else:
        assert token is None


@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address()]])
@pytest.mark.parametrize('have_decoders', [True])
def test_user_requests_retry_deferred_txs(
        rotkehlchen_api_server: APIServer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """The decode endpoint and the decoding of the PnL report retry the deferred txs right
    away, inside the cooldown. The report warns about the ones that are still deferred."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    database = rotki.data.db
    evm_manager = rotki.chains_aggregator.get_evm_manager(ChainID.ETHEREUM)
    inquirer, decoder = evm_manager.node_inquirer, evm_manager.transactions_decoder
    user = ethereum_accounts[0]
    tx_hash = _add_transaction(database, user, [_transfer_log(user)])
    with patch.object(inquirer, 'multicall_2', **NODES_DOWN):
        decoder.get_and_decode_undecoded_transactions()
    assert _deferred(database) == [tx_hash]
    database.msg_aggregator.consume_warnings()

    with (  # the report retries it, and warns since it fails again
        patch.object(inquirer, 'multicall_2', **NODES_DOWN) as multicall,
        patch.object(evm_manager.transactions, 'query_chain'),
        patch.object(evm_manager.transactions, 'get_receipts_for_transactions_missing_them'),
    ):
        rotki.history_querying_manager.get_history(
            start_ts=Timestamp(0),
            end_ts=ts_now(),
            has_premium=False,
        )
    assert multicall.call_count == 1
    assert any(
        'transactions could not be decoded since the details of their tokens' in x
        for x in database.msg_aggregator.consume_warnings()
    )

    with patch.object(inquirer, 'multicall_2', return_value=_erc20_output()):
        assert assert_proper_response_with_result(
            response=requests.post(
                api_url_for(rotkehlchen_api_server, 'transactionsdecodingresource'),
                json={'async_query': False, 'chain': 'eth'},
            ),
            rotkehlchen_api_server=rotkehlchen_api_server,
            async_query=False,
        ) == {'decoded_tx_number': 1}

    assert _is_decoded(database, tx_hash)
    assert _deferred(database) == []
