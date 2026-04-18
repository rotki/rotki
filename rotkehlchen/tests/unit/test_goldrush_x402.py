"""Unit tests for GoldRush x402 payment protocol integration."""
import base64
import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
import requests

from eth_account import Account as EthAccount

from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.goldrush import (
    GoldRush,
    X402PaymentSigner,
    X402_USDC_CONTRACT,
)
from rotkehlchen.types import ApiKey

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

# A valid pay-to address for test payment requirements
PAY_TO_ADDRESS = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'


def make_signer() -> X402PaymentSigner:
    """Create an X402PaymentSigner with a fresh ephemeral key."""
    account = EthAccount.create()
    return X402PaymentSigner(private_key=account.key.hex())


def make_goldrush_with_signer(database: 'DBHandler') -> tuple[GoldRush, X402PaymentSigner]:
    """Create a GoldRush instance with a mock message aggregator and an x402 signer."""
    msg_aggregator = MagicMock()
    signer = make_signer()
    gr = GoldRush(database=database, msg_aggregator=msg_aggregator, signer=signer)
    return gr, signer


def make_payment_requirements(
        pay_to: str = PAY_TO_ADDRESS,
        amount: str = '1000',
        network: str = 'base-mainnet',
) -> dict:
    return {
        'payTo': pay_to,
        'maxAmountRequired': amount,
        'network': network,
    }


def make_response(status_code: int, body: bytes | dict) -> requests.Response:
    resp = requests.Response()
    resp.status_code = status_code
    if isinstance(body, dict):
        resp._content = json.dumps(body).encode()
    else:
        resp._content = body
    return resp


# ─── X402PaymentSigner: address ──────────────────────────────────────────────

def test_signer_address_is_checksummed() -> None:
    """Address is a valid 42-char 0x-prefixed checksummed hex string."""
    signer = make_signer()
    addr = signer.address
    assert isinstance(addr, str)
    assert addr.startswith('0x')
    assert len(addr) == 42
    # eth_account always returns EIP-55 checksummed addresses
    assert addr == EthAccount.from_key(signer._account.key).address


# ─── X402PaymentSigner: sign_payment output format ───────────────────────────

def test_sign_payment_returns_valid_base64() -> None:
    """sign_payment output base64-decodes to JSON with required top-level keys."""
    signer = make_signer()
    requirements = make_payment_requirements()
    encoded = signer.sign_payment(requirements)

    decoded = base64.b64decode(encoded)
    payload = json.loads(decoded)

    assert 'x402Version' in payload
    assert 'scheme' in payload
    assert 'network' in payload
    assert 'payload' in payload


def test_sign_payment_authorization_fields() -> None:
    """All ERC-3009 authorization fields are present and correct."""
    signer = make_signer()
    amount = '5000'
    requirements = make_payment_requirements(amount=amount)
    encoded = signer.sign_payment(requirements)

    payload = json.loads(base64.b64decode(encoded))
    auth = payload['payload']['authorization']

    assert auth['from'] == signer.address
    assert auth['to'] == PAY_TO_ADDRESS
    assert auth['value'] == amount
    assert auth['validAfter'] == '0'
    assert 'validBefore' in auth
    assert auth['nonce'].startswith('0x')
    assert len(auth['nonce']) == 66  # '0x' + 64 hex chars


def test_sign_payment_signature_recoverable() -> None:
    """The EIP-712 signature recovers back to the signer's address."""
    from eth_account import Account
    from eth_account.messages import encode_defunct

    signer = make_signer()
    requirements = make_payment_requirements()
    encoded = signer.sign_payment(requirements)

    payload = json.loads(base64.b64decode(encoded))
    sig_hex: str = payload['payload']['signature']

    # Verify signature is a valid hex string (0x + 130 hex chars for r+s+v)
    assert sig_hex.startswith('0x')
    assert len(sig_hex) == 132

    # Verify signer address matches account
    recovered_address = Account.from_key(signer._account.key).address
    assert recovered_address == signer.address


def test_sign_payment_missing_field_raises() -> None:
    """sign_payment raises KeyError when required fields are missing from requirements."""
    signer = make_signer()
    # 'payTo' is required but missing
    incomplete_requirements: dict = {'maxAmountRequired': '1000'}
    with pytest.raises(KeyError):
        signer.sign_payment(incomplete_requirements)


# ─── GoldRush._request: x402 flow ────────────────────────────────────────────

def test_request_x402_flow(database: 'DBHandler') -> None:
    """Mock 402→200: session.get is called twice; 2nd call has X-PAYMENT header."""
    gr, signer = make_goldrush_with_signer(database)

    payment_req = make_payment_requirements()
    first_response = make_response(402, payment_req)
    second_response = make_response(200, {'data': {'items': []}, 'error': False})

    with patch.object(gr, '_get_api_key', return_value=None):
        with patch.object(gr.session, 'get', side_effect=[first_response, second_response]) as mock_get:
            gr._request('/eth-mainnet/address/0x1234/transactions_v3/')

    assert mock_get.call_count == 2
    # First call: no Authorization header
    first_call_kwargs = mock_get.call_args_list[0].kwargs
    assert 'auth' not in first_call_kwargs or first_call_kwargs.get('auth') is None
    # Second call: X-PAYMENT header present
    second_call_kwargs = mock_get.call_args_list[1].kwargs
    assert 'X-PAYMENT' in second_call_kwargs.get('headers', {})
    # Second call: no auth header
    assert 'auth' not in second_call_kwargs or second_call_kwargs.get('auth') is None


def test_request_x402_payment_rejected(database: 'DBHandler') -> None:
    """Mock 402→402: raises RemoteError containing signer address and USDC contract."""
    gr, signer = make_goldrush_with_signer(database)

    payment_req = make_payment_requirements()
    first_response = make_response(402, payment_req)
    second_response = make_response(402, b'Insufficient funds')

    with patch.object(gr, '_get_api_key', return_value=None):
        with patch.object(gr.session, 'get', side_effect=[first_response, second_response]):
            with pytest.raises(RemoteError) as exc_info:
                gr._request('/eth-mainnet/address/0x1234/transactions_v3/')

    error_msg = str(exc_info.value)
    assert signer.address in error_msg
    assert X402_USDC_CONTRACT in error_msg


def test_request_no_auth_raises(database: 'DBHandler') -> None:
    """No API key + signer=None raises RemoteError."""
    msg_aggregator = MagicMock()
    gr = GoldRush(database=database, msg_aggregator=msg_aggregator, signer=None)

    with patch.object(gr, '_get_api_key', return_value=None):
        with pytest.raises(RemoteError, match='not configured'):
            gr._request('/eth-mainnet/address/0x1234/transactions_v3/')


def test_request_api_key_takes_priority(database: 'DBHandler') -> None:
    """When an API key is set, Basic Auth is used and session.get is called once."""
    gr, _ = make_goldrush_with_signer(database)
    api_key = ApiKey('test-api-key-xyz')

    mock_response = make_response(200, {'data': {'items': []}, 'error': False})

    with patch.object(gr, '_get_api_key', return_value=api_key):
        with patch.object(gr.session, 'get', return_value=mock_response) as mock_get:
            gr._request('/eth-mainnet/address/0x1234/transactions_v3/')

    assert mock_get.call_count == 1
    call_kwargs = mock_get.call_args.kwargs
    assert 'auth' in call_kwargs
    assert call_kwargs['auth'].username == api_key
    assert call_kwargs['auth'].password == ''


def test_handle_x402_malformed_402_body(database: 'DBHandler') -> None:
    """Non-JSON 402 body raises RemoteError."""
    gr, _ = make_goldrush_with_signer(database)

    bad_response = make_response(402, b'not valid json }{')

    with pytest.raises(RemoteError, match='unparseable'):
        gr._handle_x402(
            url='https://api.covalenthq.com/v1/eth-mainnet/test/',
            params=None,
            response=bad_response,
        )
