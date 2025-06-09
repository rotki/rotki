"""Async implementation of Coinbase exchange

Provides high-performance async API for Coinbase and Coinbase Pro.
"""
import asyncio
import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Optional
from urllib.parse import urlencode

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.async_exchange import AsyncExchangeInterface
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ApiKey, ApiSecret, Location, Timestamp, TradeType
from rotkehlchen.utils.misc import ts_now_in_ms

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AsyncCoinbase(AsyncExchangeInterface):
    """Async implementation of Coinbase exchange"""
    
    def __init__(self, *args, **kwargs):
        super().__init__('coinbase', Location.COINBASE, *args, **kwargs)
        self.base_url = 'https://api.coinbase.com'
        self.api_version = 'v2'
        
    async def query_balances(self) -> dict[Asset, Balance]:
        """Query all account balances"""
        endpoint = f'/v2/accounts'
        
        # Coinbase uses pagination
        all_balances = {}
        next_uri = endpoint
        
        while next_uri:
            response = await self._api_request_signed('GET', next_uri)
            
            # Process accounts
            for account_data in response.get('data', []):
                balance_data = account_data.get('balance', {})
                amount = FVal(balance_data.get('amount', '0'))
                currency = balance_data.get('currency', '')
                
                if amount > ZERO and currency:
                    try:
                        asset = Asset(currency)
                        # Get USD value from native balance
                        native_balance = account_data.get('native_balance', {})
                        usd_value = FVal(native_balance.get('amount', '0'))
                        
                        all_balances[asset] = Balance(
                            amount=amount,
                            usd_value=usd_value,
                        )
                    except Exception as e:
                        log.warning(f'Failed to process Coinbase balance for {currency}: {e}')
                        
            # Check for next page
            pagination = response.get('pagination', {})
            next_uri = pagination.get('next_uri')
            
        return all_balances
        
    async def query_trade_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[Trade]:
        """Query trade history from Coinbase"""
        # Coinbase regular doesn't have trade history
        # Need to use transaction history and filter for trades
        all_trades = []
        
        # Get all accounts
        accounts = await self._get_accounts()
        
        # Query transactions for each account
        tasks = []
        for account_id in accounts:
            task = self._query_account_transactions(
                account_id,
                start_ts,
                end_ts,
            )
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_trades.extend(result)
            elif isinstance(result, Exception):
                log.error(f'Error querying Coinbase transactions: {result}')
                
        return all_trades
        
    async def _get_accounts(self) -> list[str]:
        """Get list of account IDs"""
        endpoint = '/v2/accounts'
        response = await self._api_request_signed('GET', endpoint)
        
        account_ids = []
        for account in response.get('data', []):
            account_ids.append(account['id'])
            
        return account_ids
        
    async def _query_account_transactions(
        self,
        account_id: str,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[Trade]:
        """Query transactions for a specific account"""
        endpoint = f'/v2/accounts/{account_id}/transactions'
        
        trades = []
        next_uri = endpoint
        
        while next_uri:
            response = await self._api_request_signed('GET', next_uri)
            
            for tx in response.get('data', []):
                # Filter for trades (buy/sell)
                tx_type = tx.get('type')
                if tx_type in ['buy', 'sell', 'trade']:
                    trade = self._deserialize_trade(tx)
                    if trade and start_ts <= trade.timestamp <= end_ts:
                        trades.append(trade)
                        
            # Check pagination
            pagination = response.get('pagination', {})
            next_uri = pagination.get('next_uri')
            
        return trades
        
    async def _api_request_signed(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a signed API request to Coinbase"""
        timestamp = str(int(time.time()))
        
        # Prepare message for signing
        message = timestamp + method + endpoint
        if data:
            message += json.dumps(data)
            
        # Generate signature
        signature = hmac.new(
            self.secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        
        # Headers
        headers = {
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-SIGN': signature,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-VERSION': '2021-01-01',
            'Content-Type': 'application/json',
        }
        
        # Make request
        url = f'{self.base_url}{endpoint}'
        return await self._api_request(
            method=method,
            endpoint=url,
            json_data=data,
            headers=headers,
        )
        
    def _deserialize_trade(self, tx_data: dict[str, Any]) -> Optional[Trade]:
        """Convert Coinbase transaction to Trade"""
        try:
            # Extract trade data
            tx_type = tx_data.get('type')
            if tx_type == 'buy':
                trade_type = TradeType.BUY
            elif tx_type == 'sell':
                trade_type = TradeType.SELL
            else:
                return None
                
            amount_data = tx_data.get('amount', {})
            native_amount = tx_data.get('native_amount', {})
            
            return Trade(
                timestamp=Timestamp(int(
                    time.mktime(time.strptime(
                        tx_data['created_at'],
                        '%Y-%m-%dT%H:%M:%SZ',
                    ))
                )),
                location=self.location,
                base_asset=Asset(amount_data['currency']),
                quote_asset=Asset(native_amount['currency']),
                trade_type=trade_type,
                amount=FVal(abs(float(amount_data['amount']))),
                rate=FVal(abs(float(native_amount['amount'])) / abs(float(amount_data['amount']))),
                fee=FVal('0'),  # Coinbase includes fees in amount
                fee_currency=Asset(native_amount['currency']),
                link=tx_data['id'],
            )
        except Exception as e:
            log.error(f'Failed to deserialize Coinbase trade: {e}')
            return None


class AsyncCoinbasePro(AsyncExchangeInterface):
    """Async implementation of Coinbase Pro (Advanced Trade API)"""
    
    def __init__(self, *args, **kwargs):
        super().__init__('coinbase_pro', Location.COINBASEPRO, *args, **kwargs)
        self.base_url = 'https://api.exchange.coinbase.com'
        
    async def query_balances(self) -> dict[Asset, Balance]:
        """Query all account balances from Coinbase Pro"""
        endpoint = '/accounts'
        response = await self._api_request_signed('GET', endpoint)
        
        balances = {}
        for account in response:
            try:
                currency = account['currency']
                balance = FVal(account['balance'])
                available = FVal(account['available'])
                hold = FVal(account['hold'])
                
                # Total balance is available + hold
                total = available + hold
                
                if total > ZERO:
                    asset = Asset(currency)
                    # Would need to query current price for USD value
                    usd_value = total * FVal('1')  # Placeholder
                    
                    balances[asset] = Balance(
                        amount=total,
                        usd_value=usd_value,
                    )
            except Exception as e:
                log.error(f'Error processing Coinbase Pro balance: {e}')
                
        return balances
        
    async def query_trade_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[Trade]:
        """Query trade history from Coinbase Pro"""
        # Get all trading pairs
        products = await self._get_products()
        
        # Query fills for each product
        all_trades = []
        for product_id in products:
            trades = await self._query_product_fills(
                product_id,
                start_ts,
                end_ts,
            )
            all_trades.extend(trades)
            
            # Small delay to respect rate limits
            await asyncio.sleep(0.1)
            
        return all_trades
        
    async def _get_products(self) -> list[str]:
        """Get list of all trading pairs"""
        endpoint = '/products'
        response = await self._api_request('GET', endpoint)
        
        products = []
        for product in response:
            if product.get('status') == 'online':
                products.append(product['id'])
                
        return products
        
    async def _query_product_fills(
        self,
        product_id: str,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[Trade]:
        """Query fills for a specific product"""
        endpoint = '/fills'
        params = {
            'product_id': product_id,
            'limit': 100,
        }
        
        trades = []
        has_more = True
        
        while has_more:
            response = await self._api_request_signed('GET', endpoint, params=params)
            
            if not response:
                break
                
            for fill in response:
                trade = self._deserialize_fill(fill)
                if trade and start_ts <= trade.timestamp <= end_ts:
                    trades.append(trade)
                elif trade and trade.timestamp < start_ts:
                    # Reached trades before our time range
                    has_more = False
                    break
                    
            # Check if there are more pages
            if len(response) < params['limit']:
                has_more = False
            else:
                # Set cursor for next page
                params['before'] = response[-1]['trade_id']
                
        return trades
        
    async def _api_request_signed(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        """Make a signed API request to Coinbase Pro"""
        timestamp = str(time.time())
        
        # Build request path with params
        path = endpoint
        if params:
            path += '?' + urlencode(params)
            
        # Create signature
        message = timestamp + method + path
        if data:
            message += json.dumps(data)
            
        message = message.encode('utf-8')
        secret = base64.b64decode(self.secret)
        signature = hmac.new(secret, message, hashlib.sha256)
        signature_b64 = base64.b64encode(signature.digest()).decode('utf-8')
        
        # Headers
        headers = {
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-SIGN': signature_b64,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-PASSPHRASE': '',  # Would need passphrase
            'Content-Type': 'application/json',
        }
        
        # Make request
        url = f'{self.base_url}{endpoint}'
        return await self._api_request(
            method=method,
            endpoint=url,
            params=params,
            json_data=data,
            headers=headers,
        )
        
    def _deserialize_fill(self, fill_data: dict[str, Any]) -> Optional[Trade]:
        """Convert Coinbase Pro fill to Trade"""
        try:
            # Parse product ID
            product_parts = fill_data['product_id'].split('-')
            base_asset = Asset(product_parts[0])
            quote_asset = Asset(product_parts[1])
            
            # Determine trade type
            side = fill_data['side']
            trade_type = TradeType.BUY if side == 'buy' else TradeType.SELL
            
            return Trade(
                timestamp=Timestamp(int(
                    time.mktime(time.strptime(
                        fill_data['created_at'],
                        '%Y-%m-%dT%H:%M:%S.%fZ',
                    ))
                )),
                location=self.location,
                base_asset=base_asset,
                quote_asset=quote_asset,
                trade_type=trade_type,
                amount=FVal(fill_data['size']),
                rate=FVal(fill_data['price']),
                fee=FVal(fill_data['fee']),
                fee_currency=quote_asset,
                link=fill_data['trade_id'],
            )
        except Exception as e:
            log.error(f'Failed to deserialize Coinbase Pro fill: {e}')
            return None