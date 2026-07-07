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


def _jacobian_double(x: int, y: int, z: int) -> tuple[int, int, int]:
    """Double a Jacobian point, using (0, 1, 0) as infinity."""
    if z == 0 or y == 0:
        return 0, 1, 0

    s = 4 * x * y % P * y % P
    m = 3 * x * x % P
    nx = (m * m - 2 * s) % P
    y_sq = y * y % P
    return nx, (m * (s - nx) - 8 * y_sq * y_sq) % P, 2 * y * z % P


def _jacobian_add(
        x1: int,
        y1: int,
        z1: int,
        x2: int,
        y2: int,
        z2: int,
) -> tuple[int, int, int]:
    """Add two Jacobian points, using (0, 1, 0) as infinity."""
    if z1 == 0:
        return x2, y2, z2
    if z2 == 0:
        return x1, y1, z1

    z1_sq, z2_sq = z1 * z1 % P, z2 * z2 % P
    u1, u2 = x1 * z2_sq % P, x2 * z1_sq % P
    s1, s2 = y1 * z2_sq % P * z2 % P, y2 * z1_sq % P * z1 % P
    if u1 == u2:
        if s1 != s2:
            return 0, 1, 0
        return _jacobian_double(x1, y1, z1)

    h, r = (u2 - u1) % P, (s2 - s1) % P
    h_sq = h * h % P
    h_cb = h_sq * h % P
    nx = (r * r - h_cb - 2 * u1 * h_sq) % P
    return nx, (r * (u1 * h_sq - nx) - s1 * h_cb) % P, h * z1 % P * z2 % P


def _point_mul(scalar: int, point: Point) -> Point | None:
    """Multiply a curve point by a non-negative scalar.

    Uses Jacobian coordinates so the multiplication needs a single field inversion instead
    of one per point addition/doubling.
    """
    if scalar < 0:
        raise ValueError('Invalid negative secp256k1 scalar')

    rx, ry, rz = 0, 1, 0
    ax, ay, az = point.x, point.y, 1
    while scalar:
        if scalar & 1:
            rx, ry, rz = _jacobian_add(rx, ry, rz, ax, ay, az)
        ax, ay, az = _jacobian_double(ax, ay, az)
        scalar >>= 1

    if rz == 0:
        return None

    z_inv = _inverse_mod(rz)
    z_inv_sq = z_inv * z_inv % P
    return Point(x=rx * z_inv_sq % P, y=ry * z_inv_sq % P * z_inv % P)


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
