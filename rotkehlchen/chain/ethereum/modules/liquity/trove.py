from enum import Enum
from typing import Any, DefaultDict, Dict, List, NamedTuple, Optional

from eth_utils import to_checksum_address
from gevent.lock import Semaphore

from rotkehlchen.accounting.structures import Balance, BalanceSheet, DefiEvent, DefiEventType
from rotkehlchen.chain.ethereum.utils import multicall_2
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_LUSD
from rotkehlchen.constants.ethereum import LIQUITY_TROVE_MANAGER
from rotkehlchen.chain.ethereum.graph import Graph, format_query_indentation
from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_or_use_default
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import deserialize_asset_amount
from rotkehlchen.typing import AssetAmount, ChecksumEthAddress, Timestamp
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.user_messages import MessagesAggregator

from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_optional,
    deserialize_timestamp,
)


from .graph import QUERY_TROVE

CONTRACT_ADDRESS = '0xA39739EF8b0231DbFA0DcdA07d7e29faAbCf4bb2'
MIN_COLL_RATE = '1.1'

class Trove(NamedTuple):
    collateral: Balance
    debt: Balance
    collateralization_ratio: Optional[str]
    liquidation_price: Optional[FVal]
    active: bool
    trove_id: int

    def get_balance(self) -> BalanceSheet:
        return BalanceSheet(
            assets=defaultdict(Balance, {A_ETH: self.collateral}),
            liabilities=defaultdict(Balance, {A_LUSD: self.debt}),
        )


class TroveOperation(Enum):
    OPENTROVE = 1
    CLOSETROVE = 2
    ADJUSTTROVE = 3
    ACCRUEREWARDS = 4
    LIQUIDATENORMALMODE = 5
    LIQUIDATERECOVERYMODE = 6
    REEDEM = 7

    @staticmethod
    def deserialize(value: str) -> 'TroveOperation':
        if value == 'openTrove':
            return TroveOperation.OPENTROVE
        if value == 'closeTrove':
            return TroveOperation.CLOSETROVE
        if value == 'adjustTrove':
            return TroveOperation.ADJUSTTROVE
        if value == 'accrueRewards':
            return TroveOperation.ACCRUEREWARDS
        if value == 'liquidateInNormalMode':
            return TroveOperation.LIQUIDATENORMALMODE
        if value == 'liquidateInRecoveryMode':
            return TroveOperation.LIQUIDATERECOVERYMODE
        if value == 'redeemCollateral':
            return TroveOperation.REEDEM
        # else
        raise DeserializationError(f'Encountered unknown TroveOperation value {value}')

    def serialize(self) -> str:
        if self == TroveOperation.OPENTROVE:
            return 'openTrove'
        if self == TroveOperation.CLOSETROVE:
            return 'closeTrove'
        if self == TroveOperation.ADJUSTTROVE:
            return 'adjustTrove'
        if self == TroveOperation.ACCRUEREWARDS:
            return 'accrueRewards'
        if self == TroveOperation.LIQUIDATENORMALMODE:
            return 'liquidateInNormalMode'
        if self == TroveOperation.LIQUIDATERECOVERYMODE:
            return 'liquidateInRecoveryMode'
        if self == TroveOperation.REEDEM:
            return 'redeemCollateral'
        # else
        raise AssertionError(f'Invalid value {self} for TroveOperation')

