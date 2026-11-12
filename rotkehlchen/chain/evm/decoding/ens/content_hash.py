"""Decoding of EIP-1577 content hashes, as set by the ENS ContentHashChanged events."""

from typing import Final

from multiformats import CID, multicodec, multihash

from rotkehlchen.utils.base58 import b58encode

_BASE58_CODECS: Final = frozenset({'ipfs', 'ipns'})
_HEX_CODEC: Final = 'swarm'
_SWARM_MAX_DIGEST_SIZE: Final = 32  # keccak-256


def decode_content_hash(content_hash: bytes) -> tuple[str, str]:
    """Decode an EIP-1577 content hash into its multicodec name and decoded value.

    The content hash is a multicodec prefixed payload. The same decoding profiles
    the `content-hash` library implemented are applied here:
    - ipfs and ipns: the multihash of the wrapped CID, base58 encoded.
    - swarm: the digest of the wrapped CID, hex encoded.
    - anything else: the payload decoded as utf-8.

    `multihash.unwrap_raw` is used instead of `multihash.unwrap` since the latter
    checks the digest size against the hash function implementation, which for
    the keccak digests of swarm content hashes imports `pycryptodomex`. We only
    look at the digest bytes, so no hash implementation is needed, and the
    maximum digest size `content-hash` enforced for swarm is checked here.

    May raise KeyError for unknown multicodecs or multihashes, ValueError for
    malformed input and TypeError for wrong argument types. Callers treat all of
    them as an undecodable content hash.
    """
    codec, raw_data = multicodec.unwrap(content_hash)
    if codec.name in _BASE58_CODECS:
        return codec.name, b58encode(CID.decode(raw_data).digest).decode('utf-8')
    if codec.name == _HEX_CODEC:
        _, digest = multihash.unwrap_raw(CID.decode(raw_data).digest)
        if len(digest) > _SWARM_MAX_DIGEST_SIZE:
            raise ValueError(
                f'swarm digest is {len(digest)} bytes, more than the maximum '
                f'{_SWARM_MAX_DIGEST_SIZE}',
            )
        return codec.name, bytes(digest).hex()

    return codec.name, raw_data.decode('utf-8')
