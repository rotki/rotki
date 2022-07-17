import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Literal, NamedTuple, Optional

from eth_utils import to_checksum_address
from gevent.lock import Semaphore

from rotkehlchen.accounting.structures.balance import AssetBalance, Balance
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.chain.ethereum.defi.defisaver_proxy import HasDSProxy
from rotkehlchen.chain.ethereum.graph import (
    SUBGRAPH_REMOTE_ERROR_MSG,
    Graph,
    format_query_indentation,
)
from rotkehlchen.chain.ethereum.utils import multicall_2, token_normalized_value_decimals
from rotkehlchen.constants.assets import A_ETH, A_LQTY, A_LUSD, A_USD
from rotkehlchen.constants.ethereum import LIQUITY_TROVE_MANAGER
from rotkehlchen.errors.misc import ModuleInitializationFailure, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_optional_to_fval,
)
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.mixins.serializableenum import SerializableEnumMixin

from .graph import QUERY_STAKE, QUERY_TROVE

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

MIN_COLL_RATE = '1.1'

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class TroveOperation(SerializableEnumMixin):
    OPENTROVE = 1
    CLOSETROVE = 2
    ADJUSTTROVE = 3
    ACCRUEREWARDS = 4
    LIQUIDATEINNORMALMODE = 5
    LIQUIDATEINRECOVERYMODE = 6
    REDEEMCOLLATERAL = 7

    def __str__(self) -> str:
        if self == TroveOperation.OPENTROVE:
            return 'Open Trove'
        if self == TroveOperation.CLOSETROVE:
            return 'Close Trove'
        if self == TroveOperation.ADJUSTTROVE:
            return 'Adjust Trove'
        if self == TroveOperation.ACCRUEREWARDS:
            return 'Accrue Rewards'
        if self == TroveOperation.LIQUIDATEINNORMALMODE:
            return 'Liquidation In Normal Mode'
        if self == TroveOperation.LIQUIDATEINRECOVERYMODE:
            return 'Liquidation In Recovery Mode'
        if self == TroveOperation.REDEEMCOLLATERAL:
            return 'Redeem Collateral'
        # else
        raise AssertionError(f'Invalid value {self} for TroveOperation')


class LiquityStakeEventType(SerializableEnumMixin):
    STAKE_CREATED = 1
    STAKE_INCREASED = 2
    STAKE_DECREASED = 3
    STAKE_REMOVED = 4
    STAKE_WITHDRAWN = 5

    @staticmethod
    def deserialize(value: str) -> 'LiquityStakeEventType':
        if value == 'stakeCreated':
            return LiquityStakeEventType.STAKE_CREATED
        if value == 'stakeIncreased':
            return LiquityStakeEventType.STAKE_INCREASED
        if value == 'stakeDecreased':
            return LiquityStakeEventType.STAKE_DECREASED
        if value == 'stakeRemoved':
            return LiquityStakeEventType.STAKE_REMOVED
        if value == 'gainsWithdrawn':
            return LiquityStakeEventType.STAKE_WITHDRAWN
        # else
        raise DeserializationError(f'Encountered unknown LiquityStakeEventType value {value}')


@dataclass(frozen=True)
class LiquityEvent:
    kind: Literal['stake', 'trove']
    tx: str
    address: str
    timestamp: Timestamp
    sequence_number: str

    def serialize(self) -> Dict[str, Any]:
        return {
            'kind': self.kind,
            'tx': self.tx,
            'sequence_number': self.sequence_number,
            'address': self.address,
            'timestamp': self.timestamp,
        }


@dataclass(frozen=True)
class LiquityTroveEvent(LiquityEvent):
    debt_after: AssetBalance
    collateral_after: AssetBalance
    debt_delta: AssetBalance
    collateral_delta: AssetBalance
    trove_operation: TroveOperation

    def serialize(self) -> Dict[str, Any]:
        result = super().serialize()
        result['debt_after'] = self.debt_after.serialize()
        result['debt_delta'] = self.debt_delta.serialize()
        result['collateral_after'] = self.collateral_after.serialize()
        result['collateral_delta'] = self.collateral_delta.serialize()
        result['trove_operation'] = str(self.trove_operation)
        return result


