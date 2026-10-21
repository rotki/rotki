import hashlib
import json
import tracemalloc
import zlib
from compression import zstd
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.crypto import (
    BACKUP_CHUNK_SIZE,
    DEFAULT_BACKUP_KDF_PARAMS,
    BackupKdfParams,
    decrypt_backup,
    decrypt_legacy,
    encrypt_backup,
)
from rotkehlchen.data_handler import DataHandler, RemoteBackup
from rotkehlchen.errors.misc import (
    RemoteBackupError,
    UnableToDecryptRemoteData,
    UnsupportedRemoteBackup,
)
from rotkehlchen.premium.backup_container import (
    COMPRESSION_ZLIB,
    COMPRESSION_ZSTD,
    CONTAINER_MAGIC,
    USER_DB_ENTRY,
    build_container,
    decompress_entry,
    read_container,
)
from rotkehlchen.types import Timestamp

FAST_KDF = BackupKdfParams(time_cost=1, memory_kib=8 * 1024, lanes=1)  # the lowest bounds
PASSWORD = b'123'
HEADER_SIZE = 100
SEALED_CHUNK_SIZE = BACKUP_CHUNK_SIZE + 16  # with the tag
FRAME_SIZE = 4 + SEALED_CHUNK_SIZE  # with the length prefix
FROZEN_PASSWORD = b'rotki frozen backup v1'
FROZEN_TS = Timestamp(1760000000)
FROZEN_SALT, FROZEN_NONCE = bytes(range(32)), bytes(range(100, 112))
# Incompressible digests keep the compressed DB over one chunk, the repetitive tail makes
# the compressors emit real compressed blocks rather than stored ones
FROZEN_USER_DB = b''.join(hashlib.sha256(i.to_bytes(4, 'big')).digest() for i in range(2100)) + b'rotki' * 20000  # noqa: E501


def _frozen_backup(compression: str = COMPRESSION_ZSTD) -> bytes:
    name = 'premium_backup_v1.bin' if compression == COMPRESSION_ZLIB else 'premium_backup_v1_zstd.bin'  # noqa: E501
    return (Path(__file__).resolve().parent.parent / 'data' / name).read_bytes()


def _compress(data: bytes, compression: str) -> bytes:
    return zstd.compress(data) if compression == COMPRESSION_ZSTD else zlib.compress(data)


def _encrypt(payload: bytes, last_modify_ts: int = 1) -> bytes:
    return bytes(encrypt_backup(PASSWORD, Timestamp(last_modify_ts), [payload], FAST_KDF))


def _with_byte(data: bytes, index: int, value: int) -> bytes:
    return data[:index] + bytes([value]) + data[index + 1:]


def _flip(data: bytes, index: int) -> bytes:
    return _with_byte(data, index, data[index] ^ 0x01)


def _container(manifest: dict, *blocks: bytes) -> bytes:
    encoded = json.dumps(manifest).encode()
    return CONTAINER_MAGIC + len(encoded).to_bytes(4, 'big') + encoded + b''.join(blocks)


def _entry(
        name: str,
        data: bytes,
        required: bool = True,
        compression: str = COMPRESSION_ZLIB,
) -> dict:
    return {'name': name, 'required': required, 'compression': compression, 'size': len(data)}


@pytest.mark.parametrize(('size', 'chunks'), [
    (0, 1),
    (1, 1),
    (BACKUP_CHUNK_SIZE - 1, 1),
    (BACKUP_CHUNK_SIZE, 2),  # a full chunk, then the empty final one
    (BACKUP_CHUNK_SIZE + 1, 2),
    (3 * BACKUP_CHUNK_SIZE + 7, 4),
])
def test_backup_round_trip(size: int, chunks: int) -> None:
    payload = bytes(i % 251 for i in range(size))
    backup = _encrypt(payload, last_modify_ts=1700000000)
    assert len(backup) == HEADER_SIZE + chunks * (4 + 16) + size
    assert decrypt_backup(PASSWORD, backup) == (1700000000, payload)


