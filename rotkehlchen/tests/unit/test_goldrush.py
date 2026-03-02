"""Unit tests for the GoldRush (Covalent) API client."""
from typing import TYPE_CHECKING, Final
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.errors.misc import ChainNotSupported, RemoteError
from rotkehlchen.externalapis.goldrush import (
    CHAINID_TO_GOLDRUSH_SLUG,
    GOLDRUSH_BASE_URL,
    GoldRush,
)
from rotkehlchen.types import ApiKey, ChainID

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

# A chain that is NOT in CHAINID_TO_GOLDRUSH_SLUG for testing unsupported path
UNSUPPORTED_CHAIN: Final = ChainID.CELO


def make_goldrush(database: 'DBHandler') -> GoldRush:
    """Create a GoldRush instance with a mock message aggregator."""
    msg_aggregator = MagicMock()
    return GoldRush(database=database, msg_aggregator=msg_aggregator)


# ─── slug mapping ────────────────────────────────────────────────────────────

def test_get_slug_all_mapped_chains(database: 'DBHandler') -> None:
    """_get_slug returns a non-empty string for all mapped chains."""
    gr = make_goldrush(database)
    for chain_id in CHAINID_TO_GOLDRUSH_SLUG:
        slug = gr._get_slug(chain_id)
        assert isinstance(slug, str) and slug, (
            f'Expected a non-empty slug for {chain_id.name}'
        )


def test_get_slug_known_values(database: 'DBHandler') -> None:
    """_get_slug returns the expected slug for specific chains."""
    gr = make_goldrush(database)
    assert gr._get_slug(ChainID.ETHEREUM) == 'eth-mainnet'
    assert gr._get_slug(ChainID.OPTIMISM) == 'optimism-mainnet'
    assert gr._get_slug(ChainID.BINANCE_SC) == 'bsc-mainnet'
    assert gr._get_slug(ChainID.ARBITRUM_ONE) == 'arbitrum-mainnet'
    assert gr._get_slug(ChainID.BASE) == 'base-mainnet'


def test_get_slug_unsupported_chain_raises(database: 'DBHandler') -> None:
    """_get_slug raises ChainNotSupported for unmapped chains."""
    gr = make_goldrush(database)
    with pytest.raises(ChainNotSupported):
        gr._get_slug(UNSUPPORTED_CHAIN)


# ─── _request: auth headers and error handling ───────────────────────────────

def test_request_no_api_key_raises(database: 'DBHandler') -> None:
    """_request raises RemoteError when no API key is configured."""
    gr = make_goldrush(database)
    # Ensure no API key is set (default state for test DB)
    with patch.object(gr, '_get_api_key', return_value=None):
        with pytest.raises(RemoteError, match='API key is not configured'):
            gr._request('/eth-mainnet/address/0x1234/transactions_v3/')


def test_request_uses_basic_auth(database: 'DBHandler') -> None:
    """_request sends HTTP Basic Auth with the API key as username."""
    gr = make_goldrush(database)
    api_key = ApiKey('test-api-key-123')

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'data': {'items': []}, 'error': False}

    with patch.object(gr, '_get_api_key', return_value=api_key):
        with patch.object(gr.session, 'get', return_value=mock_response) as mock_get:
            gr._request('/eth-mainnet/address/0x1234/transactions_v3/')

    call_kwargs = mock_get.call_args.kwargs
    assert call_kwargs['url'] == f'{GOLDRUSH_BASE_URL}/eth-mainnet/address/0x1234/transactions_v3/'
    auth = call_kwargs['auth']
    assert auth.username == api_key
    assert auth.password == ''


def test_request_raises_on_non_200(database: 'DBHandler') -> None:
    """_request raises RemoteError when the API returns a non-200 status."""
    gr = make_goldrush(database)
    api_key = ApiKey('test-key')

    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = 'Too Many Requests'

    with patch.object(gr, '_get_api_key', return_value=api_key):
        with patch.object(gr.session, 'get', return_value=mock_response):
            with pytest.raises(RemoteError, match='429'):
                gr._request('/eth-mainnet/test/')


def test_request_raises_on_api_error_field(database: 'DBHandler') -> None:
    """_request raises RemoteError when the JSON body contains error=True."""
    gr = make_goldrush(database)
    api_key = ApiKey('test-key')

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'error': True,
        'error_message': 'Invalid API key',
    }

    with patch.object(gr, '_get_api_key', return_value=api_key):
        with patch.object(gr.session, 'get', return_value=mock_response):
            with pytest.raises(RemoteError, match='Invalid API key'):
                gr._request('/eth-mainnet/test/')


