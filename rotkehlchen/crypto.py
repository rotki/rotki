import hmac
import os
import struct
from typing import TYPE_CHECKING, Final, NamedTuple

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from rotkehlchen.errors.misc import UnableToDecryptRemoteData, UnsupportedRemoteBackup
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from collections.abc import Buffer, Iterable, Iterator

AES_BLOCK_SIZE = 16

BACKUP_MAGIC: Final = b'RKPBAK01'
BACKUP_VERSION: Final = 1
BACKUP_CHUNK_SIZE: Final = 64 * 1024  # plaintext bytes per chunk
_KDF_ARGON2ID: Final = 1
# Domain separation: keys derived here can't collide with any other use of the same password
_ARGON2_AD: Final = b'rotki premium backup v1'
_ENC_KEY_INFO: Final = b'rotki premium backup v1 enc'
_COMMITMENT_INFO: Final = b'rotki premium backup v1 commit'
# magic, version, kdf, kdf passes, kdf memory in KiB, kdf lanes, salt, base nonce,
# last_modify_ts, key commitment. 100 bytes, all of it authenticated as each chunk's AAD.
_HEADER: Final = struct.Struct('>8sBBBIB32s12sQ32s')
_CHUNK_LENGTH: Final = struct.Struct('>I')
_TAG_SIZE: Final = 16
_DECRYPT_ERROR: Final = 'Could not decrypt the backup. The password is wrong or the backup was modified.'  # noqa: E501


class BackupKdfParams(NamedTuple):
    time_cost: int  # Argon2id passes
    memory_kib: int
    lanes: int


# Below the caps that decrypt_backup accepts, so a later release can raise the cost and devices
# one release behind still read its backups. Time any increase on ARM: the defaults take ~0.23s
# on an Apple M2 against ~0.035s on a Ryzen 9 7940HS, and the caps ~6.35s on the M2.
DEFAULT_BACKUP_KDF_PARAMS: Final = BackupKdfParams(time_cost=3, memory_kib=64 * 1024, lanes=4)


def is_backup_format(data: bytes) -> bool:
    """Whether the data is a backup made by encrypt_backup rather than a legacy one.

    A legacy backup starts with a random IV, so it matches by chance with probability 2^-64.
    """
    return data.startswith(BACKUP_MAGIC)


def _derive_keys(
        password: bytes,
        salt: bytes,
        kdf_params: BackupKdfParams,
) -> tuple[bytes, bytes]:
    """Returns the AES-256-GCM key and the key commitment, two HKDF subkeys of the
    Argon2id master key so that no key does two jobs"""
    master_key = Argon2id(
        salt=salt,
        length=32,
        iterations=kdf_params.time_cost,
        lanes=kdf_params.lanes,
        memory_cost=kdf_params.memory_kib,
        ad=_ARGON2_AD,
    ).derive(password)
    return (
        HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=_ENC_KEY_INFO).derive(master_key),  # noqa: E501
        HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=_COMMITMENT_INFO).derive(master_key),  # noqa: E501
    )


def _chunk_nonce(base_nonce: bytes, index: int) -> bytes:
    """The chunk index XORed into the low 8 bytes, so a nonce never repeats under a key"""
    return base_nonce[:4] + (int.from_bytes(base_nonce[4:], 'big') ^ index).to_bytes(8, 'big')


def _chunk_aad(header: bytes, index: int, final: bool) -> bytes:
    """The index stops reordering and dropping chunks, the final flag stops truncation"""
    return header + index.to_bytes(8, 'big') + (b'\x01' if final else b'\x00')


def _iter_chunks(payload: Iterable[Buffer]) -> Iterator[tuple[bytes, bool]]:
    """Regroups the payload into (chunk, final) pairs.

    Every chunk but the last is exactly BACKUP_CHUNK_SIZE. The last one is the remainder,
    which is empty when the payload length is a multiple of the chunk size, so there always
    is a final chunk and an empty payload differs from a backup cut back to its header.
    """
    buffer = bytearray()
    for segment in payload:
        view = memoryview(segment)
        while len(view) != 0:
            taken = BACKUP_CHUNK_SIZE - len(buffer)
            buffer += view[:taken]
            view = view[taken:]
            if len(buffer) == BACKUP_CHUNK_SIZE:
                yield bytes(buffer), False
                buffer.clear()

    yield bytes(buffer), True


def encrypt_backup(
        password: bytes,
        last_modify_ts: Timestamp,
        payload: Iterable[Buffer],
        kdf_params: BackupKdfParams = DEFAULT_BACKUP_KDF_PARAMS,
) -> bytearray:
    """Encrypts the payload, given as consecutive segments, into a premium backup.

    Header followed by AES-256-GCM chunks, each one prefixed by its sealed length.
    last_modify_ts goes in the header so the server can't change it.
    """
    salt, base_nonce = os.urandom(32), os.urandom(12)
    enc_key, commitment = _derive_keys(password=password, salt=salt, kdf_params=kdf_params)
    header = _HEADER.pack(
        BACKUP_MAGIC,
        BACKUP_VERSION,
        _KDF_ARGON2ID,
        kdf_params.time_cost,
        kdf_params.memory_kib,
        kdf_params.lanes,
        salt,
        base_nonce,
        last_modify_ts,
        commitment,
    )
    aesgcm, output = AESGCM(enc_key), bytearray(header)
    for index, (chunk, final) in enumerate(_iter_chunks(payload)):
        sealed = aesgcm.encrypt(
            nonce=_chunk_nonce(base_nonce, index),
            data=chunk,
            associated_data=_chunk_aad(header=header, index=index, final=final),
        )
        output += _CHUNK_LENGTH.pack(len(sealed))
        output += sealed

    return output  # not bytes(), which would copy the whole backup once more