def test_backup_payload_segments_are_joined() -> None:
    backup = encrypt_backup(PASSWORD, Timestamp(1), [b'a' * 70000, b'', b'b' * 3, bytearray(b'c')], FAST_KDF)  # noqa: E501
    assert decrypt_backup(PASSWORD, bytes(backup)) == (1, b'a' * 70000 + b'bbbc')


@pytest.mark.parametrize('compression', [COMPRESSION_ZSTD, COMPRESSION_ZLIB])
def test_frozen_backup_decrypts(compression: str) -> None:
    """A committed backup, so a change to the format, the key derivation or the
    decompression fails here. The zlib one proves that containers written with zlib can
    still be read."""
    data_handler = MagicMock()
    data_handler.db.password = FROZEN_PASSWORD.decode()
    assert DataHandler.decrypt_db(data_handler, _frozen_backup(compression)) == RemoteBackup(
        legacy=False,
        last_modify_ts=FROZEN_TS,
        user_db=FROZEN_USER_DB,
    )


@pytest.mark.parametrize('compression', [COMPRESSION_ZSTD, COMPRESSION_ZLIB])
def test_frozen_backup_is_what_the_writer_produces(compression: str) -> None:
    """Reuses the stored compressed DB, since compressor output can change between
    library versions while staying readable. The frozen backups were made by
    DataHandler.compress_and_encrypt_db, and for zlib by its pre-zstd streaming zlib level 9
    loop, with os.urandom patched to FROZEN_SALT and FROZEN_NONCE."""
    _, payload = decrypt_backup(FROZEN_PASSWORD, frozen := _frozen_backup(compression))
    entry = read_container(payload)[USER_DB_ENTRY]
    assert entry.compression == compression
    assert BACKUP_CHUNK_SIZE < len(entry.data) < len(FROZEN_USER_DB)
    with patch('rotkehlchen.crypto.os.urandom', side_effect=[FROZEN_SALT, FROZEN_NONCE]):
        backup = encrypt_backup(
            password=FROZEN_PASSWORD,
            last_modify_ts=FROZEN_TS,
            payload=build_container(entry.data, compression),
            kdf_params=DEFAULT_BACKUP_KDF_PARAMS,
        )
    assert backup == frozen


def test_full_final_chunk_is_accepted() -> None:
    """The writer makes the final chunk shorter than a full one, but a future writer may
    end on a full chunk and the reader has to accept that"""
    payload = bytes(BACKUP_CHUNK_SIZE)
    with patch('rotkehlchen.crypto._iter_chunks', return_value=iter([(payload, True)])):
        backup = _encrypt(payload)
    assert len(backup) == HEADER_SIZE + FRAME_SIZE
    assert decrypt_backup(PASSWORD, backup) == (1, payload)


def test_wrong_password_is_rejected_before_opening_any_chunk() -> None:
    backup = _encrypt(b'data')
    with patch('rotkehlchen.crypto.AESGCM') as aesgcm, pytest.raises(UnableToDecryptRemoteData):
        decrypt_backup(b'1234', backup)
    assert aesgcm.call_count == 0


def test_wrong_commitment_is_rejected_before_opening_any_chunk() -> None:
    backup = _flip(_encrypt(b'data'), HEADER_SIZE - 1)
    with patch('rotkehlchen.crypto.AESGCM') as aesgcm, pytest.raises(UnableToDecryptRemoteData):
        decrypt_backup(PASSWORD, backup)
    assert aesgcm.call_count == 0


@pytest.mark.parametrize('index', [
    20,  # salt
    50,  # base nonce
    61,  # last_modify_ts
    HEADER_SIZE + 2,  # length of the first chunk
    HEADER_SIZE + 4 + 100,  # ciphertext of the first chunk
    HEADER_SIZE + FRAME_SIZE - 1,  # tag of the first chunk
    HEADER_SIZE + FRAME_SIZE + 4,  # ciphertext of the final chunk
    -1,  # tag of the final chunk
])
def test_modified_backup_is_rejected(index: int) -> None:
    with pytest.raises(UnableToDecryptRemoteData):
        decrypt_backup(PASSWORD, _flip(_encrypt(bytes(BACKUP_CHUNK_SIZE + 10)), index))


def test_kdf_parameters_changed_within_bounds_are_rejected() -> None:
    with pytest.raises(UnableToDecryptRemoteData):
        decrypt_backup(PASSWORD, _with_byte(_encrypt(b'data'), 10, FAST_KDF.time_cost + 1))


@pytest.mark.parametrize('length', [
    pytest.param(HEADER_SIZE + 2 * FRAME_SIZE, id='final chunk dropped'),
    pytest.param(HEADER_SIZE + FRAME_SIZE, id='cut after the first chunk'),
    pytest.param(HEADER_SIZE, id='cut back to the header'),
    pytest.param(HEADER_SIZE + 2, id='cut inside a length'),
    pytest.param(HEADER_SIZE - 1, id='cut inside the header'),
    pytest.param(-1, id='cut inside the final chunk'),
])
def test_truncated_backup_is_rejected(length: int) -> None:
    backup = _encrypt(bytes(2 * BACKUP_CHUNK_SIZE + 20))  # two full chunks and a final one
    with pytest.raises(UnableToDecryptRemoteData):
        decrypt_backup(PASSWORD, backup[:length])


@pytest.mark.parametrize('modify', [
    pytest.param(
        lambda b: b[:HEADER_SIZE] + b[HEADER_SIZE + FRAME_SIZE:2 * FRAME_SIZE + HEADER_SIZE] + b[HEADER_SIZE:HEADER_SIZE + FRAME_SIZE] + b[HEADER_SIZE + 2 * FRAME_SIZE:],  # noqa: E501
        id='chunks reordered',
    ),
    pytest.param(lambda b: b + b'\x00', id='trailing byte'),
    pytest.param(lambda b: b + b[-40:], id='trailing copy of the final chunk'),
    pytest.param(lambda b: b[:HEADER_SIZE] + (SEALED_CHUNK_SIZE + 1).to_bytes(4, 'big') + b[HEADER_SIZE + 4:], id='chunk length too big'),  # noqa: E501
    pytest.param(lambda b: b[:-40] + (15).to_bytes(4, 'big') + b[-36:], id='chunk length below the tag size'),  # noqa: E501
])
def test_rearranged_backup_is_rejected(modify) -> None:
    backup = _encrypt(bytes(2 * BACKUP_CHUNK_SIZE + 20))  # two full chunks and a final one
    with pytest.raises(UnableToDecryptRemoteData):
        decrypt_backup(PASSWORD, modify(backup))


@pytest.mark.parametrize('magic', [b'RGCM\x00\x00\x00\x01', b'RKPBAK02', b'\x00' * 8])
def test_other_magic_is_rejected(magic: bytes) -> None:
    """Includes a streamcrypt file from the backup manager and a relabelled backup"""
    with pytest.raises(UnableToDecryptRemoteData):
        decrypt_backup(PASSWORD, magic + _encrypt(b'data')[8:])


@pytest.mark.parametrize(('index', 'value'), [
    (8, 2),  # unknown version
    (9, 2),  # unknown kdf
    (10, 0),  # passes below the bound
    (10, 9),  # passes above the bound
    (11, 0xff),  # memory above the bound
    (13, 0),  # memory below the bound (8 MiB is 0x00002000 KiB)
    (15, 0),  # lanes below the bound
    (15, 9),  # lanes above the bound
])
def test_unsupported_header_is_rejected_before_derivation(index: int, value: int) -> None:
    backup = _with_byte(_encrypt(b'data'), index, value)
    with patch('rotkehlchen.crypto.Argon2id') as argon2id, pytest.raises(UnsupportedRemoteBackup):
        decrypt_backup(PASSWORD, backup)
    assert argon2id.call_count == 0


@pytest.mark.parametrize('compression', [COMPRESSION_ZSTD, COMPRESSION_ZLIB])
def test_container_round_trip(compression: str) -> None:
    entries = read_container(b''.join(build_container(compressed := _compress(b'db' * 100, compression), compression)))  # noqa: E501
    assert list(entries) == [USER_DB_ENTRY]
    assert entries[USER_DB_ENTRY].compression == compression
    assert bytes(entries[USER_DB_ENTRY].data) == compressed
    assert decompress_entry(entries[USER_DB_ENTRY]) == b'db' * 100


def test_container_skips_unknown_optional_entry() -> None:
    entries = read_container(_container(
        {'container_version': 1, 'entries': [
            _entry('globaldb_diff', diff := b'diff', required=False, compression='lz4'),
            _entry(USER_DB_ENTRY, user_db := zlib.compress(b'db')),
        ]},
        diff,
        user_db,
    ))
    assert list(entries) == [USER_DB_ENTRY]
    assert decompress_entry(entries[USER_DB_ENTRY]) == b'db'


@pytest.mark.parametrize('payload', [
    pytest.param(_container(
        {'container_version': 1, 'entries': [_entry(USER_DB_ENTRY, b'db'), _entry('globaldb_diff', b'x')]},  # noqa: E501
        b'db',
        b'x',
    ), id='unknown required entry'),
    pytest.param(_container(
        {'container_version': 1, 'entries': [_entry(USER_DB_ENTRY, b'db', compression='lz4')]},
        b'db',
    ), id='unknown compression of the user DB'),
    pytest.param(_container({'container_version': 2, 'entries': []}), id='newer container'),
])
def test_container_needing_newer_rotki_is_unsupported(payload: bytes) -> None:
    with pytest.raises(UnsupportedRemoteBackup):
        read_container(payload)


@pytest.mark.parametrize('payload', [
    pytest.param(b'', id='empty'),
    pytest.param(b'RKC2' + bytes(4), id='wrong magic'),
    pytest.param(CONTAINER_MAGIC + (1024 * 1024 + 1).to_bytes(4, 'big') + b'{}', id='manifest over the limit'),  # noqa: E501
    pytest.param(CONTAINER_MAGIC + (100).to_bytes(4, 'big') + b'{}', id='manifest past the end'),
    pytest.param(CONTAINER_MAGIC + (2).to_bytes(4, 'big') + b'{]', id='manifest not json'),
    pytest.param(_container({'entries': []}), id='no container version'),
    pytest.param(_container({'container_version': True, 'entries': []}), id='bool container version'),  # noqa: E501
    pytest.param(_container({'container_version': 1, 'entries': {}}), id='entries not a list'),
    pytest.param(_container({'container_version': 1, 'entries': []}), id='no user DB'),
    pytest.param(_container(
        {'container_version': 1, 'entries': [_entry(USER_DB_ENTRY, b'a'), _entry(USER_DB_ENTRY, b'b')]},  # noqa: E501
        b'a',
        b'b',
    ), id='duplicate names'),
    pytest.param(_container(
        {'container_version': 1, 'entries': [_entry('other', b'a', required=False), _entry('other', b'b', required=False), _entry(USER_DB_ENTRY, b'c')]},  # noqa: E501
        b'a',
        b'b',
        b'c',
    ), id='duplicate unknown names'),
    pytest.param(_container({'container_version': 1, 'entries': [_entry(USER_DB_ENTRY, b'db')]}, b'db', b'x'), id='trailing data'),  # noqa: E501
    pytest.param(_container({'container_version': 1, 'entries': [_entry(USER_DB_ENTRY, b'db')]}, b'd'), id='data shorter than declared'),  # noqa: E501
    pytest.param(_container({'container_version': 1, 'entries': [{**_entry(USER_DB_ENTRY, b'db'), 'size': -1}]}, b'db'), id='negative size'),  # noqa: E501
    pytest.param(_container({'container_version': 1, 'entries': [{**_entry(USER_DB_ENTRY, b'db'), 'required': 1}]}, b'db'), id='required not a bool'),  # noqa: E501
    pytest.param(_container({'container_version': 1, 'entries': [_entry(f'e{i}', b'', required=False) for i in range(32)] + [_entry(USER_DB_ENTRY, b'')]}), id='too many entries'),  # noqa: E501
])
def test_malformed_container_is_rejected(payload: bytes) -> None:
    with pytest.raises(RemoteBackupError) as e:
        read_container(payload)
    assert type(e.value) is RemoteBackupError


