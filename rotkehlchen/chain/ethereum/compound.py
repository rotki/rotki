import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, Dict, List, NamedTuple, Optional, Tuple, Union

from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.ethereum.zerion import DefiProtocolBalances
from rotkehlchen.constants.ethereum import CTOKEN_ABI, ERC20TOKEN_ABI, EthereumConstants
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import BlockchainQueryError, RemoteError, UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import (
    deserialize_blocknumber,
    deserialize_int_from_hex_or_int,
)
from rotkehlchen.typing import BalanceType, ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import hex_or_bytes_to_int, ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager

BLOCKS_PER_DAY = 4 * 60 * 24
DAYS_PER_YEAR = 365
ETH_MANTISSA = 10**18
A_COMP = EthereumToken('COMP')

COMPTROLLER_PROXY = EthereumConstants().contract('COMPTROLLER_PROXY')
COMPTROLLER_ABI = EthereumConstants.abi('COMPTROLLER_IMPLEMENTATION')


LEND_EVENTS_QUERY_PREFIX = """{graph_event_name}
(where: {{blockTime_lte: $end_ts, blockTime_gte: $start_ts, {addr_position}: $address}}) {{
    id
    amount
    to
    from
    blockNumber
    blockTime
    cTokenSymbol
    underlyingAmount
}}}}"""


BORROW_EVENTS_QUERY_PREFIX = """{graph_event_name}
 (where: {{blockTime_lte: $end_ts, blockTime_gte: $start_ts, borrower: $address}}) {{
    id
    amount
    borrower
    blockNumber
    blockTime
    underlyingSymbol
    {payer_or_empty}
}}}}"""


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
    event_type: Literal['mint', 'redeem', 'borrow', 'repay', 'liquidation', 'comp']
    address: ChecksumEthAddress
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


