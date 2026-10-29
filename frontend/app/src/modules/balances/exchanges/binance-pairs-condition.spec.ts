import type { ExchangeFormData } from '@/modules/balances/types/exchanges';
import { describe, expect, it } from 'vitest';
import { isConnected, isConnectedConnection, savesMissingPairs } from './binance-pairs-condition';

const ACCOUNT = { identifier: 'c1', location: 'binance', name: 'main' };

function form(overrides: Partial<ExchangeFormData> = {}): ExchangeFormData {
  return { apiKey: '', apiSecret: '', identifier: 'c1', location: 'binance', mode: 'edit', name: 'main', passphrase: '', ...overrides };
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

    it('should not settle another connection, even of the same name', () => {
      expect(savesMissingPairs(ACCOUNT, form({ binanceMarkets: ['ETHBTC'], identifier: 'c2' }))).toBe(false);
      expect(savesMissingPairs(ACCOUNT, form({ binanceMarkets: ['ETHBTC'], identifier: undefined, mode: 'add' }))).toBe(false);
    });

    it('should settle a connection saved under a new name', () => {
      expect(savesMissingPairs(ACCOUNT, form({ binanceMarkets: ['ETHBTC'], name: 'renamed' }))).toBe(true);
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

  describe('isConnectedConnection', () => {
    it('should find a connection by identifier, also when renamed', () => {
      expect(isConnectedConnection(ACCOUNT, [{ identifier: 'c1' }])).toBe(true);
    });

    it('should not find a removed connection', () => {
      expect(isConnectedConnection(ACCOUNT, [{ identifier: 'c2' }])).toBe(false);
    });
  });
});
