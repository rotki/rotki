from typing import TYPE_CHECKING, Optional

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.constants.ethereum import ATOKEN_ABI, ZERO_ADDRESS
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager

ATOKEN_TO_DEPLOYED_BLOCK = {
    'aETH': 9241088,
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
    'aSNX': 9241118,
    'aWBTC': 9241225,
    'aZRX': 9241114,
}


class Aave():
    """Aave integration module

    https://docs.aave.com/developers/developing-on-aave/the-protocol/lendingpool#deposit
    """

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: DBHandler,
            premium: Premium,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_manager
        self.msg_aggregator = msg_aggregator
        self.premium = premium

    def get_deposits_for_atoken_and_address(
            self,
            user_address: ChecksumEthAddress,
            atoken: EthereumToken,
            given_from_block: Optional[int],
    ):
        from_block = ATOKEN_TO_DEPLOYED_BLOCK[atoken.identifier] if given_from_block is None else given_from_block  # noqa: E501
        argument_filters = {
            'from': ZERO_ADDRESS,
            'to': user_address,
        }
        events = self.ethereum.get_logs(
            contract_address=atoken.ethereum_address,
            abi=ATOKEN_ABI,
            event_name='Transfer',
            argument_filters=argument_filters,
            from_block=from_block,
            to_block='latest',
        )
        return events
