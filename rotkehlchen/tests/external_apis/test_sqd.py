import json
from http import HTTPStatus
from unittest.mock import patch

import pytest

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.errors.misc import ChainNotSupported, RemoteError
from rotkehlchen.externalapis.interface import HasChainActivity
from rotkehlchen.externalapis.sqd import ERC20_TRANSFER_TOPIC, SQD_CHAIN_NAMES, Sqd
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    ChainID,
    EvmTransaction,
    Timestamp,
    deserialize_evm_tx_hash,
)

YABIR_ADDRESS = string_to_evm_address('0xc37b40ABdB939635068d3c5f13E7faF686F03B65')
SMALL_RANGE_START, SMALL_LOG_RANGE_END = 21_540_000, 21_540_010


@pytest.fixture(name='sqd')
def fixture_sqd() -> Sqd:
    return Sqd()


def test_sqd_network_mapping_and_unsupported_chain(sqd: Sqd) -> None:
    """Supported chain mappings are populated and unsupported chains fail."""
    for chain_id, network_name in SQD_CHAIN_NAMES.items():
        assert isinstance(chain_id, ChainID)
        assert len(network_name) > 0

    with pytest.raises(ChainNotSupported):
        sqd.get_latest_block_number(ChainID.FANTOM)  # type: ignore[arg-type]


def test_sqd_transactions_unsupported_period(sqd: Sqd) -> None:
    """Timestamp ranges fall through to other indexers via RemoteError."""
    with pytest.raises(RemoteError, match='SQD only supports block-range queries'):
        next(sqd.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=YABIR_ADDRESS,
            internal=False,
            period=TimestampOrBlockRange(
                range_type='timestamps',
                from_value=1700000000,
                to_value=1700001000,
            ),
        ))


@pytest.mark.parametrize(
    ('mock_response', 'expected_error'),
    [
        pytest.param(
            MockResponse(
                status_code=HTTPStatus.TOO_MANY_REQUESTS,
                text='',
                headers={'Retry-After': '9999'},
            ),
            'rate limit exceeded',
            id='rate-limited',
        ),
        pytest.param(
            MockResponse(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                text='Internal Server Error',
            ),
            'failed with HTTP status code',
            id='server-error',
        ),
        pytest.param(
            MockResponse(
                status_code=HTTPStatus.OK,
                text='not valid json\n',
            ),
            'invalid JSON in NDJSON',
            id='invalid-ndjson',
        ),
    ],
)
def test_query_stream_error_handling(
        sqd: Sqd,
        mock_response: MockResponse,
        expected_error: str,
) -> None:
    """SQD stream query surfaces transport/HTTP/NDJSON failures as RemoteError."""
    query_kwargs: dict = {
        'chain_id': ChainID.ETHEREUM,
        'from_block': 0,
        'to_block': 100,
        'fields': {'block': {'number': True}},
    }

    with (
        patch.object(sqd.session, 'post', return_value=mock_response),
        pytest.raises(RemoteError, match=expected_error),
    ):
        sqd._query_stream(**query_kwargs)


def test_sqd_finalized_head_parsing(sqd: Sqd) -> None:
    """`get_latest_block_number` parses the finalized-head response payload."""
    with patch.object(sqd.session, 'get', return_value=MockResponse(
            status_code=HTTPStatus.OK,
            text=json.dumps({'number': SMALL_RANGE_START, 'hash': '0xabc'}),
    )):
        assert sqd.get_latest_block_number(ChainID.ETHEREUM) == SMALL_RANGE_START


@pytest.mark.vcr
def test_sqd_get_latest_block_number(sqd: Sqd) -> None:
    block_number = sqd.get_latest_block_number(ChainID.ETHEREUM)
    assert isinstance(block_number, int)
    assert block_number > 0


@pytest.mark.vcr
def test_sqd_has_activity(sqd: Sqd) -> None:
    assert sqd.has_activity(
        chain_id=ChainID.ETHEREUM,
        account=YABIR_ADDRESS,
    ) == HasChainActivity.TRANSACTIONS


@pytest.mark.vcr
def test_sqd_get_transactions(sqd: Sqd) -> None:
    """Query normal transactions in a small block range."""
    all_txs = [
        tx
        for batch in sqd.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=YABIR_ADDRESS,
            internal=False,
            period=TimestampOrBlockRange(
                range_type='blocks',
                from_value=24474844,
                to_value=24484844,
            ),
        )
        for tx in batch
    ]
    assert all_txs == [EvmTransaction(
          tx_hash=deserialize_evm_tx_hash('0x02d2882ba4119e2c18288d7af306903638a6c78082b9d26c57db4b3a24c2299c'),
          chain_id=ChainID.ETHEREUM,
          timestamp=Timestamp(1771431227),
          block_number=24484844,
          from_address=YABIR_ADDRESS,
          to_address=string_to_evm_address('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'),
          value=10000000000000,
          gas=21000,
          gas_price=536852812,
          gas_used=21000,
          input_data=b'',
          nonce=57,
          db_id=-1,
          authorization_list=None,
      )]


@pytest.mark.vcr
def test_sqd_get_token_transaction_hashes(sqd: Sqd) -> None:
    """Query ERC20 transfer transaction hashes and verify uniqueness."""
    all_hashes = [
        tx_hash
        for batch in sqd.get_token_transaction_hashes(
            chain_id=ChainID.ETHEREUM,
            account=YABIR_ADDRESS,
            from_block=21148990,
            to_block=21149020,
        )
        for tx_hash in batch
    ]
    assert all_hashes == [
        deserialize_evm_tx_hash('0x68746fb44d41c1e561adaae83a1199b1dc37615e70a3e6d492fc9f28fcaa9a37'),
        deserialize_evm_tx_hash('0x7e7693ef4d68f67e34aa63ca2d66ce5cbf8b18a927953968fd1aac684b1db790'),
    ]


@pytest.mark.vcr
def test_sqd_get_logs(sqd: Sqd) -> None:
    """Query USDT Transfer logs in a small block range."""
    events = sqd.get_logs(
        chain_id=ChainID.ETHEREUM,
        contract_address=string_to_evm_address('0xdAC17F958D2ee523a2206206994597C13D831ec7'),  # usdt  # noqa: E501
        topics=[ERC20_TRANSFER_TOPIC],
        from_block=SMALL_RANGE_START,
        to_block=SMALL_LOG_RANGE_END,
    )
    for event in events:
        assert {'address', 'topics', 'transactionHash'} <= set(event)
        assert SMALL_RANGE_START <= event['blockNumber'] <= SMALL_LOG_RANGE_END
