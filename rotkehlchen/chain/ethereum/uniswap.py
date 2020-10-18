import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional, Tuple, Union

from eth_utils import to_checksum_address
from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.ethereum.zerion import GIVEN_DEFI_BALANCES
from rotkehlchen.constants.ethereum import CTOKEN_ABI, ERC20TOKEN_ABI, EthereumConstants
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import BlockchainQueryError, RemoteError, UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import (
    deserialize_blocknumber,
    deserialize_int_from_hex_or_int,
)
from rotkehlchen.typing import BalanceType, ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager

A_UNI = EthereumToken('UNI')

PAIRS_QUERY_PREFIX = """{graph_event_name}
 (id: "{token_address}") {{
    id
    token0 {{
        id
        name
        symbol
    }}
    token1 {{
        id
        name
        symbol
    }}
}}}}"""

log = logging.getLogger(__name__)

class UniswapBalance(NamedTuple):
    balance_type: BalanceType
    balance: Balance

    def serialize(self) -> Dict[str, Union[Optional[str], Dict[str, str]]]:
        return {
            'balance': self.balance.serialize(),
        }

class UniswapEvent(NamedTuple):
    pass

class Uniswap(EthereumModule):
    """Uniswap integration module

    https://uniswap.org/docs/v2
    """

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: DBHandler,
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ):
        self.ethereum = ethereum_manager
        self.database = database
        self.premium = premium
        self.msg_aggregator = msg_aggregator
        self.graph = Graph('https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2')

    def get_balances(
            self,
            given_defi_balances: GIVEN_DEFI_BALANCES,
    ) -> Dict[ChecksumEthAddress, Dict]:
        uniswap_balances = {}
        if isinstance(given_defi_balances, dict):
            defi_balances = given_defi_balances
        else:
            defi_balances = given_defi_balances()

        log.info("defi_balances: {}".format(defi_balances))

        for account, balance_entries in defi_balances.items():
            log.info("account: {} balance_entries: {}".format(account, balance_entries))
            liquidity_map = {}
            rewards_map = {}
            for balance_entry in balance_entries:
                if balance_entry.protocol.name != 'Uniswap V2':
                    continue

                entry = balance_entry.base_balance

                result = self.graph.query(
                    querystr=PAIRS_QUERY_PREFIX.format(
                        graph_event_name='pair',
                        token_address=entry.token_address.lower(),
                    ),
                    param_types=None,
                    param_values=None,
                )
                log.info("graph query result: {}".format(result))
                if not result['pair']:
                    continue
                pair_name = f'Uniswap V2 {result["pair"]["token0"]["symbol"]}-{result["pair"]["token1"]["symbol"]} Pair'
                try:
                    asset_1 = Asset(result['pair']['token0']['symbol'])
                except UnknownAsset:
                    asset_1 = None

                try:
                    asset_2 = Asset(result['pair']['token1']['symbol'])
                except UnknownAsset:
                    asset_2 = None

                if asset_1 or asset_2:
                    liquidity_map[pair_name] = UniswapBalance(
                        balance_type=BalanceType.ASSET,
                        balance=entry.balance,
                    )
                else:
                    log.error(
                        f'Encountered unknown asset {pair_name} in Uniswap V2. Skipping',
                    )
                    continue

            if liquidity_map == {} and rewards_map == {}:
                # no balances for the account
                continue
            uniswap_balances[account] = {
                'rewards': rewards_map,
                'liquidity': liquidity_map,
            }


        return uniswap_balances

    def get_fees(self) -> None:
        pass

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass