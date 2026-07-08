import hashlib
import itertools
import os
from base64 import b64decode
from binascii import Error as BinasciiError
from dataclasses import dataclass
from typing import Any, Final, Self

import requests
from base58 import b58decode, b58encode

from rotkehlchen.errors.serialization import DeserializationError

LOOKUP_TABLE_META_SIZE: Final = 56
PDA_MARKER: Final = b'ProgramDerivedAddress'

_ED25519_P: Final = 2**255 - 19
_ED25519_D: Final = -121665 * pow(121666, -1, _ED25519_P) % _ED25519_P
_JSONRPC_COUNTER = itertools.count(1)
_RPC_DECODE_EXCEPTIONS = (KeyError, TypeError, ValueError, BinasciiError, DeserializationError)


class RPCException(Exception):
    """Exception raised for Solana JSON-RPC errors."""


class SolanaRpcException(Exception):
    """Exception raised when the Solana RPC request fails."""


class SerdeJSONError(Exception):
    """Exception raised when a Solana RPC response can't be decoded."""


class Pubkey:
    """A 32-byte Solana public key."""

    __slots__ = ('_value',)

    def __init__(self, value: bytes):
        if len(value) != 32:
            raise ValueError(f'expected a 32-byte public key, got {len(value)} bytes')
        self._value = value

    @classmethod
    def from_string(cls, value: str) -> Self:
        try:
            return cls(b58decode(value))
        except ValueError as e:
            raise ValueError(f'invalid public key {value}') from e

    @classmethod
    def from_bytes(cls, value: bytes) -> Self:
        return cls(value)

    @classmethod
    def new_unique(cls) -> Self:
        return cls(os.urandom(32))

    @staticmethod
    def _is_on_curve(value: bytes) -> bool:
        if len(value) != 32:
            return False

        y = int.from_bytes(value, byteorder='little') & ((1 << 255) - 1)
        y2 = y * y % _ED25519_P
        denominator = (_ED25519_D * y2 + 1) % _ED25519_P
        if denominator == 0:
            return False

        x2 = (y2 - 1) * pow(denominator, -1, _ED25519_P) % _ED25519_P
        x = pow(x2, (_ED25519_P + 3) // 8, _ED25519_P)
        if (x * x - x2) % _ED25519_P != 0:
            x = x * pow(2, (_ED25519_P - 1) // 4, _ED25519_P) % _ED25519_P
        return (x * x - x2) % _ED25519_P == 0

    @classmethod
    def create_program_address(cls, seeds: list[bytes], program_id: 'Pubkey') -> 'Pubkey':
        if len(seeds) > 16:
            raise ValueError('too many seeds')
        if any(len(seed) > 32 for seed in seeds):
            raise ValueError('seed length must be at most 32 bytes')

        value = hashlib.sha256(b''.join(seeds) + bytes(program_id) + PDA_MARKER).digest()
        if cls._is_on_curve(value):
            raise ValueError('derived address must not be on curve')
        return cls(value)

    @classmethod
    def find_program_address(
            cls,
            seeds: list[bytes],
            program_id: 'Pubkey',
    ) -> tuple['Pubkey', int]:
        for bump_seed in range(255, -1, -1):
            try:
                return (
                    cls.create_program_address([*seeds, bytes([bump_seed])], program_id),
                    bump_seed,
                )
            except ValueError:
                continue
        raise ValueError('unable to find a viable program address')

    def __bytes__(self) -> bytes:
        return self._value

    def to_bytes(self) -> bytes:
        return self._value

    def __str__(self) -> str:
        return b58encode(self._value).decode()

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Pubkey) and self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)


class Signature:
    """A 64-byte Solana transaction signature."""

    __slots__ = ('_value',)

    def __init__(self, value: bytes):
        if len(value) != 64:
            raise ValueError(f'expected a 64-byte signature, got {len(value)} bytes')
        self._value = value

    @classmethod
    def from_string(cls, value: str) -> Self:
        try:
            return cls(b58decode(value))
        except ValueError as e:
            raise ValueError(f'invalid signature {value}') from e

    @classmethod
    def from_bytes(cls, value: bytes) -> Self:
        return cls(value)

    @classmethod
    def new_unique(cls) -> 'Signature':
        return cls(os.urandom(64))

    @classmethod
    def default(cls) -> 'Signature':
        return cls(bytes(64))

    def to_bytes(self) -> bytes:
        return self._value

    def __bytes__(self) -> bytes:
        return self._value

    def __str__(self) -> str:
        return b58encode(self._value).decode()

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Signature) and self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)


