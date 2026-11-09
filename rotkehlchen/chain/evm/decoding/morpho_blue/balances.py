import logging
from collections import defaultdict
from json import JSONDecodeError
from typing import TYPE_CHECKING, NamedTuple

import requests

from rotkehlchen.accounting.structures.balance import BalanceSheet
from rotkehlchen.assets.utils import get_or_create_evm_token, token_normalized_value
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.morpho_blue.constants import (
    CPT_MORPHO_BLUE,
    MORPHO_API_BASE_URL,
    MORPHO_BLUE_ABI,
    MORPHO_BLUE_ADDRESSES,
    MORPHO_IRM_ABI,
)
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import NotERC20Conformant, NotERC721Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MARKET_ID = 'market_id'
WAD = 10**18
VIRTUAL_ASSETS = 1
VIRTUAL_SHARES = 10**6


class MarketState(NamedTuple):
    total_supply_assets: int
    total_supply_shares: int
    total_borrow_assets: int
    total_borrow_shares: int
    last_update: int
    fee: int


class MarketParams(NamedTuple):
    loan_token: ChecksumEvmAddress
    collateral_token: ChecksumEvmAddress
    oracle: ChecksumEvmAddress
    irm: ChecksumEvmAddress
    lltv: int


class Position(NamedTuple):
    supply_shares: int
    borrow_shares: int
    collateral: int


def _assets_down(shares: int, total_assets: int, total_shares: int) -> int:
    return shares * (total_assets + VIRTUAL_ASSETS) // (total_shares + VIRTUAL_SHARES)


def _assets_up(shares: int, total_assets: int, total_shares: int) -> int:
    denominator = total_shares + VIRTUAL_SHARES
    return (shares * (total_assets + VIRTUAL_ASSETS) + denominator - 1) // denominator


def _accrue_market_state(
        state: MarketState,
        borrow_rate: int,
        block_timestamp: int,
) -> MarketState:
    """Return Morpho's expected market state after accruing interest at block_timestamp."""
    if (
            (elapsed := block_timestamp - state.last_update) <= 0 or
            state.total_borrow_assets == 0 or
            borrow_rate == 0
    ):
        return state

    first_term = borrow_rate * elapsed
    second_term = first_term * first_term // (2 * WAD)
    third_term = second_term * first_term // (3 * WAD)
    interest = state.total_borrow_assets * (first_term + second_term + third_term) // WAD
    total_supply_assets = state.total_supply_assets + interest
    total_supply_shares = state.total_supply_shares
    if state.fee != 0:
        fee_amount = interest * state.fee // WAD
        total_supply_shares += (
            fee_amount * (total_supply_shares + VIRTUAL_SHARES) //
            (total_supply_assets - fee_amount + VIRTUAL_ASSETS)
        )

    return MarketState(
        total_supply_assets=total_supply_assets,
        total_supply_shares=total_supply_shares,
        total_borrow_assets=state.total_borrow_assets + interest,
        total_borrow_shares=state.total_borrow_shares,
        last_update=state.last_update,
        fee=state.fee,
    )


