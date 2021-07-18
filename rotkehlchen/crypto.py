import base64

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Hash import SHA3_256, SHA256

from rotkehlchen.errors import UnableToDecryptRemoteData


# AES encrypt/decrypt taken from here: https://stackoverflow.com/a/44212550/110395
def encrypt(key: bytes, source: bytes) -> str:
    assert isinstance(key, bytes), 'key should be given in bytes'
    assert isinstance(source, bytes), 'source should be given in bytes'
    key = SHA256.new(key).digest()  # use SHA-256 over our key to get a proper-sized AES key
    iv = Random.new().read(AES.block_size)  # generate iv
    encryptor = AES.new(key, AES.MODE_CBC, iv)
    padding = AES.block_size - len(source) % AES.block_size  # calculate needed padding
    source += bytes([padding]) * padding  # Python 2.x: source += chr(padding) * padding
    data = iv + encryptor.encrypt(source)  # store the iv at the beginning and encrypt
    return base64.b64encode(data).decode("latin-1")


def decrypt(key: bytes, given_source: str) -> bytes:
    """
    Decrypts the given source data we with the given key.

    Returns the decrypted data.
    If data can't be decrypted then raises UnableToDecryptRemoteData
    """
    assert isinstance(key, bytes), 'key should be given in bytes'
    assert isinstance(given_source, str), 'source should be given in string'
    source = base64.b64decode(given_source.encode("latin-1"))
    key = SHA256.new(key).digest()  # use SHA-256 over our key to get a proper-sized AES key
    iv = source[:AES.block_size]  # extract the iv from the beginning
    decryptor = AES.new(key, AES.MODE_CBC, iv)
    data = decryptor.decrypt(source[AES.block_size:])  # decrypt
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
    return SHA3_256.new(data).digest()