class Hash(Pubkey):
    """A 32-byte Solana hash."""


@dataclass(frozen=True)
class Account:
    data: bytes
    executable: bool
    lamports: int
    owner: Pubkey
    rent_epoch: int | None = None
    space: int | None = None


@dataclass(frozen=True)
class RpcKeyedAccount:
    pubkey: Pubkey
    account: Account


@dataclass(frozen=True)
class UiCompiledInstruction:
    accounts: list[int]
    data: str
    program_id_index: int


@dataclass(frozen=True)
class UiInnerInstructions:
    index: int
    instructions: list[UiCompiledInstruction]


@dataclass(frozen=True)
class MessageAddressTableLookup:
    account_key: Pubkey
    writable_indexes: list[int]
    readonly_indexes: list[int]


UiAddressTableLookup = MessageAddressTableLookup


@dataclass(frozen=True)
class UiTokenBalance:
    account_index: int
    mint: Pubkey
    owner: Pubkey | None


@dataclass(frozen=True)
class TransactionMeta:
    fee: int
    err: Any | None
    inner_instructions: list[UiInnerInstructions] | None
    pre_token_balances: list[UiTokenBalance] | None
    post_token_balances: list[UiTokenBalance] | None


@dataclass(frozen=True)
class UiMessage:
    account_keys: list[Pubkey]
    instructions: list[UiCompiledInstruction]
    address_table_lookups: list[MessageAddressTableLookup] | None


@dataclass(frozen=True)
class UiTransaction:
    signatures: list[Signature]
    message: UiMessage


@dataclass(frozen=True)
class TransactionWithMeta:
    transaction: UiTransaction
    meta: TransactionMeta | None


@dataclass(frozen=True)
class EncodedConfirmedTransactionWithStatusMeta:
    slot: int
    block_time: int | None
    transaction: TransactionWithMeta


@dataclass(frozen=True)
class SignatureStatus:
    signature: Signature


@dataclass(frozen=True)
class Block:
    blockhash: Hash


@dataclass(frozen=True)
class RPCResponse:
    value: Any


@dataclass(frozen=True)
class MemcmpOpts:
    offset: int
    bytes: str


@dataclass(frozen=True)
class TokenAccountOpts:
    program_id: Pubkey


def _decode_account_data(data: Any) -> bytes:
    """Decode raw account payload data.
    May raise SerdeJSONError if the data shape or encoding is unsupported.
    """
    if isinstance(data, list) and len(data) >= 2:
        if data[1] != 'base64':
            raise SerdeJSONError(f'Unexpected solana account encoding {data[1]}')
        return b64decode(data[0])
    if isinstance(data, str):
        return b58decode(data)
    raise SerdeJSONError(f'Unexpected solana account data format {data!r}')


def _parse_account(raw_account: dict[str, Any]) -> Account:
    """Parse a Solana account JSON object.
    May raise SerdeJSONError if the account data is invalid.
    """
    return Account(
        data=_decode_account_data(raw_account['data']),
        executable=raw_account['executable'],
        lamports=raw_account['lamports'],
        owner=Pubkey.from_string(raw_account['owner']),
        rent_epoch=raw_account.get('rentEpoch'),
        space=raw_account.get('space'),
    )


def _parse_instruction(raw_instruction: dict[str, Any]) -> UiCompiledInstruction:
    """Parse a Solana instruction JSON object.
    May raise SerdeJSONError from the RPC method wrapper if the instruction data is invalid.
    """
    return UiCompiledInstruction(
        accounts=list(raw_instruction['accounts']),
        data=raw_instruction['data'],
        program_id_index=raw_instruction['programIdIndex'],
    )


def _parse_token_balance(raw_balance: dict[str, Any]) -> UiTokenBalance:
    """Parse a token balance JSON object.
    May raise SerdeJSONError from the RPC method wrapper if the balance data is invalid.
    """
    return UiTokenBalance(
        account_index=raw_balance['accountIndex'],
        mint=Pubkey.from_string(raw_balance['mint']),
        owner=None if (owner := raw_balance.get('owner')) is None else Pubkey.from_string(owner),
    )


def _parse_transaction(raw_tx: dict[str, Any]) -> EncodedConfirmedTransactionWithStatusMeta:
    """Parse a Solana transaction JSON object.
    May raise SerdeJSONError from the RPC method wrapper if the transaction data is invalid.
    """
    raw_transaction = raw_tx['transaction']
    raw_message = raw_transaction['message']
    return EncodedConfirmedTransactionWithStatusMeta(
        slot=raw_tx['slot'],
        block_time=raw_tx.get('blockTime'),
        transaction=TransactionWithMeta(
            transaction=UiTransaction(
                signatures=[
                    Signature.from_string(signature)
                    for signature in raw_transaction['signatures']
                ],
                message=UiMessage(
                    account_keys=[
                        Pubkey.from_string(entry if isinstance(entry, str) else entry['pubkey'])
                        for entry in raw_message['accountKeys']
                    ],
                    instructions=[
                        _parse_instruction(entry) for entry in raw_message['instructions']
                    ],
                    address_table_lookups=None if (lookups := raw_message.get('addressTableLookups')) is None else [  # noqa: E501
                        MessageAddressTableLookup(
                            account_key=Pubkey.from_string(entry['accountKey']),
                            writable_indexes=list(entry['writableIndexes']),
                            readonly_indexes=list(entry['readonlyIndexes']),
                        ) for entry in lookups
                    ],
                ),
            ),
            meta=None if (raw_meta := raw_tx.get('meta')) is None else TransactionMeta(
                fee=raw_meta['fee'],
                err=raw_meta.get('err'),
                inner_instructions=None if (
                    inner := raw_meta.get('innerInstructions')
                ) is None else [
                    UiInnerInstructions(
                        index=entry['index'],
                        instructions=[_parse_instruction(instruction) for instruction in entry['instructions']],  # noqa: E501
                    ) for entry in inner
                ],
                pre_token_balances=None if (pre := raw_meta.get('preTokenBalances')) is None else [_parse_token_balance(entry) for entry in pre],  # noqa: E501
                post_token_balances=None if (post := raw_meta.get('postTokenBalances')) is None else [_parse_token_balance(entry) for entry in post],  # noqa: E501
            ),
        ),
    )


def _parse_keyed_account(entry: dict[str, Any]) -> RpcKeyedAccount:
    """Parse an RPC keyed-account JSON object.
    May raise SerdeJSONError from the RPC method wrapper if the account data is invalid.
    """
    return RpcKeyedAccount(
        pubkey=Pubkey.from_string(entry['pubkey']),
        account=_parse_account(entry['account']),
    )


