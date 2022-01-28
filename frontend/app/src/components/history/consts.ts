import { TradeLocationData } from '@/components/history/type';
import FOXIcon from '@/components/icons/FOXIcon.vue';
import UpholdIcon from '@/components/icons/UpholdIcon.vue';
import {
  EXCHANGE_BALANCER,
  EXCHANGE_BISQ,
  EXCHANGE_BLOCKFI,
  EXCHANGE_CRYPTOCOM,
  EXCHANGE_NEXO,
  EXCHANGE_SHAPESHIFT,
  EXCHANGE_SUSHISWAP,
  EXCHANGE_UNISWAP,
  EXCHANGE_UPHOLD,
  TRADE_LOCATION_BANKS,
  TRADE_LOCATION_BLOCKCHAIN,
  TRADE_LOCATION_COMMODITIES,
  TRADE_LOCATION_EQUITIES,
  TRADE_LOCATION_EXTERNAL,
  TRADE_LOCATION_REALESTATE
} from '@/data/defaults';
import i18n from '@/i18n';
import { TradeLocation } from '@/services/history/types';
import { SupportedExchange } from '@/types/exchanges';
import { assert } from '@/utils/assertions';

export const tradeLocations: TradeLocationData[] = [
  {
    identifier: SupportedExchange.KRAKEN,
    name: 'Kraken',
    icon: require('@/assets/images/kraken.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: SupportedExchange.POLONIEX,
    name: 'Poloniex',
    icon: require('@/assets/images/poloniex.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: SupportedExchange.BITMEX,
    name: 'Bitmex',
    icon: require('@/assets/images/bitmex.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: SupportedExchange.BITPANDA,
    name: 'Bitpanda',
    icon: require('@/assets/images/exchanges/bitpanda.svg'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: SupportedExchange.BINANCE,
    name: 'Binance',
    icon: require('@/assets/images/binance.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: SupportedExchange.BINANCEUS,
    name: 'Binance US',
    icon: require('@/assets/images/binance.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: SupportedExchange.BITTREX,
    name: 'Bittrex',
    icon: require('@/assets/images/bittrex.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: SupportedExchange.BITFINEX,
    name: 'Bitfinex',
    icon: require('@/assets/images/bitfinex.svg'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: SupportedExchange.BITCOIN_DE,
    name: 'bitcoin.de',
    icon: require('@/assets/images/btcde.svg'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: SupportedExchange.ICONOMI,
    name: 'Iconomi',
    icon: require('@/assets/images/iconomi.svg'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: SupportedExchange.GEMINI,
    name: 'Gemini',
    icon: require('@/assets/images/gemini.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: SupportedExchange.COINBASE,
    name: 'Coinbase',
    icon: require('@/assets/images/coinbase.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: SupportedExchange.COINBASEPRO,
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
    identifier: EXCHANGE_SUSHISWAP,
    name: 'Sushiswap',
    icon: require('@/assets/images/modules/sushiswap.svg'),
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
    identifier: SupportedExchange.BITSTAMP,
    name: 'Bitstamp',
    icon: require('@/assets/images/bitstamp.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: SupportedExchange.KUCOIN,
    name: 'KuCoin',
    icon: require('@/assets/images/exchanges/kucoin.svg'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: SupportedExchange.FTX,
    name: 'FTX',
    icon: require('@/assets/images/exchanges/ftx.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: EXCHANGE_SHAPESHIFT,
    name: 'ShapeShift',
    icon: '',
    imageIcon: false,
    component: FOXIcon,
    exchange: true
  },
  {
    identifier: SupportedExchange.INDEPENDENTRESERVE,
    name: 'IndependentReserve',
    icon: require('@/assets/images/exchanges/independentreserve.png'),
    imageIcon: true,
    exchange: true
  },
  {
    identifier: EXCHANGE_UPHOLD,
    name: 'uphold',
    icon: '',
    imageIcon: false,
    component: UpholdIcon,
    exchange: true
  },
  {
    identifier: EXCHANGE_BISQ,
    name: 'bisq',
    icon: require('@/assets/images/bisq.svg'),
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
