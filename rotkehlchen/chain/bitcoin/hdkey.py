# Adapted from
# https://github.com/summa-tx/riemann-keys/blob/master/riemann_keys/hdkey.py

import hashlib
import hmac
from dataclasses import dataclass
from enum import Enum
from typing import List, NamedTuple, Optional, Union, cast

from base58check import b58decode, b58encode
from coincurve import PrivateKey, PublicKey

from rotkehlchen.chain.bitcoin.utils import (
    BIP32_HARDEN,
    hash160,
    pubkey_to_base58_address,
    pubkey_to_bech32_address,
    pubkey_to_p2sh_p2wpkh_address,
)
from rotkehlchen.errors import DeserializationError, XPUBError
from rotkehlchen.typing import BTCAddress

COMPRESSED_PUBKEY = True


class PrefixParsingResult(NamedTuple):
    is_public: bool
    network: str
    hint: str


class XpubType(Enum):
    P2PKH = 1          # lecacy/xpub
    P2SH_P2WPKH = 2    # segwit/ypyb
    WPKH = 3           # native segwit/zpub

    def matches_prefix(self, prefix: str) -> bool:
        own_prefix = XPUB_TYPE_MAPPING[self]  # should not raise due to enum
        return own_prefix == prefix

    def prefix(self) -> str:
        return XPUB_TYPE_MAPPING[self]  # should not raise due to enum

    def prefix_bytes(self) -> bytes:
        return XPUB_TYPE_MAPPING_BYTES[self]  # should not raise due to enum

    @staticmethod
    def deserialize(value: str) -> 'XpubType':
        if value == 'p2pkh':
            return XpubType.P2PKH
        if value == 'p2sh_p2wpkh':
            return XpubType.P2SH_P2WPKH
        if value == 'wpkh':
            return XpubType.WPKH
        # else
        raise DeserializationError(f'Unknown xpub type {value} found at deserialization')


XPUB_TYPE_MAPPING = {
    XpubType.P2PKH: 'xpub',
    XpubType.P2SH_P2WPKH: 'ypub',
    XpubType.WPKH: 'zpub',
}

XPUB_TYPE_MAPPING_BYTES = {
    XpubType.P2PKH: b'\x04\x88\xb2\x1e',
    XpubType.P2SH_P2WPKH: b'\x04\x9d|\xb2',
    XpubType.WPKH: b'\x04\xb2GF',
}


VERSION_BYTES = {
    b'\x04\x88\xb2\x1e': PrefixParsingResult(
        is_public=True,
        network='mainnet',
        hint='xpub',
    ),
    b'\x04\x88\xad\xe4': PrefixParsingResult(
        is_public=False,
        network='mainnet',
        hint='xpub',
    ),
    b'\x04\xb2GF': PrefixParsingResult(
        is_public=True,
        network='mainnet',
        hint='zpub',
    ),
    b'\x04\xb2C\x0c': PrefixParsingResult(
        is_public=False,
        network='mainnet',
        hint='zpub',
    ),
    b'\x04\x35\x87\xcf': PrefixParsingResult(
        is_public=True,
        network='testnet',
        hint='xpub',
    ),
    b'\x04\x35\x83\x94': PrefixParsingResult(
        is_public=False,
        network='testnet',
        hint='xpub',
    ),
    b'\x04\x9d|\xb2': PrefixParsingResult(
        is_public=True,
        network='mainnet',
        hint='ypub',
    ),
    b'\x04\x9dxx': PrefixParsingResult(
        is_public=False,
        network='mainnet',
        hint='ypub',
    ),
}


