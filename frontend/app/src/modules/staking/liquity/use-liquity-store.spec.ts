import { bigNumberify, type CommonQueryStatusData } from '@rotki/common';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Section } from '@/modules/core/common/status';
import { useLiquityStore } from '@/modules/staking/liquity/use-liquity-store';

const mockResetStatus = vi.fn();

vi.mock('@/modules/shell/sync-progress/use-status-updater', () => ({
  useStatusUpdater: (): { resetStatus: typeof mockResetStatus } => ({ resetStatus: mockResetStatus }),
}));

describe('useLiquityStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('should start with default balances and empty state', () => {
    const store = useLiquityStore();
    expect(get(store.balances)).toEqual({ balances: {}, totalCollateralRatio: null });
    expect(get(store.staking)).toEqual({});
    expect(get(store.stakingPools)).toEqual({});
    expect(get(store.statistics)).toBeNull();
    expect(get(store.stakingQueryStatus)).toBeUndefined();
  });

  it('should set the staking query status', () => {
    const store = useLiquityStore();
    const status: CommonQueryStatusData = { processed: 1, total: 2 };
    store.setStakingQueryStatus(status);
    expect(get(store.stakingQueryStatus)).toEqual(status);
  });

  it('should clear the staking query status when set to null', () => {
    const store = useLiquityStore();
    store.setStakingQueryStatus({ processed: 1, total: 2 });
    store.setStakingQueryStatus(null);
    expect(get(store.stakingQueryStatus)).toBeNull();
  });

  it('should reset balances, staking and statistics to their defaults', () => {
    const store = useLiquityStore();
    store.balances = { balances: {}, totalCollateralRatio: bigNumberify(2) };
    store.statistics = {};

    store.reset();

    expect(get(store.balances)).toEqual({ balances: {}, totalCollateralRatio: null });
    expect(get(store.staking)).toEqual({});
    expect(get(store.statistics)).toBeNull();
  });

  it('should reset the status of all three liquity sections', () => {
    const store = useLiquityStore();
    store.reset();

    expect(mockResetStatus).toHaveBeenCalledWith({ section: Section.DEFI_LIQUITY_BALANCES });
    expect(mockResetStatus).toHaveBeenCalledWith({ section: Section.DEFI_LIQUITY_STAKING });
    expect(mockResetStatus).toHaveBeenCalledWith({ section: Section.DEFI_LIQUITY_STATISTICS });
  });
});
