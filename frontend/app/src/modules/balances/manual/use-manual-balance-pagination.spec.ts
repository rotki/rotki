import type { ManualBalanceRequestPayload, ManualBalanceWithPrice } from '@/modules/balances/types/manual-balances';
import type { Collection } from '@/modules/core/common/collection';
import { bigNumberify } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useManualBalancePagination } from './use-manual-balance-pagination';

const manualBalances = ref<{ id: number }[]>([{ id: 1 }]);
const manualLiabilities = ref<{ id: number }[]>([{ id: 2 }]);

const { spies } = vi.hoisted(() => ({
  spies: {
    sortAndFilterManualBalance: vi.fn(),
    getAssetPrice: vi.fn(),
  },
}));

vi.mock('@/modules/balances/use-balances-store', () => ({
  useBalancesStore: vi.fn(() => ({ manualBalances, manualLiabilities })),
}));
vi.mock('@/modules/assets/prices/use-price-utils', () => ({
  usePriceUtils: (): object => ({ getAssetPrice: spies.getAssetPrice }),
}));
vi.mock('@/modules/balances/manual-balances', () => ({
  sortAndFilterManualBalance: spies.sortAndFilterManualBalance,
}));

const payload = createMock<ManualBalanceRequestPayload>({ limit: 10, offset: 0 });

describe('useManualBalancePagination', () => {
  beforeEach(() => {
    spies.sortAndFilterManualBalance.mockReturnValue({ data: [], found: 0, limit: 10, total: 0 } satisfies Collection<ManualBalanceWithPrice>);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should sort and filter the manual balances', async () => {
    const result = await useManualBalancePagination().fetchBalances(payload);
    expect(spies.sortAndFilterManualBalance).toHaveBeenCalledWith(get(manualBalances), payload, expect.any(Object));
    expect(result).toEqual({ data: [], found: 0, limit: 10, total: 0 });
  });

  it('should sort and filter the manual liabilities', async () => {
    await useManualBalancePagination().fetchLiabilities(payload);
    expect(spies.sortAndFilterManualBalance).toHaveBeenCalledWith(get(manualLiabilities), payload, expect.any(Object));
  });

  it('should resolve asset prices through the price utils', async () => {
    spies.getAssetPrice.mockReturnValue(bigNumberify(42));
    await useManualBalancePagination().fetchBalances(payload);
    const resolvers = spies.sortAndFilterManualBalance.mock.calls[0][2];
    expect(resolvers.resolveAssetPrice('ETH')).toEqual(bigNumberify(42));
    expect(spies.getAssetPrice).toHaveBeenCalledWith('ETH');
  });
});
