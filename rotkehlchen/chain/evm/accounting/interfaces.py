import logging
from abc import ABCMeta, abstractmethod
from collections import defaultdict
from collections.abc import Iterator
from typing import TYPE_CHECKING, Literal, Optional

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.accounting.types import MissingPrice
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price
from rotkehlchen.utils.misc import ts_ms_to_sec

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.accounting.structures.evm_event import EvmEvent
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

    from .structures import TxEventSettings

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# protocols that make use of `deposit_events_num` & `withdrawal_events_num`
PROTOCOLS_WITH_EXTRA_DATA = {'curve', 'balancer-v1'}
# protocols where tokens deposited can be different from the withdrawn token(s).
# we use their LP token instead
PROTOCOLS_WITH_SPECIAL_POOLS = {'curve'}


class ModuleAccountantInterface(metaclass=ABCMeta):

    def __init__(
            self,
            node_inquirer: 'EvmNodeInquirer',  # pylint: disable=unused-argument
            msg_aggregator: 'MessagesAggregator',  # pylint: disable=unused-argument
    ) -> None:
        """This is the evm module accountant interface. All module accountants
        should implement it

        To have smaller objects and since few decoders use most of the given objects
        we do not save anything here at the moment, but instead let it up to the individual
        decoder to choose what to keep"""
        # It's okay to call overriden reset here, since super class reset does not do anything.
        # If at any point it does we have to make sure all overriden reset() call parent
        self.reset()

    @abstractmethod
    def event_settings(self, pot: 'AccountingPot') -> dict[str, 'TxEventSettings']:
        """
        Subclasses implement this to specify rules/settings for their created events
        """

    def reset(self) -> None:
        """Subclasses may implement this to reset state between accounting runs"""
        return None


