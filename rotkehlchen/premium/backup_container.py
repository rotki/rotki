"""The payload that a premium backup encrypts: a JSON manifest, then one data block per entry.

A backup is three layers. The user DB is zstd compressed, wrapped in this container, and the
container is encrypted by crypto.encrypt_backup into the RKPBAK01 envelope. The container is
laid out as:

    magic            4 bytes  b'RKC1'
    manifest length  4 bytes  big endian, at most MAX_MANIFEST_SIZE
    manifest         n bytes  JSON, see below
    entry data                one block per manifest entry, in manifest order, nothing after

    {"container_version": 1, "entries": [
        {"name": "user_db", "required": true, "compression": "zstd", "size": 48211233}
    ]}

size is the stored, so still compressed, byte count of the entry's block.

New kinds of content are new entries, not a new backup format. An entry the reader does not
know is skipped when optional and refused when required. Entries have logical names, never
paths, so restoring one can't write anywhere but where the reader puts it.
"""
import json
import logging
import struct
import zlib
from compression import zstd
from typing import TYPE_CHECKING, Final, NamedTuple

from rotkehlchen.errors.misc import RemoteBackupError, UnsupportedRemoteBackup
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from collections.abc import Buffer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

CONTAINER_MAGIC: Final = b'RKC1'
CONTAINER_VERSION: Final = 1
USER_DB_ENTRY: Final = 'user_db'
COMPRESSION_ZSTD: Final = 'zstd'
COMPRESSION_ZLIB: Final = 'zlib'  # only read, for containers written with zlib
_SUPPORTED_COMPRESSIONS: Final = frozenset((COMPRESSION_ZSTD, COMPRESSION_ZLIB))
_MANIFEST_LENGTH: Final = struct.Struct('>I')
_PREAMBLE_SIZE: Final = len(CONTAINER_MAGIC) + _MANIFEST_LENGTH.size
# Limits against decompression bombs and oversized manifests
MAX_MANIFEST_SIZE: Final = 1024 * 1024
MAX_ENTRIES: Final = 32
MAX_ENTRY_SIZE: Final = 16 * 1024 ** 3  # decompressed bytes
_KNOWN_ENTRIES: Final = frozenset((USER_DB_ENTRY,))
MALFORMED_BACKUP_MSG: Final = 'The backup on the rotki server is malformed and can not be restored.'  # noqa: E501


class ContainerEntry(NamedTuple):
    name: str
    compression: str
    data: memoryview  # as stored, so still compressed


def build_container(user_db: Buffer, compression: str = COMPRESSION_ZSTD) -> list[Buffer]:
    """Returns the container for the given compressed user DB, as consecutive segments
    so that the compressed DB is not copied: the magic, manifest length and manifest as one
    segment, then the user DB itself. The segments are never joined, encrypt_backup reads
    them chunk by chunk."""
    manifest = json.dumps(
        {
            'container_version': CONTAINER_VERSION,
            'entries': [{
                'name': USER_DB_ENTRY,
                'required': True,
                'compression': compression,
                'size': len(memoryview(user_db)),  # stored bytes, not decompressed
            }],
        },
        separators=(',', ':'),
    ).encode()
    return [CONTAINER_MAGIC + _MANIFEST_LENGTH.pack(len(manifest)) + manifest, user_db]


def read_container(payload: bytes | bytearray) -> dict[str, ContainerEntry]:
    """Validates the whole container and returns the entries this rotki version knows,
    by name. Nothing is decompressed here.

    May raise:
    - UnsupportedRemoteBackup if the container version, an unknown required entry or the
    compression of a known entry needs a newer rotki version.
    - RemoteBackupError if the container is malformed: a bad manifest, duplicate names, no
    user DB or sizes that don't add up to the data.
    """
    if len(payload) < _PREAMBLE_SIZE or not payload.startswith(CONTAINER_MAGIC):
        raise RemoteBackupError(MALFORMED_BACKUP_MSG)

    (manifest_length,) = _MANIFEST_LENGTH.unpack_from(payload, len(CONTAINER_MAGIC))
    if manifest_length > MAX_MANIFEST_SIZE or _PREAMBLE_SIZE + manifest_length > len(payload):
        raise RemoteBackupError(MALFORMED_BACKUP_MSG)

    try:
        manifest = json.loads(payload[_PREAMBLE_SIZE:_PREAMBLE_SIZE + manifest_length])
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise RemoteBackupError(MALFORMED_BACKUP_MSG) from e

    if not isinstance(manifest, dict) or type(version := manifest.get('container_version')) is not int:  # noqa: E501
        raise RemoteBackupError(MALFORMED_BACKUP_MSG)
    if version != CONTAINER_VERSION:  # a different structure that only a newer rotki parses
        raise UnsupportedRemoteBackup
    if not isinstance(entries := manifest.get('entries'), list) or len(entries) > MAX_ENTRIES:
        raise RemoteBackupError(MALFORMED_BACKUP_MSG)

    view, offset = memoryview(payload), _PREAMBLE_SIZE + manifest_length
    names: set[str] = set()
    known_entries: dict[str, ContainerEntry] = {}
    for entry in entries:
        if not (
            isinstance(entry, dict) and
            isinstance(name := entry.get('name'), str) and
            isinstance(required := entry.get('required'), bool) and
            isinstance(compression := entry.get('compression'), str) and
            type(size := entry.get('size')) is int and size >= 0  # bool is an int subclass
        ) or name in names:
            raise RemoteBackupError(MALFORMED_BACKUP_MSG)

        names.add(name)
        data, offset = view[offset:offset + size], offset + size
        if name not in _KNOWN_ENTRIES:
            if required:
                raise UnsupportedRemoteBackup

            log.warning('Skipping unknown optional entry of the remote backup', name=name)
            continue

        if compression not in _SUPPORTED_COMPRESSIONS:
            raise UnsupportedRemoteBackup

        known_entries[name] = ContainerEntry(name=name, compression=compression, data=data)

    if offset != len(payload) or USER_DB_ENTRY not in known_entries:
        raise RemoteBackupError(MALFORMED_BACKUP_MSG)

    return known_entries


def decompress_entry(entry: ContainerEntry) -> bytes:
    """Decompresses the entry, refusing to produce more than MAX_ENTRY_SIZE bytes.

    May raise:
    - RemoteBackupError if the data is not one complete stream of the entry's
    compression or is too big.
    """
    if entry.compression == COMPRESSION_ZSTD:
        zstd_decompressor = zstd.ZstdDecompressor()
        try:
            data = zstd_decompressor.decompress(entry.data, MAX_ENTRY_SIZE + 1)
        except zstd.ZstdError as e:
            raise RemoteBackupError(MALFORMED_BACKUP_MSG) from e

        if len(data) > MAX_ENTRY_SIZE or not zstd_decompressor.eof or len(zstd_decompressor.unused_data) != 0:  # noqa: E501
            raise RemoteBackupError(MALFORMED_BACKUP_MSG)

        return data

    decompressor = zlib.decompressobj()
    try:
        data = decompressor.decompress(entry.data, MAX_ENTRY_SIZE + 1)
    except zlib.error as e:
        raise RemoteBackupError(MALFORMED_BACKUP_MSG) from e

    if len(data) > MAX_ENTRY_SIZE or not decompressor.eof or len(decompressor.unused_data) != 0:
        raise RemoteBackupError(MALFORMED_BACKUP_MSG)

    return data
