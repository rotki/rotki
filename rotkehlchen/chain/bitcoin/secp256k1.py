"""Minimal secp256k1 public-key operations used for BIP32 xpub derivation.

Implemented from public specifications:
- SEC 2, section 2.4.1 for secp256k1 curve parameters.
- BIP32 for non-hardened public child derivation.
- BIP340/BIP341/BIP86 for x-only keys, tagged hashing, and Taproot output keys.

Added to rotki using Codex and ChatGPT 5.5.
"""

import hashlib
from dataclasses import dataclass
from typing import Final, NamedTuple, Self

P: Final = 0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f
N: Final = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141


class Point(NamedTuple):
    """Affine secp256k1 point."""

    x: int
    y: int


G: Final = Point(
    0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798,
    0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8,
)


def _inverse_mod(value: int) -> int:
    """Return the inverse of value modulo the field prime."""
    if value % P == 0:
        raise ValueError('Cannot invert zero modulo secp256k1 field prime')

    return pow(value, -1, P)


def _is_on_curve(point: Point) -> bool:
    """Return whether point satisfies the secp256k1 curve equation."""
    return (point.y * point.y - point.x * point.x * point.x - 7) % P == 0


def _point_add(first: Point | None, second: Point | None) -> Point | None:
    """Add two curve points, returning None for the point at infinity."""
    if first is None:
        return second
    if second is None:
        return first
    if first.x == second.x and (first.y != second.y or first.y == 0):
        return None

    if first == second:
        slope = (3 * first.x * first.x * _inverse_mod(2 * first.y)) % P
    else:
        slope = ((second.y - first.y) * _inverse_mod(second.x - first.x)) % P

    x = (slope * slope - first.x - second.x) % P
    return Point(x=x, y=(slope * (first.x - x) - first.y) % P)


def _point_mul(scalar: int, point: Point) -> Point | None:
    """Multiply a curve point by a non-negative scalar."""
    if scalar < 0:
        raise ValueError('Invalid negative secp256k1 scalar')

    result: Point | None = None
    addend: Point | None = point
    while scalar:
        if scalar & 1:
            result = _point_add(result, addend)
        addend = _point_add(addend, addend)
        scalar >>= 1

    return result


def _lift_x_even_y(x: int) -> Point:
    """Lift an x coordinate to the even-y secp256k1 point."""
    if not 0 <= x < P:
        raise ValueError('Invalid secp256k1 public key')

    y = pow((x * x * x + 7) % P, (P + 1) // 4, P)
    if (y * y - x * x * x - 7) % P != 0:
        raise ValueError('Invalid secp256k1 public key')
    return Point(x=x, y=P - y if y % 2 == 1 else y)


def _parse_public_key(data: bytes) -> Point:
    """Parse a compressed SEC public key into a curve point."""
    if len(data) != 33 or data[0] not in {2, 3}:
        raise ValueError('Invalid secp256k1 compressed public key')

    point = _lift_x_even_y(x=int.from_bytes(data[1:], byteorder='big'))
    if point.y % 2 != data[0] & 1:
        point = Point(x=point.x, y=P - point.y)
    if not _is_on_curve(point):
        raise ValueError('Invalid secp256k1 public key')

    return point


def _tagged_hash(tag: bytes, data: bytes) -> bytes:
    """Return a BIP340 tagged SHA-256 hash."""
    tag_hash = hashlib.sha256(tag).digest()
    return hashlib.sha256(tag_hash + tag_hash + data).digest()


@dataclass(frozen=True)
class PublicKey:
    """Small coincurve-compatible compressed secp256k1 public-key wrapper."""

    _point: Point

    def __init__(self, data: bytes | Point) -> None:
        """Create a public key from a compressed SEC key or internal point."""
        if isinstance(data, Point):
            if not _is_on_curve(data):
                raise ValueError('Invalid secp256k1 public key')
            point = data
        else:
            point = _parse_public_key(data)

        object.__setattr__(
            self,
            '_point',
            point,
        )

    def format(self, compressed: bool = True) -> bytes:
        """Serialize the key in compressed SEC format."""
        if compressed is not True:
            raise ValueError('Only compressed public keys are supported')

        return bytes([2 + (self._point.y & 1)]) + self._point.x.to_bytes(32, byteorder='big')

    def add(self, tweak: bytes) -> Self:
        """Return this public key plus tweak * G."""
        if len(tweak) != 32 or not 0 < (tweak_int := int.from_bytes(tweak, byteorder='big')) < N:
            raise ValueError('Invalid secp256k1 tweak')
        try:
            tweak_point = _point_mul(tweak_int, G)
            result = _point_add(self._point, tweak_point)
        except ValueError as e:
            raise ValueError('Invalid secp256k1 tweak') from e
        if tweak_point is None or result is None:
            raise ValueError('Invalid secp256k1 tweak')

        try:
            return type(self)(result)
        except ValueError as e:
            raise ValueError('Invalid secp256k1 tweak') from e

    def taproot_output_key(self) -> bytes:
        """Return the BIP86 tweaked x-only Taproot output key."""
        internal_key = self._point.x.to_bytes(32, byteorder='big')
        tweak = _tagged_hash(b'TapTweak', internal_key)
        if not 0 <= (tweak_int := int.from_bytes(tweak, byteorder='big')) < N:
            raise ValueError('Invalid taproot tweak')
        try:
            result = _point_add(
                _lift_x_even_y(self._point.x),
                _point_mul(tweak_int, G) if tweak_int != 0 else None,
            )
        except ValueError as e:
            raise ValueError('Invalid taproot tweak') from e
        if result is None:
            raise ValueError('Invalid taproot tweak')

        return result.x.to_bytes(32, byteorder='big')


@dataclass(frozen=True)
class PrivateKey:
    """Compatibility container for existing type and `.secret` references."""

    secret: bytes