@dataclass(frozen=True)
class LiquityStakeEvent(LiquityEvent):
    stake_after: AssetBalance
    stake_change: AssetBalance
    issuance_gain: AssetBalance
    redemption_gain: AssetBalance
    stake_operation: LiquityStakeEventType

    def serialize(self) -> Dict[str, Any]:
        result = super().serialize()
        result['stake_after'] = self.stake_after.serialize()
        result['stake_change'] = self.stake_change.serialize()
        result['issuance_gain'] = self.issuance_gain.serialize()
        result['redemption_gain'] = self.redemption_gain.serialize()
        result['stake_operation'] = str(self.stake_operation)
        return result


class Trove(NamedTuple):
    collateral: AssetBalance
    debt: AssetBalance
    collateralization_ratio: Optional[FVal]
    liquidation_price: Optional[FVal]
    active: bool
    trove_id: int

    def serialize(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        result['collateral'] = self.collateral.serialize()
        result['debt'] = self.debt.serialize()
        result['collateralization_ratio'] = self.collateralization_ratio
        result['liquidation_price'] = self.liquidation_price
        result['active'] = self.active
        result['trove_id'] = self.trove_id
        return result


class StakePosition(NamedTuple):
    staked: AssetBalance

    def serialize(self) -> Dict[str, Any]:
        return self.staked.serialize()


class Liquity(HasDSProxy):

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            ethereum_manager=ethereum_manager,
            database=database,
            premium=premium,
            msg_aggregator=msg_aggregator,
        )
        self.history_lock = Semaphore()
        try:
            self.graph = Graph(
                'https://api.thegraph.com/subgraphs/name/liquity/liquity',
            )
        except RemoteError as e:
            self.msg_aggregator.add_error(
                SUBGRAPH_REMOTE_ERROR_MSG.format(protocol='Liquity', error_msg=str(e)),
            )
            raise ModuleInitializationFailure('Liquity Subgraph remote error') from e

    def get_positions(
        self,
        addresses_list: List[ChecksumEvmAddress],
    ) -> Dict[ChecksumEvmAddress, Trove]:
        contract = EthereumContract(
            address=LIQUITY_TROVE_MANAGER.address,
            abi=LIQUITY_TROVE_MANAGER.abi,
            deployed_block=LIQUITY_TROVE_MANAGER.deployed_block,
        )
        # make a copy of the list to avoid modifications in the list that is passed as argument
        addresses = list(addresses_list)
        proxied_addresses = self._get_accounts_having_proxy()
        proxies_to_address = {v: k for k, v in proxied_addresses.items()}
        addresses += proxied_addresses.values()

        calls = [
            (LIQUITY_TROVE_MANAGER.address, contract.encode(method_name='Troves', arguments=[x]))
            for x in addresses
        ]
        outputs = multicall_2(
            ethereum=self.ethereum,
            require_success=False,
            calls=calls,
        )

        data: Dict[ChecksumEvmAddress, Trove] = {}
        eth_price = Inquirer().find_usd_price(A_ETH)
        lusd_price = Inquirer().find_usd_price(A_LUSD)
        for idx, output in enumerate(outputs):
            status, result = output
            if status is True:
                try:
                    trove_info = contract.decode(result, 'Troves', arguments=[addresses[idx]])
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

    def liquity_staking_balances(
        self,
        addresses: List[ChecksumEvmAddress],
    ) -> Dict[ChecksumEvmAddress, StakePosition]:
        staked = self._get_raw_history(addresses, 'stake')
        lqty_price = Inquirer().find_usd_price(A_LQTY)
        data = {}
        for stake in staked['lqtyStakes']:
            try:
                owner = to_checksum_address(stake['id'])
                amount = deserialize_optional_to_fval(
                    value=stake['amount'],
                    name='amount',
                    location='liquity',
                )
                position = AssetBalance(
                    asset=A_LQTY,
                    balance=Balance(
                        amount=amount,
                        usd_value=lqty_price * amount,
                    ),
                )
                data[owner] = StakePosition(position)
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_warning(
                    f'Ignoring Liquity staking information. '
                    f'Failed to decode remote response. {msg}.',
                )
                continue
        return data

    def _get_raw_history(
        self,
        addresses: List[ChecksumEvmAddress],
        query_for: Literal['stake', 'trove'],
    ) -> Dict[str, Any]:
        param_types = {
            '$addresses': '[Bytes!]',
        }
        param_values = {
            'addresses': [addr.lower() for addr in addresses],
        }
        if query_for == 'trove':
            querystr = format_query_indentation(QUERY_TROVE)
        else:
            querystr = format_query_indentation(QUERY_STAKE)
        return self.graph.query(
            querystr=querystr,
            param_types=param_types,
            param_values=param_values,
        )

    def get_trove_history(
        self,
        addresses: List[ChecksumEvmAddress],
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> Dict[ChecksumEvmAddress, List[LiquityEvent]]:
        addresses_to_query = list(addresses)
        proxied_addresses = self._get_accounts_having_proxy()
        proxies_to_address = {v: k for k, v in proxied_addresses.items()}
        addresses_to_query += proxied_addresses.values()

        try:
            query = self._get_raw_history(addresses_to_query, 'trove')
        except RemoteError as e:
            log.error(f'Failed to query trove graph events for liquity. {str(e)}')
            query = {}

        result: Dict[ChecksumEvmAddress, List[LiquityEvent]] = defaultdict(list)
        for trove in query.get('troves', []):
            owner = to_checksum_address(trove['owner']['id'])
            if owner in proxies_to_address:
                owner = proxies_to_address[owner]
            for change in trove['changes']:
                try:
                    timestamp = change['transaction']['timestamp']
                    if timestamp < from_timestamp:
                        continue
                    if timestamp > to_timestamp:
                        break
                    operation = TroveOperation.deserialize(change['troveOperation'])
                    collateral_change = deserialize_optional_to_fval(
                        value=change['collateralChange'],
                        name='collateralChange',
                        location='liquity',
                    )
                    debt_change = deserialize_optional_to_fval(
                        value=change['debtChange'],
                        name='debtChange',
                        location='liquity',
                    )
                    lusd_price = PriceHistorian().query_historical_price(
                        from_asset=A_LUSD,
                        to_asset=A_USD,
                        timestamp=timestamp,
                    )
                    eth_price = PriceHistorian().query_historical_price(
                        from_asset=A_ETH,
                        to_asset=A_USD,
                        timestamp=timestamp,
                    )
                    debt_after_amount = deserialize_optional_to_fval(
                        value=change['debtAfter'],
                        name='debtAfter',
                        location='liquity',
                    )
                    collateral_after_amount = deserialize_optional_to_fval(
                        value=change['collateralAfter'],
                        name='collateralAfter',
                        location='liquity',
                    )
                    event = LiquityTroveEvent(
                        kind='trove',
                        tx=change['transaction']['id'],
                        address=owner,
                        timestamp=timestamp,
                        debt_after=AssetBalance(
                            asset=A_LUSD,
                            balance=Balance(
                                amount=debt_after_amount,
                                usd_value=lusd_price * debt_after_amount,
                            ),
                        ),
                        collateral_after=AssetBalance(
                            asset=A_ETH,
                            balance=Balance(
                                amount=collateral_after_amount,
                                usd_value=eth_price * collateral_after_amount,
                            ),
                        ),
                        debt_delta=AssetBalance(
                            asset=A_LUSD,
                            balance=Balance(
                                amount=debt_change,
                                usd_value=lusd_price * debt_change,
                            ),
                        ),
                        collateral_delta=AssetBalance(
                            asset=A_ETH,
                            balance=Balance(
                                amount=collateral_change,
                                usd_value=eth_price * collateral_change,
                            ),
                        ),
                        trove_operation=operation,
                        sequence_number=str(change['sequenceNumber']),
                    )
                    result[owner].append(event)
                except (DeserializationError, KeyError) as e:
                    log.debug(f'Failed to deserialize Liquity trove event: {change}')
                    msg = str(e)
                    if isinstance(e, KeyError):
                        msg = f'Missing key entry for {msg}.'
                    self.msg_aggregator.add_warning(
                        f'Ignoring Liquity Trove event in Liquity. '
                        f'Failed to decode remote information. {msg}.',
                    )
                    continue

        return result

    def get_staking_history(
        self,
        addresses: List[ChecksumEvmAddress],
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> Dict[ChecksumEvmAddress, List[LiquityEvent]]:
        try:
            staked = self._get_raw_history(addresses, 'stake')
        except RemoteError as e:
            log.error(f'Failed to query stake graph events for liquity. {str(e)}')
            staked = {}

        result: Dict[ChecksumEvmAddress, List[LiquityEvent]] = defaultdict(list)
        for stake in staked.get('lqtyStakes', []):
            owner = to_checksum_address(stake['id'])
            for change in stake['changes']:
                try:
                    timestamp = change['transaction']['timestamp']
                    if timestamp < from_timestamp:
                        continue
                    if timestamp > to_timestamp:
                        break
                    operation_stake = LiquityStakeEventType.deserialize(change['stakeOperation'])
                    lqty_price = PriceHistorian().query_historical_price(
                        from_asset=A_LQTY,
                        to_asset=A_USD,
                        timestamp=timestamp,
                    )
                    lusd_price = PriceHistorian().query_historical_price(
                        from_asset=A_LUSD,
                        to_asset=A_USD,
                        timestamp=timestamp,
                    )
                    stake_after = deserialize_optional_to_fval(
                        value=change['stakedAmountAfter'],
                        name='stakedAmountAfter',
                        location='liquity',
                    )
                    stake_change = deserialize_optional_to_fval(
                        value=change['stakedAmountChange'],
                        name='stakedAmountChange',
                        location='liquity',
                    )
                    issuance_gain = deserialize_optional_to_fval(
                        value=change['issuanceGain'],
                        name='issuanceGain',
                        location='liquity',
                    )
                    redemption_gain = deserialize_optional_to_fval(
                        value=change['redemptionGain'],
                        name='redemptionGain',
                        location='liquity',
                    )
                    stake_event = LiquityStakeEvent(
                        kind='stake',
                        tx=change['transaction']['id'],
                        address=owner,
                        timestamp=timestamp,
                        stake_after=AssetBalance(
                            asset=A_LQTY,
                            balance=Balance(
                                amount=stake_after,
                                usd_value=lqty_price * stake_after,
                            ),
                        ),
                        stake_change=AssetBalance(
                            asset=A_LQTY,
                            balance=Balance(
                                amount=stake_change,
                                usd_value=lqty_price * stake_change,
                            ),
                        ),
                        issuance_gain=AssetBalance(
                            asset=A_LUSD,
                            balance=Balance(
                                amount=issuance_gain,
                                usd_value=lusd_price * issuance_gain,
                            ),
                        ),
                        redemption_gain=AssetBalance(
                            asset=A_LUSD,
                            balance=Balance(
                                amount=redemption_gain,
                                usd_value=lusd_price * redemption_gain,
                            ),
                        ),
                        stake_operation=operation_stake,
                        sequence_number=str(change['transaction']['sequenceNumber']),
                    )
                    result[owner].append(stake_event)
                except (DeserializationError, KeyError) as e:
                    msg = str(e)
                    log.debug(f'Failed to deserialize Liquity entry: {change}')
                    if isinstance(e, KeyError):
                        msg = f'Missing key entry for {msg}.'
                    self.msg_aggregator.add_warning(
                        f'Ignoring Liquity Stake event in Liquity. '
                        f'Failed to decode remote information. {msg}.',
                    )
                    continue
        return result

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> Optional[List['AssetBalance']]:
        super().on_account_addition(address)
        trove_info = self.get_positions([address])
        result = []
        if address in trove_info:
            result.append(trove_info[address].collateral)
        stake_info = self.liquity_staking_balances([address])
        if address in stake_info:
            result.append(stake_info[address].staked)
        return result
