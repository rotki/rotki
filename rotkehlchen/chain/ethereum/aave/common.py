from typing import TYPE_CHECKING, Dict, List, NamedTuple, Optional, Tuple, Union

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.structures import AaveEvent
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.ethereum import AAVE_ETH_RESERVE_ADDRESS
from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler


class AaveLendingBalance(NamedTuple):
    """A balance for Aave lending.

    Asset not included here since it's the key in the map that leads to this structure
    """
    balance: Balance
    apy: FVal

    def serialize(self) -> Dict[str, Union[str, Dict[str, str]]]:
        return {
            'balance': self.balance.serialize(),
            'apy': self.apy.to_percentage(precision=2),
        }


class AaveBorrowingBalance(NamedTuple):
    """A balance for Aave borrowing.

    Asset not included here since it's the key in the map that leads to this structure
    """
    balance: Balance
    variable_apr: FVal
    stable_apr: FVal

    def serialize(self) -> Dict[str, Union[str, Dict[str, str]]]:
        return {
            'balance': self.balance.serialize(),
            'variable_apr': self.variable_apr.to_percentage(precision=2),
            'stable_apr': self.stable_apr.to_percentage(precision=2),
        }


class AaveBalances(NamedTuple):
    """The Aave balances per account. Using str for symbol since ETH is not a token"""
    lending: Dict[str, AaveLendingBalance]
    borrowing: Dict[str, AaveBorrowingBalance]


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
    'aAAVE': 11093579,
    'aUNI': 11132284,
}
ATOKENS_LIST = [EthereumToken(x) for x in ATOKEN_TO_DEPLOYED_BLOCK]


AAVE_RESERVE_TO_ASSET = {
    AAVE_ETH_RESERVE_ADDRESS: A_ETH,
    '0xF629cBd94d3791C9250152BD8dfBDF380E2a3B9c': EthereumToken('ENJ'),
    '0x6B175474E89094C44Da98b954EedeAC495271d0F': EthereumToken('DAI'),
    '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48': EthereumToken('USDC'),
    '0x57Ab1ec28D129707052df4dF418D58a2D46d5f51': EthereumToken('sUSD'),
    '0x0000000000085d4780B73119b644AE5ecd22b376': EthereumToken('TUSD'),
    '0xdAC17F958D2ee523a2206206994597C13D831ec7': EthereumToken('USDT'),
    '0x4Fabb145d64652a948d72533023f6E7A623C7C53': EthereumToken('BUSD'),
    '0x0D8775F648430679A709E98d2b0Cb6250d2887EF': EthereumToken('BAT'),
    '0xdd974D5C2e2928deA5F71b9825b8b646686BD200': EthereumToken('KNC'),
    '0x80fB784B7eD66730e8b1DBd9820aFD29931aab03': EthereumToken('LEND'),
    '0x514910771AF9Ca656af840dff83E8264EcF986CA': EthereumToken('LINK'),
    '0x0F5D2fB29fb7d3CFeE444a200298f468908cC942': EthereumToken('MANA'),
    '0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2': EthereumToken('MKR'),
    '0x1985365e9f78359a9B6AD760e32412f4a445E862': EthereumToken('REP'),
    '0x408e41876cCCDC0F92210600ef50372656052a38': EthereumToken('REN'),
    '0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F': EthereumToken('SNX'),
    '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599': EthereumToken('WBTC'),
    '0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e': EthereumToken('YFI'),
    '0xE41d2489571d322189246DaFA5ebDe1F4699F498': EthereumToken('ZRX'),
    '0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9': EthereumToken('AAVE'),
    '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984': EthereumToken('UNI'),
}
ASSET_TO_AAVE_RESERVE_ADDRESS = {v: k for k, v in AAVE_RESERVE_TO_ASSET.items()}


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
    total_earned_interest: Dict[Asset, Balance]
    total_lost: Dict[Asset, Balance]
    total_earned_liquidations: Dict[Asset, Balance]


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
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            aave_balances: Dict[ChecksumEthAddress, AaveBalances],
    ) -> Dict[ChecksumEthAddress, AaveHistory]:
        """
        Queries aave history for a list of addresses.

        This function should be entered while holding the history_lock
        semaphore
        """
        raise NotImplementedError(
            'get_history_for_addresses() should only be implemented by subclasses',
        )
