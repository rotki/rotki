import { bigNumberify } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref, type ToRefs } from 'vue';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useCurrencies } from '@/types/currencies';
import { BalanceSource } from '@/types/settings/frontend-settings';
import { useUsdValueThreshold } from './usd-value-threshold';

type MockedStore<T extends (...args: any[]) => any> = ToRefs<Partial<ReturnType<T>>>;

function createMock<T>(overrides: ToRefs<Partial<T>>): T {
  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions
  return {
    ...overrides,
  } as T;
}

vi.mock('@/store/settings/frontend', () => ({
  useFrontendSettingsStore: vi.fn((): MockedStore<typeof useFrontendSettingsStore> => ({
    balanceUsdValueThreshold: ref({ BLOCKCHAIN: '10', EXCHANGES: '10', MANUAL: '10' }),
  })),
}));

describe('useUsdValueThreshold', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    const { exchangeRates } = storeToRefs(useBalancePricesStore());
    set(exchangeRates, {
      EUR: bigNumberify(1.1),
      JPY: bigNumberify(0.008),
    });
  });

  it('should return the threshold as is when currency is USD and value exists', () => {
    const result = useUsdValueThreshold(BalanceSource.BLOCKCHAIN);
    expect(get(result)).toBe('10');
  });

  it('should convert the threshold value based on exchange rate when currency is not USD', () => {
    const currencies = useCurrencies();
    useGeneralSettingsStore().settings.mainCurrency = currencies.findCurrency('EUR');
    const result = useUsdValueThreshold(BalanceSource.EXCHANGES);
    expect(result.value).toBe('11'); // 200 * 1.1
  });

  it('should return zero if the threshold is defined and is set to 0', () => {
    vi.mocked(useFrontendSettingsStore).mockImplementationOnce(() => createMock<ReturnType<typeof useFrontendSettingsStore>>({
      balanceUsdValueThreshold: ref({ BLOCKCHAIN: '0' }),
    }));
    const currencies = useCurrencies();
    useGeneralSettingsStore().settings.mainCurrency = currencies.findCurrency('TRY');
    const result = useUsdValueThreshold(BalanceSource.BLOCKCHAIN);
    expect(result.value).toBe('0');
  });

  it('should return undefined when a threshold is zero after currency conversion', () => {
    vi.mocked(useFrontendSettingsStore).mockImplementationOnce(() => createMock<ReturnType<typeof useFrontendSettingsStore>>({
      balanceUsdValueThreshold: ref({ }),
    }));
    const currencies = useCurrencies();
    useGeneralSettingsStore().settings.mainCurrency = currencies.findCurrency('TRY');
    const result = useUsdValueThreshold(BalanceSource.BLOCKCHAIN);
    expect(result.value).toBeUndefined();
  });

  it('should return undefined when no value threshold exists for the balance source', () => {
    vi.mocked(useFrontendSettingsStore).mockImplementationOnce(() => createMock<ReturnType<typeof useFrontendSettingsStore>>({
      balanceUsdValueThreshold: ref({ }),
    }));
    const result = useUsdValueThreshold(BalanceSource.MANUAL);
    expect(result.value).toBeUndefined();
  });
});
