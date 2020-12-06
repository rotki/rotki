from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from rotkehlchen.errors import UnsupportedAsset
from rotkehlchen.typing import ChecksumEthAddress

# The most common keys for serializing an <UnknownEthereumToken> via
# `serialize_as_dict()`
UNKNOWN_TOKEN_KEYS = ('ethereum_address', 'name', 'symbol')

SerializeAsDictKeys = Union[List[str], Tuple[str, ...], Set[str]]


@dataclass(init=True, repr=True, eq=False, unsafe_hash=False, frozen=True)
class UnknownEthereumToken:
    """Alternative minimal class to EthereumToken for unknown assets"""
    ethereum_address: ChecksumEthAddress  # identifier
    symbol: str
    name: Optional[str] = None
    decimals: Optional[int] = None

    def __hash__(self) -> int:
        return hash(self.ethereum_address)

    def __eq__(self, other: Any) -> bool:
        """Check if an unknown ethereum tokens is equal to something.

        We only accept comparison to unknown ethereum token or a string which
        is interpreted as an address.

        TODO: Think how to handle comparison to Asset and to Ethereum token
        in the case the UnknownEthereumToken is actually supported after some time.

        """
        if isinstance(other, UnknownEthereumToken):
            return self.ethereum_address == other.ethereum_address
        if isinstance(other, str):
            return self.ethereum_address == other

        # else for any other type comparison return false
        return False

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __str__(self) -> str:
        if self.name:
            return f'{self.name} {self.ethereum_address}'
        return f'{self.symbol} {self.ethereum_address}'

    def __repr__(self) -> str:
        return (
            f'<UnknownEthereumToken '
            f'ethereum_address:{self.ethereum_address} '
            f'symbol:{self.symbol} '
            f'name:{self.name} '
            f'decimals: {self.decimals}>'
        )

    def serialize(self) -> ChecksumEthAddress:
        return self.ethereum_address

    def serialize_as_dict(
            self,
            keys: Optional[SerializeAsDictKeys] = None,
    ) -> Dict[str, Any]:
        """Return the instance as dict

        If no keys are given, all the fields are included.
        """
        if not keys:
            return asdict(self)

        return {key: getattr(self, key) for key in keys if hasattr(self, key)}

    #  --- matching the asset interface since this class is treated like an Asset
    #
    # TODO: Perhaps find a better way to handle this. Have a common Asset interface
    # that has to be followed by using a superclass?
    @property
    def identifier(self) -> str:
        """
        Creates a unique identifier for this token.

        This should stay only as long as we use objects of this class as drop ins
        for Asset/EthereumToken
        """
        return f'custom_token {self.symbol} - {self.ethereum_address}'

    def is_fiat(self) -> bool:  # pylint: disable=no-self-use
        return False

    def to_cryptocompare(self) -> str:
        raise UnsupportedAsset(f'{self.identifier} is not supported by cryptocompare')

    def to_coingecko(self) -> str:
        raise UnsupportedAsset(f'{self.identifier} is not supported by coingecko')

    def has_coingecko(self) -> bool:  # pylint: disable=no-self-use
        return False
