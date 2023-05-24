import logging
from typing import TYPE_CHECKING, NamedTuple, Optional, Union

from rotkehlchen.accounting.structures.balance import Balance, BalanceType
from rotkehlchen.assets.asset import CryptoAsset, EvmToken
from rotkehlchen.assets.utils import symbol_to_evm_token
from rotkehlchen.chain.ethereum.constants import ETH_MANTISSA
from rotkehlchen.chain.ethereum.defi.structures import GIVEN_DEFI_BALANCES
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS
from rotkehlchen.constants.assets import A_COMP, A_ETH
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import ts_now


if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.premium.premium import Premium
    from rotkehlchen.user_messages import MessagesAggregator

ADDRESS_TO_ASSETS = dict[ChecksumEvmAddress, dict[CryptoAsset, Balance]]
BLOCKS_PER_DAY = 4 * 60 * 24
DAYS_PER_YEAR = 365


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CompoundBalance(NamedTuple):
    balance_type: BalanceType
    balance: Balance
    apy: Optional[FVal]

    def serialize(self) -> dict[str, Union[Optional[str], dict[str, str]]]:
        return {
            'balance': self.balance.serialize(),
            'apy': self.apy.to_percentage(precision=2) if self.apy else None,
        }


def _compound_symbol_to_token(symbol: str, timestamp: Timestamp) -> EvmToken:
    """
    Turns a compound symbol to an ethereum token.

    May raise UnknownAsset
    """
    if symbol == 'cWBTC':
        if timestamp >= Timestamp(1615751087):
            return EvmToken('eip155:1/erc20:0xccF4429DB6322D5C611ee964527D42E5d685DD6a')
        # else
        return EvmToken('eip155:1/erc20:0xC11b1268C1A384e55C48c2391d8d480264A3A7F4')
    # else
    return symbol_to_evm_token(symbol)


class Compound(EthereumModule):
    """Compound integration module

    https://compound.finance/docs#guides
    """

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',  # pylint: disable=unused-argument
            premium: Optional['Premium'],  # pylint: disable=unused-argument
            msg_aggregator: 'MessagesAggregator',  # pylint: disable=unused-argument
    ):
        self.ethereum = ethereum_inquirer
        self.comp = A_COMP.resolve_to_evm_token()

    def _get_apy(self, address: ChecksumEvmAddress, supply: bool) -> Optional[FVal]:
        method_name = 'supplyRatePerBlock' if supply else 'borrowRatePerBlock'

        try:
            rate = self.ethereum.call_contract(
                contract_address=address,
                abi=self.ethereum.contracts.abi('CTOKEN'),
                method_name=method_name,
            )
        except (RemoteError, BlockchainQueryError) as e:
            log.error(f'Could not query cToken {address} for supply/borrow rate: {e!s}')
            return None

        apy = ((FVal(rate) / ETH_MANTISSA * BLOCKS_PER_DAY) + 1) ** (DAYS_PER_YEAR - 1) - 1  # noqa: E501
        return apy

    def get_balances(
            self,
            given_defi_balances: GIVEN_DEFI_BALANCES,
    ) -> dict[ChecksumEvmAddress, dict[str, dict[CryptoAsset, CompoundBalance]]]:
        compound_balances = {}
        now = ts_now()
        if isinstance(given_defi_balances, dict):
            defi_balances = given_defi_balances
        else:
            defi_balances = given_defi_balances()

        for account, balance_entries in defi_balances.items():
            lending_map = {}
            borrowing_map = {}
            rewards_map = {}
            for balance_entry in balance_entries:
                if balance_entry.protocol.name not in ('Compound Governance', 'Compound'):
                    continue

                entry = balance_entry.base_balance
                if entry.token_address == ETH_SPECIAL_ADDRESS:
                    asset = A_ETH  # hacky way to specify ETH in compound
                else:
                    try:
                        asset = EvmToken(ethaddress_to_identifier(entry.token_address))
                    except UnknownAsset:
                        log.error(
                            f'Encountered unknown asset {entry.token_symbol} with address '
                            f'{entry.token_address} in compound. Skipping',
                        )
                        continue

                unclaimed_comp_rewards = (
                    entry.token_address == self.comp.evm_address and
                    balance_entry.protocol.name == 'Compound Governance'
                )
                if unclaimed_comp_rewards:
                    rewards_map[A_COMP] = CompoundBalance(
                        balance_type=BalanceType.ASSET,
                        balance=entry.balance,
                        apy=None,
                    )
                    continue

                if balance_entry.balance_type == 'Asset':
                    # Get the underlying balance
                    underlying_token_address = balance_entry.underlying_balances[0].token_address
                    try:
                        underlying_asset = EvmToken(ethaddress_to_identifier(underlying_token_address))  # noqa: E501
                    except UnknownAsset:
                        log.error(
                            f'Encountered unknown token with address '
                            f'{underlying_token_address} in compound. Skipping',
                        )
                        continue

                    lending_map[underlying_asset] = CompoundBalance(
                        balance_type=BalanceType.ASSET,
                        balance=balance_entry.underlying_balances[0].balance,
                        apy=self._get_apy(entry.token_address, supply=True),
                    )
                else:  # 'Debt'
                    try:
                        ctoken = _compound_symbol_to_token(
                            symbol='c' + entry.token_symbol,
                            timestamp=now,
                        )
                    except UnknownAsset:
                        log.error(
                            f'Encountered unknown asset {entry.token_symbol} in '
                            f'compound while figuring out cToken. Skipping',
                        )
                        continue

                    borrowing_map[asset] = CompoundBalance(
                        balance_type=BalanceType.LIABILITY,
                        balance=entry.balance,
                        apy=self._get_apy(ctoken.evm_address, supply=False),
                    )

            if lending_map == {} and borrowing_map == {} and rewards_map == {}:
                # no balances for the account
                continue

            compound_balances[account] = {
                'rewards': rewards_map,
                'lending': lending_map,
                'borrowing': borrowing_map,
            }

        return compound_balances  # type: ignore

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        pass

    def deactivate(self) -> None:
        pass
