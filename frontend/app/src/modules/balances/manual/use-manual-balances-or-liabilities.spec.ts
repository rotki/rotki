import type { ManualBalanceWithValue } from '@/modules/balances/types/manual-balances';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useManualBalancesOrLiabilities } from './use-manual-balances-or-liabilities';

function balance(location: string): ManualBalanceWithValue {
  return createMock<ManualBalanceWithValue>({ location });
}

const manualBalances = ref<ManualBalanceWithValue[]>([]);
const manualLiabilities = ref<ManualBalanceWithValue[]>([]);

const { spies } = vi.hoisted(() => ({
  spies: {
    fetchBalances: vi.fn(),
    fetchLiabilities: vi.fn(),
  },
}));

vi.mock('@/modules/balances/use-balances-store', () => ({
  useBalancesStore: vi.fn(() => ({ manualBalances, manualLiabilities })),
}));
vi.mock('@/modules/balances/manual/use-manual-balance-pagination', () => ({
  useManualBalancePagination: (): object => ({ fetchBalances: spies.fetchBalances, fetchLiabilities: spies.fetchLiabilities }),
}));

describe('useManualBalancesOrLiabilities', () => {
  beforeEach(() => {
    set(manualBalances, [balance('kraken'), balance('ethereum')]);
    set(manualLiabilities, [balance('ethereum'), balance('aave')]);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should expose balances or liabilities based on the type', () => {
    expect(get(useManualBalancesOrLiabilities('balances').dataSource)).toBe(get(manualBalances));
    expect(get(useManualBalancesOrLiabilities('liabilities').dataSource)).toBe(get(manualLiabilities));
  });

  it('should collect the unique locations across both lists', () => {
    const { locations } = useManualBalancesOrLiabilities('balances');
    expect(get(locations)).toEqual(['kraken', 'ethereum', 'aave']);
  });

  it('should fetch balances or liabilities based on the type', async () => {
    const payload = {} as never;
    await useManualBalancesOrLiabilities('balances').fetch(payload);
    expect(spies.fetchBalances).toHaveBeenCalledOnce();
    expect(spies.fetchLiabilities).not.toHaveBeenCalled();

    await useManualBalancesOrLiabilities('liabilities').fetch(payload);
    expect(spies.fetchLiabilities).toHaveBeenCalledOnce();
  });

  it('should react to a getter type', () => {
    const type = ref<'balances' | 'liabilities'>('balances');
    const { dataSource } = useManualBalancesOrLiabilities(() => get(type));
    expect(get(dataSource)).toBe(get(manualBalances));
    set(type, 'liabilities');
    expect(get(dataSource)).toBe(get(manualLiabilities));
  });
});
