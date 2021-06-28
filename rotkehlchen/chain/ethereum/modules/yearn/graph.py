import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from typing_extensions import Literal


from eth_utils import to_checksum_address

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.graph import Graph, format_query_indentation
from rotkehlchen.chain.ethereum.structures import YearnVaultEvent
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.ethereum.modules.yearn.vaults import get_usd_price_zero_if_error
from rotkehlchen.errors import UnknownAsset
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, EthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator


if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

QUERY_V2_VAULTS = (
    """
    {{
    vaults {{
        id
        shareToken {{
            symbol
            name
            decimals
        }}
        token {{
            symbol
            name
            decimals
            id
        }}
        apiVersion
        activation
        tags
    }}
    }}
    """
)

QUERY_USER_DEPOSITS = (
    """
    {{
    deposits(
        where: {{
            account_in: $addresses,
            blockNumber_gte: $from_block,
            blockNumber_lte: $to_block,
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
            blockNumber_gte: $from_block,
            blockNumber_lte: $to_block,
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


class YearnVaultsV2Graph:
    """Reads Yearn vaults v2 information from the graph"""

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

    def _process_event(
        self,
        events: List[Dict[str, Any]],
        event_type: Literal['deposit', 'withdraw'],
    ) -> List[YearnVaultEvent]:
        result = []

        for entry in events:
            # The id returned is a composition of hash + '-' + log_index
            try:
                _, tx_hash, log_index, _ = entry['id'].split('-')
            except ValueError as e:
                log.debug(
                    f'Failed to extract transaction hash and log index from {event_type} event '
                    f'in yearn vaults v2 graph query. Got {entry["id"]}. {str(e)}.',
                )
                self.msg_aggregator.add_warning(
                    f'Ignoring {event_type} in yearn vault V2. Failed to read id {entry["id"]}',
                )
                continue

            try:
                if event_type == 'deposit':
                    from_asset = EthereumToken(entry['vault']['token']['id'])
                    to_asset = EthereumToken(entry['vault']['shareToken']['id'])
                elif event_type == 'withdraw':
                    from_asset = EthereumToken(entry['vault']['shareToken']['id'])
                    to_asset = EthereumToken(entry['vault']['token']['id'])
            except UnknownAsset:
                if event_type == 'deposit':
                    from_str = entry['vault']['token']['symbol']
                    to_str = entry['vault']['shareToken']['symbol']
                elif event_type == 'withdraw':
                    from_str = entry['vault']['shareToken']['symbol']
                    to_str = entry['vault']['token']['symbol']
                self.msg_aggregator.add_warning(
                    f'Ignoring {event_type} in yearn vaults V2 from {from_str} to '
                    f'{to_str} because the token is not recognized.',
                )
                continue
            except KeyError as e:
                log.debug(
                    f'Failed to extract token information from {event_type} event '
                    f'in yearn vaults v2 graph query. {str(e)}.',
                )
                self.msg_aggregator.add_warning(
                    f'Ignoring {event_type} {tx_hash} in yearn vault V2 Failed to decode'
                    f' remote information. ',
                )
                continue

            try:
                from_asset_usd_price = get_usd_price_zero_if_error(
                    asset=from_asset,
                    time=Timestamp(int(entry['timestamp']) // 1000),
                    location='yearn vault v2 deposit',
                    msg_aggregator=self.msg_aggregator,
                )
                to_asset_usd_price = get_usd_price_zero_if_error(
                    asset=to_asset,
                    time=Timestamp(int(entry['timestamp']) // 1000),
                    location='yearn v2 vault deposit',
                    msg_aggregator=self.msg_aggregator,
                )
                if event_type == 'deposit':
                    from_asset_amount = token_normalized_value(
                        token_amount=int(entry['tokenAmount']),
                        token=from_asset,
                    )
                    to_asset_amount = token_normalized_value(
                        token_amount=int(entry['sharesMinted']),
                        token=to_asset,
                    )
                elif event_type == 'withdraw':
                    from_asset_amount = token_normalized_value(
                        token_amount=int(entry['sharesBurnt']),
                        token=from_asset,
                    )
                    to_asset_amount = token_normalized_value(
                        token_amount=int(entry['tokenAmount']),
                        token=to_asset,
                    )
                result.append(YearnVaultEvent(
                    event_type=event_type,
                    block_number=int(entry['blockNumber']),
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
                    log_index=int(log_index),
                    version=2,
                ))
            except (KeyError, ValueError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                log.error(
                    f'Failed to read {event_type} from yearn vaults v2 graph because the response'
                    f' does not have the expected output.',
                    error=msg,
                )
                self.msg_aggregator.add_warning(
                    f'Ignoring {event_type} {tx_hash} in yearn vault V2 from {from_asset} to '
                    f'{to_asset} because the remote information is not correct.',
                )
                continue
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
        return self._process_event(query["deposits"], 'deposit')

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

        return self._process_event(query["withdrawals"], 'withdraw')

    def get_all_events(
        self,
        addresses: List[EthAddress],
        from_block: int,
        to_block: int,
    ) -> Dict[ChecksumEthAddress, Dict[str, List[YearnVaultEvent]]]:

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

        querystr = format_query_indentation(QUERY_USER_EVENTS.format())
        query = self.graph.query(
            querystr=querystr,
            param_types=param_types,
            param_values=param_values,
        )

        result: Dict[ChecksumEthAddress, Dict[str, List[YearnVaultEvent]]] = {}

        for account in query['accounts']:
            account_id = to_checksum_address(account['id'])
            result[account_id] = {}
            result[account_id]['deposits'] = self._process_event(account['deposits'], 'deposit')
            result[account_id]['withdrawals'] = self._process_event(
                account['withdrawals'],
                'withdraw',
            )

        return result
