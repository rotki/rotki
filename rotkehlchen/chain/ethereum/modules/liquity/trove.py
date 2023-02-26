import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, DefaultDict, NamedTuple, Optional

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures.balance import AssetBalance, Balance
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.defi.defisaver_proxy import HasDSProxy
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.constants.assets import A_ETH, A_LQTY, A_LUSD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import deserialize_asset_amount
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.user_messages import MessagesAggregator

from .constants import CPT_LIQUITY

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.contracts import EvmContract
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

MIN_COLL_RATE = '1.1'

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# This queries search for events having a specific combination of asset + staking type + reward
# and being from liquity this helps to filter if they are from the stability pool or the LQTY
# staking. Then we need to consider the rewards in other assets that appear in the same
# transaction and this is why we use the IN operator as filter.
QUERY_STAKING_EVENTS = """
WHERE event_identifier IN
(SELECT A.event_identifier FROM history_events AS A JOIN history_events AS B ON A.event_identifier = B.event_identifier WHERE
    A.counterparty=? AND A.asset=? AND
    B.asset=? AND B.subtype != ? AND B.type == ?
) AND type=? AND subtype=?
"""  # noqa: E501
BINDINGS_STAKING_EVENTS = [
    CPT_LIQUITY, A_LQTY.identifier, A_LUSD.identifier, HistoryEventSubType.DEPOSIT_ASSET.serialize(),  # noqa: E501
    HistoryEventType.STAKING.serialize(), HistoryEventType.STAKING.serialize(),
    HistoryEventSubType.REWARD.serialize(),
]
# stability pool rewards
QUERY_STABILITY_POOL_EVENTS = """
WHERE event_identifier IN (
    SELECT A.event_identifier FROM history_events AS A JOIN history_events AS B ON
    A.event_identifier = B.event_identifier WHERE A.counterparty = "liquity" AND
    B.asset=? AND B.subtype=?
) AND type=? AND subtype=?
"""
BINDINGS_STABILITY_POOL_EVENTS = [
    A_LQTY.identifier,
    HistoryEventSubType.REWARD.serialize(),
    HistoryEventType.STAKING.serialize(),
    HistoryEventSubType.REWARD.serialize(),
]
QUERY_STABILITY_POOL_DEPOSITS = (
    'SELECT SUM(CAST(amount AS REAL)), SUM(CAST(usd_value AS REAL)) '
    'FROM history_events WHERE asset=? AND type=? AND subtype=?'
)


class Trove(NamedTuple):
    collateral: AssetBalance
    debt: AssetBalance
    collateralization_ratio: Optional[FVal]
    liquidation_price: Optional[FVal]
    active: bool
    trove_id: int

    def serialize(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        result['collateral'] = self.collateral.serialize()
        result['debt'] = self.debt.serialize()
        result['collateralization_ratio'] = self.collateralization_ratio
        result['liquidation_price'] = self.liquidation_price
        result['active'] = self.active
        result['trove_id'] = self.trove_id
        return result


class Liquity(HasDSProxy):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            ethereum_inquirer=ethereum_inquirer,
            database=database,
            premium=premium,
            msg_aggregator=msg_aggregator,
        )
        self.history_lock = Semaphore()
        self.trove_manager_contract = self.ethereum.contracts.contract('LIQUITY_TROVE_MANAGER')
        self.stability_pool_contract = self.ethereum.contracts.contract('LIQUITY_STABILITY_POOL')
        self.staking_contract = self.ethereum.contracts.contract('LIQUITY_STAKING')

    def get_positions(
            self,
            addresses_list: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, Trove]:
        """Query liquity contract to detect open troves"""
        # make a copy of the list to avoid modifications in the list that is passed as argument
        addresses = addresses_list.copy()
        proxied_addresses = self.ethereum.proxies_inquirer.get_accounts_having_proxy()
        proxies_to_address = {v: k for k, v in proxied_addresses.items()}
        addresses += proxied_addresses.values()

        calls = [
            (self.trove_manager_contract.address, self.trove_manager_contract.encode(method_name='Troves', arguments=[x]))  # noqa: E501
            for x in addresses
        ]
        outputs = self.ethereum.multicall_2(
            require_success=False,
            calls=calls,
        )

        data: dict[ChecksumEvmAddress, Trove] = {}
        eth_price = Inquirer().find_usd_price(A_ETH)
        lusd_price = Inquirer().find_usd_price(A_LUSD)
        for idx, output in enumerate(outputs):
            status, result = output
            if status is True:
                try:
                    trove_info = self.trove_manager_contract.decode(result, 'Troves', arguments=[addresses[idx]])  # noqa: E501
                    trove_is_active = bool(trove_info[3])  # pylint: disable=unsubscriptable-object
                    if not trove_is_active:
                        continue
                    collateral = deserialize_asset_amount(
                        token_normalized_value_decimals(trove_info[1], 18),  # noqa: E501 pylint: disable=unsubscriptable-object
                    )
                    debt = deserialize_asset_amount(
                        token_normalized_value_decimals(trove_info[0], 18),  # noqa: E501 pylint: disable=unsubscriptable-object
                    )
                    collateral_balance = AssetBalance(
                        asset=A_ETH,
                        balance=Balance(
                            amount=collateral,
                            usd_value=eth_price * collateral,
                        ),
                    )
                    debt_balance = AssetBalance(
                        asset=A_LUSD,
                        balance=Balance(
                            amount=debt,
                            usd_value=lusd_price * debt,
                        ),
                    )
                    # Avoid division errors
                    collateralization_ratio: Optional[FVal]
                    liquidation_price: Optional[FVal]
                    if debt > 0:
                        collateralization_ratio = eth_price * collateral / debt * 100
                    else:
                        collateralization_ratio = None
                    if collateral > 0:
                        liquidation_price = debt * lusd_price * FVal(MIN_COLL_RATE) / collateral
                    else:
                        liquidation_price = None

                    account_address = addresses[idx]
                    if account_address in proxies_to_address:
                        account_address = proxies_to_address[account_address]
                    data[account_address] = Trove(
                        collateral=collateral_balance,
                        debt=debt_balance,
                        collateralization_ratio=collateralization_ratio,
                        liquidation_price=liquidation_price,
                        active=trove_is_active,
                        trove_id=trove_info[4],  # pylint: disable=unsubscriptable-object
                    )
                except DeserializationError as e:
                    self.msg_aggregator.add_warning(
                        f'Ignoring Liquity trove information. '
                        f'Failed to decode contract information. {str(e)}.',
                    )
        return data

    def _query_deposits_and_rewards(
            self,
            contract: 'EvmContract',
            addresses: list[ChecksumEvmAddress],
            methods: tuple[str, str, str],
            keys: tuple[str, str, str],
            assets: tuple['Asset', 'Asset', 'Asset'],
    ) -> dict[ChecksumEvmAddress, dict[str, AssetBalance]]:
        """
        For Liquity staking contracts there is always one asset that we stake and two other assets
        for rewards. This method abstracts the logic of querying the staked amount and the
        rewards for both the stability pool and the LQTY staking.

        - addresses: The addresses that will be queried
        - methods: the methods that need to be queried to get the staked amount and rewards
        - keys: the keys used in the dict response to map each method
        - assets: the asset associated with each method called
        """
        # make a copy of the list to avoid modifications in the list that is passed as argument
        addresses = addresses.copy()
        proxied_addresses = self.ethereum.proxies_inquirer.get_accounts_having_proxy()
        addresses += proxied_addresses.values()

        # Build the calls that need to be made in order to get the status in the SP
        calls = []
        for address in addresses:
            for method in methods:
                calls.append(
                    (contract.address, contract.encode(method_name=method, arguments=[address])),
                )

        try:
            outputs = self.ethereum.multicall_2(
                require_success=False,
                calls=calls,
            )
        except (RemoteError, BlockchainQueryError) as e:
            self.msg_aggregator.add_error(
                f'Failed to query information about stability pool {str(e)}',
            )
            return {}

        # the structure of the queried data is:
        # staked address 1, reward 1 of address 1, reward 2 of address 1, staked address 2, reward 1 of address 2, ...  # noqa: E501
        data: DefaultDict[ChecksumEvmAddress, dict[str, AssetBalance]] = defaultdict(dict)
        for idx, output in enumerate(outputs):
            # depending on the output index get the address we are tracking
            current_address = addresses[idx // 3]
            status, result = output
            if status is False:
                continue

            # make sure that variables always have a value set. It is guaranteed that the response
            # will have the desired format because we include and process failed queries.
            key, asset, gain_info = keys[0], assets[0], 0
            for method_idx, (method, _asset, _key) in enumerate(zip(methods, assets, keys)):
                # get the asset, key used in the response and the amount based on the index
                # for this address
                if idx % 3 == method_idx:
                    asset = _asset
                    key = _key
                    gain_info = contract.decode(result, method, arguments=[current_address])[0]    # pylint: disable=unsubscriptable-object  # noqa: E501
                    break

            # get price information for the asset and deserialize the amount
            asset_price = Inquirer().find_usd_price(asset)
            amount = deserialize_asset_amount(
                token_normalized_value_decimals(gain_info, 18),
            )
            data[current_address][key] = AssetBalance(
                asset=asset,
                balance=Balance(
                    amount=amount,
                    usd_value=asset_price * amount,
                ),
            )

        return data

    def get_stability_pool_balances(
            self,
            addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, dict[str, AssetBalance]]:
        return self._query_deposits_and_rewards(
            contract=self.stability_pool_contract,
            addresses=addresses,
            methods=('getDepositorETHGain', 'getDepositorLQTYGain', 'getCompoundedLUSDDeposit'),
            keys=('gains', 'rewards', 'deposited'),
            assets=(A_ETH, A_LQTY, A_LUSD),
        )

    def liquity_staking_balances(
            self,
            addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, dict[str, AssetBalance]]:
        """
        Query the ethereum chain to retrieve information about staked assets
        """
        return self._query_deposits_and_rewards(
            contract=self.staking_contract,
            addresses=addresses,
            methods=('stakes', 'getPendingLUSDGain', 'getPendingETHGain'),
            keys=('staked', 'lusd_rewards', 'eth_rewards'),
            assets=(A_LQTY, A_LUSD, A_ETH),
        )

    def _get_stats(
            self,
            cursor: 'DBCursor',
            history_events_db: DBHistoryEvents,
            query_staking: str,
            bindings_staking: list[Any],
            query_stability_pool: str,
            bindings_stability_pool: list[Any],
            query_stability_pool_deposits: str,
            deposit_pool_bindings: list[Any],
            withdrawal_pool_bindings: list[Any],
    ) -> dict[str, Any]:
        """
        Query the database using the given pre-computed filters and create a report
        with all the information related to staking
        """
        total_usd_staking_rewards, staking_rewards_breakdown = history_events_db.get_value_stats(
            cursor=cursor,
            query_filters=query_staking,
            bindings=bindings_staking,
        )
        total_usd_stability_rewards, stability_rewards_breakdown = history_events_db.get_value_stats(  # noqa: E501
            cursor=cursor,
            query_filters=query_stability_pool,
            bindings=bindings_stability_pool,
        )
        # get stats about LUSD deposited in the stability pool
        cursor.execute(query_stability_pool_deposits, deposit_pool_bindings)
        stability_pool_deposits = cursor.fetchone()

        cursor.execute(query_stability_pool_deposits, withdrawal_pool_bindings)
        stability_pool_withdrawals = cursor.fetchone()

        return {
            'total_usd_gains_stability_pool': total_usd_stability_rewards,
            'total_usd_gains_stacking': total_usd_staking_rewards,
            'total_deposited_stability_pool': FVal(stability_pool_deposits[0]) if stability_pool_deposits[0] is not None else ZERO,  # noqa: E501
            'total_withdrawn_stability_pool': FVal(stability_pool_withdrawals[0]) if stability_pool_withdrawals[0] is not None else ZERO,  # noqa: E501
            'total_deposited_stability_pool_usd_value': FVal(stability_pool_deposits[1]) if stability_pool_deposits[1] is not None else ZERO,  # noqa: E501
            'total_withdrawn_stability_pool_usd_value': FVal(stability_pool_withdrawals[1]) if stability_pool_withdrawals[1] is not None else ZERO,  # noqa: E501
            'staking_gains': [
                {
                    'asset': entry[0],
                    'amount': entry[1],
                    'usd_value': entry[2],
                } for entry in staking_rewards_breakdown
            ],
            'stability_pool_gains': [
                {
                    'asset': entry[0],
                    'amount': entry[1],
                    'usd_value': entry[2],
                } for entry in stability_rewards_breakdown
            ],
        }

    def get_stats(self, addresses: list[ChecksumEvmAddress]) -> dict[str, Any]:
        """
        Query staking information for the liquity module related to both the LQTY statking
        and the stability pool. It returns a dictionary combining the information from all
        the addresses and stats per address.
        """
        history_events_db = DBHistoryEvents(self.database)
        result = {}
        with self.database.conn.read_ctx() as cursor:
            result['global_stats'] = self._get_stats(
                cursor=cursor,
                history_events_db=history_events_db,
                query_staking=QUERY_STAKING_EVENTS,
                bindings_staking=BINDINGS_STAKING_EVENTS,
                query_stability_pool=QUERY_STABILITY_POOL_EVENTS,
                bindings_stability_pool=BINDINGS_STABILITY_POOL_EVENTS,
                query_stability_pool_deposits=QUERY_STABILITY_POOL_DEPOSITS,
                deposit_pool_bindings=[A_LUSD.identifier, HistoryEventType.STAKING.serialize(), HistoryEventSubType.DEPOSIT_ASSET.serialize()],  # noqa: E501
                withdrawal_pool_bindings=[A_LUSD.identifier, HistoryEventType.STAKING.serialize(), HistoryEventSubType.REMOVE_ASSET.serialize()],  # noqa: E501
            )

            if len(addresses) == 0:
                return result

            result['by_address'] = {}
            query_staking_events_with_address = QUERY_STAKING_EVENTS + ' AND location_label=?'
            query_stability_pool_events_with_address = QUERY_STABILITY_POOL_EVENTS + ' AND location_label=?'  # noqa: E501
            query_stability_pool_deposits = QUERY_STABILITY_POOL_DEPOSITS + ' AND location_label=?'
            for address in addresses:
                result['by_address'][address] = self._get_stats(
                    cursor=cursor,
                    history_events_db=history_events_db,
                    query_staking=query_staking_events_with_address,
                    bindings_staking=[*BINDINGS_STAKING_EVENTS, address],
                    query_stability_pool=query_stability_pool_events_with_address,
                    bindings_stability_pool=[*BINDINGS_STABILITY_POOL_EVENTS, address],
                    query_stability_pool_deposits=query_stability_pool_deposits,
                    deposit_pool_bindings=[A_LUSD.identifier, HistoryEventType.STAKING.serialize(), HistoryEventSubType.DEPOSIT_ASSET.serialize(), address],  # noqa: E501
                    withdrawal_pool_bindings=[A_LUSD.identifier, HistoryEventType.STAKING.serialize(), HistoryEventSubType.REMOVE_ASSET.serialize(), address],  # noqa: E501
                )
        return result
