import type { ExchangeFormData } from '@/modules/balances/types/exchanges';
import { describe, expect, it } from 'vitest';
import { isConnected, savesMissingPairs } from './binance-pairs-condition';

const ACCOUNT = { location: 'binance', name: 'main' };

function form(overrides: Partial<ExchangeFormData> = {}): ExchangeFormData {
  return { apiKey: '', apiSecret: '', location: 'binance', mode: 'edit', name: 'main', passphrase: '', ...overrides };
}

describe('modules/balances/exchanges/binance-pairs-condition', () => {
  describe('savesMissingPairs', () => {
    it('should settle the account once it is saved with pairs', () => {
      expect(savesMissingPairs(ACCOUNT, form({ binanceMarkets: ['ETHBTC'] }))).toBe(true);
    });

    it('should not settle it when saved with no pairs', () => {
      expect(savesMissingPairs(ACCOUNT, form({ binanceMarkets: [] }))).toBe(false);
      expect(savesMissingPairs(ACCOUNT, form())).toBe(false);
    });

    it('should not settle another account, even of the same name on Binance US', () => {
      expect(savesMissingPairs(ACCOUNT, form({ binanceMarkets: ['ETHBTC'], name: 'other' }))).toBe(false);
      expect(savesMissingPairs(ACCOUNT, form({ binanceMarkets: ['ETHBTC'], location: 'binanceus' }))).toBe(false);
    });
  });

  describe('isConnected', () => {
    it('should find an account that is still connected', () => {
      expect(isConnected(ACCOUNT, [{ location: 'kraken', name: 'main' }, ACCOUNT])).toBe(true);
    });

    it('should not find one that was removed or renamed', () => {
      expect(isConnected(ACCOUNT, [{ location: 'binance', name: 'renamed' }])).toBe(false);
    });
  });
});
