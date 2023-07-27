import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from rotkehlchen.errors.misc import UnableToDecryptRemoteData

AES_BLOCK_SIZE = 16


# AES encrypt/decrypt taken from here: https://stackoverflow.com/a/44212550/110395
# and updated to use cryptography library as pyCrypto is deprecated
# TODO: Perhaps use Fernet instead of this algorithm in the future? The docs of the
# cryptography library seem to suggest it's the safest options. Problem is the
# already encrypted and saved database files and how to handle the previous encryption
# We need to keep a versioning of encryption used for each file.
def encrypt(key: bytes, source: bytes) -> bytes:
    assert isinstance(key, bytes), 'key should be given in bytes'
    assert isinstance(source, bytes), 'source should be given in bytes'
    digest = hashes.Hash(hashes.SHA256())
    digest.update(key)
    key = digest.finalize()  # use SHA-256 over our key to get a proper-sized AES key
    iv = os.urandom(AES_BLOCK_SIZE)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    padding = AES_BLOCK_SIZE - len(source) % AES_BLOCK_SIZE  # calculate needed padding
    source += bytes([padding]) * padding  # Python 2.x: source += chr(padding) * padding
    # store the iv at the beginning and encrypt
    data = iv + (encryptor.update(source) + encryptor.finalize())
    return data


def decrypt(key: bytes, source: bytes) -> bytes:
    """
    Decrypts the given source data we with the given key.

    Returns the decrypted data.
    If data can't be decrypted then raises UnableToDecryptRemoteData
    """
    assert isinstance(key, bytes), 'key should be given in bytes'
    assert isinstance(source, bytes), 'source should be given in bytes'
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
