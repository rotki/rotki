import { describe, expect, it } from 'vitest';
import { toThresholds } from '@/modules/settings/hide-small-balances-form';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';

const existing = {
  [BalanceSource.BLOCKCHAIN]: '1',
  [BalanceSource.EXCHANGES]: '2',
};

describe('settings/hide-small-balances-form', () => {
  describe('applying to every source', () => {
    it('should set the same threshold on all three sources', () => {
      const thresholds = toThresholds(
        { applyToAllBalances: true, hide: true, hideBelow: '5' },
        BalanceSource.BLOCKCHAIN,
        existing,
      );

      expect(thresholds).toEqual({
        [BalanceSource.BLOCKCHAIN]: '5',
        [BalanceSource.EXCHANGES]: '5',
        [BalanceSource.MANUAL]: '5',
      });
    });

    it('should clear every threshold when hiding is off', () => {
      const thresholds = toThresholds(
        { applyToAllBalances: true, hide: false, hideBelow: '5' },
        BalanceSource.BLOCKCHAIN,
        existing,
      );

      expect(thresholds).toEqual({});
    });
  });

  describe('applying to one source', () => {
    it('should set this source and leave the others untouched', () => {
      const thresholds = toThresholds(
        { applyToAllBalances: false, hide: true, hideBelow: '5' },
        BalanceSource.BLOCKCHAIN,
        existing,
      );

      expect(thresholds).toEqual({
        [BalanceSource.BLOCKCHAIN]: '5',
        [BalanceSource.EXCHANGES]: '2',
      });
    });

    // Absence is how the setting expresses "do not hide", so the key has to go rather than be zeroed.
    it('should drop only this source when hiding is off', () => {
      const thresholds = toThresholds(
        { applyToAllBalances: false, hide: false, hideBelow: '5' },
        BalanceSource.BLOCKCHAIN,
        existing,
      );

      expect(thresholds).toEqual({ [BalanceSource.EXCHANGES]: '2' });
    });

    it('should add a source that had no threshold before', () => {
      const thresholds = toThresholds(
        { applyToAllBalances: false, hide: true, hideBelow: '3' },
        BalanceSource.MANUAL,
        existing,
      );

      expect(thresholds).toEqual({
        [BalanceSource.BLOCKCHAIN]: '1',
        [BalanceSource.EXCHANGES]: '2',
        [BalanceSource.MANUAL]: '3',
      });
    });
  });
});