class DepositableAccountantInterface(ModuleAccountantInterface):
    """
    Interface for protocols that allow to deposit multiple tokens in exchange for a token
    representing the position in the pool.

    This also handles accounting for PnL during withdrawals for the said protocols.

    These protocols include:
    - Curve
    - Balancer
    - Yearn
    - Uniswap v2 & v3
    - Sushiswap v2
    - Aave v1
    """
    # a mapping of assets deposited to their balance. For protocols like curve,
    # the asset is the LP token since tokens deposited can be different from
    # the ones withdrawn depending on the type of liquidity pool.
    total_value_deposited: dict[Asset, Balance] = defaultdict(Balance)

    def reset(self) -> None:
        self.total_value_deposited = defaultdict(Balance)

    def process_withdrawal(
            self,
            pot: 'AccountingPot',
            event: 'EvmEvent',
            other_events: Iterator['EvmEvent'],
    ) -> None:
        """Process withdrawals from protocols and deducts the USD value of the token(s) withdrawn."""  # noqa: E501
        if event.counterparty in PROTOCOLS_WITH_EXTRA_DATA:
            self._process_protocols_with_extra_data_deposit_or_withdrawal(
                pot=pot,
                event=event,
                action_type='withdrawal',
                other_events=other_events,
            )
        else:
            self._process_protocols_deposit_or_withdrawal(
                pot=pot,
                event=event,
                action='withdrawal',
            )

    def process_deposit(
            self,
            pot: 'AccountingPot',
            event: 'EvmEvent',
            other_events: Iterator['EvmEvent'],
    ) -> None:
        """Process deposits to protocols and stores the USD value of the token(s) deposited."""
        if event.counterparty in PROTOCOLS_WITH_EXTRA_DATA:
            self._process_protocols_with_extra_data_deposit_or_withdrawal(
                pot=pot,
                event=event,
                action_type='deposit',
                other_events=other_events,
            )
        else:
            self._process_protocols_deposit_or_withdrawal(
                pot=pot,
                event=event,
                action='deposit',
            )

    def _process_protocols_deposit_or_withdrawal(
            self,
            event: 'EvmEvent',
            pot: 'AccountingPot',
            action: Literal['deposit', 'withdrawal'],
    ) -> None:
        usd_price, usd_value = self._query_historical_price(pot=pot, event=event)
        if action == 'deposit':
            self.total_value_deposited[event.asset] += Balance(
                amount=event.balance.amount,
                usd_value=usd_value,
            )
        else:
            self._calculate_pnl(
                pot=pot,
                event=event,
                usd_price=usd_price,
                usd_value=usd_value,
            )

    def _process_protocols_with_extra_data_deposit_or_withdrawal(
            self,
            pot: 'AccountingPot',
            action_type: Literal['deposit', 'withdrawal'],
            event: 'EvmEvent',
            other_events: Iterator['EvmEvent'],
    ) -> None:
        """Processes deposit/withdrawals for certain protocols.

        These protocols are Curve & Balancer.
        """
        asset_change_method: Literal['spend', 'acquisition']
        if action_type == 'deposit':
            dict_key = 'deposit_events_num'
            asset_change_method = 'spend'
        else:  # can only be withdrawal
            dict_key = 'withdrawal_events_num'
            asset_change_method = 'acquisition'

        events_to_consume = event.extra_data.get(dict_key) if event.extra_data is not None else None  # noqa: E501
        if events_to_consume is None:
            log.debug(
                f'Could not find the number of events to consume for a {event.counterparty} '
                f'{action_type} transaction {event.serialized_event_identifier}',
            )
            return

        # for curve pools, we assign the usd value of the pool to
        # the pool token instead of the tokens deposited since
        # a different token can be withdrawn in comparison to the
        # one deposited.
        if (
            event.counterparty in PROTOCOLS_WITH_SPECIAL_POOLS and
            action_type == 'withdrawal'
        ):
            self.total_value_deposited[event.asset] -= Balance(
                amount=event.balance.amount,
            )
        elif (
            event.counterparty in PROTOCOLS_WITH_SPECIAL_POOLS and
            action_type == 'deposit'
        ):
            self.total_value_deposited[event.asset] += Balance(
                amount=event.balance.amount,
            )

        for idx in range(events_to_consume):
            next_event = next(other_events, None)
            if next_event is None:
                log.debug(
                    f'Could not consume {action_type} event nr. {idx} for {event.counterparty} '
                    f'receive event with identifier {event.serialized_event_identifier}',
                )
                return

            if next_event.balance.amount == ZERO:
                log.debug(
                    f'Skipping {next_event.counterparty} {action_type} event '
                    f'{event.serialized_event_identifier} due to zero balance...',
                )
                continue

            usd_price, usd_value = self._query_historical_price(pot=pot, event=next_event)
            if action_type == 'deposit':
                if next_event.counterparty in PROTOCOLS_WITH_SPECIAL_POOLS:
                    self.total_value_deposited[event.asset] += Balance(usd_value=usd_value)
                else:
                    # balancer protocol issues refund when the amount deposited is
                    # more than enough. These refunds should be deducted from the
                    # initial amount deposited to ensure accurate accounting.
                    balance = Balance(amount=next_event.balance.amount, usd_value=usd_value)
                    if (
                        next_event.event_type == HistoryEventType.RECEIVE and
                        next_event.event_subtype == HistoryEventSubType.REMOVE_ASSET
                    ):
                        self.total_value_deposited[next_event.asset] -= balance
                    else:
                        self.total_value_deposited[next_event.asset] += balance
            else:  # can only be withdrawal
                pool_token_event = event if event.counterparty in PROTOCOLS_WITH_SPECIAL_POOLS else None  # noqa: E501
                self._calculate_pnl(
                    pot=pot,
                    event=next_event,
                    pool_token_event=pool_token_event,
                    usd_price=usd_price,
                    usd_value=usd_value,
                )

            self._add_asset_change(
                pot=pot,
                method=asset_change_method,
                event=next_event,
            )

    @staticmethod
    def _query_historical_price(event: 'EvmEvent', pot: 'AccountingPot') -> tuple[Price, FVal]:
        """Queries historical USD price for an asset.

        Returns a tuple of usd_price & usd_value.
        If price is not found, it is added to the pot `missing_prices` set.
        """
        try:
            usd_price = PriceHistorian().query_historical_price(
                from_asset=event.asset,
                to_asset=A_USD,
                timestamp=ts_ms_to_sec(event.timestamp),
            )
            usd_value = usd_price * event.balance.amount
        except NoPriceForGivenTimestamp as e:
            usd_price, usd_value = Price(ZERO), ZERO
            pot.cost_basis.missing_prices.add(MissingPrice(
                from_asset=e.from_asset,
                to_asset=e.to_asset,
                time=e.time,
                rate_limited=e.rate_limited,
            ))

        return usd_price, usd_value

    def _calculate_pnl(
            self,
            pot: 'AccountingPot',
            event: 'EvmEvent',
            usd_price: Price,
            usd_value: FVal,
            pool_token_event: Optional['EvmEvent'] = None,
    ) -> None:
        """Checks if the withdrawal event in a pool product causes a profit/loss.

        `pool_token_event` represents the return/receive event of the LP token.
        This is only used for Curve.

        For curve, the PnL is recorded in USD
        Other protocols, the PnL is recorded in the token withdrawn.
        """
        amount_withdrawn = ZERO if pool_token_event is not None else event.balance.amount  # noqa: E501
        asset = pool_token_event.asset if pool_token_event is not None else event.asset
        self.total_value_deposited[asset] -= Balance(
            amount=amount_withdrawn,
            usd_value=usd_value,
        )

        if self.total_value_deposited[asset].amount <= ZERO > self.total_value_deposited[asset].usd_value:  # noqa: E501
            if pool_token_event is not None:
                profit = abs(self.total_value_deposited[asset].usd_value)
                profit_asset = A_USD.resolve_to_asset_with_symbol()
            else:
                profit = abs(self.total_value_deposited[asset].usd_value) / usd_price
                profit_asset = event.asset.resolve_to_asset_with_symbol()

            crypto_asset = event.asset.resolve_to_crypto_asset()
            pot.add_acquisition(
                event_type=AccountingEventType.TRANSACTION_EVENT,
                location=event.location,
                notes=f'Gained {profit} {profit_asset.symbol} from withdrawing {event.balance.amount} {crypto_asset.symbol} from {event.counterparty} pool',  # noqa: E501
                timestamp=event.get_timestamp_in_sec(),
                asset=profit_asset,
                amount=profit,
                extra_data={'tx_hash': event.serialized_event_identifier},
                taxable=True,
            )
            self.total_value_deposited[asset] = Balance()
        elif self.total_value_deposited[asset].amount <= ZERO < self.total_value_deposited[asset].usd_value:  # noqa: E501
            if pool_token_event is not None:
                loss = self.total_value_deposited[asset].usd_value
                loss_asset = A_USD.resolve_to_asset_with_symbol()
            else:
                loss = self.total_value_deposited[asset].usd_value / usd_price
                loss_asset = event.asset.resolve_to_asset_with_symbol()

            crypto_asset = event.asset.resolve_to_crypto_asset()
            pot.add_acquisition(
                event_type=AccountingEventType.TRANSACTION_EVENT,
                location=event.location,
                notes=f'Lost {loss} {loss_asset.symbol} from withdrawing {event.balance.amount} {crypto_asset.symbol} from {event.counterparty} pool',  # noqa: E501
                timestamp=event.get_timestamp_in_sec(),
                asset=loss_asset,
                amount=loss,
                extra_data={'tx_hash': event.serialized_event_identifier},
                taxable=True,
            )
            self.total_value_deposited[asset] = Balance()

    def _add_asset_change(
            self,
            pot: 'AccountingPot',
            method: Literal['spend', 'acquisition'],
            event: 'EvmEvent',
    ) -> None:
        pot.add_asset_change_event(
            method=method,
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes=event.notes if event.notes else '',
            location=event.location,
            timestamp=event.get_timestamp_in_sec(),
            asset=event.asset,
            amount=event.balance.amount,
            taxable=False,  # Deposits and withdrawals are not taxable
            count_entire_amount_spend=False,
            count_cost_basis_pnl=False,
            extra_data={'tx_hash': event.serialized_event_identifier},
        )
