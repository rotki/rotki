from typing import TYPE_CHECKING, Dict, List, NamedTuple, Optional, Tuple

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.structures import AaveEvent
from rotkehlchen.constants.ethereum import AAVE_ETH_RESERVE_ADDRESS
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

ATOKEN_TO_DEPLOYED_BLOCK = {
    'aETH': 9241088,
    'aENJ': 10471941,
    'aDAI': 9241063,
    'aUSDC': 9241071,
    'aSUSD': 9241077,
    'aTUSD': 9241068,
    'aUSDT': 9241076,
    'aBUSD': 9747321,
    'aBAT': 9241085,
    'aKNC': 9241097,
    'aLEND': 9241081,
    'aLINK': 9241091,
    'aMANA': 9241110,
    'aMKR': 9241106,
    'aREP': 9241100,
    'aREN': 10472062,
    'aSNX': 9241118,
    'aWBTC': 9241225,
    'aYFI': 10748286,
    'aZRX': 9241114,
}
ATOKENS_LIST = [EthereumToken(x) for x in ATOKEN_TO_DEPLOYED_BLOCK]


def _get_reserve_address_decimals(symbol: str) -> Tuple[ChecksumEthAddress, int]:
    """Get the reserve address and the number of decimals for symbol"""
    if symbol == 'ETH':
        reserve_address = AAVE_ETH_RESERVE_ADDRESS
        decimals = 18
    else:
        token = EthereumToken(symbol)
        reserve_address = token.ethereum_address
        decimals = token.decimals

    return reserve_address, decimals


class AaveHistory(NamedTuple):
    """All events and total interest accrued for all Atoken of an address
    """
    events: List[AaveEvent]
    total_earned: Dict[EthereumToken, Balance]


class AaveInquirer():

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_manager
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.premium = premium

    def get_history_for_addresses(
            self,
            addresses: List[ChecksumEthAddress],
            to_block: int,
    ) -> Dict[ChecksumEthAddress, AaveHistory]:
        """
        Queries aave history for a list of addresses.

        This function should be entered while holding the history_lock
        semaphore
        """
        raise NotImplementedError(
            'get_history_for_addresses() should only be implemented by subclasses',
        )
