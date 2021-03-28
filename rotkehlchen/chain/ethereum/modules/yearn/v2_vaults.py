from collections import defaultdict
import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.yearn.vaults import YearnVaultHistory, YearnVaultBalance
from rotkehlchen.chain.ethereum.modules.yearn.graph import YearnV2Inquirer
from rotkehlchen.chain.ethereum.structures import YearnVault, YearnVaultEvent
from rotkehlchen.constants.ethereum import (
    MAX_BLOCKTIME_CACHE,
    YEARN_DAI_VAULT,
    YEARN_V2_VAULTS_PREFIX,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import RemoteError, UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.chain.ethereum.modules.yearn.vaults import get_usd_price_zero_if_error
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, EthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.defi.structures import (
        GIVEN_DEFI_BALANCES,
        DefiProtocolBalances,
    )
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

BLOCKS_PER_YEAR = 2425846

log = logging.getLogger(__name__)


class YearnV2Vaults(EthereumModule):

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
            self.graph_inquirer: Optional[YearnV2Inquirer] = YearnV2Inquirer(
                ethereum_manager=ethereum_manager,
                database=database,
                premium=premium,
                msg_aggregator=msg_aggregator,
            )
        except RemoteError as e:
            self.graph_inquirer = None
            self.msg_aggregator.add_error(
                f'Could not initialize the Yearn V2 subgraph due to {str(e)}.',
            )

    def _calculate_vault_roi(self, vault: YearnVault) -> FVal:
        """
        getPricePerFullShare A @ block X
        getPricePerFullShare B @ block Y

        (A-B / X-Y) * blocksPerYear (2425846)

        So the numbers you see displayed on http://yearn.finance/vaults
        are ROI since launch of contract. All vaults start with pricePerFullShare = 1e18
        """
        now_block_number = self.ethereum.get_latest_block_number()
        price_per_full_share = self.ethereum.call_contract(
            contract_address=vault[0],
            abi=YEARN_DAI_VAULT.abi,  # Any vault ABI will do
            method_name='getPricePerFullShare',
        )
        nominator = price_per_full_share - (10**18)
        denonimator = now_block_number - vault.contract.deployed_block
        return FVal(nominator) / FVal(denonimator) * BLOCKS_PER_YEAR / 10**18

    def _get_single_addr_balance(
            self,
            defi_balances: List['DefiProtocolBalances'],
            roi_cache: Dict[str, FVal],
    ) -> Dict[str, YearnVaultBalance]:
        result = {}
        for balance in defi_balances:
            if balance.protocol.name == 'yearn.finance • Vaults':
                underlying_symbol = balance.underlying_balances[0].token_symbol
                vault_symbol = balance.base_balance.token_symbol
                vault_address = balance.base_balance.token_address
                vault = self.database.get_yearn_v2_basic_info(vault_address)
                if vault is None:
                    self.msg_aggregator.add_warning(
                        f'Found balance for unsupported yearn vault {vault_symbol}',
                    )
                    continue

                try:
                    underlying_asset = Asset(underlying_symbol)
                    vault_asset = Asset(vault_symbol)
                except UnknownAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Found unknown asset {e.asset_name} for yearn vault entry',
                    )
                    continue

                roi = roi_cache.get(vault_address, None)
                if roi is None:
                    roi = self._calculate_vault_roi(vault)
                    roi_cache[vault_address] = roi

                result[vault.name] = YearnVaultBalance(
                    underlying_token=underlying_asset,
                    vault_token=vault_asset,
                    underlying_value=balance.underlying_balances[0].balance,
                    vault_value=balance.base_balance.balance,
                    roi=roi,
                )

        return result

    def get_balances(
        self,
        given_defi_balances: 'GIVEN_DEFI_BALANCES',
    ) -> Dict[ChecksumEthAddress, Dict[str, YearnVaultBalance]]:
        if isinstance(given_defi_balances, dict):
            defi_balances = given_defi_balances
        else:
            defi_balances = given_defi_balances()

        roi_cache: Dict[str, FVal] = {}
        result = {}
        for address, balances in defi_balances.items():
            vault_balances = self._get_single_addr_balance(balances, roi_cache)
            if len(vault_balances) != 0:
                result[address] = vault_balances

        return result

    def _process_vault_events(self, events: List[YearnVaultEvent]) -> Balance:
        """Process the events for a single vault and returns total profit/loss after all events"""
        total = Balance()
        profit_so_far = Balance()
        for event in events:
            if event.event_type == 'deposit':
                total -= event.from_value
            else:  # withdraws
                profit_amount = total.amount + event.to_value.amount - profit_so_far.amount
                profit: Optional[Balance]
                if profit_amount >= 0:
                    usd_price = get_usd_price_zero_if_error(
                        asset=event.to_asset,
                        time=event.timestamp,
                        location='yearn vault event processing',
                        msg_aggregator=self.msg_aggregator,
                    )
                    profit = Balance(profit_amount, profit_amount * usd_price)
                    profit_so_far += profit
                else:
                    profit = None

                event.realized_pnl = profit
                total += event.to_value

        return total

    def _get_vault_deposit_events(
            self,
            vault: YearnVault,
            address: ChecksumEthAddress,
            from_block: int,
            to_block: int,
    ) -> List[YearnVaultEvent]:
        pass

    def _get_vault_withdraw_events(
            self,
            vault: YearnVault,
            address: ChecksumEthAddress,
            from_block: int,
            to_block: int,
    ) -> List[YearnVaultEvent]:
        pass

    def get_vaults_history(
            self,
            defi_balances: List['DefiProtocolBalances'],
            addresses: ChecksumEthAddress,
            from_block: int,
            to_block: int,
    ) -> Optional[Dict[str, YearnVaultHistory]]:

        if self.graph_inquirer is None:
            return None

        # Addresses that we will query
        query_addresses: List[EthAddress] = []

        # Skip addresses recently fetched
        for address in addresses:
            lowered_addr = address.lower()
            last_query = self.database.get_used_query_range(
                name=f'{YEARN_V2_VAULTS_PREFIX}_{lowered_addr}',
            )
            skip_query = last_query and to_block - last_query[1] < MAX_BLOCKTIME_CACHE
            if not skip_query:
                query_addresses.append(EthAddress(lowered_addr))

        # if None of the addresses has yearn v2 positions this
        # will return a map of addresses to empty lists
        new_events_addresses = self.graph_inquirer.get_all_events(
            addresses=query_addresses,
            from_block=from_block,
            to_block=to_block,
        )

        vaults_histories_per_address: Dict[ChecksumEthAddress, Dict[str, YearnVaultHistory]] = {}

        for address, new_events in new_events_addresses.items():
            # Query events from db for address
            db_events = self.database.get_all_yearn_v2_vaults_events(address=address)

            # Flattern the data into an unique list
            events = list(new_events['deposits'])
            events.extend(new_events['withdrawals'])

            if len(db_events) == 0 and len(events) == 0:
                # After all events have been queried then also update the query range.
                # Even if no events are found for an address we need to remember the range
                self.database.update_used_block_query_range(
                    name=f'{YEARN_V2_VAULTS_PREFIX}_{address}',
                    from_block=from_block,
                    to_block=to_block,
                )
                continue

            # Vaults histories
            vaults_histories: Dict[str, YearnVaultHistory] = {}

            # Dict that stores vault token symbol and their events + total pnl
            vaults: Dict[str, Dict[str, List[YearnVaultEvent]]] = defaultdict(
                lambda: defaultdict(list),
            )

            self.database.add_yearn_v2_vaults_events(address, events)

            all_events = db_events + events

            for event in all_events:
                if event.event_type == 'deposit':
                    vault_token_symbol = event.to_asset.identifier
                    underlying_token = event.from_asset
                else:
                    vault_token_symbol = event.from_asset.identifier
                    underlying_token = event.to_asset

                vaults[vault_token_symbol]['events'].append(event)

            # Sort events in each vault
            for key in vaults.keys():
                vaults[key]['events'].sort(key=lambda x: x.timestamp)
                total_pnl = self._process_vault_events(vaults[key]['events'])

                current_balance = None
                for balance in defi_balances:
                    found_balance = (
                        balance.protocol.name == 'yearn.finance • Vaults' and
                        balance.base_balance.token_symbol == vault_token_symbol
                    )
                    if found_balance:
                        current_balance = balance.underlying_balances[0].balance
                        total_pnl += current_balance
                        break

                    # Due to the way we calculate usd prices for vaults we
                    # need to get the current usd price of the actual pnl
                    # amount at this point
                    if total_pnl.amount != ZERO:
                        usd_price = get_usd_price_zero_if_error(
                            asset=underlying_token,
                            time=ts_now(),
                            location='yearn vault history',
                            msg_aggregator=self.msg_aggregator,
                        )
                        total_pnl.usd_value = usd_price * total_pnl.amount

                vaults_histories[key] = YearnVaultHistory(
                    events=vaults[key]['events'],
                    profit_loss=total_pnl,
                )
            vaults_histories_per_address[address] = vaults_histories

            self.database.update_used_block_query_range(
                name=f'{YEARN_V2_VAULTS_PREFIX}_{address}',
                from_block=from_block,
                to_block=to_block,
            )

        for address in query_addresses: 
            if address in vaults_histories_per_address.keys():
                has_no_len = len(vaults_histories_per_address[address]) == 0
                if key_in and has_no_len:
                    del vaults_histories_per_address[address]

        return vaults_histories_per_address

    def get_history(
            self,
            given_defi_balances: 'GIVEN_DEFI_BALANCES',
            addresses: List[ChecksumEthAddress],
            reset_db_data: bool,
            from_timestamp: Timestamp,  # pylint: disable=unused-argument
            to_timestamp: Timestamp,  # pylint: disable=unused-argument
    ) -> Dict[ChecksumEthAddress, Dict[str, YearnVaultHistory]]:
        with self.history_lock:

            if reset_db_data is True:
                self.database.delete_yearn_vaults_data()
            if isinstance(given_defi_balances, dict):
                defi_balances = given_defi_balances
            else:
                defi_balances = given_defi_balances()

            from_block = self.ethereum.get_blocknumber_by_time(from_timestamp)
            to_block = self.ethereum.get_blocknumber_by_time(to_timestamp)

            return self.get_vaults_history(
                defi_balances=defi_balances,
                addresses=addresses,
                from_block=from_block,
                to_block=to_block,
            )

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass

    def deactivate(self) -> None:
        self.database.delete_yearn_vaults_data()
