from typing import NamedTuple, Optional, Tuple

from rotkehlchen.serialization.deserialize import deserialize_ethereum_address
from rotkehlchen.typing import ChecksumEthAddress, Timestamp

DBEntryEthereumTokenTuple = Tuple[
    str,                  # address
    int,                  # decimals
    str,                  # name
    str,                  # symbol
    Optional[int],  # started
    Optional[str],        # coingecko
    Optional[str],        # cryptocompare
]


class DBEntryEthereumToken(NamedTuple):
    address: ChecksumEthAddress
    decimals: int
    name: str
    symbol: str
    started: Optional[Timestamp]
    coingecko: Optional[str]
    cryptocompare: Optional[str]

    def to_db_tuple(self) -> DBEntryEthereumTokenTuple:
        return (
            self.address,
            self.decimals,
            self.name,
            self.symbol,
            self.started,
            self.coingecko,
            self.cryptocompare,
        )

    @classmethod
    def deserialize_from_db(cls, entry: DBEntryEthereumTokenTuple) -> 'DBEntryEthereumToken':
        return DBEntryEthereumToken(
            address=deserialize_ethereum_address(entry[0]),
            decimals=entry[1],
            name=entry[2],
            symbol=entry[3],
            started=Timestamp(entry[4]),  # type: ignore
            coingecko=entry[5],
            cryptocompare=entry[6],
        )