class MorphoBlueBalances(ProtocolWithBalance):

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            tx_decoder: EVMTransactionDecoder,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_MORPHO_BLUE,
            deposit_event_types={
                (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL),
            },
        )
        self.morpho_contract = EvmContract(
            address=MORPHO_BLUE_ADDRESSES[self.evm_inquirer.chain_id],
            abi=MORPHO_BLUE_ABI,
        )
        self.irm_contract = EvmContract(address=ZERO_ADDRESS, abi=MORPHO_IRM_ABI)

    def _query_api_market_ids(self, address: ChecksumEvmAddress) -> set[str]:
        """Discover active markets when the local decoded history has none.

        This fallback makes first-time imports and accounts with incomplete explorer history work.
        It is deliberately not called for addresses whose markets were found locally.
        """
        market_ids: set[str] = set()
        cursor = None
        while True:
            params = {
                'active_only': 'true',
                'chain_ids': str(self.evm_inquirer.chain_id.value),
                'limit': '100',
            }
            if cursor is not None:
                params['cursor'] = cursor

            try:
                response = requests.get(
                    url=f'{MORPHO_API_BASE_URL}/users/{address}/positions',
                    params=params,
                    timeout=CachedSettings().get_timeout_tuple(),
                )
                response.raise_for_status()
                payload = response.json()
                entries = payload['data']
                cursor = payload.get('cursor')
            except (requests.RequestException, JSONDecodeError, KeyError, TypeError) as e:
                log.error(
                    'Failed to discover Morpho Blue markets for %s on %s due to %s',
                    address,
                    self.evm_inquirer.chain_name,
                    e,
                )
                break

            for entry in entries:
                if (
                        isinstance(entry, dict) and
                        entry.get('chain_id') == self.evm_inquirer.chain_id.value and
                        isinstance(market_id := entry.get('market_id'), str) and
                        market_id.startswith('0x') and
                        len(market_id) == 66
                ):
                    market_ids.add(market_id)

            if cursor is None:
                break

        return market_ids

    def _get_address_markets(
            self,
            addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, set[str]]:
        address_to_markets: dict[ChecksumEvmAddress, set[str]] = defaultdict(set)
        for address, events in self.addresses_with_activity(
            event_types={
                (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL),
                (HistoryEventType.WITHDRAWAL, HistoryEventSubType.WITHDRAW_FROM_PROTOCOL),
                (HistoryEventType.RECEIVE, HistoryEventSubType.GENERATE_DEBT),
                (HistoryEventType.SPEND, HistoryEventSubType.PAYBACK_DEBT),
            },
            location_labels=addresses,
        ).items():
            for event in events:
                if (
                        event.extra_data is not None and
                        isinstance(market_id := event.extra_data.get(MARKET_ID), str)
                ):
                    address_to_markets[address].add(market_id)

        for address in addresses:
            if len(address_to_markets[address]) == 0:
                address_to_markets[address].update(self._query_api_market_ids(address=address))

        return {address: markets for address, markets in address_to_markets.items() if markets}

    def _query_contract_data(
            self,
            address_to_markets: dict[ChecksumEvmAddress, set[str]],
    ) -> tuple[
        dict[str, MarketParams],
        dict[str, MarketState],
        dict[tuple[ChecksumEvmAddress, str], Position],
    ] | None:
        market_ids = sorted({
            market_id
            for markets in address_to_markets.values()
            for market_id in markets
        })
        address_market_pairs = [
            (address, market_id)
            for address, markets in address_to_markets.items()
            for market_id in sorted(markets)
        ]
        calls = [
            (
                self.morpho_contract.address,
                self.morpho_contract.encode('idToMarketParams', [market_id]),
            )
            for market_id in market_ids
        ] + [
            (self.morpho_contract.address, self.morpho_contract.encode('market', [market_id]))
            for market_id in market_ids
        ] + [
            (
                self.morpho_contract.address,
                self.morpho_contract.encode('position', [market_id, address]),
            )
            for address, market_id in address_market_pairs
        ]
        try:
            latest_block = self.evm_inquirer.get_latest_block_number()
            outputs = self.evm_inquirer.multicall(calls=calls, block_identifier=latest_block)
            block_timestamp = self.evm_inquirer.get_block_timestamp(
                block_number=latest_block,
                full_transactions=False,
            )
        except (RemoteError, DeserializationError, KeyError) as e:
            log.error('Failed to query Morpho Blue positions due to %s', e)
            return None

        market_params = {
            market_id: MarketParams(*self.morpho_contract.decode(
                result=outputs[idx],
                method_name='idToMarketParams',
                arguments=[market_id],
            ))
            for idx, market_id in enumerate(market_ids)
        }
        state_offset = len(market_ids)
        market_states = {
            market_id: MarketState(*self.morpho_contract.decode(
                result=outputs[state_offset + idx],
                method_name='market',
                arguments=[market_id],
            ))
            for idx, market_id in enumerate(market_ids)
        }
        position_offset = state_offset * 2
        positions = {
            pair: Position(*self.morpho_contract.decode(
                result=outputs[position_offset + idx],
                method_name='position',
                arguments=[pair[1], pair[0]],
            ))
            for idx, pair in enumerate(address_market_pairs)
        }

        accruing_markets = [
            market_id for market_id in market_ids
            if (
                market_states[market_id].total_borrow_assets != 0 and
                market_states[market_id].last_update < block_timestamp and
                market_params[market_id].irm != ZERO_ADDRESS
            )
        ]
        if len(accruing_markets) == 0:
            return market_params, market_states, positions

        try:
            rate_outputs = self.evm_inquirer.multicall_2(
                calls=[(
                    market_params[market_id].irm,
                    self.irm_contract.encode('borrowRateView', [
                        market_params[market_id],
                        market_states[market_id],
                    ]),
                ) for market_id in accruing_markets],
                require_success=False,
                block_identifier=latest_block,
            )
        except RemoteError as e:
            log.error('Failed to query Morpho Blue borrow rates due to %s', e)
            return None

        for idx, market_id in enumerate(accruing_markets):
            if rate_outputs[idx][0] is False:
                log.error(
                    'Failed to query the Morpho Blue borrow rate for market %s on %s. '
                    'Using the last accrued balance instead.',
                    market_id,
                    self.evm_inquirer.chain_name,
                )
                continue

            market_states[market_id] = _accrue_market_state(
                state=market_states[market_id],
                borrow_rate=self.irm_contract.decode(
                    result=rate_outputs[idx][1],
                    method_name='borrowRateView',
                    arguments=[market_params[market_id], market_states[market_id]],
                )[0],
                block_timestamp=block_timestamp,
            )

        return market_params, market_states, positions

    def _get_token(self, address: ChecksumEvmAddress) -> EvmToken:
        return get_or_create_evm_token(
            userdb=self.evm_inquirer.database,
            evm_address=address,
            chain_id=self.evm_inquirer.chain_id,
            evm_inquirer=self.evm_inquirer,
        )

    def query_balances(self, addresses: list[ChecksumEvmAddress]) -> BalancesSheetType:
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(address_to_markets := self._get_address_markets(addresses=addresses)) == 0:
            return balances

        if (contract_data := self._query_contract_data(address_to_markets)) is None:
            return balances
        market_params, market_states, positions = contract_data

        assets = []
        liabilities = []
        tokens: dict[ChecksumEvmAddress, EvmToken] = {}
        try:
            for (address, market_id), position in positions.items():
                params, state = market_params[market_id], market_states[market_id]
                if position.collateral != 0:
                    if (collateral_token := tokens.get(params.collateral_token)) is None:
                        tokens[params.collateral_token] = collateral_token = self._get_token(
                            address=params.collateral_token,
                        )
                    assets.append((
                        address,
                        collateral_token,
                        token_normalized_value(position.collateral, collateral_token),
                    ))
                if position.supply_shares != 0:
                    if (loan_token := tokens.get(params.loan_token)) is None:
                        tokens[params.loan_token] = loan_token = self._get_token(
                            address=params.loan_token,
                        )
                    assets.append((
                        address,
                        loan_token,
                        token_normalized_value(
                            _assets_down(
                                shares=position.supply_shares,
                                total_assets=state.total_supply_assets,
                                total_shares=state.total_supply_shares,
                            ),
                            loan_token,
                        ),
                    ))
                if position.borrow_shares != 0:
                    if (loan_token := tokens.get(params.loan_token)) is None:
                        tokens[params.loan_token] = loan_token = self._get_token(
                            address=params.loan_token,
                        )
                    liabilities.append((
                        address,
                        loan_token,
                        token_normalized_value(
                            _assets_up(
                                shares=position.borrow_shares,
                                total_assets=state.total_borrow_assets,
                                total_shares=state.total_borrow_shares,
                            ),
                            loan_token,
                        ),
                    ))
        except (DeserializationError, NotERC20Conformant, NotERC721Conformant) as e:
            log.error('Failed to resolve tokens for Morpho Blue positions due to %s', e)
            return balances

        self._add_priced_balances(balances=balances, amounts=assets)
        self._add_priced_balances(
            balances=balances,
            amounts=liabilities,
            category='liabilities',
        )
        return balances
