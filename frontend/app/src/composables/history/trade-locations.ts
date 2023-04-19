import { type ComputedRef } from 'vue';
import { type MaybeRef } from '@vueuse/core';
import { SupportedExchange } from '@/types/exchanges';
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
  TRADE_LOCATION_ETHEREUM,
  TRADE_LOCATION_EXTERNAL,
  TRADE_LOCATION_OPTIMISM,
  TRADE_LOCATION_REALESTATE
} from '@/data/defaults';
import {
  type TradeLocation,
  type TradeLocationData
} from '@/types/history/trade/location';

export const useTradeLocations = createSharedComposable(() => {
  const { tc } = useI18n();

  const tradeLocations: ComputedRef<TradeLocationData[]> = computed(() => [
    {
      identifier: SupportedExchange.KRAKEN,
      name: 'Kraken',
      icon: './assets/images/protocols/kraken.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.POLONIEX,
      name: 'Poloniex',
      icon: './assets/images/protocols/poloniex.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.BITMEX,
      name: 'Bitmex',
      icon: './assets/images/protocols/bitmex.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.BITPANDA,
      name: 'Bitpanda',
      icon: './assets/images/protocols/bitpanda.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.BINANCE,
      name: 'Binance',
      icon: './assets/images/protocols/binance.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.BINANCEUS,
      name: 'Binance US',
      icon: './assets/images/protocols/binance.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.BITTREX,
      name: 'Bittrex',
      icon: './assets/images/protocols/bittrex.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.BITFINEX,
      name: 'Bitfinex',
      icon: './assets/images/protocols/bitfinex.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.BITCOIN_DE,
      name: 'bitcoin.de',
      icon: './assets/images/protocols/btcde.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.ICONOMI,
      name: 'Iconomi',
      icon: './assets/images/protocols/iconomi.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.GEMINI,
      name: 'Gemini',
      icon: './assets/images/protocols/gemini.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.COINBASE,
      name: 'Coinbase',
      icon: './assets/images/protocols/coinbase.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.COINBASEPRO,
      name: 'Coinbase Pro',
      icon: './assets/images/protocols/coinbasepro.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: EXCHANGE_UNISWAP,
      name: 'Uniswap',
      icon: './assets/images/protocols/uniswap.svg',
      imageIcon: true,
      exchange: false
    },
    {
      identifier: EXCHANGE_BALANCER,
      name: 'Balancer',
      icon: './assets/images/protocols/balancer.svg',
      imageIcon: true,
      exchange: false
    },
    {
      identifier: EXCHANGE_SUSHISWAP,
      name: 'Sushiswap',
      icon: './assets/images/protocols/sushiswap.svg',
      imageIcon: true,
      exchange: false
    },
    {
      identifier: EXCHANGE_BLOCKFI,
      name: 'BlockFi',
      icon: './assets/images/protocols/blockfi.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: EXCHANGE_CRYPTOCOM,
      name: 'Crypto.com',
      icon: './assets/images/protocols/crypto_com.svg',
      imageIcon: true,
      exchange: false
    },
    {
      identifier: EXCHANGE_NEXO,
      name: 'Nexo',
      icon: './assets/images/protocols/nexo.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.BITSTAMP,
      name: 'Bitstamp',
      icon: './assets/images/protocols/bitstamp.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.KUCOIN,
      name: 'KuCoin',
      icon: './assets/images/protocols/kucoin.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.FTX,
      name: 'FTX',
      icon: './assets/images/protocols/ftx.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.FTXUS,
      name: 'FTX US',
      icon: './assets/images/protocols/ftxus.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.OKX,
      name: 'OKX',
      icon: './assets/images/protocols/okx.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: EXCHANGE_SHAPESHIFT,
      name: 'ShapeShift',
      icon: './assets/images/protocols/shapeshift.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: SupportedExchange.INDEPENDENTRESERVE,
      name: 'IndependentReserve',
      icon: './assets/images/protocols/independentreserve.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: EXCHANGE_UPHOLD,
      name: 'Uphold',
      icon: './assets/images/protocols/uphold.svg',
      imageIcon: true,
      exchange: true
    },
    {
      identifier: EXCHANGE_BISQ,
      name: 'Bisq',
      icon: './assets/images/protocols/bisq.svg',
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
      identifier: TRADE_LOCATION_ETHEREUM,
      name: 'Ethereum',
      icon: './assets/images/protocols/ethereum.svg',
      imageIcon: true,
      exchange: false
    },
    {
      identifier: TRADE_LOCATION_OPTIMISM,
      name: 'Optimism',
      icon: './assets/images/protocols/optimism.svg',
      imageIcon: true,
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
      icon: './assets/images/protocols/gitcoin.svg',
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
