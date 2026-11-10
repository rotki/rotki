import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final, NamedTuple

from eth_utils import is_hexstr

from rotkehlchen.accounting.structures.balance import BalanceSheet
from rotkehlchen.assets.utils import get_or_create_evm_token, token_normalized_value
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.morpho_blue.constants import (
    CPT_MORPHO_BLUE,
    MORPHO_BLUE_ABI,
    MORPHO_BLUE_ADDRESSES,
    MORPHO_IRM_ABI,
)
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

MARKET_ID: Final = 'market_id'
WAD: Final = 10**18
VIRTUAL_ASSETS: Final = 1
VIRTUAL_SHARES: Final = 10**6


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
            (elapsed := block_timestamp - state.last_update) <= 0
    ):
        return state
    if state.total_borrow_assets == 0 or borrow_rate == 0:
        return state._replace(last_update=block_timestamp)

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
        last_update=block_timestamp,
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
                        isinstance(market_id := event.extra_data.get(MARKET_ID), str) and
                        len(market_id) == 66 and
                        is_hexstr(market_id)
                ):
                    address_to_markets[address].add(market_id)
                else:
                    log.error(
                        'Skipping Morpho Blue event %s during balance query due to missing %s '
                        'in extra data',
                        event.identifier,
                        MARKET_ID,
                    )

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

        try:
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
        except DeserializationError as e:
            log.error('Failed to decode Morpho Blue positions due to %s', e)
            return None

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

            try:
                borrow_rate = self.irm_contract.decode(
                    result=rate_outputs[idx][1],
                    method_name='borrowRateView',
                    arguments=[market_params[market_id], market_states[market_id]],
                )[0]
            except DeserializationError as e:
                log.error('Failed to decode Morpho Blue borrow rate for market %s due to %s', market_id, e)  # noqa: E501
                continue

            market_states[market_id] = _accrue_market_state(
                state=market_states[market_id],
                borrow_rate=borrow_rate,
                block_timestamp=block_timestamp,
            )

        return market_params, market_states, positions

    def _get_token(self, address: ChecksumEvmAddress) -> EvmToken | None:
        try:
            return get_or_create_evm_token(
                userdb=self.evm_inquirer.database,
                evm_address=address,
                chain_id=self.evm_inquirer.chain_id,
                evm_inquirer=self.evm_inquirer,
            )
        except (DeserializationError, NotERC20Conformant, NotERC721Conformant) as e:
            log.error('Failed to resolve Morpho Blue token %s due to %s', address, e)
            return None

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
        failed_tokens: set[ChecksumEvmAddress] = set()
        for (address, market_id), position in positions.items():
            params, state = market_params[market_id], market_states[market_id]
            if position.collateral != 0 and params.collateral_token not in failed_tokens:
                if (collateral_token := tokens.get(params.collateral_token)) is None:
                    if (collateral_token := self._get_token(params.collateral_token)) is None:
                        failed_tokens.add(params.collateral_token)
                    else:
                        tokens[params.collateral_token] = collateral_token
                if collateral_token is not None:
                    assets.append((
                        address,
                        collateral_token,
                        token_normalized_value(position.collateral, collateral_token),
                    ))
            loan_token = tokens.get(params.loan_token)
            if (
                    (position.supply_shares != 0 or position.borrow_shares != 0) and
                    params.loan_token not in failed_tokens and
                    loan_token is None
            ):
                if (loan_token := self._get_token(params.loan_token)) is None:
                    failed_tokens.add(params.loan_token)
                else:
                    tokens[params.loan_token] = loan_token
            if position.supply_shares != 0 and loan_token is not None:
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
            if position.borrow_shares != 0 and loan_token is not None:
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

        self._add_priced_balances(balances=balances, amounts=assets)
        self._add_priced_balances(
            balances=balances,
            amounts=liabilities,
            category='liabilities',
        )
        return balances
