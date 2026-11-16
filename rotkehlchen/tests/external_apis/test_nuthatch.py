import json
from http import HTTPStatus
from unittest.mock import patch

import pytest

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.nuthatch import Nuthatch
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ChainID

ACCOUNT = string_to_evm_address('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')


@pytest.fixture(name='nuthatch')
def fixture_nuthatch(database, messages_aggregator):
    return Nuthatch(database=database, msg_aggregator=messages_aggregator)


def test_nuthatch_url_and_params(nuthatch: Nuthatch) -> None:
    assert nuthatch._get_url(chain_id=ChainID.ETHEREUM) == 'http://127.0.0.1:8288/api'
    CachedSettings().update_entry('nuthatch_api_endpoint', 'http://nest.local:9000/')
    assert nuthatch._get_url(chain_id=ChainID.ETHEREUM) == 'http://nest.local:9000/api'
    assert nuthatch._build_query_params(
        module='account',
        action='txlist',
        api_key=nuthatch.default_api_key,
        chain_id=ChainID.ETHEREUM,
    ) == {'module': 'account', 'action': 'txlist', 'chainid': '1'}


def test_nuthatch_refusal_raises(nuthatch: Nuthatch) -> None:
    """A range the nest has not indexed must fall through to the next indexer, never read as
    an account with no transactions."""
    with (
        patch.object(nuthatch.session, 'get', return_value=MockResponse(
            status_code=HTTPStatus.OK,
            text='{"status":"0","message":"NOTOK","result":"NUTHATCH_INCOMPLETE: history starts at block 24000000"}',  # noqa: E501
        )),
        pytest.raises(RemoteError, match='Nuthatch cannot answer txlist on ethereum: NUTHATCH_INCOMPLETE'),  # noqa: E501
    ):
        list(nuthatch.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=ACCOUNT,
            action='txlist',
            period_or_hash=TimestampOrBlockRange('blocks', 20000000, 20001000),
        ))


def test_nuthatch_internal_trace_index(nuthatch: Nuthatch) -> None:
    """traceId is a depth path that two frames at the same depth share, so the nest's own
    frame index is used instead."""
    parent_hash = str(make_evm_tx_hash())
    rows = [{
        'blockNumber': '26366016',
        'timeStamp': '1762900000',
        'hash': parent_hash,
        'from': str(make_evm_address()),
        'to': ACCOUNT,
        'value': value,
        'gas': '0',
        'gasUsed': '0',
        'isError': '0',
        'type': 'call',
        'traceId': '0_1',
        'nuthatchTraceIndex': index,
    } for value, index in (('1', '17'), ('2', '22'))]
    with patch.object(nuthatch.session, 'get', return_value=MockResponse(
        status_code=HTTPStatus.OK,
        text=json.dumps({'status': '1', 'message': 'OK', 'result': rows}),
    )):
        txs = [tx for page in nuthatch.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=ACCOUNT,
            action='txlistinternal',
            period_or_hash=TimestampOrBlockRange('blocks', 26000000, 26400000),
        ) for tx in page]

    assert [(tx.trace_id, tx.value) for tx in txs] == [(17, 1), (22, 2)]