SUBGRAPH_REMOTE_ERROR_MSG = (
    "Failed to request the Liquity subgraph due to {error_msg}. "
    "All the deposits and withdrawals history queries are not functioning until this is fixed. "  # noqa: E501
    "Probably will get fixed with time. If not report it to rotki's support channel"  # noqa: E501
)


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
            self.msg_aggregator.add_error(SUBGRAPH_REMOTE_ERROR_MSG.format(error_msg=str(e)))
            raise ModuleInitializationFailure('Liquity Subgraph remote error') from e

    def get_positions(
        self,
        #reset_db_data: bool,
        addresses: List[ChecksumEthAddress]
    ) -> Dict[ChecksumEthAddress, Trove]:
        decimals = 10**-18

        contract = EthereumContract(
            address=LIQUITY_TROVE_MANAGER.address,
            abi=LIQUITY_TROVE_MANAGER.abi,
            deployed_block=LIQUITY_TROVE_MANAGER.deployed_block,
        )
        calls = [
            (LIQUITY_TROVE_MANAGER.address, contract.encode(method_name='Troves', arguments=[i]))
            for i in addresses
        ]
        outputs = multicall_2(
            ethereum=self.ethereum,
            require_success=False,
            calls=calls,
        )

        troves = {}
        for i, output in enumerate(outputs):
            status, result = output
            if status is True:
                trove_info = contract.decode(result, 'Troves', arguments=[addresses[i]])
                collateral = deserialize_asset_amount(trove_info[1]*decimals)
                debt = deserialize_asset_amount(trove_info[0]*decimals)
                eth_price = Inquirer().find_usd_price(A_ETH)
                lusd_price = Inquirer().find_usd_price(A_LUSD)
                collateral_balance = Balance(
                    amount=collateral,
                    usd_value=eth_price,
                )
                debt_balance = Balance(
                    amount=debt,
                    usd_value=lusd_price,
                )
                troves[addresses[i]] = Trove(
                    collateral=collateral_balance,
                    debt=debt_balance,
                    collateralization_ratio=eth_price*collateral/debt*100,
                    liquidation_price=debt*lusd_price*FVal(MIN_COLL_RATE)/collateral,
                    active=bool(trove_info[3]),
                    trove_id=trove_info[4],
                )
        return troves

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
                # In one transaction is possible to generate debt and change the colateral
                if debt_change != AssetAmount(ZERO):
                    if debt_change > ZERO:
                        # Generate debt
                        count_spent_got_cost_basis = True
                        got_asset = A_LUSD
                        got_balance = Balance(
                            amount=debt_change,
                            usd_value=query_usd_price_or_use_default(
                                A_LUSD,
                                timestamp,
                                ZERO,
                                'Liquity'
                            ),
                        )
                        total_lusd_trove_balance += got_balance
                    else:
                        # payback debt
                        count_spent_got_cost_basis = True
                        spent_asset = A_LUSD
                        spent_balance = Balance(
                            amount=abs(debt_change),
                            usd_value=query_usd_price_or_use_default(
                                A_LUSD,
                                timestamp,
                                ZERO,
                                'Liquity'
                            ),
                        )
                        total_lusd_trove_balance -= spent_balance
                        if total_lusd_trove_balance.amount + realized_trove_lusd_loss.amount < ZERO:
                            pnl_balance = total_lusd_trove_balance + realized_trove_lusd_loss
                            realized_trove_lusd_loss += -pnl_amount
                            pnl = [AssetBalance(asset=A_LUSD, balance=pnl_balance)]
                if collateral_change != AssetAmount(ZERO):
                    if collateral_change < ZERO:
                        # Withdraw collateral
                        got_asset = A_ETH
                        got_balance = Balance(
                            amount=abs(collateral_change),
                            usd_value=query_usd_price_or_use_default(
                                A_ETH,
                                timestamp,
                                ZERO,
                                'Liquity'
                            ),
                        )
                    else:
                        # Deposit collateral
                        spent_asset = A_ETH
                        spent_balance = Balance(
                            amount=collateral_change,
                            usd_value=query_usd_price_or_use_default(
                                A_ETH,
                                timestamp,
                                ZERO,
                                'Liquity'
                            ),
                        )
                if operation in (
                    TroveOperation.LIQUIDATENORMALMODE,
                    TroveOperation.LIQUIDATERECOVERYMODE,
                ):
                    count_spent_got_cost_basis = True
                    spent_asset = A_ETH
                    spent_balance = Balance(
                        amount=abs(caollateral_change),
                        usd_value=query_usd_price_or_use_default(
                            A_ETH,
                            timestamp,
                            ZERO,
                            'Liquity'
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
            except KeyError as e:
                self.msg_aggregator.add_warning(
                    f'Ignoring Liquity Trove event in {2+2}. '
                    f'Failed to decode remote information. {str(e)}.',
                )
                continue
        return events

    def get_events(
        self,
        addresses: List[ChecksumEthAddress],
        reset_db_data: bool,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> List[DefiEvent]:
        param_types = {
            '$addresses': '[Bytes!]',
        }
        param_values = {
            'addresses': [addr.lower() for addr in addresses],
        }
        querystr = format_query_indentation(QUERY_TROVE.format())
        query = self.graph.query(
            querystr=querystr,
            param_types=param_types,
            param_values=param_values,
        )
        result: Dict[ChecksumEthAddress, List[DefiEvent]] = {}
        for trove in query['troves']:
            account_id = to_checksum_address(trove['owner']['id'])
            result[account_id] = []
            changes = self._process_trove_events(trove['changes'], from_timestamp, to_timestamp)
            result[account_id] = changes
        print(result)
        return result


    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass

    def deactivate(self) -> None:
        self.database.delete_yearn_vaults_data(version=2)
