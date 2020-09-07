import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional, Tuple, Union

from eth_utils import to_checksum_address
from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.ethereum.zerion import GIVEN_DEFI_BALANCES
from rotkehlchen.constants.ethereum import CTOKEN_ABI, ERC20TOKEN_ABI, EthereumConstants
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import BlockchainQueryError, RemoteError, UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import (
    deserialize_blocknumber,
    deserialize_int_from_hex_or_int,
)
from rotkehlchen.typing import BalanceType, ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager

ADDRESS_TO_ASSETS = Dict[ChecksumEthAddress, Dict[Asset, Balance]]
BLOCKS_PER_DAY = 4 * 60 * 24
DAYS_PER_YEAR = 365
ETH_MANTISSA = 10**18
A_COMP = EthereumToken('COMP')

COMPTROLLER_PROXY = EthereumConstants().contract('COMPTROLLER_PROXY')
COMPTROLLER_ABI = EthereumConstants.abi('COMPTROLLER_IMPLEMENTATION')
COMP_DEPLOYED_BLOCK = 9601359


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
    realized_pnl: Optional[Balance]
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
        self.comptroller_address = to_checksum_address(self.ethereum.call_contract(
            contract_address=COMPTROLLER_PROXY.address,
            abi=COMPTROLLER_PROXY.abi,
            method_name='comptrollerImplementation',
        ))

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
            given_defi_balances: GIVEN_DEFI_BALANCES,
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
                    # Get the underlying balance
                    underlying_symbol = balance_entry.underlying_balances[0].token_symbol
                    try:
                        underlying_asset = Asset(underlying_symbol)
                    except UnknownAsset:
                        log.error(
                            f'Encountered unknown asset {underlying_symbol} in compound. Skipping',
                        )
                        continue

                    lending_map[underlying_asset.identifier] = CompoundBalance(
                        balance_type=BalanceType.ASSET,
                        balance=balance_entry.underlying_balances[0].balance,
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
            timestamp = entry['blockTime']
            usd_price = query_usd_price_zero_if_error(
                asset=underlying_asset,
                time=timestamp,
                location=f'compound {event_type}',
                msg_aggregator=self.msg_aggregator,
            )
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
                timestamp=timestamp,
                asset=underlying_asset,
                value=Balance(amount=amount, usd_value=amount * usd_price),
                to_asset=None,
                to_value=None,
                realized_pnl=None,
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
            timestamp = entry['blockTime']
            # Amount/value of underlying asset paid by liquidator
            underlying_amount = FVal(entry['underlyingRepayAmount'])
            underlying_usd_price = query_usd_price_zero_if_error(
                asset=underlying_asset,
                time=timestamp,
                location='compound liquidation underlying asset',
                msg_aggregator=self.msg_aggregator,
            )
            underlying_usd_value = underlying_amount * underlying_usd_price
            # Amount/value of ctoken_asset lost to the liquidator
            amount = FVal(entry['amount'])
            usd_price = query_usd_price_zero_if_error(
                asset=ctoken_asset,
                time=timestamp,
                location='compound liquidation ctoken asset',
                msg_aggregator=self.msg_aggregator,
            )
            usd_value = amount * usd_price
            parse_result = _get_txhash_and_logidx(entry['id'])
            if parse_result is None:
                log.error(
                    f'Found unprocessable liquidation id from the graph {entry["id"]}. Skipping',
                )
                continue

            value = Balance(amount=amount, usd_value=usd_value)
            events.append(CompoundEvent(
                event_type='liquidation',
                address=address,
                block_number=entry['blockNumber'],
                timestamp=timestamp,
                asset=underlying_asset,
                value=Balance(amount=underlying_amount, usd_value=underlying_usd_value),
                to_asset=ctoken_asset,
                to_value=value,
                realized_pnl=value,
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
            timestamp = entry['blockTime']
            usd_price = query_usd_price_zero_if_error(
                asset=underlying_asset,
                time=timestamp,
                location=f'compound {event_type}',
                msg_aggregator=self.msg_aggregator,
            )
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
                timestamp=timestamp,
                asset=from_asset,
                value=from_value,
                to_asset=to_asset,
                to_value=to_value,
                realized_pnl=None,
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
            COMP_DEPLOYED_BLOCK,
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
            to_block=self.ethereum.etherscan.get_blocknumber_by_time(to_ts),
        )

        events = []
        for event in comp_events:
            timestamp = self.ethereum.get_event_timestamp(event)
            amount = token_normalized_value(hex_or_bytes_to_int(event['data']), A_COMP.decimals)
            usd_price = query_usd_price_zero_if_error(
                asset=A_COMP,
                time=timestamp,
                location='comp_claim',
                msg_aggregator=self.msg_aggregator,
            )
            value = Balance(amount, amount * usd_price)
            events.append(CompoundEvent(
                event_type='comp',
                address=address,
                block_number=deserialize_blocknumber(event['blockNumber']),
                timestamp=timestamp,
                asset=A_COMP,
                value=value,
                to_asset=None,
                to_value=None,
                realized_pnl=value,
                tx_hash=event['transactionHash'],
                log_index=deserialize_int_from_hex_or_int(event['logIndex'], 'comp log index'),
            ))

        return events

    def _process_events(
            self,
            events: List[CompoundEvent],
            given_defi_balances: GIVEN_DEFI_BALANCES,
    ) -> Tuple[ADDRESS_TO_ASSETS, ADDRESS_TO_ASSETS, ADDRESS_TO_ASSETS]:
        """Processes all events and returns a dictionary of earned balances totals"""
        assets: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))
        loss_assets: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))
        rewards_assets: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))

        balances = self.get_balances(given_defi_balances)

        for idx, event in enumerate(events):
            if event.event_type == 'mint':
                assets[event.address][event.asset] -= event.value
            elif event.event_type == 'redeem':
                assert event.to_asset, 'redeem events should have a to_asset'
                e_profit = assets[event.address][event.to_asset] + event.to_value
                profit = e_profit if e_profit.amount >= 0 else None  # not realized profit yet
                assets[event.address][event.to_asset] += event.to_value
                events[idx] = event._replace(realized_pnl=profit)  # TODO: maybe not named tuple?

            elif event.event_type == 'borrow':
                loss_assets[event.address][event.asset] -= event.value
            elif event.event_type == 'repay':
                e_loss = loss_assets[event.address][event.asset] + event.value
                loss = e_loss if e_loss.amount >= 0 else None  # not realized loss yet
                loss_assets[event.address][event.asset] += event.value
                events[idx] = event._replace(realized_pnl=loss)  # TODO: maybe not named tuple?
            elif event.event_type == 'liquidation':
                assert event.to_asset, 'liquidation events should have a to_asset'
                loss_assets[event.address][event.to_asset] += event.to_value
            elif event.event_type == 'comp':
                rewards_assets[event.address][A_COMP] += event.value

        for address, bentry in balances.items():
            for asset, entry in bentry['lending'].items():
                # get the underlying
                assets[address][asset] += entry.balance

            for asset, entry in bentry['borrowing'].items():
                loss_assets[address][asset] += entry.balance

            for asset, entry in bentry['rewards'].items():
                rewards_assets[address][asset] += entry.balance

        return assets, loss_assets, rewards_assets

    def get_history(
            self,
            given_defi_balances: GIVEN_DEFI_BALANCES,
            addresses: List[ChecksumEthAddress],
            reset_db_data: bool,  # pylint: disable=unused-argument
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Dict[str, Any]:
        """May raise:
        - RemoteError due to the graph query failure or etherscan
        """
        history: Dict[str, Any] = {}
        events: List[CompoundEvent] = []
        for address in addresses:
            events.extend(self._get_lend_events('mint', address, from_timestamp, to_timestamp))
            events.extend(self._get_lend_events('redeem', address, from_timestamp, to_timestamp))
            events.extend(self._get_borrow_events('borrow', address, from_timestamp, to_timestamp))
            events.extend(self._get_borrow_events('repay', address, from_timestamp, to_timestamp))
            events.extend(self._get_liquidation_events(address, from_timestamp, to_timestamp))
            events.extend(self._get_comp_events(address, from_timestamp, to_timestamp))

        events.sort(key=lambda x: x.timestamp)
        history['events'] = events
        profit, loss, rewards = self._process_events(events, given_defi_balances)
        history['interest_profit'] = profit
        history['debt_loss'] = loss
        history['rewards'] = rewards

        return history

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass
