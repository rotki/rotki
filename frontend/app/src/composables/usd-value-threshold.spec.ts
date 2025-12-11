import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref, type ToRefs } from 'vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { BalanceSource } from '@/types/settings/frontend-settings';
import { useValueThreshold } from './usd-value-threshold';

type MockedStore<T extends (...args: any[]) => any> = ToRefs<Partial<ReturnType<T>>>;

function createMock<T>(overrides: ToRefs<Partial<T>>): T {
  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions
  return {
    ...overrides,
  } as T;
}

vi.mock('@/store/settings/frontend', () => ({
  useFrontendSettingsStore: vi.fn((): MockedStore<typeof useFrontendSettingsStore> => ({
    balanceValueThreshold: ref({ BLOCKCHAIN: '10', EXCHANGES: '10', MANUAL: '10' }),
  })),
}));

describe('useValueThreshold', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
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
    vi.mocked(useFrontendSettingsStore).mockImplementationOnce(() => createMock<ReturnType<typeof useFrontendSettingsStore>>({
      balanceValueThreshold: ref({}),
    }));
    const result = useValueThreshold(BalanceSource.MANUAL);
    expect(get(result)).toBeUndefined();
  });
});
