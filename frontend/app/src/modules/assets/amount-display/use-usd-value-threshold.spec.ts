import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { BalanceSource, type BalanceValueThreshold } from '@/modules/settings/types/frontend-settings';
import { useValueThreshold } from './use-usd-value-threshold';

const mockBalanceValueThreshold = ref<BalanceValueThreshold>({ BLOCKCHAIN: '10', EXCHANGES: '10', MANUAL: '10' });
vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => mockBalanceValueThreshold),
}));

describe('useValueThreshold', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(mockBalanceValueThreshold, { BLOCKCHAIN: '10', EXCHANGES: '10', MANUAL: '10' });
  });

  it('should return the threshold value for BLOCKCHAIN', () => {
    const result = useValueThreshold(BalanceSource.BLOCKCHAIN);
    expect(get(result)).toBe('10');
  });

  it('should return the threshold value for EXCHANGES', () => {
    const result = useValueThreshold(BalanceSource.EXCHANGES);
    expect(get(result)).toBe('10');
  });

  it('should return the threshold value for MANUAL', () => {
    const result = useValueThreshold(BalanceSource.MANUAL);
    expect(get(result)).toBe('10');
  });

  it('should return undefined when no value threshold exists for the balance source', () => {
    set(mockBalanceValueThreshold, {});
    const result = useValueThreshold(BalanceSource.MANUAL);
    expect(get(result)).toBeUndefined();
  });
});
