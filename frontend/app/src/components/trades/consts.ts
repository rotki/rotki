import { TradeLocationData } from '@/components/trades/type';

export const tradeLocations: TradeLocationData[] = [
  {
    identifier: 'kraken',
    name: 'Kraken',
    icon: require('@/assets/images/kraken.png')
  },
  {
    identifier: 'bittrex',
    name: 'Bittrex',
    icon: require('@/assets/images/bittrex.png')
  },
  {
    identifier: 'binance',
    name: 'Binance',
    icon: require('@/assets/images/binance.png')
  },
  {
    identifier: 'gemini',
    name: 'Gemini',
    icon: require('@/assets/images/gemini.png')
  },
  {
    identifier: 'external',
    name: 'External'
  }
];
