import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional, Set, Tuple

from eth_utils.address import to_checksum_address

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.chain.ethereum.modules.makerdao.common import RAY
from rotkehlchen.chain.ethereum.structures import (
    YearnVault,
    YearnVaultEvent,
    YearnVaults,
    get_usd_price_zero_if_error,
)
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.constants.ethereum import ATOKEN_ABI
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now

from .common import (
    AAVE_RESERVE_TO_ASSET,
    ASSET_TO_AAVE_RESERVE_ADDRESS,
    AaveBalances,
    AaveHistory,
    AaveInquirer,
    _get_reserve_address_decimals,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

log = logging.getLogger(__name__)

QUERY_USER_DEPOSITS="""
{{
  deposits(where: {{account: "{address}"{block_filter}}}) {
    id
    blockNumber
    timestamp
    tokenAmount
    sharesMinted
    transaction{{
      hash
    }}
    vault {{
      id
      token {{
        id
        symbol
      }}
      shareToken {{
        id
        symbol
      }}
    }}
  }}
}}
"""

QUERY_USER_WITHDRAWLS="""
{{
  withdrawals(where: {{account: "{address}"{block_filter}}}) {{
    id
    tokenAmount
    sharesBurnt
    blockNumber
    timestamp
    transaction{{
      hash
    }}
    vault {{
      id
      token {{
        id
        symbol
        decimals
      }}
      shareToken{{
        id
        symbol
        decimals
      }}
    }}
  }}
}}

"""

class YearnV2Inquirer:
    """Reads Yearn V2 vaults information from the graph"""

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
        self.graph = Graph('https://api.thegraph.com/subgraphs/name/salazarguille/yearn-vaults-v2-subgraph-mainnet')


    def get_deposit_events(
        self,
        address: EthAddress,
        from_block: int,
        to_block: int,
    ) -> List[YearnVaultEvent]:
        block_filter = f', blockNumber_gt: {from_block}, blockNumber_lt: {to_block}'
        query = self.graph.query(
            querystr=QUERY_USER_DEPOSITS.format(address=address, block_filter=block_filter)
        )
        result = []

        # Since multiple transactions can be made against the same token
        # I'll save here the queried price
        prices_cache: Dict[Asset, Price] = dict()

        for entry in query["deposits"]:
            # The id returned is a composition of hash + '-' + log_index
            tx_hash, log_index = entry['id'].split()

            from_asset = EthereumToken(entry['vault']['token']['symbol'])
            to_asset = EthereumToken(entry['vault']['shareToken']['symbol'])

            # since the query of prices is expensive we check if
            # it's in the dict and if not query it
            from_asset_usd_price = prices_cache.get(from_asset)
            to_asset_usd_price = prices_cache.get(to_asset)
            
            if from_asset_usd_price is None:
                prices_cache[from_asset] = get_usd_price_zero_if_error(
                    asset=from_asset,
                    time=entry['timestamp'],
                    location='yearn v2 vault deposit',
                    msg_aggregator=self.msg_aggregator
                )
                from_asset_usd_price = prices_cache.get(from_asset)
            
            if to_asset_price is None:
                to_asset_usd_price[to_asset_price] = get_usd_price_zero_if_error(
                    asset=to_asset_price,
                    time=entry['timestamp'],
                    location='yearn v2 vault deposit',
                    msg_aggregator=self.msg_aggregator
                )
                to_asset_usd_price = prices_cache.get(to_asset)

            result.append(YearnVaultEvent(
                event_type='deposit',
                block_number=entry['blockNumber'],
                timestamp=entry['timestamp'],
                from_asset=from_asset,
                from_value=Balance(
                    amount=entry['tokenAmount'],
                    usd_value=entry['tokenAmount'] * from_asset_usd_price
                ),
                to_asset=to_asset,
                from_value=Balance(
                    amount=entry['sharesMinted'],
                    usd_value=entry['sharesMinted'] * to_asset_usd_price
                ),
                realized_pnl=None,
                tx_hash=tx_hash,
                log_index=log_index
            ))

        return result

    def get_withdraw_events(
        self,
        address: EthAddress,
        from_block: int,
        to_block: int,
    ) -> List[YearnVaultEvent]:
        block_filter = f', blockNumber_gt: {from_block}, blockNumber_lt: {to_block}'
        query = self.graph.query(
            querystr=QUERY_USER_DEPOSITS.format(address=address, block_filter=block_filter)
        )
        result = []
        
        # Since multiple transactions can be made against the same token
        # I'll save here the queried price
        prices_cache: Dict[Asset, Price] = dict()

        for entry in query["deposits"]:
            # The id returned is a composition of hash + '-' + log_index

            tx_hash, log_index = entry['id'].split()

            from_asset = EthereumToken(entry['vault']['shareToken']['symbol'])
            to_asset = EthereumToken(entry['vault']['token']['symbol'])

            # since the query of prices is expensive we check if
            # it's in the dict and if not query it
            from_asset_usd_price = prices_cache.get(from_asset)
            to_asset_usd_price = prices_cache.get(to_asset)
            
            if from_asset_usd_price is None:
                prices_cache[from_asset] = get_usd_price_zero_if_error(
                    asset=from_asset,
                    time=entry['timestamp'],
                    location='yearn v2 vault deposit',
                    msg_aggregator=self.msg_aggregator
                )
                from_asset_usd_price = prices_cache.get(from_asset)
            
            if to_asset_price is None:
                to_asset_usd_price[to_asset_price] = get_usd_price_zero_if_error(
                    asset=to_asset_price,
                    time=entry['timestamp'],
                    location='yearn v2 vault deposit',
                    msg_aggregator=self.msg_aggregator
                )
                to_asset_usd_price = prices_cache.get(to_asset)

            result.append(YearnVaultEvent(
                event_type='deposit',
                block_number=entry['blockNumber'],
                timestamp=entry['timestamp'],
                from_asset=from_asset,
                from_value=Balance(
                    amount=entry['sharesBurnt'],
                    usd_value=entry['sharesBurnt'] * from_asset_usd_price
                ),
                to_asset=to_asset,
                from_value=Balance(
                    amount=entry['tokenAmount'],
                    usd_value=entry['tokenAmount'] * to_asset_usd_price
                ),
                realized_pnl=None,
                tx_hash=tx_hash,
                log_index=log_index
            ))

        return result