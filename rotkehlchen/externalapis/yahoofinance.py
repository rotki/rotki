import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import yfinance as yf

from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKeyOptionalDB
from rotkehlchen.interfaces import HistoricalPriceOracleWithCoinListInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ExternalService, Price, Timestamp
from rotkehlchen.utils.misc import timestamp_to_date, ts_now
from rotkehlchen.utils.mixins.penalizable_oracle import PenalizablePriceOracleMixin

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class YahooFinance(
        ExternalServiceWithApiKeyOptionalDB,
        HistoricalPriceOracleWithCoinListInterface,
        PenalizablePriceOracleMixin,
):
    """Yahoo Finance price oracle implementation"""

    def __init__(self, database: 'Optional[DBHandler]') -> None:
        ExternalServiceWithApiKeyOptionalDB.__init__(
            self,
            database=database,
            service_name=ExternalService.YAHOO_FINANCE,
        )
        HistoricalPriceOracleWithCoinListInterface.__init__(self, oracle_name='yahoo finance')
        PenalizablePriceOracleMixin.__init__(self)
        self.db: 'Optional[DBHandler]' = database  # type: ignore  # "solve" the self.db discrepancy

    def _get_ticker_data(self, ticker: str) -> Any:
        """Get ticker data from Yahoo Finance
        
        May raise:
        - RemoteError if there is an error with reaching Yahoo Finance
        """
        try:
            ticker_data = yf.Ticker(ticker)
            return ticker_data
        except Exception as e:
            log.error(
                f'Yahoo Finance API request for {ticker} failed due to: {str(e)}',
            )
            raise RemoteError(f'Yahoo Finance API request failed: {str(e)}') from e

    def query_multiple_current_prices(
            self,
            from_assets: List[AssetWithOracles],
            to_asset: AssetWithOracles,
    ) -> Dict[AssetWithOracles, Price]:
        """Query current prices for multiple assets from Yahoo Finance
        
        Returns a dict mapping assets to prices found. Assets for which a price was not found
        are not included in the dict.
        
        May raise:
        - RemoteError if there is a problem querying Yahoo Finance
        """
        prices: Dict[AssetWithOracles, Price] = {}
        
        # Yahoo Finance is primarily for stocks and ETFs, typically in USD
        # If to_asset is not USD, we might need additional conversion
        to_symbol = to_asset.symbol.upper()
        
        for from_asset in from_assets:
            try:
                yahoo_symbol = from_asset.to_yahoo_finance()
                
                # Add currency if needed (for non-USD requests)
                if to_symbol != 'USD':
                    yahoo_symbol = f"{yahoo_symbol}{to_symbol}=X"
                
                ticker_data = self._get_ticker_data(yahoo_symbol)
                
                # Try to get the last price
                last_price = ticker_data.info.get('regularMarketPrice')
                if last_price is not None and last_price > 0:
                    prices[from_asset] = Price(last_price)
                    log.debug(
                        f'Got Yahoo Finance price',
                        from_asset=from_asset.identifier,
                        to_asset=to_asset.identifier,
                        price=last_price,
                    )
            except (UnsupportedAsset, RemoteError) as e:
                log.debug(
                    f'Failed to get Yahoo Finance price',
                    from_asset=from_asset.identifier,
                    to_asset=to_asset.identifier,
                    error=str(e),
                )
                # Skip assets that aren't supported or have errors
                continue
                
        return prices
        
    def query_current_price(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
    ) -> Price:
        """Query current price from Yahoo Finance
        
        Returns the asset price or ZERO_PRICE if no price is found.
        """
        return self.query_multiple_current_prices(
            from_assets=[from_asset],
            to_asset=to_asset,
        ).get(from_asset, ZERO_PRICE)

    def can_query_history(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
            seconds: Optional[int] = None,
    ) -> bool:
        """Check if we can query historical data
        
        Yahoo Finance has historical data for most stocks and ETFs
        """
        if self.is_penalized():
            return False
            
        # Yahoo Finance typically has data up to 5-10 years back for most assets
        # For simplicity, we'll assume it can handle queries
        return True

    def query_historical_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        """Query historical price from Yahoo Finance
        
        May raise:
        - PriceQueryUnsupportedAsset if either from_asset or to_asset are not supported
        - NoPriceForGivenTimestamp if no price is found for the given timestamp
        """
        try:
            from_asset_with_oracles = from_asset.resolve_to_asset_with_oracles()
            to_asset_with_oracles = to_asset.resolve_to_asset_with_oracles()
        except UnknownAsset as e:
            raise PriceQueryUnsupportedAsset(e.identifier) from e
            
        # Get the Yahoo Finance symbol
        try:
            yahoo_symbol = from_asset_with_oracles.to_yahoo_finance()
        except UnsupportedAsset as e:
            log.warning(
                f'Tried to query Yahoo Finance historical price from {from_asset.identifier} '
                f'to {to_asset.identifier}, but from_asset is not supported in Yahoo Finance',
            )
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
            ) from e
            
        # Add currency if needed (for non-USD requests)
        to_symbol = to_asset_with_oracles.symbol.upper()
        if to_symbol != 'USD':
            yahoo_symbol = f"{yahoo_symbol}{to_symbol}=X"
            
        # Get the date in the format Yahoo Finance expects
        date_str = timestamp_to_date(timestamp, formatstr='%Y-%m-%d')
        
        try:
            # Get historical data spanning a small window around the requested date
            # Using a 10-day window to catch any market holidays or weekends
            start_date = timestamp_to_date(timestamp - (5 * DAY_IN_SECONDS), formatstr='%Y-%m-%d')
            end_date = timestamp_to_date(timestamp + (5 * DAY_IN_SECONDS), formatstr='%Y-%m-%d')
            
            ticker_data = self._get_ticker_data(yahoo_symbol)
            hist_data = ticker_data.history(start=start_date, end=end_date)
            
            if hist_data.empty:
                log.warning(
                    f'No historical data from Yahoo Finance for {yahoo_symbol} '
                    f'around {date_str}',
                )
                raise NoPriceForGivenTimestamp(
                    from_asset=from_asset,
                    to_asset=to_asset,
                    time=timestamp,
                )
                
            # Find the closest date to our target date
            # Yahoo Finance doesn't have prices for weekends and holidays
            closest_date = None
            min_diff = float('inf')
            
            for date_index in hist_data.index:
                date_ts = Timestamp(date_index.timestamp())
                diff = abs(date_ts - timestamp)
                
                if diff < min_diff:
                    min_diff = diff
                    closest_date = date_index
                    
            if closest_date is not None:
                # Use the closing price for the closest date
                price_value = hist_data.loc[closest_date]['Close']
                return Price(price_value)
                
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
            )
            
        except RemoteError as e:
            log.warning(
                f'Failed to query Yahoo Finance historical price due to: {str(e)}',
                from_asset=from_asset.identifier,
                to_asset=to_asset.identifier,
                timestamp=timestamp,
            )
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
            ) from e

    def all_coins(self) -> Dict[str, Dict[str, Any]]:
        """Yahoo Finance doesn't have a comprehensive list of all available symbols.
        
        This is more applicable for crypto oracles like Coingecko.
        For Yahoo Finance, we'll return a minimal implementation.
        
        May raise:
        - RemoteError if there is an error with reaching Yahoo Finance
        """
        # Check if we have a cached list
        if (data := self.maybe_get_cached_coinlist(considered_recent_secs=DAY_IN_SECONDS)) is not None:
            return data
            
        # Since Yahoo Finance doesn't provide a comprehensive list,
        # we'll just return a minimal structure
        data: Dict[str, Dict[str, Any]] = {
            # Common stock indices
            'SPY': {'symbol': 'SPY', 'name': 'SPDR S&P 500 ETF Trust'},
            'QQQ': {'symbol': 'QQQ', 'name': 'Invesco QQQ Trust'},
            'DIA': {'symbol': 'DIA', 'name': 'SPDR Dow Jones Industrial Average ETF'},
            # We could add more common symbols here
        }
        
        # Cache the minimal list
        self.cache_coinlist(data)
        
        return data
