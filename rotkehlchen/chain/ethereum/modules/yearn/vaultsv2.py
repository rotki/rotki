import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.graph import SUBGRAPH_REMOTE_ERROR_MSG
from rotkehlchen.constants.ethereum import (
    MAX_BLOCKTIME_CACHE,
    YEARN_VAULT_V2_ABI,
    YEARN_VAULTS_V2_PREFIX,
)
from rotkehlchen.constants.misc import EXP18, ZERO
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.misc import ModuleInitializationFailure, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import YEARN_VAULTS_V2_PROTOCOL, ChecksumEvmAddress, EvmAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import ts_now

from .db import add_yearn_vaults_events, get_yearn_vaults_v2_events
from .graph import YearnVaultsV2Graph
from .structures import YearnVaultEvent
from .vaults import YearnVaultBalance, YearnVaultHistory, get_usd_price_zero_if_error

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.defi.structures import GIVEN_ETH_BALANCES
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

BLOCKS_PER_YEAR = 2425846
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class YearnVaultsV2(EthereumModule):

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
            self.graph_inquirer: YearnVaultsV2Graph = YearnVaultsV2Graph(
                ethereum_manager=ethereum_manager,
                database=database,
                premium=premium,
                msg_aggregator=msg_aggregator,
            )
        except RemoteError as e:
            self.msg_aggregator.add_error(
                SUBGRAPH_REMOTE_ERROR_MSG.format(protocol="Yearn V2", error_msg=str(e)),
            )
            raise ModuleInitializationFailure('Yearn Vaults v2 Subgraph remote error') from e

    def _calculate_vault_roi(self, vault: EvmToken) -> Tuple[FVal, int]:
        """
        getPricePerFullShare A @ block X
        getPricePerFullShare B @ block Y

        (A-B / X-Y) * blocksPerYear (2425846)

        So the numbers you see displayed on http://yearn.finance/vaults
        are ROI since launch of contract. All vaults start with pricePerFullShare = 1e18

        A value of 0 for ROI is returned if the calculation couldn't be made
        """
        if vault.started is None:
            self.msg_aggregator.add_error(
                f'Failed to query ROI for vault {vault.evm_address}. Missing creation time.',
            )
            return ZERO, 0

        now_block_number = self.ethereum.get_latest_block_number()
        price_per_full_share = self.ethereum.call_contract(
            contract_address=vault.evm_address,
            abi=YEARN_VAULT_V2_ABI,  # Any vault ABI will do
            method_name='pricePerShare',
        )
        nominator = price_per_full_share - EXP18
        try:
            denonimator = now_block_number - self.ethereum.etherscan.get_blocknumber_by_time(vault.started)  # noqa: E501
        except RemoteError as e:
            self.msg_aggregator.add_error(
                f'Failed to query ROI for vault {vault.evm_address}. '
                f'Etherscan error {str(e)}.',
            )
            return ZERO, price_per_full_share
        return FVal(nominator) / FVal(denonimator) * BLOCKS_PER_YEAR / EXP18, price_per_full_share

    def _get_single_addr_balance(
            self,
            defi_balances: Dict[Asset, Balance],
            roi_cache: Dict[str, FVal],
            pps_cache: Dict[str, int],  # price per share
    ) -> Dict[ChecksumEvmAddress, YearnVaultBalance]:
        result = {}
        globaldb = GlobalDBHandler()
        with globaldb.conn.read_ctx() as cursor:
            for asset, balance in defi_balances.items():
                if asset.is_evm_token() is False:
                    continue
                asset = asset.resolve_to_evm_token()
                if asset.protocol == YEARN_VAULTS_V2_PROTOCOL:
                    underlying = globaldb.fetch_underlying_tokens(cursor, ethaddress_to_identifier(asset.evm_address))  # noqa: E501
                    if underlying is None:
                        log.error(f'Found yearn asset {asset} without underlying asset')
                        continue
                    underlying_token = EvmToken(ethaddress_to_identifier(underlying[0].address))
                    vault_address = asset.evm_address

                    roi = roi_cache.get(vault_address, None)
                    pps = pps_cache.get(vault_address, None)
                    if roi is None:
                        roi, pps = self._calculate_vault_roi(asset)
                        if roi == ZERO:
                            self.msg_aggregator.add_warning(
                                f'Ignoring vault {asset} because information failed to '
                                f'be correctly queried.',
                            )
                            continue
                        roi_cache[vault_address] = roi
                        pps_cache[vault_address] = pps

                    underlying_balance = Balance(
                        amount=balance.amount * FVal(pps * 10**-asset.decimals),
                        usd_value=balance.usd_value,
                    )
                    result[asset.evm_address] = YearnVaultBalance(
                        underlying_token=underlying_token,
                        vault_token=asset,
                        underlying_value=underlying_balance,
                        vault_value=balance,
                        roi=roi,
                    )

        return result

    def get_balances(
        self,
        given_eth_balances: 'GIVEN_ETH_BALANCES',
    ) -> Dict[ChecksumEvmAddress, Dict[ChecksumEvmAddress, YearnVaultBalance]]:

        if isinstance(given_eth_balances, dict):
            defi_balances = given_eth_balances
        else:
            defi_balances = given_eth_balances()

        roi_cache: Dict[str, FVal] = {}
        pps_cache: Dict[str, int] = {}  # price per share cache
        result = {}

        for address, balances in defi_balances.items():
            vault_balances = self._get_single_addr_balance(balances.assets, roi_cache, pps_cache)
            if len(vault_balances) != 0:
                result[address] = vault_balances
        return result

    def _process_vault_events(self, events: List[YearnVaultEvent]) -> Balance:
        """Process the events for a single vault and returns total profit/loss after all events"""
        total = Balance()
        profit_so_far = Balance()

        if len(events) < 2:
            return total

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
                        location=f'yearn vault v2 event {event.tx_hash.hex()} processing',
                        msg_aggregator=self.msg_aggregator,
                    )
                    profit = Balance(profit_amount, profit_amount * usd_price)
                    profit_so_far += profit
                else:
                    profit = None

                event.realized_pnl = profit
                total += event.to_value

        return total

    def get_vaults_history(
            self,
            write_cursor: 'DBCursor',
            eth_balances: Dict[ChecksumEvmAddress, BalanceSheet],
            addresses: List[ChecksumEvmAddress],
            from_block: int,
            to_block: int,
    ) -> Dict[ChecksumEvmAddress, Dict[str, YearnVaultHistory]]:
        query_addresses: List[EvmAddress] = []
        query_checksumed_addresses: List[ChecksumEvmAddress] = []

        # Skip addresses recently fetched
        for address in addresses:
            last_query = self.database.get_used_query_range(
                cursor=write_cursor,
                name=f'{YEARN_VAULTS_V2_PREFIX}_{address}',
            )
            skip_query = last_query and to_block - last_query[1] < MAX_BLOCKTIME_CACHE
            if not skip_query:
                query_addresses.append(EvmAddress(address.lower()))
                query_checksumed_addresses.append(address)

        # if None of the addresses has yearn v2 positions this
        # will return a map of addresses to empty lists
        new_events_addresses = self.graph_inquirer.get_all_events(
            addresses=query_addresses,
            from_block=from_block,
            to_block=to_block,
        )
        current_time = ts_now()
        vaults_histories_per_address: Dict[ChecksumEvmAddress, Dict[str, YearnVaultHistory]] = {}

        for address, new_events in new_events_addresses.items():
            # Query events from db for address
            db_events = get_yearn_vaults_v2_events(
                cursor=write_cursor,
                address=address,
                from_block=from_block,
                to_block=to_block,
                msg_aggregator=self.msg_aggregator,
            )
            # Flatten the data into a unique list
            events = list(new_events['deposits'])
            events.extend(new_events['withdrawals'])

            if len(db_events) == 0 and len(events) == 0:
                # After all events have been queried then also update the query range.
                # Even if no events are found for an address we need to remember the range
                self.database.update_used_block_query_range(
                    write_cursor=write_cursor,
                    name=f'{YEARN_VAULTS_V2_PREFIX}_{address}',
                    from_block=from_block,
                    to_block=to_block,
                )
                continue
            add_yearn_vaults_events(write_cursor, address, events)

        for address in addresses:
            all_events = get_yearn_vaults_v2_events(
                cursor=write_cursor,
                address=address,
                from_block=from_block,
                to_block=to_block,
                msg_aggregator=self.msg_aggregator,
            )
            vaults_histories: Dict[str, YearnVaultHistory] = {}
            # Dict that stores vault token symbol and their events + total pnl
            vaults: Dict[str, Dict[str, List[YearnVaultEvent]]] = defaultdict(
                lambda: defaultdict(list),
            )
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
                balances = eth_balances.get(address)

                if balances:
                    for asset, balance in balances.assets.items():
                        found_balance = (
                            isinstance(asset, EvmToken) and
                            asset.protocol == YEARN_VAULTS_V2_PROTOCOL and
                            asset.symbol == vault_token_symbol
                        )
                        if found_balance:
                            total_pnl += balance.amount
                            break

                # Due to the way we calculate usd prices for vaults we
                # need to get the current usd price of the actual pnl
                # amount at this point
                if total_pnl.amount != ZERO:
                    usd_price = get_usd_price_zero_if_error(
                        asset=underlying_token,
                        time=current_time,
                        location='yearn vault v2 history',
                        msg_aggregator=self.msg_aggregator,
                    )
                    total_pnl.usd_value = usd_price * total_pnl.amount

                vaults_histories[key] = YearnVaultHistory(
                    events=vaults[key]['events'],
                    profit_loss=total_pnl,
                )
            vaults_histories_per_address[address] = vaults_histories

            self.database.update_used_block_query_range(
                write_cursor=write_cursor,
                name=f'{YEARN_VAULTS_V2_PREFIX}_{address}',
                from_block=from_block,
                to_block=to_block,
            )

        for address in query_checksumed_addresses:
            if (  # the address has no history, omit the key from the final results
                address in vaults_histories_per_address and
                len(vaults_histories_per_address[address]) == 0
            ):
                del vaults_histories_per_address[address]

        return vaults_histories_per_address

    def get_history(
            self,
            given_eth_balances: 'GIVEN_ETH_BALANCES',
            addresses: List[ChecksumEvmAddress],
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Dict[ChecksumEvmAddress, Dict[str, YearnVaultHistory]]:
        with self.history_lock:

            if isinstance(given_eth_balances, dict):
                eth_balances = given_eth_balances
            else:
                eth_balances = given_eth_balances()

            with self.database.user_write() as cursor:
                if reset_db_data is True:
                    self.database.delete_yearn_vaults_data(write_cursor=cursor, version=2)

                from_block = self.ethereum.get_blocknumber_by_time(from_timestamp)
                to_block = self.ethereum.get_blocknumber_by_time(to_timestamp)

                return self.get_vaults_history(
                    write_cursor=cursor,
                    eth_balances=eth_balances,
                    addresses=addresses,
                    from_block=from_block,
                    to_block=to_block,
                )

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        pass

    def deactivate(self) -> None:
        with self.database.user_write() as cursor:
            self.database.delete_yearn_vaults_data(write_cursor=cursor, version=2)
