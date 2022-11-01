import { MaybeRef } from '@vueuse/core';
import { ComputedRef } from 'vue';
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
import { SupportedExchange } from '@/types/exchanges';
import { TradeLocation } from '@/types/history/trade-location';
import { assert } from '@/utils/assertions';

export type TradeLocationData = {
  readonly identifier: TradeLocation;
  readonly name: string;
  readonly icon: string;
  readonly imageIcon: boolean;
  readonly component?: any;
  readonly exchange: boolean;
  readonly detailPath?: string;
};

export const useTradeLocations = createSharedComposable(() => {
  const { tc } = useI18n();

  const tradeLocations: ComputedRef<TradeLocationData[]> = computed(() => [
    {
      identifier: SupportedExchange.KRAKEN,
      name: 'Kraken',
      icon: '/assets/images/exchanges/kraken.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.POLONIEX,
      name: 'Poloniex',
      icon: '/assets/images/exchanges/poloniex.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.BITMEX,
      name: 'Bitmex',
      icon: '/assets/images/exchanges/bitmex.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.BITPANDA,
      name: 'Bitpanda',
      icon: '/assets/images/exchanges/bitpanda.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.BINANCE,
      name: 'Binance',
      icon: '/assets/images/exchanges/binance.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.BINANCEUS,
      name: 'Binance US',
      icon: '/assets/images/exchanges/binance.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.BITTREX,
      name: 'Bittrex',
      icon: '/assets/images/exchanges/bittrex.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.BITFINEX,
      name: 'Bitfinex',
      icon: '/assets/images/exchanges/bitfinex.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.BITCOIN_DE,
      name: 'bitcoin.de',
      icon: '/assets/images/exchanges/btcde.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.ICONOMI,
      name: 'Iconomi',
      icon: '/assets/images/exchanges/iconomi.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.GEMINI,
      name: 'Gemini',
      icon: '/assets/images/exchanges/gemini.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.COINBASE,
      name: 'Coinbase',
      icon: '/assets/images/exchanges/coinbase.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.COINBASEPRO,
      name: 'Coinbase Pro',
      icon: '/assets/images/exchanges/coinbasepro.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: EXCHANGE_UNISWAP,
      name: 'Uniswap',
      icon: '/assets/images/defi/uniswap.svg',
      imageIcon: true,
      exchange: false
    },
    {
      identifier: EXCHANGE_BALANCER,
      name: 'Balancer',
      icon: '/assets/images/defi/balancer.svg',
      imageIcon: true,
      exchange: false
    },
    {
      identifier: EXCHANGE_SUSHISWAP,
      name: 'Sushiswap',
      icon: '/assets/images/modules/sushiswap.svg',
      imageIcon: true,
      exchange: false
    },
    {
      identifier: EXCHANGE_BLOCKFI,
      name: 'BlockFi',
      icon: '/assets/images/blockfi.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: EXCHANGE_CRYPTOCOM,
      name: 'Crypto.com',
      icon: '/assets/images/crypto_com.svg',
      imageIcon: true,
      exchange: false
    },
    {
      identifier: EXCHANGE_NEXO,
      name: 'Nexo',
      icon: '/assets/images/nexo.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.BITSTAMP,
      name: 'Bitstamp',
      icon: '/assets/images/exchanges/bitstamp.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.KUCOIN,
      name: 'KuCoin',
      icon: '/assets/images/exchanges/kucoin.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.FTX,
      name: 'FTX',
      icon: '/assets/images/exchanges/ftx.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.FTXUS,
      name: 'FTX US',
      icon: '/assets/images/exchanges/ftxus.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: EXCHANGE_SHAPESHIFT,
      name: 'ShapeShift',
      icon: '/assets/images/shapeshift.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.INDEPENDENTRESERVE,
      name: 'IndependentReserve',
      icon: '/assets/images/exchanges/independentreserve.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: EXCHANGE_UPHOLD,
      name: 'Uphold',
      icon: '/assets/images/uphold.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: EXCHANGE_BISQ,
      name: 'Bisq',
      icon: '/assets/images/bisq.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: TRADE_LOCATION_EXTERNAL,
      name: tc('trade_location.external'),
      icon: 'mdi-book',
      imageIcon: false,
      exchange: false
    },
    {
      identifier: TRADE_LOCATION_BANKS,
      name: tc('trade_location.banks'),
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
      name: tc('trade_location.equities'),
      icon: 'mdi-bag-suitcase',
      imageIcon: false,
      exchange: false
    },
    {
      identifier: TRADE_LOCATION_REALESTATE,
      name: tc('trade_location.real_estate'),
      icon: 'mdi-home',
      imageIcon: false,
      exchange: false
    },
    {
      identifier: TRADE_LOCATION_COMMODITIES,
      name: tc('trade_location.commodities'),
      icon: 'mdi-basket',
      imageIcon: false,
      exchange: false
    },
    {
      identifier: 'gitcoin',
      name: 'Gitcoin',
      icon: '/assets/images/gitcoin.svg',
      imageIcon: true,
      exchange: false
    }
  ]);

  const exchangeName: (
    location: MaybeRef<TradeLocation>
  ) => string = location => {
    const exchange = get(tradeLocations).find(
      tl => tl.identifier === get(location)
    );
    assert(exchange);
    return exchange.name;
  };

  return {
    tradeLocations,
    exchangeName
  };
});
