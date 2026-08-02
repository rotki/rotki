import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useLiquityStore } from '@/modules/staking/liquity/use-liquity-store';

describe('useLiquityStore', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    vi.clearAllMocks();
  });

  it('should start with default balances and empty state', () => {
    const store = useLiquityStore();
    expect(get(store.balances)).toEqual({ balances: {}, totalCollateralRatio: null });
    expect(get(store.staking)).toEqual({});
    expect(get(store.statistics)).toBeNull();
  });
});
