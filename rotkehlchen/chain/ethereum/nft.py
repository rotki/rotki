from typing import Any, Dict, List, NamedTuple

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.externalapis.opensea import NFT, Opensea
from rotkehlchen.typing import ChecksumEthAddress
from rotkehlchen.user_messages import MessagesAggregator

FREE_NFT_LIMIT = 5


class NFTResult(NamedTuple):
    addresses: Dict[ChecksumEthAddress, List[NFT]]
    entries_found: int
    entries_limit: int

    def serialize(self) -> Dict[str, Any]:
        return {
            'addresses': {address: [x.serialize() for x in nfts] for address, nfts in self.addresses.items()},  # noqa: E501
            'entries_found': self.entries_found,
            'entries_limit': self.entries_limit,
        }


class NFTManager():

    def __init__(
            self,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.opensea = Opensea(database=database, msg_aggregator=msg_aggregator)

    def get_all_nfts(
            self,
            addresses: List[ChecksumEthAddress],
            has_premium: bool,
    ) -> NFTResult:
        """Gets all NFTs of the given addresses

        Returns a tuple with:
        - Mapping of addresses to list of NFTs
        - Total NFTs found - integer
        - Limit for free NFTs - integer

        May raise:
        - RemoteError
        """

        result = {}
        total_nfts_num = 0
        for address in addresses:
            nfts = self.opensea.get_account_nfts(address)
            nfts_num = len(nfts)
            if nfts_num != 0:
                if has_premium is False:
                    if nfts_num + total_nfts_num > FREE_NFT_LIMIT:
                        remaining_size = FREE_NFT_LIMIT - total_nfts_num
                    else:
                        remaining_size = nfts_num
                    if remaining_size != 0:
                        result[address] = nfts[:remaining_size]
                        total_nfts_num += remaining_size

                    break  # we hit the nft limit

                result[address] = nfts
                total_nfts_num += nfts_num

        return NFTResult(
            addresses=result,
            entries_found=total_nfts_num,
            entries_limit=FREE_NFT_LIMIT,
        )