# ─── _paginate ────────────────────────────────────────────────────────────────

def _make_page_response(items: list, has_more: bool, page_number: int) -> dict:
    return {
        'data': {
            'items': items,
            'pagination': {
                'has_more': has_more,
                'page_number': page_number,
                'page_size': 100,
            },
        },
        'error': False,
    }


def test_paginate_single_page(database: 'DBHandler') -> None:
    """_paginate returns all items from a single-page response."""
    gr = make_goldrush(database)
    items = [{'tx_hash': '0xabc'}, {'tx_hash': '0xdef'}]
    page_response = _make_page_response(items=items, has_more=False, page_number=0)

    with patch.object(gr, '_request', return_value=page_response):
        result = gr._paginate('/eth-mainnet/test/')

    assert result == items


def test_paginate_multi_page(database: 'DBHandler') -> None:
    """_paginate collects items from multiple pages until has_more=False."""
    gr = make_goldrush(database)
    page0_items = [{'tx_hash': f'0x{i:04x}'} for i in range(100)]
    page1_items = [{'tx_hash': f'0x{i:04x}'} for i in range(100, 150)]

    page0_response = _make_page_response(items=page0_items, has_more=True, page_number=0)
    page1_response = _make_page_response(items=page1_items, has_more=False, page_number=1)

    call_count = 0

    def mock_request(path: str, params: dict | None = None) -> dict:
        nonlocal call_count
        response = page0_response if call_count == 0 else page1_response
        call_count += 1
        return response

    with patch.object(gr, '_request', side_effect=mock_request):
        result = gr._paginate('/eth-mainnet/test/')

    assert len(result) == 150
    assert call_count == 2


def test_paginate_empty_response(database: 'DBHandler') -> None:
    """_paginate returns empty list when the response has no items."""
    gr = make_goldrush(database)
    empty_response = _make_page_response(items=[], has_more=False, page_number=0)

    with patch.object(gr, '_request', return_value=empty_response):
        result = gr._paginate('/eth-mainnet/test/')

    assert result == []


# ─── transaction format conversion ───────────────────────────────────────────

def test_goldrush_tx_to_etherscan_fmt_basic() -> None:
    """_goldrush_tx_to_etherscan_fmt converts a GoldRush transaction item correctly."""
    item = {
        'tx_hash': '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
        'from_address': '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c',
        'to_address': '0xd3CdA913deB6f4967b2Ef3aa68f5A843aFd14b0',
        'value': '1000000000000000000',
        'gas_offered': 21000,
        'gas_spent': 21000,
        'gas_price': 20000000000,
        'nonce': 42,
        'block_height': 12345678,
        'block_signed_at': '2021-06-01T12:00:00Z',
        'successful': True,
        'input': '0x',
    }

    result = GoldRush._goldrush_tx_to_etherscan_fmt(item)

    assert result['hash'] == item['tx_hash']
    assert result['value'] == '1000000000000000000'
    assert result['gas'] == '21000'
    assert result['gasUsed'] == '21000'
    assert result['gasPrice'] == '20000000000'
    assert result['nonce'] == '42'
    assert result['blockNumber'] == '12345678'
    assert result['isError'] == '0'
    assert result['input'] == '0x'
    # Addresses should be checksummed
    assert result['from'] == '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'


def test_goldrush_tx_to_etherscan_fmt_failed_tx() -> None:
    """isError is '1' for failed transactions."""
    item = {
        'tx_hash': '0xaaaa',
        'from_address': '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c',
        'to_address': '0xd3CdA913deB6f4967b2Ef3aa68f5A843aFd14b0',
        'block_signed_at': '2021-06-01T12:00:00Z',
        'successful': False,
    }

    result = GoldRush._goldrush_tx_to_etherscan_fmt(item)
    assert result['isError'] == '1'


def test_goldrush_tx_to_etherscan_fmt_contract_creation() -> None:
    """to_address is empty string for contract creation transactions."""
    item = {
        'tx_hash': '0xbbbb',
        'from_address': '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c',
        'to_address': None,
        'block_signed_at': '2021-06-01T12:00:00Z',
        'successful': True,
    }

    result = GoldRush._goldrush_tx_to_etherscan_fmt(item)
    assert result['to'] == ''


# ─── _paginate_v3_transactions ────────────────────────────────────────────────

def test_paginate_v3_transactions_embeds_page_in_path(database: 'DBHandler') -> None:
    """_paginate_v3_transactions calls the API with page number in the URL path."""
    gr = make_goldrush(database)
    items = [{'tx_hash': '0xabc'}]
    page_response = _make_page_response(items=items, has_more=False, page_number=0)

    with patch.object(gr, '_request', return_value=page_response) as mock_req:
        gr._paginate_v3_transactions('/eth-mainnet/address/0x1234/transactions_v3/')

    call_path = mock_req.call_args.kwargs['path']
    assert 'page/0/' in call_path


