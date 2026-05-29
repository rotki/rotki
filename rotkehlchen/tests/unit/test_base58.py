from typing import Final

import pytest

from rotkehlchen.utils.base58 import b58decode, b58encode

TEST_DATA: Final = [
    (
        b'1BoatSLRHtKNngkdXEeobR76b53LETtpyT',
        b'\x00v\x80\xad\xec\x8e\xab\xca\xba\xc6v\xbe\x9e\x83\x85J\xde\x0b\xd2,\xdb\x0b\xb9`\xde',
    ), (
        b'3QJmV3qfvL9SuYo34YihAf3sRCW3qSinyC',
        b'\x05\xf8\x15\xb06\xd9\xbb\xbc\xe5\xe9\xf2\xa0\n\xbd\x1b\xf3\xdc\x91\xe9U\x10\xcd\x001\x07',
    ), (
        b'mkwV3DZkgYwKaXkphBtcXAjsYQEqZ8aB3x',
        b'o;|F\xa5\xa6\x00\xb2\x98k\xd8\x04\x13|\xf9\x1d\xbbZE\xa2|\xa8\x00l+',
    ), (
        b'n1tpDjEJw32qGwkdQKPfACpcTtCa6hDVBw',
        b'o\xdf\x84\xed0\x95\xc6_\xddu\xf4j\xd8|3\xe0\xb1\xf4\x14\xff\xe6\xf8\t\x8f\xaa',
    ), (
        b'LeF6vC9k1qfFDEj6UGjM5e4fwHtiKsakTd',
        b'0\xd0\xa2\x07\xd1\x82\xa7\xe0]\x7fD\xb6\\5\xf9\xe1\xd1v\xeb\xde\xa7\xba\x08\x90\\',
    ), (
        b'muE4dcYXagWA7WT8ZnCriiy65FELikhdUy',
        b'o\x96_\xfa\xccH\xe6\x87\xe0\xd3NJ\x8a\x86\x83*\x8dl\xfc\xf0{\xf1#\xb76',
    ),
]


@pytest.mark.parametrize(('encoded', 'decoded'), TEST_DATA)
def test_base58_encode(encoded: bytes, decoded: bytes) -> None:
    assert b58encode(decoded) == encoded


@pytest.mark.parametrize(('encoded', 'decoded'), TEST_DATA)
def test_base58_decode(encoded: bytes, decoded: bytes) -> None:
    assert b58decode(encoded) == decoded


def test_base58_decode_rejects_invalid_characters() -> None:
    with pytest.raises(ValueError, match="invalid base58 character: '0'"):
        b58decode(b'0')
