from dataclasses import dataclass, asdict
from typing import (
    Any,
    Dict,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
)

from rotkehlchen.typing import ChecksumEthAddress


SerializeAsDictKeys = Union[List[str], Tuple[str, ...], Set[str]]


class FakeAsset(NamedTuple):
    """A class that fakes Asset properties when the class can't be
    instantiated (i.e. the identifier belongs to an unknown ethereum token).

    For instance this happens with DB trades entries whose `fee_currency` is an
    unknown ethereum token and Trade can't be instantiated.
    """
    identifier: str

    def __str__(self) -> str:
        return self.identifier

    def to_binance(self) -> str:
        return self.identifier


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
        if other is None:
            return False
        if isinstance(other, UnknownEthereumToken):
            return self.ethereum_address == other.ethereum_address
        if isinstance(other, str):
            return self.ethereum_address == other

        raise TypeError(f'Invalid type: {type(other)}')

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
