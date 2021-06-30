import logging
from typing import List, Optional

from rotkehlchen.accounting.cost_basis import CostBasisCalculator
from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.accounting.structures import DefiEvent
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import BCH_BSV_FORK_TS, BTC_BCH_FORK_TS, ETH_DAO_FORK_TS, ZERO
from rotkehlchen.constants.assets import A_BCH, A_BSV, A_BTC, A_ETC, A_ETH
from rotkehlchen.csv_exporter import CSVExporter
from rotkehlchen.errors import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import PriceHistorian, get_balance_asset_rate_at_time_zero_if_error
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import Fee, Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import taxable_gain_for_sell, timestamp_to_date

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class TaxableEvents():

    def __init__(
            self,
            csv_exporter: CSVExporter,
            profit_currency: Asset,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.csv_exporter = csv_exporter
        self.msg_aggregator = msg_aggregator
        self.profit_currency = profit_currency
        # later customized via accountant._customize()
        self.taxable_ledger_actions: List[LedgerActionType] = []
        self.cost_basis = CostBasisCalculator(csv_exporter, profit_currency, msg_aggregator)

        # If this flag is True when your asset is being forcefully sold as a
        # loan/margin settlement then profit/loss is also calculated before the entire
        # amount is taken as a loss
        self.count_profit_for_settlements = False

    def reset(self, profit_currency: Asset, start_ts: Timestamp, end_ts: Timestamp) -> None:
        self.cost_basis.reset(profit_currency)
        self.query_start_ts = start_ts
        self.query_end_ts = end_ts
        self.general_trade_profit_loss = ZERO
        self.taxable_trade_profit_loss = ZERO
        self.loan_profit = ZERO
        self.defi_profit_loss = ZERO
        self.settlement_losses = ZERO
        self.margin_positions_profit_loss = ZERO
        self.defi_profit_loss = ZERO
        self.ledger_actions_profit_loss = ZERO

    @property
    def include_crypto2crypto(self) -> Optional[bool]:
        return self._include_crypto2crypto

    @include_crypto2crypto.setter
    def include_crypto2crypto(self, value: Optional[bool]) -> None:
        self._include_crypto2crypto = value

    @property
    def taxfree_after_period(self) -> Optional[int]:
        return self.cost_basis._taxfree_after_period

    @taxfree_after_period.setter
    def taxfree_after_period(self, value: Optional[int]) -> None:
        self.cost_basis.taxfree_after_period = value

    @property
    def account_for_assets_movements(self) -> Optional[bool]:
        return self._account_for_assets_movements

    @account_for_assets_movements.setter
    def account_for_assets_movements(self, value: Optional[bool]) -> None:
        self._account_for_assets_movements = value

    def get_rate_in_profit_currency(self, asset: Asset, timestamp: Timestamp) -> FVal:
        """Get the profit_currency price of asset in the given timestamp

        May raise:
        - PriceQueryUnsupportedAsset if from/to asset is missing from price oracles
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from the price oracle
        - RemoteError if there is a problem reaching the price oracle server
        or with reading the response returned by the server
        """
        if asset == self.profit_currency:
            rate = FVal(1)
        else:
            rate = PriceHistorian().query_historical_price(
                from_asset=asset,
                to_asset=self.profit_currency,
                timestamp=timestamp,
            )
        return rate

    def handle_prefork_asset_buys(
            self,
            location: Location,
            bought_asset: Asset,
            bought_amount: FVal,
            paid_with_asset: Asset,
            trade_rate: FVal,
            fee_in_profit_currency: Fee,
            timestamp: Timestamp,
            is_from_prefork_virtual_buy: bool,
    ) -> None:
        if is_from_prefork_virtual_buy:
            # This way we avoid double counting. For example BTC before BCH/BSV fork
            # adding the BSV twice
            return

        # TODO: Should fee also be taken into account here?
        if bought_asset == A_ETH and timestamp < ETH_DAO_FORK_TS:
            self.add_buy(
                location=location,
                bought_asset=A_ETC,
                bought_amount=bought_amount,
                paid_with_asset=paid_with_asset,
                trade_rate=trade_rate,
                fee_in_profit_currency=fee_in_profit_currency,
                fee_currency=None,
                fee_amount=Fee(ZERO),
                timestamp=timestamp,
                is_virtual=True,
                is_from_prefork_virtual_buy=True,
            )

        if bought_asset == A_BTC and timestamp < BTC_BCH_FORK_TS:
            # Acquiring BTC before the BCH fork provides equal amount of BCH and BSV
            self.add_buy(
                location=location,
                bought_asset=A_BCH,
                bought_amount=bought_amount,
                paid_with_asset=paid_with_asset,
                trade_rate=trade_rate,
                fee_in_profit_currency=fee_in_profit_currency,
                fee_currency=None,
                fee_amount=Fee(ZERO),
                timestamp=timestamp,
                is_virtual=True,
                is_from_prefork_virtual_buy=True,
            )
            self.add_buy(
                location=location,
                bought_asset=A_BSV,
                bought_amount=bought_amount,
                paid_with_asset=paid_with_asset,
                trade_rate=trade_rate,
                fee_in_profit_currency=fee_in_profit_currency,
                fee_currency=None,
                fee_amount=Fee(ZERO),
                timestamp=timestamp,
                is_virtual=True,
                is_from_prefork_virtual_buy=True,
            )

        if bought_asset == A_BCH and timestamp < BCH_BSV_FORK_TS:
            # Acquiring BCH before the BSV fork provides equal amount of BSV
            self.add_buy(
                location=location,
                bought_asset=A_BSV,
                bought_amount=bought_amount,
                paid_with_asset=paid_with_asset,
                trade_rate=trade_rate,
                fee_in_profit_currency=fee_in_profit_currency,
                fee_currency=None,
                fee_amount=Fee(ZERO),
                timestamp=timestamp,
                is_virtual=True,
                is_from_prefork_virtual_buy=True,
            )

    def handle_prefork_asset_sells(
            self, sold_asset: Asset,
            sold_amount: FVal,
            timestamp: Timestamp,
    ) -> None:
        # For now for those don't use inform_user_missing_acquisition since if those hit
        # the preforked asset acquisition data is what's missing so user would getLogger
        # two messages. So as an example one for missing ETH data and one for ETC data
        if sold_asset == A_ETH and timestamp < ETH_DAO_FORK_TS:
            if not self.cost_basis.reduce_asset_amount(asset=A_ETC, amount=sold_amount):
                log.critical(
                    'No documented buy found for ETC (ETH equivalent) before {}'.format(
                        self.csv_exporter.timestamp_to_date(timestamp),
                    ),
                )

        if sold_asset == A_BTC and timestamp < BTC_BCH_FORK_TS:
            if not self.cost_basis.reduce_asset_amount(asset=A_BCH, amount=sold_amount):
                log.critical(
                    'No documented buy found for BCH (BTC equivalent) before {}'.format(
                        self.csv_exporter.timestamp_to_date(timestamp),
                    ),
                )
            if not self.cost_basis.reduce_asset_amount(asset=A_BSV, amount=sold_amount):
                log.critical(
                    'No documented buy found for BSV (BTC equivalent) before {}'.format(
                        self.csv_exporter.timestamp_to_date(timestamp),
                    ),
                )

        if sold_asset == A_BCH and timestamp < BCH_BSV_FORK_TS:
            if not self.cost_basis.reduce_asset_amount(asset=A_BSV, amount=sold_amount):
                log.critical(
                    'No documented buy found for BSV (BCH equivalent) before {}'.format(
                        self.csv_exporter.timestamp_to_date(timestamp),
                    ),
                )

    def add_buy_and_corresponding_sell(
            self,
            location: Location,
            bought_asset: Asset,
            bought_amount: FVal,
            paid_with_asset: Asset,
            trade_rate: FVal,
            fee_in_profit_currency: Fee,
            fee_currency: Optional[Asset],
            fee_amount: Optional[Fee],
            timestamp: Timestamp,
    ) -> None:
        """
        Account for the given buy and the corresponding sell if it's a crypto to crypto

        May raise:
        - PriceQueryUnsupportedAsset if from/to asset is missing from price oracles
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from cryptocompare
        - RemoteError if there is a problem reaching the price oracle server
        or with reading the response returned by the server
        """
        self.add_buy(
            location=location,
            bought_asset=bought_asset,
            bought_amount=bought_amount,
            paid_with_asset=paid_with_asset,
            trade_rate=trade_rate,
            fee_in_profit_currency=fee_in_profit_currency,
            fee_currency=fee_currency,
            fee_amount=fee_amount,
            timestamp=timestamp,
            is_virtual=False,
        )

        if paid_with_asset.is_fiat() or not self.include_crypto2crypto:
            return

        # else you are also selling some other asset to buy the bought asset
        log.debug(
            f'Buying {bought_asset} with {paid_with_asset} also introduces a virtual sell event',
        )
        try:
            bought_asset_rate_in_profit_currency = self.get_rate_in_profit_currency(
                bought_asset,
                timestamp,
            )
        except (NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset):
            bought_asset_rate_in_profit_currency = FVal(-1)

        if bought_asset_rate_in_profit_currency != FVal(-1):
            # The asset bought does not have a price yet
            # Can happen for Token sales, presales e.t.c.
            with_bought_asset_gain = bought_asset_rate_in_profit_currency * bought_amount
            receiving_asset = bought_asset
            receiving_amount = bought_amount
            rate_in_profit_currency = bought_asset_rate_in_profit_currency / trade_rate
            gain_in_profit_currency = with_bought_asset_gain

        sold_amount = trade_rate * bought_amount
        if sold_amount == ZERO:
            logger.error(
                f'Not adding a virtual sell event. Could not calculate it from '
                f'trade_rate * bought_amount = {trade_rate} * {bought_amount}',
            )
            return

        sold_asset_rate_in_profit_currency = self.get_rate_in_profit_currency(
            paid_with_asset,
            timestamp,
        )
        with_sold_asset_gain = sold_asset_rate_in_profit_currency * sold_amount

        # Consider as value of the sell what would give the least profit
        if (bought_asset_rate_in_profit_currency == -1 or
                with_sold_asset_gain < with_bought_asset_gain):
            receiving_asset = self.profit_currency
            receiving_amount = with_sold_asset_gain
            rate_in_profit_currency = sold_asset_rate_in_profit_currency
            gain_in_profit_currency = with_sold_asset_gain

        self.add_sell(
            location=location,
            selling_asset=paid_with_asset,
            selling_amount=sold_amount,
            receiving_asset=receiving_asset,
            receiving_amount=receiving_amount,
            rate_in_profit_currency=rate_in_profit_currency,
            gain_in_profit_currency=gain_in_profit_currency,
            total_fee_in_profit_currency=Fee(ZERO),  # do not pay double fees
            fee_currency=None,
            fee_amount=Fee(ZERO),
            timestamp=timestamp,
            is_virtual=True,
        )

    def add_buy(
            self,
            location: Location,
            bought_asset: Asset,
            bought_amount: FVal,
            paid_with_asset: Asset,
            trade_rate: FVal,
            fee_in_profit_currency: Fee,
            fee_currency: Optional[Asset],
            fee_amount: Optional[Fee],
            timestamp: Timestamp,
            is_virtual: bool = False,
            is_from_prefork_virtual_buy: bool = False,
    ) -> None:
        """
        Account for the given buy

        May raise:
        - PriceQueryUnsupportedAsset if from/to asset is missing from all price oracles
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from cryptocompare
        - RemoteError if there is a problem reaching the price oracle server
        or with reading the response returned by the server
        """
        skip_trade = (
            not self.include_crypto2crypto and
            not bought_asset.is_fiat() and
            not paid_with_asset.is_fiat()
        )
        if skip_trade:
            return

        logger.debug(
            f'Processing buy trade of {bought_asset.identifier} with '
            f'{paid_with_asset.identifier} at {timestamp}',
        )

        paid_with_asset_rate = self.get_rate_in_profit_currency(paid_with_asset, timestamp)
        buy_rate = paid_with_asset_rate * trade_rate

        self.handle_prefork_asset_buys(
            location=location,
            bought_asset=bought_asset,
            bought_amount=bought_amount,
            paid_with_asset=paid_with_asset,
            trade_rate=trade_rate,
            fee_in_profit_currency=fee_in_profit_currency,
            timestamp=timestamp,
            is_from_prefork_virtual_buy=is_from_prefork_virtual_buy,
        )

        gross_cost = bought_amount * buy_rate
        cost_in_profit_currency = gross_cost + fee_in_profit_currency

        self.cost_basis.obtain_asset(
            location=location,
            timestamp=timestamp,
            description='trade',
            asset=bought_asset,
            amount=bought_amount,
            rate=buy_rate,
            fee_in_profit_currency=fee_in_profit_currency,
        )
        if fee_currency is not None and not fee_currency.is_fiat() and fee_amount is not None:
            self.cost_basis.calculate_spend_cost_basis(
                spending_amount=fee_amount,
                spending_asset=fee_currency,
                timestamp=timestamp,
            )

        if timestamp >= self.query_start_ts:
            self.csv_exporter.add_buy(
                location=location,
                bought_asset=bought_asset,
                rate_in_profit_currency=buy_rate,
                fee_cost=fee_in_profit_currency,
                amount=bought_amount,
                cost_in_profit_currency=cost_in_profit_currency,
                paid_with_asset=paid_with_asset,
                paid_with_asset_rate=paid_with_asset_rate,
                paid_with_asset_amount=trade_rate * bought_amount,
                timestamp=timestamp,
                is_virtual=is_virtual,
            )

    def add_sell_and_corresponding_buy(
            self,
            location: Location,
            selling_asset: Asset,
            selling_amount: FVal,
            receiving_asset: Asset,
            receiving_amount: FVal,
            gain_in_profit_currency: FVal,
            total_fee_in_profit_currency: Fee,
            fee_currency: Optional[Asset],
            fee_amount: Optional[Fee],
            trade_rate: FVal,
            rate_in_profit_currency: FVal,
            timestamp: Timestamp,
    ) -> None:
        """
        Account for the given sell and the corresponding buy if it's a crypto to crypto

        Args:
            selling_asset (str): The ticker representation of the asset we sell.
            selling_amount (FVal): The amount of `selling_asset` for sale.
            receiving_asset (str): The ticker representation of the asset we receive
                                   in exchange for `selling_asset`.
            receiving_amount (FVal): The amount of `receiving_asset` we receive.
            gain_in_profit_currency (FVal): This is the amount of `profit_currency` equivalent
                                            we receive after doing this trade. Fees are not counted
                                            in this.
            total_fee_in_profit_currency (FVal): This is the amount of `profit_currency` equivalent
                                                 we pay in fees after doing this trade.
            trade_rate (FVal): How much does 1 unit of `receiving_asset` cost in `selling_asset`
            rate_in_profit_currency (FVal): The equivalent of `trade_rate` in `profit_currency`
            timestamp (int): The timestamp for the trade

        May raise:
        - PriceQueryUnsupportedAsset if from/to asset is missing from price oracles
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from cryptocompare
        - RemoteError if there is a problem reaching the price oracle server
        or with reading the response returned by the server
        """
        self.add_sell(
            location=location,
            selling_asset=selling_asset,
            selling_amount=selling_amount,
            receiving_asset=receiving_asset,
            receiving_amount=receiving_amount,
            gain_in_profit_currency=gain_in_profit_currency,
            total_fee_in_profit_currency=total_fee_in_profit_currency,
            fee_currency=fee_currency,
            fee_amount=fee_amount,
            rate_in_profit_currency=rate_in_profit_currency,
            timestamp=timestamp,
            is_virtual=False,
        )

        if receiving_asset.is_fiat() or not self.include_crypto2crypto:
            return

        log.debug(
            f'Selling {selling_asset} for {receiving_asset} also introduces a virtual buy event',
        )
        # else then you are also buying some other asset through your sell
        assert trade_rate != 0, 'Trade rate should not be zero at this point'
        self.add_buy(
            location=location,
            bought_asset=receiving_asset,
            bought_amount=receiving_amount,
            paid_with_asset=selling_asset,
            trade_rate=1 / trade_rate,
            fee_in_profit_currency=Fee(ZERO),  # do not count fee twice
            fee_currency=None,
            fee_amount=Fee(ZERO),
            timestamp=timestamp,
            is_virtual=True,
        )

    def add_sell(
            self,
            location: Location,
            selling_asset: Asset,
            selling_amount: FVal,
            receiving_asset: Optional[Asset],
            receiving_amount: Optional[FVal],
            gain_in_profit_currency: FVal,
            total_fee_in_profit_currency: Fee,
            fee_currency: Optional[Asset],
            fee_amount: Optional[Fee],
            rate_in_profit_currency: FVal,
            timestamp: Timestamp,
            loan_settlement: bool = False,
            is_virtual: bool = False,
    ) -> None:
        """Account for the given sell action

        May raise:
        - PriceQueryUnsupportedAsset if from/to asset is missing from price oracles
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from cryptocompare
        - RemoteError if there is a problem reaching the price oracle server
        or with reading the response returned by the server
        """
        skip_trade = (
            not self.include_crypto2crypto and
            not selling_asset.is_fiat() and
            receiving_asset and not receiving_asset.is_fiat()
        )
        if skip_trade:
            return

        if selling_amount == ZERO:
            logger.error(
                f'Skipping sell trade of {selling_asset.identifier} for '
                f'{receiving_asset.identifier if receiving_asset else "nothing"} at {timestamp}'
                f' since the selling amount is 0',
            )
            return

        if selling_asset.is_fiat():
            # Should be handled by a virtual buy
            logger.debug(
                f'Skipping sell trade of {selling_asset.identifier} for '
                f'{receiving_asset.identifier if receiving_asset else "nothing"} at {timestamp} '
                f'since selling of FIAT of something will just be treated as a buy.',
            )
            return

        logger.debug(
            f'Processing sell trade of {selling_asset.identifier} for '
            f'{receiving_asset.identifier if receiving_asset else "nothing"} at {timestamp}',
        )

        self.cost_basis.spend_asset(
            location=location,
            timestamp=timestamp,
            asset=selling_asset,
            amount=selling_amount,
            rate=rate_in_profit_currency,
            fee_in_profit_currency=total_fee_in_profit_currency,
            gain_in_profit_currency=gain_in_profit_currency,
        )
        if fee_currency is not None and not fee_currency.is_fiat() and fee_amount is not None:
            self.cost_basis.calculate_spend_cost_basis(
                spending_amount=fee_amount,
                spending_asset=fee_currency,
                timestamp=timestamp,
            )
        self.handle_prefork_asset_sells(selling_asset, selling_amount, timestamp)

        # now search the acquisitions for `paid_with_asset` and calculate profit/loss
        cost_basis_info = self.cost_basis.calculate_spend_cost_basis(
            spending_amount=selling_amount,
            spending_asset=selling_asset,
            timestamp=timestamp,
        )
        general_profit_loss = ZERO
        taxable_profit_loss = ZERO

        # If we don't include crypto2crypto and we sell for crypto, stop here
        if receiving_asset and not receiving_asset.is_fiat() and not self.include_crypto2crypto:
            return

        # calculate profit/loss
        if not loan_settlement or (loan_settlement and self.count_profit_for_settlements):
            taxable_gain = taxable_gain_for_sell(
                taxable_amount=cost_basis_info.taxable_amount,
                rate_in_profit_currency=rate_in_profit_currency,
                total_fee_in_profit_currency=total_fee_in_profit_currency,
                selling_amount=selling_amount,
            )

            total_bought_cost_in_profit_currency = (
                cost_basis_info.taxfree_bought_cost +
                cost_basis_info.taxable_bought_cost +
                total_fee_in_profit_currency
            )
            general_profit_loss = gain_in_profit_currency - total_bought_cost_in_profit_currency
            taxable_profit_loss = taxable_gain - cost_basis_info.taxable_bought_cost

        # should never happen, should be stopped at the main loop
        assert timestamp <= self.query_end_ts, (
            'Trade time > query_end_ts found in adding to sell event'
        )

        # count profit/losses if we are inside the query period
        if timestamp >= self.query_start_ts:
            if loan_settlement:
                # If it's a loan settlement we are charged both the fee and the gain
                settlement_loss = gain_in_profit_currency + total_fee_in_profit_currency
                expected = rate_in_profit_currency * selling_amount + total_fee_in_profit_currency
                msg = (
                    f'Expected settlement loss mismatch. rate_in_profit_currency'
                    f' ({rate_in_profit_currency}) * selling_amount'
                    f' ({selling_amount}) + total_fee_in_profit_currency'
                    f' ({total_fee_in_profit_currency}) != settlement_loss '
                    f'({settlement_loss})'
                )
                assert expected == settlement_loss, msg
                self.settlement_losses += settlement_loss
                log.debug(
                    'Loan Settlement Loss',
                    settlement_loss=settlement_loss,
                    profit_currency=self.profit_currency,
                )
            else:
                log.debug(
                    "After Sell Profit/Loss",
                    taxable_profit_loss=taxable_profit_loss,
                    general_profit_loss=general_profit_loss,
                    profit_currency=self.profit_currency,
                )

            self.general_trade_profit_loss += general_profit_loss
            self.taxable_trade_profit_loss += taxable_profit_loss

            if loan_settlement:
                self.csv_exporter.add_loan_settlement(
                    location=location,
                    asset=selling_asset,
                    amount=selling_amount,
                    rate_in_profit_currency=rate_in_profit_currency,
                    total_fee_in_profit_currency=total_fee_in_profit_currency,
                    timestamp=timestamp,
                    cost_basis_info=cost_basis_info,
                )
            else:
                assert receiving_asset, 'Here receiving asset should have a value'
                self.csv_exporter.add_sell(
                    location=location,
                    selling_asset=selling_asset,
                    rate_in_profit_currency=rate_in_profit_currency,
                    total_fee_in_profit_currency=total_fee_in_profit_currency,
                    gain_in_profit_currency=gain_in_profit_currency,
                    selling_amount=selling_amount,
                    receiving_asset=receiving_asset,
                    receiving_amount=receiving_amount,
                    receiving_asset_rate_in_profit_currency=self.get_rate_in_profit_currency(
                        receiving_asset,
                        timestamp,
                    ),
                    taxable_amount=cost_basis_info.taxable_amount,
                    taxable_bought_cost=cost_basis_info.taxable_bought_cost,
                    timestamp=timestamp,
                    cost_basis_info=cost_basis_info,
                    is_virtual=is_virtual,
                    total_bought_cost=total_bought_cost_in_profit_currency,
                )

    def add_loan_gain(
            self,
            location: Location,
            gained_asset: Asset,
            gained_amount: FVal,
            fee_in_asset: Fee,
            lent_amount: FVal,
            open_time: Timestamp,
            close_time: Timestamp,
    ) -> None:
        """Account for gains from the given loan
        May raise:
        - PriceQueryUnsupportedAsset if from/to asset is missing from price oracles
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from the external service.
        - RemoteError if there is a problem reaching the price oracle server
        or with reading the response returned by the server
        """

        timestamp = close_time
        rate = self.get_rate_in_profit_currency(gained_asset, timestamp)

        net_gain_amount = gained_amount - fee_in_asset
        gain_in_profit_currency = net_gain_amount * rate
        assert gain_in_profit_currency > 0, "Loan profit is negative. Should never happen"
        self.cost_basis.obtain_asset(
            location=location,
            timestamp=timestamp,
            description='loan gain',
            asset=gained_asset,
            amount=net_gain_amount,
            rate=rate,
            fee_in_profit_currency=ZERO,
        )
        # count profits if we are inside the query period
        if timestamp >= self.query_start_ts:
            log.debug(
                'Accounting for loan profit',
                location=location,
                gained_asset=gained_asset,
                gained_amount=gained_amount,
                gain_in_profit_currency=gain_in_profit_currency,
                lent_amount=lent_amount,
                open_time=open_time,
                close_time=close_time,
            )

            self.loan_profit += gain_in_profit_currency
            self.csv_exporter.add_loan_profit(
                location=location,
                gained_asset=gained_asset,
                gained_amount=gained_amount,
                gain_in_profit_currency=gain_in_profit_currency,
                lent_amount=lent_amount,
                open_time=open_time,
                close_time=close_time,
            )

    def add_margin_position(self, margin: MarginPosition) -> None:
        """Account for the given margin position

        May raise:
        - PriceQueryUnsupportedAsset if from/to asset is missing from price oracles
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from the external service.
        - RemoteError if there is a problem reaching the price oracle server
        or with reading the response returned by the server
        """
        pl_currency_rate = self.get_rate_in_profit_currency(margin.pl_currency, margin.close_time)
        fee_currency_rate = self.get_rate_in_profit_currency(margin.pl_currency, margin.close_time)
        net_gain_loss_in_profit_currency = (
            margin.profit_loss * pl_currency_rate - margin.fee * fee_currency_rate
        )

        # Add or remove to the pl_currency asset
        if margin.profit_loss > 0:
            self.cost_basis.obtain_asset(
                location=margin.location,
                timestamp=margin.close_time,
                description='margin position',
                asset=margin.pl_currency,
                amount=margin.profit_loss,
                rate=pl_currency_rate,
                fee_in_profit_currency=ZERO,
            )
        elif margin.profit_loss < 0:
            result = self.cost_basis.reduce_asset_amount(
                asset=margin.pl_currency,
                amount=-margin.profit_loss,
            )
            if not result:
                log.critical(
                    f'No documented acquisition found for {margin.pl_currency} before '
                    f'{self.csv_exporter.timestamp_to_date(margin.close_time)}',
                )

        # Reduce the fee_currency asset
        result = self.cost_basis.reduce_asset_amount(asset=margin.fee_currency, amount=margin.fee)
        if not result:
            log.critical(
                f'No documented acquisition found for {margin.fee_currency} before '
                f'{timestamp_to_date(margin.close_time, formatstr="%d/%m/%Y %H:%M:%S")}',
            )

        # count profit/loss if we are inside the query period
        if margin.close_time >= self.query_start_ts:
            self.margin_positions_profit_loss += net_gain_loss_in_profit_currency

            log.debug(
                'Accounting for margin position',
                notes=margin.notes,
                gain_loss_asset=margin.pl_currency,
                gain_loss_amount=margin.profit_loss,
                net_gain_loss_in_profit_currency=net_gain_loss_in_profit_currency,
                timestamp=margin.close_time,
            )

            self.csv_exporter.add_margin_position(
                location=margin.location,
                margin_notes=margin.notes,
                gain_loss_asset=margin.pl_currency,
                gain_loss_amount=margin.profit_loss,
                gain_loss_in_profit_currency=net_gain_loss_in_profit_currency,
                timestamp=margin.close_time,
            )

    def add_defi_event(self, event: DefiEvent) -> None:
        event_description = str(event)
        log.debug(
            'Processing DeFi event',
            event=event_description,
        )

        # count cost basis regardless of being in query time range
        if event.count_spent_got_cost_basis:
            if event.got_asset is not None:
                assert event.got_balance is not None, 'got_balance cant be missing for got_asset'
                # With this we use the calculated usd_value to get the usd rate
                rate = get_balance_asset_rate_at_time_zero_if_error(
                    balance=event.got_balance,
                    asset=self.profit_currency,
                    timestamp=event.timestamp,
                    location_hint=event_description,
                    msg_aggregator=self.msg_aggregator,
                )
                # we can also use the commented out code to use oracle query
                # rate = self.get_rate_in_profit_currency(entry.asset, event.timestamp)

                self.cost_basis.obtain_asset(
                    location=Location.BLOCKCHAIN,
                    timestamp=event.timestamp,
                    description=event_description,
                    asset=event.got_asset,
                    amount=event.got_balance.amount,
                    rate=rate,
                    fee_in_profit_currency=ZERO,
                )

            if event.spent_asset is not None:
                assert event.spent_balance is not None, 'spent_balance cant be missing for spent_asset'  # noqa: E501
                result = self.cost_basis.reduce_asset_amount(
                    asset=event.spent_asset,
                    amount=event.spent_balance.amount,
                )
                if not result:
                    log.critical(
                        f'No documented acquisition found for {event.spent_asset} before '
                        f'{self.csv_exporter.timestamp_to_date(event.timestamp)}',
                    )

        elif event.pnl is not None:
            # if we don't count got/spent in cost basis then we should at least count pnl
            for entry in event.pnl:
                if entry.balance.amount > ZERO:
                    # With this we use the calculated usd_value to get the usd rate
                    rate = get_balance_asset_rate_at_time_zero_if_error(
                        balance=entry.balance,
                        asset=self.profit_currency,
                        timestamp=event.timestamp,
                        location_hint=event_description,
                        msg_aggregator=self.msg_aggregator,
                    )
                    # we can also use the commented out code to use oracle query
                    # rate = self.get_rate_in_profit_currency(entry.asset, event.timestamp)
                    self.cost_basis.obtain_asset(
                        location=Location.BLOCKCHAIN,
                        timestamp=event.timestamp,
                        description=event_description,
                        asset=entry.asset,
                        amount=entry.balance.amount,
                        rate=rate,
                        fee_in_profit_currency=ZERO,
                    )
                else:
                    result = self.cost_basis.reduce_asset_amount(
                        asset=entry.asset,
                        amount=-entry.balance.amount,
                    )
                    if not result:
                        log.critical(
                            f'No documented acquisition found for {entry.asset} before '
                            f'{self.csv_exporter.timestamp_to_date(event.timestamp)}',
                        )

        if event.timestamp < self.query_start_ts:
            return

        # now we are within the range. Count profit/loss if any
        profit_loss_list = []
        log.debug(
            'Accounting for DeFi event',
            event=event_description,
        )

        if event.pnl is not None:
            for entry in event.pnl:
                # With this we use the calculated usd_value to get the usd rate
                rate = get_balance_asset_rate_at_time_zero_if_error(
                    balance=entry.balance,
                    asset=self.profit_currency,
                    timestamp=event.timestamp,
                    location_hint=event_description,
                    msg_aggregator=self.msg_aggregator,
                )
                # we can also use the commented out code to use oracle query
                # rate = self.get_rate_in_profit_currency(entry.asset, event.timestamp)

                single_profit_loss = entry.balance.amount * rate
                log.debug(f'Counting profit/loss for {event_description}: {single_profit_loss}')
                profit_loss_list.append(single_profit_loss)
                self.defi_profit_loss += single_profit_loss

        self.csv_exporter.add_defi_event(
            event=event,
            profit_loss_in_profit_currency_list=profit_loss_list,
        )

    def add_ledger_action(self, action: LedgerAction) -> None:
        # should never happen, should be stopped at the main loop
        assert action.timestamp <= self.query_end_ts, (
            'Ledger action time > query_end_ts found in processing'
        )
        # calculate the profit currency rate
        if action.rate is None or action.rate_asset is None:
            rate = self.get_rate_in_profit_currency(action.asset, action.timestamp)
        else:
            if action.rate_asset == self.profit_currency:
                rate = action.rate
            else:
                quote_rate = self.get_rate_in_profit_currency(action.rate_asset, action.timestamp)
                rate = action.rate * quote_rate

        profit_loss = action.amount * rate
        account_for_action = (
            action.timestamp > self.query_start_ts and
            action.action_type in self.taxable_ledger_actions
        )
        log.debug(
            'Processing LedgerAction',
            action=action,
            rate_used=rate,
            account_for_action=account_for_action,
        )
        if account_for_action is False:
            profit_loss = ZERO

        if action.is_profitable():
            self.ledger_actions_profit_loss += profit_loss
            self.cost_basis.obtain_asset(
                location=action.location,
                timestamp=action.timestamp,
                description=f'{str(action.action_type)}',
                asset=action.asset,
                amount=action.amount,
                rate=rate,
                fee_in_profit_currency=ZERO,
            )
        else:
            self.ledger_actions_profit_loss -= profit_loss

            result = self.cost_basis.reduce_asset_amount(
                asset=action.asset,
                amount=action.amount,
            )
            if not result:
                log.critical(
                    f'No documented buy found for {action.asset} before '
                    f'{self.csv_exporter.timestamp_to_date(action.timestamp)}',
                )

        if action.timestamp > self.query_start_ts:
            self.csv_exporter.add_ledger_action(
                action=action,
                profit_loss_in_profit_currency=profit_loss,
            )
