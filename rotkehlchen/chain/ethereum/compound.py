import logging
from typing import TYPE_CHECKING, Callable, Dict, List, NamedTuple, Optional, Union

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.zerion import DefiProtocolBalances
from rotkehlchen.constants.ethereum import CTOKEN_ABI
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import BlockchainQueryError, RemoteError, UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import BalanceType, ChecksumEthAddress
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager

BLOCKS_PER_DAY = 4 * 60 * 24
DAYS_PER_YEAR = 365
ETH_MANTISSA = 10**18
A_COMP = EthereumToken('COMP')
log = logging.getLogger(__name__)


class CompoundBalance(NamedTuple):
    balance_type: BalanceType
    balance: Balance
    apy: Optional[FVal]

    def serialize(self) -> Dict[str, Union[Optional[str], Dict[str, str]]]:
        return {
            'balance': self.balance.serialize(),
            'apy': self.apy.to_percentage(precision=2) if self.apy else None,
        }


class Compound(EthereumModule):
    """Compound integration module

    https://compound.finance/docs#guides
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

    def _get_apy(self, address: ChecksumEthAddress, supply: bool) -> Optional[FVal]:
        method_name = 'supplyRatePerBlock' if supply else 'borrowRatePerBlock'

        try:
            rate = self.ethereum.call_contract(
                contract_address=address,
                abi=CTOKEN_ABI,
                method_name=method_name,
            )
        except (RemoteError, BlockchainQueryError) as e:
            log.error(f'Could not query cToken {address} for supply/borrow rate: {str(e)}')
            return None

        apy = ((FVal(rate) / ETH_MANTISSA * BLOCKS_PER_DAY) + 1) ** (DAYS_PER_YEAR - 1) - 1  # noqa: E501
        return apy

    def get_balances(
            self,
            given_defi_balances: Union[
                Dict[ChecksumEthAddress, List[DefiProtocolBalances]],
                Callable[[], Dict[ChecksumEthAddress, List[DefiProtocolBalances]]],
            ],
    ) -> Dict[ChecksumEthAddress, Dict]:
        compound_balances = {}
        if isinstance(given_defi_balances, dict):
            defi_balances = given_defi_balances
        else:
            defi_balances = given_defi_balances()

        for account, balance_entries in defi_balances.items():
            lending_map = {}
            borrowing_map = {}
            rewards_map = {}
            for balance_entry in balance_entries:
                if balance_entry.protocol.name != 'Compound':
                    continue

                entry = balance_entry.base_balance
                try:
                    asset = Asset(entry.token_symbol)
                except UnknownAsset:
                    log.error(
                        f'Encountered unknown asset {entry.token_symbol} in compound. Skipping',
                    )
                    continue

                if entry.token_address == A_COMP.ethereum_address:
                    rewards_map[A_COMP] = CompoundBalance(
                        balance_type=BalanceType.ASSET,
                        balance=entry.balance,
                        apy=None,
                    )
                    continue

                if balance_entry.balance_type == 'Asset':
                    lending_map[asset.identifier] = CompoundBalance(
                        balance_type=BalanceType.ASSET,
                        balance=entry.balance,
                        apy=self._get_apy(entry.token_address, supply=True),
                    )
                else:  # 'Debt'
                    try:
                        ctoken = EthereumToken('c' + entry.token_symbol)
                    except UnknownAsset:
                        log.error(
                            f'Encountered unknown asset {entry.token_symbol} in '
                            f'compound while figuring out cToken. Skipping',
                        )
                        continue

                    borrowing_map[asset.identifier] = CompoundBalance(
                        balance_type=BalanceType.DEBT,
                        balance=entry.balance,
                        apy=self._get_apy(ctoken.ethereum_address, supply=False),
                    )

            if lending_map == {} and borrowing_map == {} and rewards_map == {}:
                # no balances for the account
                continue
            compound_balances[account] = {
                'rewards': rewards_map,
                'lending': lending_map,
                'borrowing': borrowing_map,
            }

        return compound_balances

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass
