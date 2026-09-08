import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { Exchange } from '@/modules/balances/types/exchanges';
import { useExchangeApi } from '@/modules/balances/api/use-exchange-api';

/** The two binance connections that need their traded pairs selected before a report is accurate. */
const BINANCE_LOCATIONS: readonly string[] = ['binance', 'binanceus'];

interface UseBinanceMarketCheckReturn {
  /** The names of the connected binance accounts with no market pairs selected. */
  exchangesWithoutMarkets: Readonly<Ref<readonly string[]>>;
  /** Whether any connected binance account is still missing its pairs. */
  hasExchangesWithoutMarkets: ComputedRef<boolean>;
  /** Re-reads every connected binance account's pairs. */
  checkMarketPairs: () => Promise<void>;
}

/**
 * Which connected binance accounts have no traded pairs selected, since a report generated
 * without them silently misses those trades.
 *
 * @remarks
 * An account whose pairs cannot be read counts as missing them. The check exists to stop a report
 * being generated from incomplete data, so failing to prove the pairs are there is treated the
 * same as their absence rather than waved through.
 *
 * @param connectedExchanges - every exchange the user has connected, binance or not
 * @returns the accounts missing their pairs and the way to re-read them
 */
export function useBinanceMarketCheck(
  connectedExchanges: MaybeRefOrGetter<Exchange[]>,
): UseBinanceMarketCheckReturn {
  const { queryBinanceUserMarkets } = useExchangeApi();

  const exchangesWithoutMarkets = ref<string[]>([]);

  const hasExchangesWithoutMarkets = computed<boolean>(() => get(exchangesWithoutMarkets).length > 0);

  async function hasMarkets(exchange: Exchange): Promise<boolean> {
    try {
      const markets = await queryBinanceUserMarkets(exchange.name, exchange.location);
      return !!markets && markets.length > 0;
    }
    catch {
      return false;
    }
  }

  async function checkMarketPairs(): Promise<void> {
    const binanceExchanges = toValue(connectedExchanges)
      .filter(exchange => BINANCE_LOCATIONS.includes(exchange.location));

    const checked = await Promise.all(
      binanceExchanges.map(async exchange => ({ name: exchange.name, ok: await hasMarkets(exchange) })),
    );

    set(exchangesWithoutMarkets, checked.filter(({ ok }) => !ok).map(({ name }) => name));
  }

  return {
    checkMarketPairs,
    exchangesWithoutMarkets: readonly(exchangesWithoutMarkets),
    hasExchangesWithoutMarkets,
  };
}
