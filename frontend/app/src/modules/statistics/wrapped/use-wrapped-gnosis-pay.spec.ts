import type { WrapStatisticsResult } from '@/modules/statistics/api/use-wrap-statistics-api';
import { bigNumberify } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useWrappedGnosisPay } from '@/modules/statistics/wrapped/use-wrapped-gnosis-pay';

const mockAllowed = ref<boolean>(true);
const mockGetApiKey = vi.fn<(name: string) => string>(() => 'key');
const mockFindCurrency = vi.fn();

vi.mock('@/modules/premium/use-feature-access', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/premium/use-feature-access')>(),
  useFeatureAccess: (): { allowed: typeof mockAllowed } => ({ allowed: mockAllowed }),
}));

vi.mock('@/modules/settings/api-keys/external/use-external-api-keys', () => ({
  useExternalApiKeys: (): { getApiKey: typeof mockGetApiKey } => ({ getApiKey: mockGetApiKey }),
}));

vi.mock('@/modules/assets/amount-display/currencies', () => ({
  useCurrencies: (): { findCurrency: typeof mockFindCurrency } => ({ findCurrency: mockFindCurrency }),
}));

function summary(symbols: string[]): WrapStatisticsResult {
  return {
    ethOnGas: bigNumberify(0),
    ethOnGasPerAddress: {},
    gnosisMaxPaymentsByCurrency: symbols.map(symbol => ({ amount: bigNumberify(10), symbol })),
    score: 0,
    topDaysByNumberOfTransactions: [],
    tradesByExchange: {},
    transactionsPerChain: {},
    transactionsPerProtocol: [],
  };
}

describe('useWrappedGnosisPay', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(mockAllowed, true);
    mockGetApiKey.mockReturnValue('key');
    mockFindCurrency.mockReset();
  });

  it('should expose the gnosis pay api key', () => {
    mockGetApiKey.mockReturnValue('my-key');
    const { gnosisPayKey } = useWrappedGnosisPay(null);
    expect(get(gnosisPayKey)).toBe('my-key');
    expect(mockGetApiKey).toHaveBeenCalledWith('gnosis_pay');
  });

  it('should show gnosis data only when allowed and a key exists', () => {
    const { showGnosisData } = useWrappedGnosisPay(null);
    expect(get(showGnosisData)).toBe(true);
  });

  it('should hide gnosis data when not allowed', () => {
    set(mockAllowed, false);
    const { showGnosisData } = useWrappedGnosisPay(null);
    expect(get(showGnosisData)).toBe(false);
  });

  it('should hide gnosis data when no key is set', () => {
    mockGetApiKey.mockReturnValue('');
    const { showGnosisData } = useWrappedGnosisPay(null);
    expect(get(showGnosisData)).toBe(false);
  });

  it('should return an empty result when the summary is missing', () => {
    const { gnosisPayResult } = useWrappedGnosisPay(undefined);
    expect(get(gnosisPayResult)).toEqual([]);
  });

  it('should map payments using the resolved currency metadata', () => {
    mockFindCurrency.mockReturnValue({ name: 'US Dollar', unicodeSymbol: '$' });
    const { gnosisPayResult } = useWrappedGnosisPay(summary(['USD']));
    expect(get(gnosisPayResult)).toEqual([
      { amount: bigNumberify(10), code: 'USD', name: 'US Dollar', symbol: '$' },
    ]);
  });

  it('should fall back to the raw symbol when the currency lookup throws', () => {
    mockFindCurrency.mockImplementation(() => {
      throw new Error('unknown');
    });
    const { gnosisPayResult } = useWrappedGnosisPay(summary(['XYZ']));
    expect(get(gnosisPayResult)).toEqual([
      { amount: bigNumberify(10), code: 'XYZ', name: 'XYZ', symbol: 'XYZ' },
    ]);
  });

  it('should skip payments when the currency lookup returns nothing', () => {
    mockFindCurrency.mockReturnValue(undefined);
    const { gnosisPayResult } = useWrappedGnosisPay(summary(['ZZZ']));
    expect(get(gnosisPayResult)).toEqual([]);
  });
});
