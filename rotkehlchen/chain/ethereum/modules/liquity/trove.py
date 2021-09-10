from collections import defaultdict
from dataclasses import dataclass
from functools import reduce
import logging
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional, Union
from operator import add

from eth_utils import to_checksum_address
from gevent.lock import Semaphore
from typing_extensions import Literal

from rotkehlchen.assets.asset import Asset
from rotkehlchen.accounting.structures import (
    AssetBalance,
    Balance,
    DefiEvent,
    DefiEventType,
)
from rotkehlchen.chain.ethereum.utils import multicall_2
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_LUSD, A_LQTY, A_USD
from rotkehlchen.constants.ethereum import LIQUITY_TROVE_MANAGER
from rotkehlchen.chain.ethereum.graph import (
    SUBGRAPH_REMOTE_ERROR_MSG,
    Graph,
    format_query_indentation,
)
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.errors import DeserializationError, ModuleInitializationFailure, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_or_use_default, PriceHistorian
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import AssetAmount, ChecksumEthAddress, Timestamp
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.mixins.serializableenum import SerializableEnumMixin
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_optional_fval,
)

from .graph import QUERY_TROVE, QUERY_STAKE

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

CONTRACT_ADDRESS = '0xA39739EF8b0231DbFA0DcdA07d7e29faAbCf4bb2'
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
    REEDEM = 7

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
        if self == TroveOperation.REEDEM:
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

    def serialize(self) -> Dict[str, Any]:
        return {
            'kind': self.kind,
            'tx': self.tx,
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


class Liquity(EthereumModule):

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
        addresses: List[ChecksumEthAddress],
    ) -> Dict[ChecksumEthAddress, Dict[str, Union[Trove, StakePosition]]]:
        contract = EthereumContract(
            address=LIQUITY_TROVE_MANAGER.address,
            abi=LIQUITY_TROVE_MANAGER.abi,
            deployed_block=LIQUITY_TROVE_MANAGER.deployed_block,
        )
        calls = [
            (LIQUITY_TROVE_MANAGER.address, contract.encode(method_name='Troves', arguments=[x]))
            for x in addresses
        ]
        outputs = multicall_2(
            ethereum=self.ethereum,
            require_success=False,
            calls=calls,
        )

        data: Dict[ChecksumEthAddress, Dict[str, Union[Trove, StakePosition]]] = {}
        eth_price = Inquirer().find_usd_price(A_ETH)
        lusd_price = Inquirer().find_usd_price(A_LUSD)
        lqty_price = Inquirer().find_usd_price(A_LQTY)
        for idx, output in enumerate(outputs):
            status, result = output
            if status is True:
                try:
                    trove_info = contract.decode(result, 'Troves', arguments=[addresses[idx]])
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

                    data[addresses[idx]] = {}
                    data[addresses[idx]]['trove'] = Trove(
                        collateral=collateral_balance,
                        debt=debt_balance,
                        collateralization_ratio=collateralization_ratio,
                        liquidation_price=liquidation_price,
                        active=bool(trove_info[3]),  # pylint: disable=unsubscriptable-object
                        trove_id=trove_info[4],  # pylint: disable=unsubscriptable-object
                    )
                except DeserializationError as e:
                    self.msg_aggregator.add_warning(
                        f'Ignoring Liquity trove information. '
                        f'Failed to decode contract information. {str(e)}.',
                    )

        if self.premium:
            staked = self._get_raw_history(addresses, 'stake')
            for stake in staked['lqtyStakes']:
                try:
                    owner = to_checksum_address(stake['id'])
                    amount = deserialize_optional_fval(stake['amount'], 'amount', 'liquity')
                    position = AssetBalance(
                        asset=A_LQTY,
                        balance=Balance(
                            amount=amount,
                            usd_value=lqty_price * amount,
                        ),
                    )
                    data[owner]['stake'] = StakePosition(position)
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

    def _process_trove_events(
        self,
        changes: List[Dict[str, Any]],
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> List[DefiEvent]:
        events = []
        total_lusd_trove_balance = Balance()
        realized_trove_lusd_loss = Balance()
        for change in changes:
            try:
                operation = TroveOperation.deserialize(change['troveOperation'])
                collateral_change = deserialize_asset_amount(change['collateralChange'])
                debt_change = deserialize_asset_amount(change['debtChange'])
                timestamp = change['transaction']['timestamp']
                if timestamp < from_timestamp:
                    continue
                if timestamp > to_timestamp:
                    break

                got_asset: Optional[Asset]
                spent_asset: Optional[Asset]
                pnl = got_asset = got_balance = spent_asset = spent_balance = None
                count_spent_got_cost_basis = False
                # In one transaction it is possible to generate debt and change the collateral
                if debt_change != AssetAmount(ZERO):
                    if debt_change > ZERO:
                        # Generate debt
                        count_spent_got_cost_basis = True
                        got_asset = A_LUSD
                        got_balance = Balance(
                            amount=debt_change,
                            usd_value=query_usd_price_or_use_default(
                                asset=A_LUSD,
                                time=timestamp,
                                default_value=ZERO,
                                location='Liquity',
                            ),
                        )
                        total_lusd_trove_balance += got_balance
                    else:  # payback debt
                        count_spent_got_cost_basis = True
                        spent_asset = A_LUSD
                        spent_balance = Balance(
                            amount=abs(debt_change),
                            usd_value=query_usd_price_or_use_default(
                                asset=A_LUSD,
                                time=timestamp,
                                default_value=ZERO,
                                location='Liquity',
                            ),
                        )
                        total_lusd_trove_balance -= spent_balance
                        balance = total_lusd_trove_balance.amount + realized_trove_lusd_loss.amount
                        if balance < ZERO:
                            pnl_balance = total_lusd_trove_balance + realized_trove_lusd_loss
                            realized_trove_lusd_loss += -pnl_balance
                            pnl = [AssetBalance(asset=A_LUSD, balance=pnl_balance)]

                if collateral_change != AssetAmount(ZERO):
                    if collateral_change < ZERO:
                        # Withdraw collateral
                        got_asset = A_ETH
                        got_balance = Balance(
                            amount=abs(collateral_change),
                            usd_value=query_usd_price_or_use_default(
                                asset=A_ETH,
                                time=timestamp,
                                default_value=ZERO,
                                location='Liquity',
                            ),
                        )
                    else:  # Deposit collateral
                        spent_asset = A_ETH
                        spent_balance = Balance(
                            amount=collateral_change,
                            usd_value=query_usd_price_or_use_default(
                                asset=A_ETH,
                                time=timestamp,
                                default_value=ZERO,
                                location='Liquity',
                            ),
                        )

                if operation in (
                    TroveOperation.LIQUIDATEINNORMALMODE,
                    TroveOperation.LIQUIDATEINRECOVERYMODE,
                ):
                    count_spent_got_cost_basis = True
                    spent_asset = A_ETH
                    spent_balance = Balance(
                        amount=abs(collateral_change),
                        usd_value=query_usd_price_or_use_default(
                            asset=A_ETH,
                            time=timestamp,
                            default_value=ZERO,
                            location='Liquity',
                        ),
                    )
                    pnl = [AssetBalance(asset=A_ETH, balance=-spent_balance)]
                event = DefiEvent(
                    timestamp=Timestamp(change['transaction']['timestamp']),
                    wrapped_event=change,
                    event_type=DefiEventType.LIQUITY,
                    got_asset=got_asset,
                    got_balance=got_balance,
                    spent_asset=spent_asset,
                    spent_balance=spent_balance,
                    pnl=pnl,
                    count_spent_got_cost_basis=count_spent_got_cost_basis,
                    tx_hash=change['transaction']['id'],
                )
                events.append(event)
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                log.debug(f'Failed to extract defievent in Liquity from {change}')
                self.msg_aggregator.add_warning(
                    f'Ignoring Liquity Trove event in Liquity. '
                    f'Failed to decode remote information. {msg}.',
                )
                continue
        return events

    def _get_raw_history(
        self,
        addresses: List[ChecksumEthAddress],
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

    def get_history(
        self,
        addresses: List[ChecksumEthAddress],
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> Dict[ChecksumEthAddress, Dict[str, List[LiquityEvent]]]:
        try:
            query = self._get_raw_history(addresses, 'trove')
        except RemoteError as e:
            log.error(f'Failed to query trove graph events for liquity. {str(e)}')
            query = {}
        try:
            staked = self._get_raw_history(addresses, 'stake')
        except RemoteError as e:
            log.error(f'Failed to query stake graph events for liquity. {str(e)}')
            staked = {}

        result: Dict[ChecksumEthAddress, Dict[str, List[LiquityEvent]]] = defaultdict(lambda: defaultdict(list))  # noqa: E501
        for trove in query.get('troves', []):
            owner = to_checksum_address(trove['owner']['id'])
            for change in trove['changes']:
                try:
                    timestamp = change['transaction']['timestamp']
                    if timestamp < from_timestamp:
                        continue
                    if timestamp > to_timestamp:
                        break
                    operation = TroveOperation.deserialize(change['troveOperation'])
                    collateral_change = deserialize_optional_fval(change['collateralChange'], 'collateralChange', 'liquity')  # noqa: E501
                    debt_change = deserialize_optional_fval(change['debtChange'], 'debtChange', 'liquity')  # noqa: E501
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
                    debt_after_amount = deserialize_optional_fval(change['debtAfter'], 'debtAfter', 'liquity')  # noqa: E501
                    collateral_after_amount = deserialize_optional_fval(change['collateralAfter'], 'collateralAfter', 'liquity')  # noqa: E501
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
                    )
                    result[owner]['trove'].append(event)
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
                    stake_after = deserialize_optional_fval(change['stakedAmountAfter'], 'stakedAmountAfter', 'liquity')  # noqa: E501
                    stake_change = deserialize_optional_fval(change['stakedAmountChange'], 'stakedAmountChange', 'liquity')  # noqa: E501
                    issuance_gain = deserialize_optional_fval(change['issuanceGain'], 'issuanceGain', 'liquity')  # noqa: E501
                    redemption_gain = deserialize_optional_fval(change['redemptionGain'], 'redemptionGain', 'liquity')  # noqa: E501
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
                    )
                    result[owner]['stake'].append(stake_event)
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

    def get_history_events(
        self,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
        addresses: List[ChecksumEthAddress],
    ) -> List[DefiEvent]:
        query = self._get_raw_history(addresses, 'trove')
        result = []
        for trove in query['troves']:
            changes = self._process_trove_events(trove['changes'], from_timestamp, to_timestamp)
            result.append(changes)
        # Flatten the result (list of lists to list)
        if result:
            return reduce(add, result)
        return []

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> Optional[List['AssetBalance']]:
        info = self.get_positions([address])
        result = []
        if address in info:
            if 'trove' in info[address]:
                result.append(info[address]['trove'].collateral)  # type: ignore
            if 'stake' in info[address]:
                result.append(info[address]['stake'].staked)  # type: ignore
        return result

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass

    def deactivate(self) -> None:
        pass
