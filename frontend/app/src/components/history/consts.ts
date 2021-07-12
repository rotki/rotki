import { TradeLocationData } from '@/components/history/type';
import {
  EXCHANGE_BALANCER,
  EXCHANGE_BINANCE,
  EXCHANGE_BINANCEUS,
  EXCHANGE_BITCOIN_DE,
  EXCHANGE_BITFINEX,
  EXCHANGE_BITMEX,
  EXCHANGE_BITSTAMP,
  EXCHANGE_BITTREX,
  EXCHANGE_BLOCKFI,
  EXCHANGE_COINBASE,
  EXCHANGE_COINBASEPRO,
  EXCHANGE_CRYPTOCOM,
  EXCHANGE_FTX,
  EXCHANGE_GEMINI,
  EXCHANGE_ICONOMI,
  EXCHANGE_KRAKEN,
  EXCHANGE_KUCOIN,
  EXCHANGE_NEXO,
  EXCHANGE_POLONIEX,
  EXCHANGE_UNISWAP,
  EXCHANGE_INDEPENDENTRESERVE,
  TRADE_LOCATION_BANKS,
  TRADE_LOCATION_BLOCKCHAIN,
  TRADE_LOCATION_COMMODITIES,
  TRADE_LOCATION_EQUITIES,
  TRADE_LOCATION_EXTERNAL,
  TRADE_LOCATION_REALESTATE
} from '@/data/defaults';
import i18n from '@/i18n';
import { TradeLocation } from '@/services/history/types';
import { assert } from '@/utils/assertions';

export const tradeLocations: TradeLocationData[] = [
  {
    identifier: EXCHANGE_KRAKEN,
    name: 'Kraken',
    icon: require('@/assets/images/kraken.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: EXCHANGE_POLONIEX,
    name: 'Poloniex',
    icon: require('@/assets/images/poloniex.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: EXCHANGE_BITMEX,
    name: 'Bitmex',
    icon: require('@/assets/images/bitmex.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: EXCHANGE_BINANCE,
    name: 'Binance',
    icon: require('@/assets/images/binance.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: EXCHANGE_BINANCEUS,
    name: 'Binance US',
    icon: require('@/assets/images/binance.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: EXCHANGE_BITTREX,
    name: 'Bittrex',
    icon: require('@/assets/images/bittrex.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: EXCHANGE_BITFINEX,
    name: 'Bitfinex',
    icon: require('@/assets/images/bitfinex.svg'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: EXCHANGE_BITCOIN_DE,
    name: 'bitcoin.de',
    icon: require('@/assets/images/btcde.svg'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: EXCHANGE_ICONOMI,
    name: 'Iconomi',
    icon: require('@/assets/images/iconomi.svg'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: EXCHANGE_GEMINI,
    name: 'Gemini',
    icon: require('@/assets/images/gemini.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: EXCHANGE_COINBASE,
    name: 'Coinbase',
    icon: require('@/assets/images/coinbase.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: EXCHANGE_COINBASEPRO,
    name: 'Coinbase Pro',
    icon: require('@/assets/images/coinbasepro.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: EXCHANGE_UNISWAP,
    name: 'Uniswap',
    icon: require('@/assets/images/defi/uniswap.svg'),
    imageIcon: true,
    exchange: false
  },
  {
    identifier: EXCHANGE_BALANCER,
    name: 'Balancer',
    icon: require('@/assets/images/defi/balancer.svg'),
    imageIcon: true,
    exchange: false
  },
  {
    identifier: EXCHANGE_BLOCKFI,
    name: 'BlockFi',
    icon: require('@/assets/images/blockfi.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: EXCHANGE_CRYPTOCOM,
    name: 'Crypto.com',
    icon: require('@/assets/images/crypto.com.png'),
    imageIcon: true,
    exchange: false
  },
  {
    identifier: EXCHANGE_NEXO,
    name: 'Nexo',
    icon: require('@/assets/images/nexo.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: EXCHANGE_BITSTAMP,
    name: 'Bitstamp',
    icon: require('@/assets/images/bitstamp.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: EXCHANGE_KUCOIN,
    name: 'KuCoin',
    icon: require('@/assets/images/exchanges/kucoin.svg'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: EXCHANGE_FTX,
    name: 'FTX',
    icon: require('@/assets/images/exchanges/ftx.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: EXCHANGE_INDEPENDENTRESERVE,
    name: 'IndepentReserve',
    icon: require('@/assets/images/exchanges/independentreserve.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: TRADE_LOCATION_EXTERNAL,
    name: i18n.t('trade_location.external').toString(),
    icon: 'mdi-book',
    imageIcon: false,
    exchange: false
  },
  {
    identifier: TRADE_LOCATION_BANKS,
    name: i18n.t('trade_location.banks').toString(),
    icon: 'mdi-bank',
    imageIcon: false,
    exchange: false
  },
  {
    identifier: TRADE_LOCATION_BLOCKCHAIN,
    name: 'Blockchain',
    icon: 'mdi-link',
    imageIcon: false,
    exchange: false
  },
  {
    identifier: TRADE_LOCATION_EQUITIES,
    name: i18n.t('trade_location.equities').toString(),
    icon: 'mdi-bag-suitcase',
    imageIcon: false,
    exchange: false
  },
  {
    identifier: TRADE_LOCATION_REALESTATE,
    name: i18n.t('trade_location.real_estate').toString(),
    icon: 'mdi-home',
    imageIcon: false,
    exchange: false
  },
  {
    identifier: TRADE_LOCATION_COMMODITIES,
    name: i18n.t('trade_location.commodities').toString(),
    icon: 'mdi-basket',
    imageIcon: false,
    exchange: false
  },
  {
    identifier: 'gitcoin',
    name: 'Gitcoin',
    icon: require('@/assets/images/gitcoin.png'),
    imageIcon: true,
    exchange: false
  }
];

export const exchangeName: (location: TradeLocation) => string = location => {
  const exchange = tradeLocations.find(tl => tl.identifier === location);
  assert(exchange);
  return exchange.name;
};