def test_paginate_v3_transactions_multi_page(database: 'DBHandler') -> None:
    """_paginate_v3_transactions iterates pages via path-based pagination."""
    gr = make_goldrush(database)
    page0_items = [{'tx_hash': f'0x{i:04x}'} for i in range(100)]
    page1_items = [{'tx_hash': f'0x{i:04x}'} for i in range(100, 150)]

    page0_response = _make_page_response(items=page0_items, has_more=True, page_number=0)
    page1_response = _make_page_response(items=page1_items, has_more=False, page_number=1)

    call_count = 0

    def mock_request(path: str, params: dict | None = None) -> dict:
        nonlocal call_count
        response = page0_response if call_count == 0 else page1_response
        call_count += 1
        return response

    with patch.object(gr, '_request', side_effect=mock_request):
        result = gr._paginate_v3_transactions(
            '/eth-mainnet/address/0x1234/transactions_v3/',
        )

    assert len(result) == 150
    assert call_count == 2


# ─── get_transactions: block range filtering ──────────────────────────────────

def test_get_transactions_passes_block_range(database: 'DBHandler') -> None:
    """get_transactions passes starting-block/ending-block when given a block range."""
    from rotkehlchen.chain.structures import TimestampOrBlockRange

    gr = make_goldrush(database)
    address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'
    period = TimestampOrBlockRange(range_type='blocks', from_value=100, to_value=200)

    with patch.object(gr, '_paginate_v3_transactions', return_value=[]) as mock_pag:
        next(gr.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=address,
            action='txlist',
            period_or_hash=period,
        ))

    call_params = mock_pag.call_args.kwargs.get('params') or mock_pag.call_args.args[1] if len(mock_pag.call_args.args) > 1 else mock_pag.call_args.kwargs.get('params')
    assert call_params is not None
    assert call_params.get('starting-block') == '100'
    assert call_params.get('ending-block') == '200'


def test_get_transactions_no_filter_when_no_period(database: 'DBHandler') -> None:
    """get_transactions passes no block params when period_or_hash is None."""
    gr = make_goldrush(database)
    address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'

    with patch.object(gr, '_paginate_v3_transactions', return_value=[]) as mock_pag:
        next(gr.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=address,
            action='txlist',
            period_or_hash=None,
        ))

    call_params = mock_pag.call_args.kwargs.get('params')
    assert call_params is None


# ─── get_token_transaction_hashes: block range filtering ──────────────────────

def test_get_token_transaction_hashes_passes_block_range(database: 'DBHandler') -> None:
    """get_token_transaction_hashes passes starting-block/ending-block params."""
    gr = make_goldrush(database)
    address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'

    with patch.object(gr, '_paginate', return_value=[]) as mock_pag:
        next(gr.get_token_transaction_hashes(
            chain_id=ChainID.ETHEREUM,
            account=address,
            from_block=500,
            to_block=1000,
        ))

    call_params = mock_pag.call_args.kwargs.get('params')
    assert call_params is not None
    assert call_params.get('starting-block') == '500'
    assert call_params.get('ending-block') == '1000'


def test_get_token_transaction_hashes_no_filter_when_no_blocks(database: 'DBHandler') -> None:
    """get_token_transaction_hashes passes no block params when both are None."""
    gr = make_goldrush(database)
    address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'

    with patch.object(gr, '_paginate', return_value=[]) as mock_pag:
        next(gr.get_token_transaction_hashes(
            chain_id=ChainID.ETHEREUM,
            account=address,
        ))

    call_params = mock_pag.call_args.kwargs.get('params')
    assert call_params is None


# ─── get_transactions: internal tx action raises ──────────────────────────────

def test_get_transactions_internal_raises(database: 'DBHandler') -> None:
    """get_transactions with action='txlistinternal' raises RemoteError."""
    gr = make_goldrush(database)
    address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'

    with pytest.raises(RemoteError, match='internal'):
        next(gr.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=address,
            action='txlistinternal',
        ))


# ─── unsupported chain handling ───────────────────────────────────────────────

def test_get_transactions_unsupported_chain(database: 'DBHandler') -> None:
    """get_transactions raises ChainNotSupported for unmapped chains."""
    gr = make_goldrush(database)
    address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'

    with pytest.raises(ChainNotSupported):
        next(gr.get_transactions(
            chain_id=UNSUPPORTED_CHAIN,
            account=address,
            action='txlist',
        ))