def _parse_prefix(prefix: bytes) -> PrefixParsingResult:
    result = VERSION_BYTES.get(prefix, None)
    if not result:
        raise XPUBError(f'Unknown XPUB prefix {prefix.hex()} found')

    return result


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class HDKey():

    path: Optional[str]
    network: str
    depth: Optional[int]
    parent_fingerprint: Optional[bytes]
    index: Optional[int]
    parent: Optional['HDKey']  # forward type reference
    chain_code: Optional[bytes]
    fingerprint: bytes
    xpub: Optional[str]
    pubkey: PublicKey
    privkey: Optional[PrivateKey]
    hint: str

    @staticmethod
    def from_xpub(
            xpub: str,
            xpub_type: Optional[XpubType] = None,
            path: Optional[str] = None,
    ) -> 'HDKey':
        """
        Instantiate an HDKey from an xpub. Populates all possible fields
        Args:
            xpub (str): the xpub
            path (str): the path if it's known. useful for calling derive_path
        Returns:
            (HDKey): the key object

        May raise:
        - XPUBError if there is a problem with decoding the xpub
        """
        try:
            xpub_bytes = b58decode(xpub)
        except ValueError as e:
            raise XPUBError(f'Given XPUB {xpub} is not b58 encoded') from e

        if len(xpub_bytes) < 78:
            raise XPUBError(f'Given XPUB {xpub} is too small')

        try:
            pubkey = PublicKey(xpub_bytes[45:78])
        except ValueError as e:
            raise XPUBError(str(e)) from e

        result = _parse_prefix(xpub_bytes[0:4])
        if not result.is_public:
            raise XPUBError('Given xpub is an extended private key')

        if result.network != 'mainnet':
            raise XPUBError('Given xpub is not for the bitcoin mainnet')

        hint = result.hint
        if xpub_type is not None and xpub_type.matches_prefix(xpub[0:4]) is False:
            # the given type does not match the prefix, re-encode with correct pref
            new_xpub = bytearray()
            new_xpub.extend(xpub_type.prefix_bytes())
            new_xpub.extend(xpub_bytes[4:])
            new_xpub_bytes = new_xpub
            hint = xpub_type.prefix()
            xpub = b58encode(bytes(new_xpub_bytes)).decode('ascii')

        return HDKey(
            path=path,
            network=result.network,
            depth=xpub_bytes[4],
            parent_fingerprint=xpub_bytes[5:9],
            index=int.from_bytes(xpub_bytes[9:13], byteorder='big'),
            parent=None,
            chain_code=xpub_bytes[13:45],
            fingerprint=hash160(pubkey.format(COMPRESSED_PUBKEY))[:4],
            xpub=xpub,
            privkey=None,
            pubkey=pubkey,
            hint=hint,
        )

    @staticmethod
    def _normalize_index(idx: Union[int, str]) -> int:
        """
        Normalizes an index so that we can accept ints or strings
        Args:
            idx (int or str): the index as an integer, or a string with h/'
        Returns:
            (int): the index as an integer
        """
        if isinstance(idx, int):
            return idx
        if not isinstance(idx, str):
            raise XPUBError('XPUB path index must be string or integer')
        if idx[-1] in ['h', "'"]:  # account for h or ' conventions
            return int(idx[:-1]) + BIP32_HARDEN
        return int(idx)

    def _child_from_xpub(self, index: int, child_xpub: str) -> 'HDKey':
        """
        Returns a new HDKey object based on the current object and the new
            child xpub. Don't call this directly, it's for child derivation.
        Args:
            index      (int): the index of the child
            child_xpub (str): the child's xpub
        Returns
            HDKey: the new child object
        """
        path: Optional[str]
        if self.path is not None:
            path = '{}/{}'.format(self.path, str(index))
        else:
            path = None
        xpub_bytes = b58decode(child_xpub)
        pubkey = xpub_bytes[45:78]

        result = _parse_prefix(xpub_bytes[0:4])
        if not result.is_public:
            raise XPUBError('Given xpub is an extended private key')

        return HDKey(
            path=path,
            network=result.network,
            depth=xpub_bytes[4],
            parent_fingerprint=xpub_bytes[5:9],
            index=int.from_bytes(xpub_bytes[9:13], byteorder='big'),
            parent=self,
            chain_code=xpub_bytes[13:45],
            fingerprint=hash160(pubkey)[:4],
            xpub=child_xpub,
            privkey=None,
            pubkey=PublicKey(pubkey),
            hint=result.hint,
        )

    def _make_child_xpub(
            self,
            child_pubkey: PublicKey,
            index: int,
            chain_code: bytes) -> str:
        """
        Makes a child xpub based on the current key and the child key info.
        Args:
            child_pubkey (bytes): the child pubkey
            index          (int): the child index
            chain_code   (bytes): the child chain code
        Returns
            (str): the child xpub
        """
        xpub = bytearray()

        xpub.extend(b58decode(cast(str, self.xpub))[0:4])  # prefix
        xpub.extend([cast(int, self.depth) + 1])               # depth
        xpub.extend(self.fingerprint)                          # fingerprint
        xpub.extend(index.to_bytes(4, byteorder='big'))        # index
        xpub.extend(chain_code)                                # chain_code
        xpub.extend(child_pubkey.format(COMPRESSED_PUBKEY))    # pubkey (comp)
        return b58encode(bytes(xpub)).decode('ascii')

    @staticmethod
    def _parse_derivation(derivation_path: str) -> List[int]:
        """
        turns a derivation path (e.g. m/44h/0) into a list of integer indexes
            e.g. [2147483692, 0]
        Args:
            derivation_path (str): the human-readable derivation path
        Returns:
            (list(int)): the derivaion path as a list of indexes
        """
        int_nodes: List[int] = []

        # Must be / separated
        nodes: List[str] = derivation_path.split('/')
        # If the first node is not m, error.
        # TODO: allow partial path knowledge
        if nodes[0] != 'm':
            raise XPUBError(f'Got bad xpub path {derivation_path} for xpub')

        # Go over all other nodes, and convert to indexes
        nodes = nodes[1:]
        for node in nodes:
            if node[-1] in ['h', "'"]:  # Support 0h and 0' conventions
                int_nodes.append(int(node[:-1]) + BIP32_HARDEN)
            else:
                int_nodes.append(int(node))
        return int_nodes

    def derive_path(self, path: str) -> 'HDKey':
        """
        Derives a descendant of the current node
        Throws an error if the requested path is not known to be a descendant

        Args:
            path (str): the requested derivation path from master
        Returns:
            (HDKey): the descendant
        """
        if not self.path:
            raise XPUBError('XPUB current key\'s path is unknown')

        own_path = self.path
        path_nodes = self._parse_derivation(path)
        my_nodes = self._parse_derivation(own_path)

        # compare own path to requested path see if it is a descendant
        for i, my_node in enumerate(my_nodes):
            if my_node != path_nodes[i]:
                raise XPUBError('XPUB requested child not in descendant branches')

        # iteratively derive descendants through the path
        current_node = self
        for i in range(len(my_nodes), len(path_nodes)):
            current_node = current_node.derive_child(path_nodes[i])
        return current_node

    def derive_child(self, idx: Union[int, str]) -> 'HDKey':
        """
        Derives a bip32 child node from the current node
        Args:
            idx (int or str): the index of the child
        Returns:
            (HDKey): the child
        """
        # TODO: Break up this function

        # normalize the index, error if we can't derive the child
        index: int = self._normalize_index(idx)
        if index >= BIP32_HARDEN and not self.privkey:
            raise XPUBError('Need private key to derive XPUB hardened children')

        # error if we can't derive a child
        if not self.chain_code:
            raise XPUBError('Cannot derive XPUB child without chain_code')

        own_chain_code = self.chain_code
        # start key derivation process
        data = bytearray()
        index_as_bytes = index.to_bytes(4, byteorder='big')
        if index >= BIP32_HARDEN:
            if not self.privkey:
                raise XPUBError('Cannot derive XPUB for hardened index without privkey')
            # Data = 0x00 || ser256(kpar) || ser32(i)
            # (Note: The 0x00 pads the private key to make it 33 bytes long.)
            data.extend(b'\x00')
            data.extend(self.privkey.secret)
            data.extend(index_as_bytes)
        else:
            # Data = serP(point(kpar)) || ser32(i)).
            data.extend(self.pubkey.format(COMPRESSED_PUBKEY))
            data.extend(index_as_bytes)

        mac = hmac.new(own_chain_code, digestmod=hashlib.sha512)
        mac.update(data)
        digest = mac.digest()  # noqa: E741
        tweak, chain_code = digest[:32], digest[32:]
        # end key derivation process

        try:
            if self.privkey:
                raise NotImplementedError('Privkeys xpub derivation not implemented in rotki')
                # if we have a private key, give the child a private key
                # child_privkey = self.privkey.add(tweak)
                # child_pubkey = PublicKey.from_secret(child_privkey.secret)

            # otherwise, just derive a pubkey
            child_pubkey = self.pubkey.add(tweak)
        except ValueError:
            # NB: it is possible to derive an "impossible" key.
            #     e.g. the privkey is too high, or is 0
            #     if that happens, the spec says to derive at the next index
            return self.derive_child(index + 1)

        # no privkey here so make a new public child
        child_xpub = self._make_child_xpub(
            child_pubkey, index=index, chain_code=chain_code,
        )
        return self._child_from_xpub(index=index, child_xpub=child_xpub)

    def address(self) -> BTCAddress:
        if self.hint == 'xpub':
            return pubkey_to_base58_address(self.pubkey.format(COMPRESSED_PUBKEY))
        if self.hint == 'ypub':
            return pubkey_to_p2sh_p2wpkh_address(self.pubkey.format(COMPRESSED_PUBKEY))
        if self.hint == 'zpub':
            return pubkey_to_bech32_address(
                data=self.pubkey.format(COMPRESSED_PUBKEY),
                witver=0,
            )
        # else
        raise AssertionError(f'Unknown hint {self.hint} ended up in an HDKey')
