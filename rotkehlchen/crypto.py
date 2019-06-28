import base64
from binascii import hexlify

from coincurve import PrivateKey
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Hash import SHA3_256, SHA256  # type: ignore

from rotkehlchen.typing import BinaryEthAddress, EthAddress


# AES encrypt/decrypt taken from here: https://stackoverflow.com/a/44212550/110395
def encrypt(key: bytes, source: bytes) -> str:
    assert isinstance(key, bytes), 'key should be given in bytes'
    assert isinstance(source, bytes), 'source should be given in bytes'
    key = SHA256.new(key).digest()  # use SHA-256 over our key to get a proper-sized AES key
    IV = Random.new().read(AES.block_size)  # generate IV
    encryptor = AES.new(key, AES.MODE_CBC, IV)
    padding = AES.block_size - len(source) % AES.block_size  # calculate needed padding
    source += bytes([padding]) * padding  # Python 2.x: source += chr(padding) * padding
    data = IV + encryptor.encrypt(source)  # store the IV at the beginning and encrypt
    return base64.b64encode(data).decode("latin-1")


def decrypt(key: bytes, given_source: str) -> bytes:
    assert isinstance(key, bytes), 'key should be given in bytes'
    assert isinstance(given_source, str), 'source should be given in string'
    source = base64.b64decode(given_source.encode("latin-1"))
    key = SHA256.new(key).digest()  # use SHA-256 over our key to get a proper-sized AES key
    IV = source[:AES.block_size]  # extract the IV from the beginning
    decryptor = AES.new(key, AES.MODE_CBC, IV)
    data = decryptor.decrypt(source[AES.block_size:])  # decrypt
    padding = data[-1]  # pick the padding value from the end; Python 2.x: ord(data[-1])
    if data[-padding:] != bytes([padding]) * padding:  # Python 2.x: chr(padding) * padding
        raise ValueError("Invalid padding...")
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


def ishash(data: bytes) -> bool:
    return isinstance(data, bytes) and len(data) == 32


def privatekey_to_publickey(private_key_bin: bytes) -> bytes:
    """ Returns public key in bitcoins 'bin' encoding. """
    if not ishash(private_key_bin):
        raise ValueError('private_key_bin format mismatch. maybe hex encoded?')
    private_key = PrivateKey(private_key_bin)
    return private_key.public_key.format(compressed=False)


def publickey_to_address(publickey: bytes) -> BinaryEthAddress:
    return BinaryEthAddress(sha3(publickey[1:])[12:])


def privatekey_to_address(private_key_bin: bytes) -> BinaryEthAddress:
    return publickey_to_address(privatekey_to_publickey(private_key_bin))


def address_encoder(address: BinaryEthAddress) -> EthAddress:
    assert len(address) in (20, 0)
    return EthAddress('0x' + hexlify(address).decode())
