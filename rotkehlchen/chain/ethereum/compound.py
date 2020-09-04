import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, NamedTuple, Optional, Tuple, Union

from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.chain.ethereum.zerion import DefiProtocolBalances
from rotkehlchen.constants.ethereum import CTOKEN_ABI
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import BlockchainQueryError, RemoteError, UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import BalanceType, ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager

BLOCKS_PER_DAY = 4 * 60 * 24
DAYS_PER_YEAR = 365
ETH_MANTISSA = 10**18
A_COMP = EthereumToken('COMP')

EVENTS_QUERY_PREFIX = """(where: {blockTime_lte: $end_ts, blockTime_gte: $start_ts, to: $address}) {
    id
    amount
    to
    from
    blockNumber
    blockTime
    cTokenSymbol
    underlyingAmount
}}"""

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


class CompoundEvent(NamedTuple):
    event_type: Literal['mint', 'redeem', 'borrow', 'repay', 'liquidation']
    block_number: int
    timestamp: int
    asset: Asset
    value: Balance
    to_asset: Optional[Asset]
    to_value: Optional[Balance]
    tx_hash: str
    log_index: int  # only used to identify uniqueness

    def serialize(self) -> Dict[str, Any]:
        serialized = self._asdict()  # pylint: disable=no-member
        del serialized['log_index']
        return serialized


def _get_txhash_and_logidx(identifier: str) -> Optional[Tuple[str, int]]:
    result = identifier.split('-')
    if len(result) != 2:
        return None

    if len(result[0]) == 0 or len(result[1]) == 0:
        return None

    try:
        log_index = int(result[1])
    except ValueError:
        return None

    return result[0], log_index


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
        self.graph = Graph('https://api.thegraph.com/subgraphs/name/graphprotocol/compound-v2')

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

    def _get_mint_events(
            self,
            address: ChecksumEthAddress,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> List[CompoundEvent]:
        param_types = {
            '$start_ts': 'Int!',
            '$end_ts': 'Int!',
            '$address': 'Bytes!',
        }
        param_values = {
            'start_ts': from_ts,
            'end_ts': to_ts,
            'address': address,
        }
        result = self.graph.query(
            querystr='mintEvents ' + EVENTS_QUERY_PREFIX,
            param_types=param_types,
            param_values=param_values,
        )
        events = []
        for entry in result['mintEvents']:
            ctoken_symbol = entry['cTokenSymbol']
            try:
                minted_asset = Asset(ctoken_symbol)
            except UnknownAsset:
                log.error(
                    f'Found unexpected cTokenSymbol {ctoken_symbol} during graph query. Skipping.')
                continue

            deposited_symbol = ctoken_symbol[1:]
            try:
                deposited_asset = Asset(deposited_symbol)
            except UnknownAsset:
                log.error(
                    f'Found unexpected deposited symbol {deposited_symbol} during '
                    f'graph query. Skipping.',
                )
                continue
            usd_price = Inquirer().find_usd_price(deposited_asset)
            underlying_amount = FVal(entry['underlyingAmount'])
            usd_value = underlying_amount * usd_price
            parse_result = _get_txhash_and_logidx(entry['id'])
            if parse_result is None:
                log.error(f'Found unprocessable mint id from the graph {entry["id"]}. Skipping')
                continue

            events.append(CompoundEvent(
                event_type='mint',
                block_number=entry['blockNumber'],
                timestamp=entry['blockTime'],
                asset=deposited_asset,
                value=Balance(amount=underlying_amount, usd_value=usd_value),
                to_asset=minted_asset,
                to_value=Balance(amount=FVal(entry['amount']), usd_value=usd_value),
                tx_hash=parse_result[0],
                log_index=parse_result[1],
            ))

        return events

    def _get_redeem_events(
            self,
            address: ChecksumEthAddress,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> List[CompoundEvent]:
        param_types = {
            '$start_ts': 'Int!',
            '$end_ts': 'Int!',
            '$address': 'Bytes!',
        }
        param_values = {
            'start_ts': from_ts,
            'end_ts': to_ts,
            'address': address,
        }
        result = self.graph.query(
            querystr='redeemEvents ' + EVENTS_QUERY_PREFIX,
            param_types=param_types,
            param_values=param_values,
        )
        events = []
        for entry in result['redeemEvents']:
            ctoken_symbol = entry['cTokenSymbol']
            try:
                returning_asset = Asset(ctoken_symbol)
            except UnknownAsset:
                log.error(
                    f'Found unexpected cTokenSymbol {ctoken_symbol} during graph query. Skipping.')
                continue

            redeemed_symbol = ctoken_symbol[1:]
            try:
                redeemed_asset = Asset(redeemed_symbol)
            except UnknownAsset:
                log.error(
                    f'Found unexpected redeemed symbol {redeemed_symbol} during '
                    f'graph query. Skipping.',
                )
                continue
            usd_price = Inquirer().find_usd_price(redeemed_asset)
            underlying_amount = FVal(entry['underlyingAmount'])
            usd_value = underlying_amount * usd_price
            parse_result = _get_txhash_and_logidx(entry['id'])
            if parse_result is None:
                log.error(f'Found unprocessable mint id from the graph {entry["id"]}. Skipping')
                continue

            events.append(CompoundEvent(
                event_type='redeem',
                block_number=entry['blockNumber'],
                timestamp=entry['blockTime'],
                asset=returning_asset,
                value=Balance(amount=FVal(entry['amount']), usd_value=usd_value),
                to_asset=redeemed_asset,
                to_value=Balance(amount=underlying_amount, usd_value=usd_value),
                tx_hash=parse_result[0],
                log_index=parse_result[1],
            ))

        return events

    def get_history(
            self,
            addresses: List[ChecksumEthAddress],
            reset_db_data: bool,
    ) -> Dict[ChecksumEthAddress, List[CompoundEvent]]:
        from_ts = Timestamp(0)
        to_ts = ts_now()
        history = {}
        for address in addresses:
            events = self._get_mint_events(address, from_ts, to_ts)
            events.extend(self._get_redeem_events(address, from_ts, to_ts))
            history[address] = events

        return history

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass
