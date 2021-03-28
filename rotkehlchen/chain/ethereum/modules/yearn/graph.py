import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.graph import Graph, format_query_indentation
from rotkehlchen.chain.ethereum.structures import YearnVaultEvent
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.ethereum.modules.yearn.vaults import get_usd_price_zero_if_error
from rotkehlchen.errors import UnknownAsset
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import Price, EthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator


if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

log = logging.getLogger(__name__)

QUERY_USER_DEPOSITS = (
    """
    {{
    deposits(
        where: {{
            account_in: $addresses,
            timestamp_gte: $from_block,
            timestamp_lte: $to_block,
        }}) {{
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
)

QUERY_USER_WITHDRAWLS = (
    """
    {{
    withdrawals(
        where: {{
            account_in: $addresses,
            timestamp_gte: $from_block,
            timestamp_lte: $to_block,
        }}) {{
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
        }}
        shareToken{{
            id
            symbol
        }}
        }}
    }}
    }}
    """
)

QUERY_USER_EVENTS = (
    """
    accounts(
        where: {{
            id_in: $addresses
        }}) {{
            id
            deposits(where:{{blockNumber_gte: $from_block, blockNumber_lte: $to_block }}){{
                id
                blockNumber
                timestamp
                tokenAmount
                sharesMinted
                vault {{
                    id
                    shareToken {{
                        id
                        symbol
                        name
                    }}
                    token {{
                        id
                        symbol
                        name
                    }}
                }}
            }}
            withdrawals(where:{{blockNumber_gte: $from_block, blockNumber_lte: $to_block }}) {{
                id
                blockNumber
                timestamp
                tokenAmount
                sharesBurnt
                vault {{
                    id
                    shareToken {{
                        id
                        symbol
                        name
                    }}
                    token {{
                        id
                        symbol
                        name
                    }}
                }}
            }}
        }}
    }}
    """
)


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
        self.graph = Graph('https://api.thegraph.com/subgraphs/name/salazarguille/yearn-vaults-v2-subgraph-mainnet')  # noqa: E501

    def _process_deposits(self, deposits: List[Dict[str, Any]]) -> List[YearnVaultEvent]:
        result = []

        # Since multiple transactions can be made against the same token
        # I'll save here the queried price
        prices_cache: Dict[Asset, Price] = {}

        for entry in deposits:
            # The id returned is a composition of hash + '-' + log_index
            _, tx_hash, log_index = entry['id'].split('-')

            try:
                from_asset = EthereumToken(entry['vault']['token']['symbol'])
                to_asset = EthereumToken(entry['vault']['shareToken']['symbol'])
            except UnknownAsset:
                from_str = entry['vault']['token']['symbol']
                to_str = entry['vault']['shareToken']['symbol']

                self.msg_aggregator.add_warning(
                    f'Ignoring deposit in yearn V2 from {from_str} to '
                    f'{to_str} because the token is not recognized.',
                )
                continue

            # since the query of prices is expensive we check if
            # it's in the dict and if not query it
            from_asset_usd_price = prices_cache.get(from_asset)
            to_asset_usd_price = prices_cache.get(to_asset)

            if from_asset_usd_price is None:
                prices_cache[from_asset] = get_usd_price_zero_if_error(
                    asset=from_asset,
                    time=Timestamp(int(entry['timestamp']) // 1000),
                    location='yearn v2 vault deposit',
                    msg_aggregator=self.msg_aggregator,
                )
                from_asset_usd_price = prices_cache.get(from_asset)

            if to_asset_usd_price is None:
                prices_cache[to_asset] = get_usd_price_zero_if_error(
                    asset=to_asset,
                    time=Timestamp(int(entry['timestamp']) // 1000),
                    location='yearn v2 vault deposit',
                    msg_aggregator=self.msg_aggregator,
                )
                to_asset_usd_price = prices_cache.get(to_asset)

            from_asset_amount = token_normalized_value(
                token_amount=int(entry['tokenAmount']),
                token=from_asset,
            )

            to_asset_amount = token_normalized_value(
                token_amount=int(entry['sharesMinted']),
                token=to_asset,
            )

            result.append(YearnVaultEvent(
                event_type='deposit',
                block_number=entry['blockNumber'],
                timestamp=Timestamp(int(entry['timestamp']) // 1000),
                from_asset=from_asset,
                from_value=Balance(
                    amount=from_asset_amount,
                    usd_value=from_asset_amount * from_asset_usd_price,
                ),
                to_asset=to_asset,
                to_value=Balance(
                    amount=to_asset_amount,
                    usd_value=to_asset_amount * to_asset_usd_price,
                ),
                realized_pnl=None,
                tx_hash=tx_hash,
                log_index=log_index,
            ))
        return result

    def _process_withdrawals(self, withdrawals: List[Any]) -> List[YearnVaultEvent]:
        # Since multiple transactions can be made against the same token
        # I'll save here the queried price
        prices_cache: Dict[Asset, Price] = {}

        result = []

        for entry in withdrawals:
            # The id returned is a composition of address + hash + '-' + log_index

            _, tx_hash, log_index = entry['id'].split('-')

            try:
                from_asset = EthereumToken(entry['vault']['shareToken']['symbol'])
                to_asset = EthereumToken(entry['vault']['token']['symbol'])
            except UnknownAsset:
                from_str = entry['vault']['shareToken']['symbol']
                to_str = entry['vault']['token']['symbol']

                self.msg_aggregator.add_warning(
                    f'Ignoring deposit in yearn V2 from {from_str} to '
                    f'{to_str} because the token is not recognized.',
                )
                continue

            # since the query of prices is expensive we check if
            # it's in the dict and if not query it
            from_asset_usd_price = prices_cache.get(from_asset)
            to_asset_usd_price = prices_cache.get(to_asset)

            if from_asset_usd_price is None:
                prices_cache[from_asset] = get_usd_price_zero_if_error(
                    asset=from_asset,
                    time=Timestamp(int(entry['timestamp']) // 1000),
                    location='yearn v2 vault withdrawal',
                    msg_aggregator=self.msg_aggregator,
                )
                from_asset_usd_price = prices_cache.get(from_asset)

            if to_asset_usd_price is None:
                prices_cache[to_asset] = get_usd_price_zero_if_error(
                    asset=to_asset,
                    time=Timestamp(int(entry['timestamp']) // 1000),
                    location='yearn v2 vault withdrawal',
                    msg_aggregator=self.msg_aggregator,
                )
                to_asset_usd_price = prices_cache.get(to_asset)

            from_asset_amount = token_normalized_value(
                token_amount=int(entry['sharesBurnt']),
                token=from_asset,
            )

            to_asset_amount = token_normalized_value(
                token_amount=int(entry['tokenAmount']),
                token=to_asset,
            )

            result.append(YearnVaultEvent(
                event_type='deposit',
                block_number=entry['blockNumber'],
                timestamp=Timestamp(int(entry['timestamp']) // 1000),
                from_asset=from_asset,
                from_value=Balance(
                    amount=from_asset_amount,
                    usd_value=from_asset_amount * from_asset_usd_price,
                ),
                to_asset=to_asset,
                to_value=Balance(
                    amount=to_asset_amount,
                    usd_value=to_asset_amount * to_asset_usd_price,
                ),
                realized_pnl=None,
                tx_hash=tx_hash,
                log_index=log_index,
            ))

        return result

    def get_deposit_events(
        self,
        addresses: EthAddress,
        from_block: int,
        to_block: int,
    ) -> List[YearnVaultEvent]:
        param_types = {
            '$from_block': 'BigInt!',
            '$to_block': 'BigInt!',
            '$addresses': '[Bytes!]',
        }

        param_values = {
            'from_block': from_block,
            'to_block': to_block,
            'addresses': addresses,
        }
        query = self.graph.query(
            querystr=QUERY_USER_DEPOSITS,
            param_types=param_types,
            param_values=param_values,
        )
        return self._process_deposits(query["deposits"])

    def get_withdraw_events(
        self,
        addresses: EthAddress,
        from_block: int,
        to_block: int,
    ) -> List[YearnVaultEvent]:
        param_types = {
            '$from_block': 'BigInt!',
            '$to_block': 'BigInt!',
            '$addresses': '[Bytes!]',
        }
        param_values = {
            'from_block': from_block,
            'to_block': to_block,
            'addresses': addresses,
        }
        query = self.graph.query(
            querystr=QUERY_USER_WITHDRAWLS,
            param_types=param_types,
            param_values=param_values,
        )
        return self._process_withdrawals(query["withdrawals"])

    def get_all_events(
        self,
        addresses: List[EthAddress],
        from_block: int,
        to_block: int,
    ) -> Dict[str, List[YearnVaultEvent]]:

        param_types = {
            '$from_block': 'BigInt!',
            '$to_block': 'BigInt!',
            '$addresses': '[Bytes!]',
        }
        param_values = {
            'from_block': from_block,
            'to_block': to_block,
            'addresses': addresses,
        }
        #  TODO: need to paginate correctly this query
        querystr = format_query_indentation(QUERY_USER_EVENTS.format())
        query = self.graph.query(
            querystr=querystr,
            param_types=param_types,
            param_values=param_values,
        )
        result = {}

        for account in query['accounts']:
            account_id = account['id']
            result[account_id] = {}
            result[account_id]['deposits'] = self._process_deposits(account['deposits'])
            result[account_id]['withdrawals'] = self._process_withdrawals(account['withdrawals'])

        return result