def decrypt_backup(password: bytes, data: bytes) -> tuple[Timestamp, bytearray]:
    """Decrypts a backup made by encrypt_backup.

    Returns the authenticated last_modify_ts of the header and the payload. Each chunk is
    verified before its plaintext is used, and the payload is only returned once the final
    chunk is verified, so nothing of an incomplete or modified backup gets out.

    May raise:
    - UnsupportedRemoteBackup if the version, the KDF or its parameters are not ones this
    rotki version reads. Checked before any key derivation.
    - UnableToDecryptRemoteData if the password is wrong or the backup was modified. The two
    cases are not told apart on purpose.
    """
    if len(data) < _HEADER.size or not is_backup_format(data):
        raise UnableToDecryptRemoteData(_DECRYPT_ERROR)

    header = data[:_HEADER.size]
    (
        _, version, kdf, time_cost, memory_kib, lanes,
        salt, base_nonce, last_modify_ts, commitment,
    ) = _HEADER.unpack(header)
    # The header is only authenticated once the first chunk opens, so a crafted header could
    # make us run the KDF with any parameters. Cap that work before deriving anything. The
    # defaults sit below these caps, so the cost can go up to them with no reader change.
    if (
        version != BACKUP_VERSION or kdf != _KDF_ARGON2ID or
        not 1 <= time_cost <= 8 or
        not 8 * 1024 <= memory_kib <= 256 * 1024 or
        not 1 <= lanes <= 8
    ):
        raise UnsupportedRemoteBackup

    enc_key, expected_commitment = _derive_keys(
        password=password,
        salt=salt,
        kdf_params=BackupKdfParams(time_cost=time_cost, memory_kib=memory_kib, lanes=lanes),
    )
    # GCM alone is not key committing. Without this a crafted backup could open under more
    # than one key and be used as an oracle for guessing the password.
    if not hmac.compare_digest(commitment, expected_commitment):
        raise UnableToDecryptRemoteData(_DECRYPT_ERROR)

    aesgcm, plaintext = AESGCM(enc_key), bytearray()
    offset, index = _HEADER.size, 0
    while True:
        if len(data) - offset < _CHUNK_LENGTH.size:  # cut back to the header or mid length
            raise UnableToDecryptRemoteData(_DECRYPT_ERROR)

        (sealed_length,) = _CHUNK_LENGTH.unpack_from(data, offset)
        start = offset + _CHUNK_LENGTH.size
        end = start + sealed_length
        # The final chunk is the one that ends the data. The writer makes it shorter than a
        # full chunk, but a full final chunk is accepted too.
        final = end == len(data)
        if (
            not _TAG_SIZE <= sealed_length <= BACKUP_CHUNK_SIZE + _TAG_SIZE or
            end > len(data) or
            (not final and sealed_length != BACKUP_CHUNK_SIZE + _TAG_SIZE)
        ):
            raise UnableToDecryptRemoteData(_DECRYPT_ERROR)

        try:
            plaintext += aesgcm.decrypt(
                nonce=_chunk_nonce(base_nonce, index),
                data=data[start:end],
                associated_data=_chunk_aad(header=header, index=index, final=final),
            )
        except InvalidTag as e:
            raise UnableToDecryptRemoteData(_DECRYPT_ERROR) from e

        if final:
            return Timestamp(last_modify_ts), plaintext

        offset, index = end, index + 1


# AES decrypt taken from here: https://stackoverflow.com/a/44212550/110395
# and updated to use cryptography library as pyCrypto is deprecated.
# Only reads backups made before encrypt_backup existed. Nothing writes this format anymore.
def decrypt_legacy(key: bytes, source: bytes) -> bytes:
    """
    Decrypts the given source data we with the given key.

    Returns the decrypted data.
    If data can't be decrypted then raises UnableToDecryptRemoteData
    """
    assert isinstance(key, bytes), 'key should be given in bytes'
    assert isinstance(source, bytes), 'source should be given in bytes'
    # A valid blob is the IV plus whole blocks, at least one for the padding. Anything else
    # would make the cipher or the padding lookup raise instead of failing to decrypt.
    if len(source) < 2 * AES_BLOCK_SIZE or len(source) % AES_BLOCK_SIZE != 0:
        raise UnableToDecryptRemoteData(
            'The DB data we received from the server is too short or not a whole number of '
            'AES blocks, so it can not be decrypted.',
        )

    digest = hashes.Hash(hashes.SHA256())
    digest.update(key)
    key = digest.finalize()  # use SHA-256 over our key to get a proper-sized AES key
    iv = source[:AES_BLOCK_SIZE]  # extract the iv from the beginning
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()

    data = source[AES_BLOCK_SIZE:]  # decrypt
    data = decryptor.update(data)
    padding = data[-1]  # pick the padding value from the end; Python 2.x: ord(data[-1])
    if data[-padding:] != bytes([padding]) * padding:  # Python 2.x: chr(padding) * padding
        raise UnableToDecryptRemoteData(
            'Invalid padding when decrypting the DB data we received from the server. '
            'Are you using a new user and if yes have you used the same password as before? '
            'If you have then please open a bug report.',
        )
    return data[:-padding]  # remove the padding


def sha3(data: bytes) -> bytes:
    """
    Raises:
        RuntimeError: If Keccak lib initialization failed, or if the function
        failed to compute the hash.

        TypeError: This function does not accept unicode objects, they must be
        encoded prior to usage.
    """
    digest = hashes.Hash(hashes.SHA3_256())
    digest.update(data)
    return digest.finalize()