class Client:
    """Small Solana JSON-RPC client implementing the methods rotki uses."""

    def __init__(self, endpoint: str, timeout: int):
        self.endpoint = endpoint
        self.timeout = timeout
        self.session = requests.Session()  # keep-alive: tx sync makes many sequential calls and a new TLS handshake per call is ~4x slower  # noqa: E501

    def _request(self, method: str, params: list[Any] | None = None) -> Any:
        """Perform a Solana JSON-RPC request.
        May raise SolanaRpcException, RPCException or SerdeJSONError.
        """
        try:
            response = self.session.post(
                url=self.endpoint,
                json={
                    'jsonrpc': '2.0',
                    'id': next(_JSONRPC_COUNTER),
                    'method': method,
                    'params': params or [],
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.JSONDecodeError as e:  # subclasses RequestException, so must be caught first  # noqa: E501
            raise SerdeJSONError(str(e)) from e
        except requests.exceptions.RequestException as e:
            raise SolanaRpcException(str(e)) from e

        if not isinstance(payload, dict):
            raise SerdeJSONError(f'Unexpected solana RPC response format {payload!r}')
        if (error := payload.get('error')) is not None:
            raise RPCException(error)
        if 'result' not in payload:
            raise SerdeJSONError(f'Missing result in solana RPC response {payload!r}')
        return payload['result']

    def is_connected(self) -> bool:
        self.get_health()
        return True

    def get_health(self) -> RPCResponse:
        return RPCResponse(value=self._request('getHealth'))

    def get_genesis_hash(self) -> RPCResponse:
        try:
            return RPCResponse(value=Hash.from_string(self._request('getGenesisHash')))
        except _RPC_DECODE_EXCEPTIONS as e:
            raise SerdeJSONError(f'Failed to decode solana getGenesisHash response due to {e!s}') from e  # noqa: E501

    def get_block(self, slot: int) -> RPCResponse:
        try:
            return RPCResponse(value=Block(blockhash=Hash.from_string(self._request('getBlock', [
                slot,
                {'transactionDetails': 'none', 'rewards': False},
            ])['blockhash'])))
        except _RPC_DECODE_EXCEPTIONS as e:
            raise SerdeJSONError(f'Failed to decode solana getBlock response due to {e!s}') from e

    def get_account_info(self, pubkey: Pubkey) -> RPCResponse:
        try:
            result = self._request('getAccountInfo', [str(pubkey), {'encoding': 'base64'}])
            return RPCResponse(
                value=None if result['value'] is None else _parse_account(result['value']),
            )
        except _RPC_DECODE_EXCEPTIONS as e:
            raise SerdeJSONError(f'Failed to decode solana getAccountInfo response due to {e!s}') from e  # noqa: E501

    def get_multiple_accounts(self, pubkeys: list[Pubkey]) -> RPCResponse:
        try:
            result = self._request('getMultipleAccounts', [
                [str(pubkey) for pubkey in pubkeys],
                {'encoding': 'base64'},
            ])
            return RPCResponse(value=[
                None if account is None else _parse_account(account)
                for account in result['value']
            ])
        except _RPC_DECODE_EXCEPTIONS as e:
            raise SerdeJSONError(f'Failed to decode solana getMultipleAccounts response due to {e!s}') from e  # noqa: E501

    def get_token_accounts_by_owner(self, owner: Pubkey, opts: TokenAccountOpts) -> RPCResponse:
        try:
            result = self._request('getTokenAccountsByOwner', [
                str(owner),
                {'programId': str(opts.program_id)},
                {'encoding': 'base64'},
            ])
            return RPCResponse(value=[_parse_keyed_account(entry) for entry in result['value']])
        except _RPC_DECODE_EXCEPTIONS as e:
            raise SerdeJSONError(f'Failed to decode solana getTokenAccountsByOwner response due to {e!s}') from e  # noqa: E501

    def get_program_accounts(self, pubkey: Pubkey, filters: list[MemcmpOpts]) -> RPCResponse:
        try:
            result = self._request('getProgramAccounts', [
                str(pubkey),
                {
                    'encoding': 'base64',
                    'filters': [{'memcmp': {'offset': entry.offset, 'bytes': entry.bytes}} for entry in filters],  # noqa: E501
                },
            ])
            return RPCResponse(value=[_parse_keyed_account(entry) for entry in result])
        except _RPC_DECODE_EXCEPTIONS as e:
            raise SerdeJSONError(f'Failed to decode solana getProgramAccounts response due to {e!s}') from e  # noqa: E501

    def get_signatures_for_address(
            self,
            account: Pubkey,
            limit: int,
            before: Signature | None = None,
            until: Signature | None = None,
    ) -> RPCResponse:
        config: dict[str, Any] = {'limit': limit}
        if before is not None:
            config['before'] = str(before)
        if until is not None:
            config['until'] = str(until)
        try:
            return RPCResponse(value=[
                SignatureStatus(signature=Signature.from_string(entry['signature']))
                for entry in self._request('getSignaturesForAddress', [str(account), config])
            ])
        except _RPC_DECODE_EXCEPTIONS as e:
            raise SerdeJSONError(f'Failed to decode solana getSignaturesForAddress response due to {e!s}') from e  # noqa: E501

    def get_transaction(
            self,
            tx_sig: Signature,
            max_supported_transaction_version: int,
    ) -> RPCResponse:
        result = self._request('getTransaction', [
            str(tx_sig),
            {
                'encoding': 'json',
                'maxSupportedTransactionVersion': max_supported_transaction_version,
            },
        ])
        try:
            return RPCResponse(value=None if result is None else _parse_transaction(result))
        except _RPC_DECODE_EXCEPTIONS as e:
            raise SerdeJSONError(f'Failed to decode solana getTransaction response due to {e!s}') from e  # noqa: E501
