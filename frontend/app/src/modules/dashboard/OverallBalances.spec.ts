import type { NetValueChartData } from '@/modules/dashboard/graph/types';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import OverallBalances from '@/modules/dashboard/OverallBalances.vue';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

const state = vi.hoisted(() => ({ loading: false, netWorthLoading: false }));
const { mockFetchNetValue } = vi.hoisted(() => ({ mockFetchNetValue: vi.fn() }));

vi.mock('@/modules/statistics/use-statistics-data-fetching', () => ({
  useStatisticsDataFetching: vi.fn(() => ({ fetchNetValue: mockFetchNetValue })),
}));

vi.mock('@/modules/balances/use-balance-loading', async () => {
  const { computed: createComputed } = await import('vue');
  return {
    useBalancesLoading: vi.fn(() => ({
      loadingBlockchainBalances: createComputed<boolean>(() => state.loading),
    })),
  };
});

vi.mock('@/modules/dashboard/use-net-worth-loading', async () => {
  const { computed: createComputed } = await import('vue');
  return {
    useNetWorthLoading: vi.fn(() => createComputed<boolean>(() => state.netWorthLoading)),
  };
});

vi.mock('@/modules/statistics/use-statistics-store', async () => {
  const { defineStore } = await import('pinia');
  const { ref: createRef } = await import('vue');
  const emptyNetValue: NetValueChartData = { data: [], snapshotCount: 0, times: [] };
  return {
    useStatisticsStore: defineStore('statistics', () => {
      const totalNetWorth = createRef(bigNumberify('1500.5'));
      const netValueError = createRef<string | undefined>(undefined);
      const getNetValue = vi.fn(() => emptyNetValue);
      return { getNetValue, netValueError, totalNetWorth };
    }),
  };
});

describe('overallBalances', () => {
  let wrapper: VueWrapper<InstanceType<typeof OverallBalances>>;

  const netWorthSelector = '[data-testid=overall-balances-net-worth] [data-testid=fiat-display]';
  const skeletonSelector = '[data-testid=overall-balances-net-worth-loading]';
  const deltaSkeletonSelector = '[data-testid=overall-balances-delta-loading]';

  function createWrapper(): VueWrapper<InstanceType<typeof OverallBalances>> {
    return mount(OverallBalances, {
      global: {
        stubs: {
          FiatDisplay: {
            props: { value: { required: true, type: Object } },
            template: '<span data-testid="fiat-display">{{ value.toString() }}</span>',
          },
          NetWorthChart: true,
          SnapshotActionButton: true,
          TimeframeSelector: true,
        },
      },
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    state.loading = false;
    state.netWorthLoading = false;
    vi.clearAllMocks();
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should show a skeleton instead of a zero while the first balances load', () => {
    state.loading = true;
    state.netWorthLoading = true;
    wrapper = createWrapper();

    expect(wrapper.find(skeletonSelector).exists()).toBe(true);
    expect(wrapper.find(netWorthSelector).exists()).toBe(false);
    expect(wrapper.find(deltaSkeletonSelector).exists()).toBe(true);
  });

  it('should skeleton the header before any balance work is submitted', () => {
    state.loading = false;
    state.netWorthLoading = true;
    wrapper = createWrapper();

    expect(wrapper.find(skeletonSelector).exists()).toBe(true);
    expect(wrapper.find(deltaSkeletonSelector).exists()).toBe(true);
  });

  it('should keep showing a known net worth during a refresh', () => {
    state.loading = true;
    state.netWorthLoading = false;
    wrapper = createWrapper();

    expect(wrapper.find(skeletonSelector).exists()).toBe(false);
    expect(wrapper.find(netWorthSelector).text()).toBe('1500.5');
    expect(wrapper.find(deltaSkeletonSelector).exists()).toBe(true);
  });

  it('should show the net worth and the delta once everything settles', () => {
    wrapper = createWrapper();

    expect(wrapper.find(skeletonSelector).exists()).toBe(false);
    expect(wrapper.find(netWorthSelector).text()).toBe('1500.5');
    expect(wrapper.find(deltaSkeletonSelector).exists()).toBe(false);
  });

  describe('when the net value read failed', () => {
    const errorSelector = '[data-testid=net-value-error]';

    function failWith(message: string): VueWrapper<InstanceType<typeof OverallBalances>> {
      const created = createWrapper();
      set(storeToRefs(useStatisticsStore()).netValueError, message);
      return created;
    }

    it('should say why the graph is empty rather than leaving a blank chart', async () => {
      wrapper = failWith('backend is down');
      await nextTick();

      expect(wrapper.find(errorSelector).text()).toContain('backend is down');
    });

    it('should stay quiet while the load is still running', async () => {
      state.netWorthLoading = true;
      wrapper = failWith('backend is down');
      await nextTick();

      expect(wrapper.find(errorSelector).exists()).toBe(false);
    });

    it('should show nothing when the read succeeded', () => {
      wrapper = createWrapper();

      expect(wrapper.find(errorSelector).exists()).toBe(false);
    });

    it('should offer a retry that re-reads the net value', async () => {
      wrapper = failWith('backend is down');
      await nextTick();

      await wrapper.find('[data-testid=net-value-retry]').trigger('click');

      expect(mockFetchNetValue).toHaveBeenCalledOnce();
    });
  });
});
