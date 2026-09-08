import type { Exchange } from '@/modules/balances/types/exchanges';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBinanceMarketCheck } from '@/modules/reports/use-binance-market-check';

const queryBinanceUserMarkets = vi.fn<(name: string, location: string) => Promise<string[]>>();

vi.mock('@/modules/balances/api/use-exchange-api', () => ({
  useExchangeApi: (): { queryBinanceUserMarkets: typeof queryBinanceUserMarkets } => ({
    queryBinanceUserMarkets,
  }),
}));

function exchange(name: string, location: string): Exchange {
  return { location, name };
}

describe('useBinanceMarketCheck', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryBinanceUserMarkets.mockResolvedValue(['ETHEUR']);
  });

  describe('which exchanges it asks about', () => {
    it('should ask about both binance flavours', async () => {
      const { checkMarketPairs } = useBinanceMarketCheck([
        exchange('Binance 1', 'binance'),
        exchange('Binance US 1', 'binanceus'),
      ]);

      await checkMarketPairs();

      expect(queryBinanceUserMarkets).toHaveBeenCalledWith('Binance 1', 'binance');
      expect(queryBinanceUserMarkets).toHaveBeenCalledWith('Binance US 1', 'binanceus');
    });

    it('should leave every other exchange alone', async () => {
      const { checkMarketPairs } = useBinanceMarketCheck([
        exchange('Kraken 1', 'kraken'),
        exchange('Coinbase 1', 'coinbase'),
      ]);

      await checkMarketPairs();

      expect(queryBinanceUserMarkets).not.toHaveBeenCalled();
    });

    it('should ask about nothing when no exchange is connected', async () => {
      const { checkMarketPairs, hasExchangesWithoutMarkets } = useBinanceMarketCheck([]);

      await checkMarketPairs();

      expect(queryBinanceUserMarkets).not.toHaveBeenCalled();
      expect(get(hasExchangesWithoutMarkets)).toBe(false);
    });
  });

  describe('what counts as missing its pairs', () => {
    it('should accept an exchange that has pairs', async () => {
      const { checkMarketPairs, exchangesWithoutMarkets } = useBinanceMarketCheck([
        exchange('Binance 1', 'binance'),
      ]);

      await checkMarketPairs();

      expect(get(exchangesWithoutMarkets)).toEqual([]);
    });

    it('should flag an exchange with an empty pair list', async () => {
      queryBinanceUserMarkets.mockResolvedValue([]);
      const { checkMarketPairs, exchangesWithoutMarkets } = useBinanceMarketCheck([
        exchange('Binance 1', 'binance'),
      ]);

      await checkMarketPairs();

      expect(get(exchangesWithoutMarkets)).toEqual(['Binance 1']);
    });

    /**
     * The check exists to stop a report being generated from incomplete data, so failing to prove
     * the pairs are there has to be treated the same as their absence.
     */
    it('should flag an exchange whose pairs could not be read', async () => {
      queryBinanceUserMarkets.mockRejectedValue(new Error('network'));
      const { checkMarketPairs, exchangesWithoutMarkets } = useBinanceMarketCheck([
        exchange('Binance 1', 'binance'),
      ]);

      await checkMarketPairs();

      expect(get(exchangesWithoutMarkets)).toEqual(['Binance 1']);
    });

    it('should flag only the exchange that is missing them', async () => {
      queryBinanceUserMarkets.mockImplementation(async name =>
        name === 'Binance 1' ? [] : ['ETHEUR'],
      );
      const { checkMarketPairs, exchangesWithoutMarkets } = useBinanceMarketCheck([
        exchange('Binance 1', 'binance'),
        exchange('Binance 2', 'binance'),
      ]);

      await checkMarketPairs();

      expect(get(exchangesWithoutMarkets)).toEqual(['Binance 1']);
    });

    it('should not let one failure hide another exchange', async () => {
      queryBinanceUserMarkets.mockRejectedValue(new Error('network'));
      const { checkMarketPairs, exchangesWithoutMarkets } = useBinanceMarketCheck([
        exchange('Binance 1', 'binance'),
        exchange('Binance 2', 'binance'),
      ]);

      await checkMarketPairs();

      expect(get(exchangesWithoutMarkets)).toEqual(['Binance 1', 'Binance 2']);
    });
  });

  describe('re-reading', () => {
    it('should clear an earlier complaint once the pairs are selected', async () => {
      queryBinanceUserMarkets.mockResolvedValue([]);
      const { checkMarketPairs, hasExchangesWithoutMarkets } = useBinanceMarketCheck([
        exchange('Binance 1', 'binance'),
      ]);

      await checkMarketPairs();

      expect(get(hasExchangesWithoutMarkets)).toBe(true);

      queryBinanceUserMarkets.mockResolvedValue(['ETHEUR']);
      await checkMarketPairs();

      expect(get(hasExchangesWithoutMarkets)).toBe(false);
    });

    it('should follow a changing list of connected exchanges', async () => {
      queryBinanceUserMarkets.mockResolvedValue([]);
      const exchanges = ref<Exchange[]>([]);
      const { checkMarketPairs, exchangesWithoutMarkets } = useBinanceMarketCheck(exchanges);

      await checkMarketPairs();

      expect(get(exchangesWithoutMarkets)).toEqual([]);

      set(exchanges, [exchange('Binance 1', 'binance')]);
      await checkMarketPairs();

      expect(get(exchangesWithoutMarkets)).toEqual(['Binance 1']);
    });
  });
});
