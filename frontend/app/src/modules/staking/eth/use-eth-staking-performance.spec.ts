import type { Ref } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useEthStakingPerformance } from '@/modules/staking/eth/use-eth-staking-performance';

interface MockPerformance { entriesTotal: number }

const mockPagination = ref<Record<string, unknown>>({});
const mockPerformance = ref<MockPerformance | undefined>({ entriesTotal: 5 });
const mockPerformanceLoading = ref<boolean>(false);
const mockRefreshPerformance = vi.fn(async (_userInitiated?: boolean) => {});

vi.mock('@/modules/staking/eth2/use-eth2', () => ({
  useEth2Staking: (): {
    pagination: Ref<Record<string, unknown>>;
    performance: Ref<MockPerformance | undefined>;
    performanceLoading: Ref<boolean>;
    refreshPerformance: typeof mockRefreshPerformance;
  } => ({
    pagination: mockPagination,
    performance: mockPerformance,
    performanceLoading: mockPerformanceLoading,
    refreshPerformance: mockRefreshPerformance,
  }),
}));

describe('useEthStakingPerformance', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(mockPerformance, { entriesTotal: 5 });
    set(mockPerformanceLoading, false);
  });

  it('should pass through the underlying performance, loading and pagination refs', () => {
    const { performance, performanceLoading, performancePagination } = useEthStakingPerformance();
    expect(performance).toBe(mockPerformance);
    expect(performanceLoading).toBe(mockPerformanceLoading);
    expect(performancePagination).toBe(mockPagination);
  });

  it('should return the entries total from getPerformance', () => {
    const { getPerformance } = useEthStakingPerformance();
    expect(getPerformance()).toEqual({ entriesTotal: 5 });
  });

  it('should default entries total to zero when there is no performance', () => {
    set(mockPerformance, undefined);
    const { getPerformance } = useEthStakingPerformance();
    expect(getPerformance()).toEqual({ entriesTotal: 0 });
  });

  it('should forward the user-initiated flag to refreshPerformance', async () => {
    const { refreshPerformance } = useEthStakingPerformance();
    await refreshPerformance(true);
    expect(mockRefreshPerformance).toHaveBeenCalledWith(true);
  });

  it('should default the user-initiated flag to false', async () => {
    const { refreshPerformance } = useEthStakingPerformance();
    await refreshPerformance();
    expect(mockRefreshPerformance).toHaveBeenCalledWith(false);
  });
});
