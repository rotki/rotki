import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import time
import json
import requests
from datetime import datetime

import yfinance as yf

from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKeyOptionalDB
from rotkehlchen.fval import FVal
from rotkehlchen.interfaces import HistoricalPriceOracleWithCoinListInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ExternalService, Price, Timestamp
from rotkehlchen.utils.misc import timestamp_to_date, ts_now
from rotkehlchen.utils.mixins.penalizable_oracle import PenalizablePriceOracleMixin

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.assets.asset import CustomAsset

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
        # Add a simple in-memory cache for recent stock prices to reduce API calls
        self._price_cache = {}
        self._price_cache_time = {}
        self._price_cache_duration = 300  # Cache for 5 minutes

    def _get_ticker_data(self, ticker: str) -> Any:
        """Get ticker data from Yahoo Finance
        
        May raise:
        - RemoteError if there is an error with reaching Yahoo Finance
        """
        try:
            # Add retry logic for rate limiting
            retry_count = 0
            max_retries = 3
            backoff_time = 2  # Initial backoff in seconds
            
            while True:
                try:
                    ticker_data = yf.Ticker(ticker)
                    return ticker_data
                except Exception as retry_error:
                    if "Too Many Requests" in str(retry_error) and retry_count < max_retries:
                        retry_count += 1
                        wait_time = backoff_time * (2 ** (retry_count - 1))  # Exponential backoff
                        log.warning(
                            f"Yahoo Finance rate limited, retrying in {wait_time} seconds",
                            retry=retry_count,
                            ticker=ticker,
                        )
                        time.sleep(wait_time)
                        continue
                    # If not a rate limiting issue or max retries reached, re-raise
                    raise
        except Exception as e:
            log.error(
                f'Yahoo Finance API request for {ticker} failed due to: {str(e)}',
            )
            raise RemoteError(f'Yahoo Finance API request failed: {str(e)}') from e

    def _extract_ticker_from_asset(self, asset: AssetWithOracles) -> str:
        """Extract a usable ticker symbol from an asset for Yahoo Finance API
        
        Tries multiple approaches to get a valid ticker symbol.
        
        Returns:
            A ticker symbol to use with Yahoo Finance
            
        Raises:
            UnsupportedAsset if no usable ticker can be determined
        """
        log.debug(f"Extracting Yahoo Finance ticker for asset: {asset.identifier}")
        
        # First check if this is a custom asset with stock/etf type
        custom_asset_type = getattr(asset, 'custom_asset_type', None)
        if custom_asset_type and custom_asset_type.lower() in ('stock', 'etf'):
            # Look for ticker in notes (format "ticker: XXX")
            notes = getattr(asset, 'notes', '')
            if notes and 'ticker:' in notes.lower():
                ticker = notes.lower().split('ticker:')[1].strip().split()[0].upper()
                log.debug(f"Extracted ticker {ticker} from asset notes")
                return ticker
                
            # For custom assets, try to use symbol directly
            symbol = getattr(asset, 'symbol', None)
            if symbol:
                log.debug(f"Using asset symbol as ticker: {symbol}")
                return symbol
                
            # As a fallback for custom assets, use name but remove common suffixes
            name = getattr(asset, 'name', '').upper()
            if name:
                # Remove common company name suffixes
                for suffix in (' INC', ' CORP', ' LTD', ' CO', ' GROUP', ' HOLDINGS', ' PLC'):
                    if name.endswith(suffix):
                        name = name[:-len(suffix)]
                log.debug(f"Using cleaned asset name as ticker: {name}")
                return name.strip()
        
        # Check if we have a dedicated yahoo_finance attribute
        yahoo_finance = getattr(asset, 'yahoo_finance', None)
        if yahoo_finance:
            log.debug(f"Using dedicated yahoo_finance attribute: {yahoo_finance}")
            return yahoo_finance
            
        # Use symbol as fallback
        symbol = getattr(asset, 'symbol', None)
        if not symbol:
            raise UnsupportedAsset(f"{asset.identifier} has no symbol for Yahoo Finance")
            
        log.debug(f"Using asset symbol as ticker: {symbol}")
        return symbol

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
        log.debug(f"Yahoo Finance oracle querying prices for {len(from_assets)} assets to {to_symbol}")
        
        for from_asset in from_assets:
            try:
                log.debug(f"Processing asset: {from_asset.identifier} (name: {getattr(from_asset, 'name', 'unknown')})")
                
                # Check if this is a CustomAsset (for stocks/ETFs)
                from rotkehlchen.assets.asset import CustomAsset
                from rotkehlchen.assets.types import AssetType
                
                if hasattr(from_asset, 'asset_type') and from_asset.asset_type == AssetType.CUSTOM_ASSET:
                    try:
                        custom_asset = from_asset.resolve()  # This should return a CustomAsset
                        if isinstance(custom_asset, CustomAsset):
                            price = self.query_custom_asset_price(custom_asset, to_symbol)
                            if price != ZERO_PRICE:
                                log.debug(
                                    f"Got price for custom asset from Yahoo Finance",
                                    asset=from_asset.identifier,
                                    price=price,
                                )
                                prices[from_asset] = price
                                continue
                    except Exception as e:
                        log.warning(
                            f"Failed to get custom asset price from Yahoo Finance",
                            asset=from_asset.identifier,
                            error=str(e),
                        )
                
                # Get ticker symbol for this asset
                yahoo_symbol = None
                
                # Try to get the yahoo_finance attribute if it exists
                if hasattr(from_asset, 'yahoo_finance') and from_asset.yahoo_finance:
                    yahoo_symbol = from_asset.yahoo_finance
                    log.debug(f"Using yahoo_finance attribute: {yahoo_symbol}")
                else:
                    # Try standard to_yahoo_finance method 
                    try:
                        yahoo_symbol = from_asset.to_yahoo_finance()
                        log.debug(f"Got symbol from to_yahoo_finance(): {yahoo_symbol}")
                    except (UnsupportedAsset, AttributeError) as e:
                        log.debug(f"Asset doesn't support Yahoo Finance: {str(e)}")
                        # Asset doesn't support Yahoo Finance
                        continue
                
                # We have a symbol, now query price directly using our reliable method
                log.debug(f"Using direct API to query Yahoo Finance for {yahoo_symbol}")
                price = self.get_direct_ticker_price(yahoo_symbol)
                
                if price != ZERO_PRICE:
                    log.info(
                        f"Successfully got price from Yahoo Finance direct API",
                        asset=from_asset.identifier,
                        symbol=yahoo_symbol,
                        price=price
                    )
                    prices[from_asset] = price
                else:
                    log.warning(
                        f"Failed to get price from Yahoo Finance direct API",
                        asset=from_asset.identifier,
                        symbol=yahoo_symbol
                    )
                
            except Exception as e:
                log.exception(
                    'Error processing asset with Yahoo Finance',
                    asset=from_asset.identifier,
                    error=str(e),
                )
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
            
        # Can handle queries for assets that are supported by Yahoo Finance
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
            # we can expand on this list if needed by including more common symbols here
        }
        
        # Cache the minimal list
        self.cache_coinlist(data)
        
        return data

    def query_custom_asset_price(self, custom_asset: 'CustomAsset', to_currency: str) -> Price:
        """Special method to query prices for custom assets of type 'stock' or 'etf'.
        
        This method extracts the ticker from custom asset notes and queries Yahoo Finance.
        
        Args:
            custom_asset: The custom asset to query
            to_currency: Currency code to convert price to (e.g., 'USD')
            
        Returns:
            The price of the stock/ETF or ZERO_PRICE if not found
            
        May raise:
            RemoteError: If there's an issue contacting Yahoo Finance
        """
        log.info(
            f"Attempting to query custom asset price via Yahoo Finance",
            asset=custom_asset.identifier,
            name=getattr(custom_asset, 'name', 'unknown'),
            asset_type=getattr(custom_asset, 'custom_asset_type', 'unknown'),
            notes=getattr(custom_asset, 'notes', 'none')
        )
        
        if not hasattr(custom_asset, 'custom_asset_type') or custom_asset.custom_asset_type.lower() not in ('stock', 'etf'):
            log.debug(
                f"Custom asset is not stock/ETF type",
                asset=custom_asset.identifier,
                type=getattr(custom_asset, 'custom_asset_type', 'none')
            )
            return ZERO_PRICE
            
        if not hasattr(custom_asset, 'notes') or not custom_asset.notes:
            log.debug(
                f"Custom asset has no notes (needed for ticker)",
                asset=custom_asset.identifier
            )
            return ZERO_PRICE
            
        # Try to extract ticker - look for both lowercase and uppercase "ticker:"
        notes = custom_asset.notes
        ticker = None
        
        # Check for "ticker:" format (case insensitive)
        if 'ticker:' in notes.lower():
            parts = notes.lower().split('ticker:')
            ticker_part = parts[1].strip()
            ticker = ticker_part.split()[0].upper() if ' ' in ticker_part else ticker_part.upper()
        # Check for direct ticker format (e.g., "AAPL")
        elif len(notes.strip().split()) == 1 and notes.strip().isupper():
            ticker = notes.strip()
            log.debug(
                f"Using notes directly as ticker",
                asset=custom_asset.identifier,
                ticker=ticker
            )
        
        # If no ticker found, try to use the name as a fallback
        if not ticker and hasattr(custom_asset, 'name'):
            name = custom_asset.name
            # If name looks like a ticker (all caps, no spaces, reasonable length)
            if name.isupper() and ' ' not in name and len(name) < 6:
                ticker = name
                log.debug(
                    f"Using name as ticker (looks like a ticker)",
                    asset=custom_asset.identifier,
                    name=name
                )
            else:
                # Try to extract ticker-like part from name (e.g., "Apple Inc (AAPL)")
                if '(' in name and ')' in name:
                    potential_ticker = name.split('(')[1].split(')')[0].strip()
                    if potential_ticker.isupper() and ' ' not in potential_ticker:
                        ticker = potential_ticker
                        log.debug(
                            f"Extracted ticker from name parentheses",
                            asset=custom_asset.identifier,
                            name=name,
                            ticker=ticker
                        )
        
        if not ticker:
            log.warning(
                f"Could not extract ticker from custom asset",
                asset=custom_asset.identifier
            )
            return ZERO_PRICE
            
        log.info(
            f"Extracted ticker symbol from custom asset",
            asset=custom_asset.identifier,
            name=getattr(custom_asset, 'name', 'unknown'),
            ticker=ticker
        )
        
        # Use our more reliable direct API method
        log.info(f"Using direct API method to query Yahoo Finance for ticker: {ticker}")
        price = self.get_direct_ticker_price(ticker)
        
        if price != ZERO_PRICE:
            log.info(
                f'Successfully got price from Yahoo Finance',
                asset=custom_asset.identifier,
                ticker=ticker,
                price=price,
            )
        else:
            log.warning(
                f'Failed to get price from Yahoo Finance',
                asset=custom_asset.identifier,
                ticker=ticker,
            )
            
        return price

    def test_ticker_lookup(self, ticker: str) -> None:
        """Test method for direct debugging of Yahoo Finance price lookup.
        
        This prints extensive debugging information about the ticker lookup process.
        """
        print("\n==================== YAHOO FINANCE TEST ====================")
        print(f"Testing ticker lookup for: {ticker}")
        
        try:
            print(f"Calling _get_ticker_data for {ticker}...")
            ticker_data = self._get_ticker_data(ticker)
            
            print(f"Ticker data object type: {type(ticker_data)}")
            
            if hasattr(ticker_data, 'info'):
                print("\nTicker info data:")
                info = ticker_data.info
                for key in ['regularMarketPrice', 'currentPrice', 'bid', 'ask', 'shortName', 'longName']:
                    if key in info:
                        print(f"  {key}: {info[key]}")
                
                price = info.get('regularMarketPrice')
                if price:
                    print(f"\nFOUND PRICE: {price}")
                else:
                    print("\nNO PRICE FOUND in regularMarketPrice")
                    
                # Try alternative price fields
                for field in ['currentPrice', 'bid', 'ask', 'previousClose']:
                    if field in info and info[field]:
                        print(f"Alternative price from {field}: {info[field]}")
            else:
                print("Ticker data has no 'info' attribute")
                
            # Try direct history method
            print("\nTrying history() method...")
            history = ticker_data.history(period="1d")
            print(f"History data shape: {history.shape}")
            if not history.empty:
                print(f"Latest close price from history: {history['Close'].iloc[-1]}")
                
        except Exception as e:
            print(f"ERROR in Yahoo Finance lookup: {str(e)}")
            import traceback
            print(f"Exception details:\n{traceback.format_exc()}")
            
        print("==================== TEST COMPLETE ====================\n")

    def get_direct_ticker_price(self, ticker: str) -> Price:
        """Get stock price directly from Yahoo Finance API using requests library.
        
        This method is more reliable than using yfinance library for simple price lookups,
        especially when dealing with rate limiting.
        
        Args:
            ticker: The stock/ETF ticker symbol
            
        Returns:
            The price of the stock/ETF or ZERO_PRICE if not found
            
        May raise:
            RemoteError: If there's an issue contacting Yahoo Finance API
        """
        # Check cache first to avoid unnecessary API calls
        current_time = ts_now()
        if ticker in self._price_cache and (current_time - self._price_cache_time.get(ticker, 0)) < self._price_cache_duration:
            cached_price = self._price_cache[ticker]
            log.debug(
                f"Using cached price for {ticker}",
                ticker=ticker,
                price=cached_price,
                cache_age=current_time - self._price_cache_time.get(ticker, 0)
            )
            return cached_price
            
        try:
            log.debug(f"Requesting direct price data for {ticker}")
            
            # Add retry logic for rate limiting
            retry_count = 0
            max_retries = 3
            backoff_time = 2  # Initial backoff in seconds
            
            # Introduce a small artificial delay to avoid rate limiting when querying multiple assets
            time.sleep(0.5)
            
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            while True:
                try:
                    log.info(f"Sending request to Yahoo Finance API for ticker: {ticker}")
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    if response.status_code == 429:  # Too Many Requests
                        if retry_count >= max_retries:
                            log.warning(
                                f"Yahoo Finance rate limit reached after {retry_count} retries",
                                ticker=ticker
                            )
                            break
                            
                        retry_count += 1
                        wait_time = backoff_time * (2 ** (retry_count - 1))
                        log.warning(
                            f"Yahoo Finance rate limited, retrying in {wait_time} seconds",
                            retry=retry_count,
                            ticker=ticker,
                        )
                        time.sleep(wait_time)
                        continue
                        
                    if response.status_code != 200:
                        log.warning(
                            f"Yahoo Finance API returned non-200 status code: {response.status_code}",
                            ticker=ticker,
                            status=response.status_code
                        )
                        break
                    
                    # Debug response
                    log.debug(f"Received response from Yahoo Finance API for {ticker}")
                    
                    data = response.json()
                    
                    # Extract price from chart data
                    if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
                        result = data['chart']['result'][0]
                        
                        # Extract metadata
                        meta = result.get('meta', {})
                        
                        # Get the latest price
                        if 'regularMarketPrice' in meta:
                            price_float = meta['regularMarketPrice']
                            currency = meta.get('currency', 'Unknown')
                            
                            # Debug the price we found
                            log.debug(f"Found price for {ticker}: {price_float} {currency}")
                            
                            # Convert to FVal first to ensure correct type
                            price_fval = FVal(price_float)
                            
                            log.info(
                                f"Successfully fetched price from Yahoo Finance API",
                                ticker=ticker,
                                price=price_fval,
                                currency=currency
                            )
                            
                            price = Price(price_fval)
                            
                            # Update cache
                            self._price_cache[ticker] = price
                            self._price_cache_time[ticker] = current_time
                            
                            return price
                    
                    # If we reached here, JSON didn't contain expected data
                    log.warning(
                        f"Yahoo Finance API response didn't contain expected price data",
                        ticker=ticker
                    )
                    break
                    
                except requests.RequestException as e:
                    if retry_count >= max_retries:
                        log.warning(
                            f"Yahoo Finance request error after {retry_count} retries",
                            ticker=ticker,
                            error=str(e)
                        )
                        break
                        
                    retry_count += 1
                    wait_time = backoff_time * (2 ** (retry_count - 1))
                    log.warning(
                        f"Yahoo Finance request error, retrying in {wait_time} seconds",
                        retry=retry_count,
                        ticker=ticker,
                        error=str(e)
                    )
                    time.sleep(wait_time)
                    
            return ZERO_PRICE
                
        except Exception as e:
            log.error(
                f"Error fetching direct price from Yahoo Finance",
                ticker=ticker,
                error=str(e)
            )
            return ZERO_PRICE