def _get_params(
        from_ts: Timestamp,
        to_ts: Timestamp,
        address: ChecksumEthAddress,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
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
    return param_types, param_values


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
        self.comptroller_address = self.ethereum.call_contract(
            contract_address=COMPTROLLER_PROXY.address,
            abi=COMPTROLLER_PROXY.abi,
            method_name='comptrollerImplementation',
        )

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

    def _get_borrow_events(
            self,
            event_type: Literal['borrow', 'repay'],
            address: ChecksumEthAddress,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> List[CompoundEvent]:
        param_types, param_values = _get_params(from_ts, to_ts, address)
        if event_type == 'borrow':
            graph_event_name = 'borrowEvents'
            payer_or_empty = ''
        elif event_type == 'repay':
            graph_event_name = 'repayEvents'
            payer_or_empty = 'payer'

        result = self.graph.query(
            querystr=BORROW_EVENTS_QUERY_PREFIX.format(
                graph_event_name=graph_event_name,
                payer_or_empty=payer_or_empty,
            ),
            param_types=param_types,
            param_values=param_values,
        )

        events = []
        for entry in result[graph_event_name]:
            if event_type == 'repay' and entry['borrower'] != entry['payer']:
                continue  # skip repay event. It's actually a liquidation

            underlying_symbol = entry['underlyingSymbol']
            try:
                underlying_asset = Asset(underlying_symbol)
            except UnknownAsset:
                log.error(
                    f'Found unexpected token symbol {underlying_symbol} during '
                    f'graph query. Skipping.',
                )
                continue
            usd_price = Inquirer().find_usd_price(underlying_asset)
            amount = FVal(entry['amount'])
            parse_result = _get_txhash_and_logidx(entry['id'])
            if parse_result is None:
                log.error(
                    f'Found unprocessable borrow/repay id from the graph {entry["id"]}. Skipping',
                )
                continue

            events.append(CompoundEvent(
                event_type=event_type,
                address=address,
                block_number=entry['blockNumber'],
                timestamp=entry['blockTime'],
                asset=underlying_asset,
                value=Balance(amount=amount, usd_value=amount * usd_price),
                to_asset=None,
                to_value=None,
                tx_hash=parse_result[0],
                log_index=parse_result[1],
            ))

        return events

    def _get_liquidation_events(
            self,
            address: ChecksumEthAddress,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> List[CompoundEvent]:
        param_types, param_values = _get_params(from_ts, to_ts, address)
        result = self.graph.query(
            querystr="""liquidationEvents (where: {blockTime_lte: $end_ts, blockTime_gte: $start_ts, from: $address}) {
    id
    amount
    from
    blockNumber
    blockTime
    cTokenSymbol
    underlyingSymbol
    underlyingRepayAmount
}}""",
            param_types=param_types,
            param_values=param_values,
        )

        events = []
        for entry in result['liquidationEvents']:
            ctoken_symbol = entry['cTokenSymbol']
            try:
                ctoken_asset = Asset(ctoken_symbol)
            except UnknownAsset:
                log.error(
                    f'Found unexpected cTokenSymbol {ctoken_symbol} during graph query. Skipping.')
                continue
            underlying_symbol = entry['underlyingSymbol']
            try:
                underlying_asset = Asset(underlying_symbol)
            except UnknownAsset:
                log.error(
                    f'Found unexpected token symbol {underlying_symbol} during '
                    f'graph query. Skipping.',
                )
                continue
            # Amount/value of underlying asset paid by liquidator
            underlying_amount = FVal(entry['amount'])
            underlying_usd_value = underlying_amount * Inquirer().find_usd_price(underlying_asset)
            # Amount/value of ctoken_asset lost to the liquidator
            amount = FVal(entry['amount'])
            usd_value = amount * Inquirer().find_usd_price(ctoken_asset)
            parse_result = _get_txhash_and_logidx(entry['id'])
            if parse_result is None:
                log.error(
                    f'Found unprocessable liquidation id from the graph {entry["id"]}. Skipping',
                )
                continue

            events.append(CompoundEvent(
                event_type='liquidation',
                address=address,
                block_number=entry['blockNumber'],
                timestamp=entry['blockTime'],
                asset=underlying_asset,
                value=Balance(amount=underlying_amount, usd_value=underlying_usd_value),
                to_asset=ctoken_asset,
                to_value=Balance(amount=amount, usd_value=usd_value),
                tx_hash=parse_result[0],
                log_index=parse_result[1],
            ))

        return events

    def _get_lend_events(
            self,
            event_type: Literal['mint', 'redeem'],
            address: ChecksumEthAddress,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> List[CompoundEvent]:
        param_types, param_values = _get_params(from_ts, to_ts, address)
        if event_type == 'mint':
            graph_event_name = 'mintEvents'
            addr_position = 'to'
        elif event_type == 'redeem':
            graph_event_name = 'redeemEvents'
            addr_position = 'from'

        result = self.graph.query(
            querystr=LEND_EVENTS_QUERY_PREFIX.format(
                graph_event_name=graph_event_name,
                addr_position=addr_position,
            ),
            param_types=param_types,
            param_values=param_values,
        )

        events = []
        for entry in result[graph_event_name]:
            ctoken_symbol = entry['cTokenSymbol']
            try:
                ctoken_asset = Asset(ctoken_symbol)
            except UnknownAsset:
                log.error(
                    f'Found unexpected cTokenSymbol {ctoken_symbol} during graph query. Skipping.')
                continue

            underlying_symbol = ctoken_symbol[1:]
            try:
                underlying_asset = Asset(underlying_symbol)
            except UnknownAsset:
                log.error(
                    f'Found unexpected token symbol {underlying_symbol} during '
                    f'graph query. Skipping.',
                )
                continue
            usd_price = Inquirer().find_usd_price(underlying_asset)
            underlying_amount = FVal(entry['underlyingAmount'])
            usd_value = underlying_amount * usd_price
            parse_result = _get_txhash_and_logidx(entry['id'])
            if parse_result is None:
                log.error(f'Found unprocessable mint id from the graph {entry["id"]}. Skipping')
                continue
            amount = FVal(entry['amount'])

            if event_type == 'mint':
                from_value = Balance(amount=underlying_amount, usd_value=usd_value)
                to_value = Balance(amount=amount, usd_value=usd_value)
                from_asset = underlying_asset
                to_asset = ctoken_asset
            else:  # redeem
                from_value = Balance(amount=amount, usd_value=usd_value)
                to_value = Balance(amount=underlying_amount, usd_value=usd_value)
                from_asset = ctoken_asset
                to_asset = underlying_asset

            events.append(CompoundEvent(
                event_type=event_type,
                address=address,
                block_number=entry['blockNumber'],
                timestamp=entry['blockTime'],
                asset=from_asset,
                value=from_value,
                to_asset=to_asset,
                to_value=to_value,
                tx_hash=parse_result[0],
                log_index=parse_result[1],
            ))

        return events

    def _get_comp_events(
            self,
            address: ChecksumEthAddress,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> List[CompoundEvent]:
        self.ethereum.etherscan.get_blocknumber_by_time(from_ts)
        from_block = max(
            COMPTROLLER_PROXY.deployed_block,
            self.ethereum.etherscan.get_blocknumber_by_time(from_ts),
        )
        argument_filters = {
            'from': COMPTROLLER_PROXY.address,
            'to': address,
        }
        comp_events = self.ethereum.get_logs(
            contract_address=A_COMP.ethereum_address,
            abi=ERC20TOKEN_ABI,
            event_name='Transfer',
            argument_filters=argument_filters,
            from_block=from_block,
            # to_block=to_block,
        )
        events = []
        for event in comp_events:
            timestamp = self.ethereum.get_event_timestamp(event)
            amount = hex_or_bytes_to_int(event['topics'][2])
            usd_price = query_usd_price_zero_if_error(
                asset=A_COMP,
                time=timestamp,
                location='comp_claim',
                msg_aggregator=self.msg_aggregator,
            )
            events.append(CompoundEvent(
                event_type='comp',
                address=address,
                block_number=deserialize_blocknumber(event['blockNumber']),
                timestamp=timestamp,
                asset=A_COMP,
                value=Balance(FVal(amount), amount * usd_price),
                to_asset=None,
                to_value=None,
                tx_hash=event['transactionHash'],
                log_index=deserialize_int_from_hex_or_int(event['logIndex'], 'comp log index'),
            ))

        return events

    def _process_events(
            self,
            events: List[CompoundEvent],
    ) -> Dict[ChecksumEthAddress, Dict[Asset, Balance]]:
        """Processes all events and returns a dictionary of earned balances totals"""
        assets: Dict[ChecksumEthAddress, Dict[Asset, Balance]] = defaultdict(
            lambda: defaultdict(Balance),
        )
        # assets: Dict[Asset, Balance] = defaultdict(Balance)
        addresses = set()
        for event in events:
            if event == 'mint':
                assets[event.address][event.asset] -= event.value
                addresses.add(event.address)
            elif event == 'redeem':
                assert event.to_asset, 'redeem events should have a to_asset'
                assets[event.address][event.to_asset] += event.to_value
                addresses.add(event.address)
            elif event == 'comp':
                assets[event.address][A_COMP] += event.value
                addresses.add(event.address)

        for address, asset_entry in assets.items():
            for asset, _ in asset_entry.items():
                ctoken_symbol = 'c' + asset.identifier
                try:
                    ctoken = EthereumToken(ctoken_symbol)
                except UnknownAsset:
                    log.error(
                        f'Found unknown cTokenSymbol {ctoken_symbol} during graph query. Skipping',
                    )
                balance = self.ethereum.call_contract(
                    contract_address=ctoken.ethereum_address,
                    abi=CTOKEN_ABI,
                    method_name='balanceOf',
                    arguments=[address],
                )
                if balance == 0:
                    continue

                ctoken_usd_price = Inquirer().find_usd_price(ctoken)
                asset_usd_price = Inquirer().find_usd_price(asset)
                if ctoken_usd_price == 0 or asset_usd_price == 0:
                    self.msg_aggregator.add_warning(
                        f'Could not find price for {asset} or its cToken during compound query',
                    )
                    continue

                # convert ctoken balance to asset balance with current price
                asset_balance = FVal(balance) * ctoken_usd_price / asset_usd_price
                # and now add it to what user has in compound with current price
                assets[address][asset] += Balance(asset_balance, balance * ctoken_usd_price)

        comp_usd_price = Inquirer().find_usd_price(A_COMP)
        for address in addresses:
            unclaimed_comp = self.ethereum.call_contract(
                contract_address=self.comptroller_address,
                abi=COMPTROLLER_ABI,
                method_name='compAccrued',
                arguments=[address],
            )
            amount = token_normalized_value(unclaimed_comp, A_COMP.decimals)
            assets[address][A_COMP] += Balance(amount, amount * comp_usd_price)

        return assets

    def get_history(
            self,
            addresses: List[ChecksumEthAddress],
            reset_db_data: bool,
    ) -> Dict[str, Any]:
        from_ts = Timestamp(0)
        to_ts = ts_now()
        history: Dict[str, Any] = {}
        for address in addresses:
            events = self._get_lend_events('mint', address, from_ts, to_ts)
            events.extend(self._get_lend_events('redeem', address, from_ts, to_ts))
            events.extend(self._get_borrow_events('borrow', address, from_ts, to_ts))
            events.extend(self._get_borrow_events('repay', address, from_ts, to_ts))
            events.extend(self._get_liquidation_events(address, from_ts, to_ts))
            events.extend(self._get_comp_events(address, from_ts, to_ts))
            events.sort(key=lambda x: x.timestamp)
            history[address] = {'events': events}

        earned_assets_mapping = self._process_events(events)
        history['earned'] = earned_assets_mapping

        return history

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass
