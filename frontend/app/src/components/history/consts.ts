import { TradeLocationData } from '@/components/history/type';
import {
  EXCHANGE_BINANCE,
  EXCHANGE_BINANCE_US,
  EXCHANGE_BITCOIN_DE,
  EXCHANGE_BITFINEX,
  EXCHANGE_BITMEX,
  EXCHANGE_BITSTAMP,
  EXCHANGE_BITTREX,
  EXCHANGE_COINBASE,
  EXCHANGE_COINBASEPRO,
  EXCHANGE_CRYPTOCOM,
  EXCHANGE_GEMINI,
  EXCHANGE_ICONOMI,
  EXCHANGE_KRAKEN,
  EXCHANGE_POLONIEX,
  EXCHANGE_UNISWAP
} from '@/data/defaults';
import { TradeLocation } from '@/services/history/types';
import { assert } from '@/utils/assertions';

export const tradeLocations: TradeLocationData[] = [
  {
    identifier: EXCHANGE_KRAKEN,
    name: 'Kraken',
    icon: require('@/assets/images/kraken.png')
  },
  {
    identifier: EXCHANGE_POLONIEX,
    name: 'Poloniex',
    icon: require('@/assets/images/poloniex.png')
  },
  {
    identifier: EXCHANGE_BITMEX,
    name: 'Bitmex',
    icon: require('@/assets/images/bitmex.png')
  },
  {
    identifier: EXCHANGE_BINANCE,
    name: 'Binance',
    icon: require('@/assets/images/binance.png')
  },
  {
    identifier: EXCHANGE_BINANCE_US,
    name: 'Binance US',
    icon: require('@/assets/images/binance.png')
  },
  {
    identifier: EXCHANGE_BITTREX,
    name: 'Bittrex',
    icon: require('@/assets/images/bittrex.png')
  },
  {
    identifier: EXCHANGE_BITFINEX,
    name: 'Bitfinex',
    icon: require('@/assets/images/bitfinex.svg')
  },
  {
    identifier: EXCHANGE_BITCOIN_DE,
    name: 'bitcoin.de',
    icon: require('@/assets/images/btcde.svg')
  },
  {
    identifier: EXCHANGE_ICONOMI,
    name: 'Iconomi',
    icon: require('@/assets/images/iconomi.svg')
  },
  {
    identifier: EXCHANGE_GEMINI,
    name: 'Gemini',
    icon: require('@/assets/images/gemini.png')
  },
  {
    identifier: EXCHANGE_COINBASE,
    name: 'Coinbase',
    icon: require('@/assets/images/coinbase.png')
  },
  {
    identifier: EXCHANGE_COINBASEPRO,
    name: 'Coinbase Pro',
    icon: require('@/assets/images/coinbasepro.png')
  },
  {
    identifier: EXCHANGE_UNISWAP,
    name: 'Uniswap',
    icon: require('@/assets/images/defi/uniswap.svg')
  },
  {
    identifier: EXCHANGE_CRYPTOCOM,
    name: 'Crypto.com',
    icon: require('@/assets/images/crypto.com.png')
  },
  {
    identifier: EXCHANGE_BITSTAMP,
    name: 'Bitstamp',
    icon: require('@/assets/images/bitstamp.png')
  },
  {
    identifier: 'external',
    name: 'External'
  }
];

export const exchangeName: (location: TradeLocation) => string = location => {
  const exchange = tradeLocations.find(tl => tl.identifier === location);
  assert(exchange);
  return exchange.name;
};