@pytest.mark.parametrize(('compression', 'data'), [
    pytest.param(COMPRESSION_ZLIB, zlib.compress(b'db')[:-2], id='truncated zlib stream'),
    pytest.param(COMPRESSION_ZLIB, zlib.compress(b'db') + b'x', id='data after the zlib stream'),
    pytest.param(COMPRESSION_ZLIB, b'not zlib', id='not zlib'),
    pytest.param(COMPRESSION_ZLIB, zlib.compress(bytes(101)), id='zlib over the size limit'),
    pytest.param(COMPRESSION_ZSTD, zstd.compress(b'db')[:-2], id='truncated zstd stream'),
    pytest.param(COMPRESSION_ZSTD, zstd.compress(b'db') + b'x', id='data after the zstd stream'),
    pytest.param(COMPRESSION_ZSTD, zstd.compress(b'a') + zstd.compress(b'b'), id='two zstd frames'),  # noqa: E501
    pytest.param(COMPRESSION_ZSTD, b'not zstd', id='not zstd'),
    pytest.param(COMPRESSION_ZSTD, zstd.compress(bytes(101)), id='zstd over the size limit'),
])
def test_bad_entry_data_is_rejected(compression: str, data: bytes) -> None:
    entry = read_container(_container({'container_version': 1, 'entries': [_entry(USER_DB_ENTRY, data, compression=compression)]}, data))[USER_DB_ENTRY]  # noqa: E501
    with patch('rotkehlchen.premium.backup_container.MAX_ENTRY_SIZE', 100), pytest.raises(RemoteBackupError):  # noqa: E501
        decompress_entry(entry)


@pytest.mark.parametrize('compression', [COMPRESSION_ZSTD, COMPRESSION_ZLIB])
def test_decompression_bomb_is_not_expanded(compression: str) -> None:
    """The output must be bounded while decompressing, not only checked afterwards"""
    data = _compress(bytes(64 * 1024 ** 2), compression)
    entry = read_container(_container({'container_version': 1, 'entries': [_entry(USER_DB_ENTRY, data, compression=compression)]}, data))[USER_DB_ENTRY]  # noqa: E501
    tracemalloc.start()
    try:
        with patch('rotkehlchen.premium.backup_container.MAX_ENTRY_SIZE', 100), pytest.raises(RemoteBackupError):  # noqa: E501
            decompress_entry(entry)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 1024 ** 2


@pytest.mark.parametrize('compression', [COMPRESSION_ZSTD, COMPRESSION_ZLIB])
def test_entry_at_the_size_limit_is_accepted(compression: str) -> None:
    data = _compress(bytes(100), compression)
    entry = read_container(_container({'container_version': 1, 'entries': [_entry(USER_DB_ENTRY, data, compression=compression)]}, data))[USER_DB_ENTRY]  # noqa: E501
    with patch('rotkehlchen.premium.backup_container.MAX_ENTRY_SIZE', 100):
        assert decompress_entry(entry) == bytes(100)


@pytest.mark.parametrize('length', [0, 15, 16, 17, 47])
def test_legacy_backup_with_bad_length_is_rejected(length: int) -> None:
    """Too short for the IV plus one block, or not whole blocks, would otherwise raise
    ValueError or IndexError and fail the login instead of reporting the decrypt error"""
    with pytest.raises(UnableToDecryptRemoteData, match='whole number of AES blocks'):
        decrypt_legacy(PASSWORD, bytes(length))


def test_legacy_backup_with_bad_zlib_is_malformed() -> None:
    with (
        patch('rotkehlchen.data_handler.decrypt_legacy', return_value=b'not zlib'),
        pytest.raises(RemoteBackupError, match='malformed'),
    ):
        DataHandler.decrypt_db(MagicMock(), bytes(32))
