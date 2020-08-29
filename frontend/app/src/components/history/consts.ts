import { TradeLocationData } from '@/components/history/type';
import { TradeLocation } from '@/services/history/types';
import { assert } from '@/utils/assertions';

export const tradeLocations: TradeLocationData[] = [
  {
    identifier: 'kraken',
    name: 'Kraken',
    icon: require('@/assets/images/kraken.png')
  },
  {
    identifier: 'poloniex',
    name: 'Poloniex',
    icon: require('@/assets/images/poloniex.png')
  },
  {
    identifier: 'bitmex',
    name: 'Bitmex',
    icon: require('@/assets/images/bitmex.png')
  },
  {
    identifier: 'binance',
    name: 'Binance',
    icon: require('@/assets/images/binance.png')
  },
  {
    identifier: 'bittrex',
    name: 'Bittrex',
    icon: require('@/assets/images/bittrex.png')
  },
  {
    identifier: 'gemini',
    name: 'Gemini',
    icon: require('@/assets/images/gemini.png')
  },
  {
    identifier: 'coinbase',
    name: 'Coinbase',
    icon: require('@/assets/images/coinbase.png')
  },
  {
    identifier: 'coinbasepro',
    name: 'Coinbase Pro',
    icon: require('@/assets/images/coinbasepro.png')
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
