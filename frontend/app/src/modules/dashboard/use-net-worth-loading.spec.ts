import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBalancesLoading } from '@/modules/balances/use-balance-loading';
import { useBalanceStatus } from '@/modules/balances/use-balance-status';
import { useNetWorthLoading } from '@/modules/dashboard/use-net-worth-loading';

/**
 * The seam: a latch that starts closed and opens once, when the first load settles. It must not
 * track liveness in either direction. The balance activities are submitted after the dashboard
 * renders, so a live read is false on those first frames; and once it has opened a refresh must
 * not close it again, or the total the user is reading would blank on every refresh.
 */

vi.mock('@/modules/balances/use-balance-loading', () => ({ useBalancesLoading: vi.fn() }));

vi.mock('@/modules/balances/use-balance-status', () => ({ useBalanceStatus: vi.fn() }));

describe('useNetWorthLoading', () => {
  const loading = ref<boolean>(false);
  const cached = ref<boolean>(false);

  beforeEach(() => {
    setActivePinia(createPinia());
    set(loading, false);
    set(cached, false);

    vi.mocked(useBalancesLoading).mockReturnValue({
      loadingBalances: computed<boolean>(() => get(loading)),
      loadingBalancesAndDetection: computed<boolean>(() => get(loading)),
      loadingBlockchainBalances: computed<boolean>(() => get(loading)),
    });

    vi.mocked(useBalanceStatus).mockReturnValue({
      hasCachedData: computed<boolean>(() => get(cached)),
      isInitialLoading: computed<boolean>(() => get(loading) && !get(cached)),
      isRefreshing: computed<boolean>(() => get(loading)),
    });
  });

  it('should start closed, before any balance work has been submitted', () => {
    expect(get(useNetWorthLoading())).toBe(true);
  });

  it('should stay closed while a chain has landed but the load runs on', async () => {
    set(loading, true);
    const netWorthLoading = useNetWorthLoading();
    expect(get(netWorthLoading)).toBe(true);

    set(cached, true);
    await nextTick();

    expect(get(netWorthLoading)).toBe(true);
  });

  it('should open when the first load settles', async () => {
    set(loading, true);
    set(cached, true);
    const netWorthLoading = useNetWorthLoading();
    expect(get(netWorthLoading)).toBe(true);

    set(loading, false);
    await nextTick();

    expect(get(netWorthLoading)).toBe(false);
  });

  it('should stay open across a later refresh', async () => {
    set(cached, true);
    const netWorthLoading = useNetWorthLoading();
    expect(get(netWorthLoading)).toBe(false);

    set(loading, true);
    await nextTick();

    expect(get(netWorthLoading)).toBe(false);
  });
});
