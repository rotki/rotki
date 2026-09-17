import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DashboardLocations from '@/modules/dashboard/holdings/components/DashboardLocations.vue';
import '@test/i18n';

const netWorthLoading = ref<boolean>(true);

vi.mock('@/modules/dashboard/use-net-worth-loading', () => ({
  useNetWorthLoading: vi.fn(() => computed<boolean>(() => get(netWorthLoading))),
}));

vi.mock('@/modules/dashboard/holdings/use-dashboard-holdings', () => ({
  useDashboardHoldings: vi.fn(() => ({ holdings: computed(() => []), summary: computed(() => undefined) })),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({ getBlockchainRedirectLink: vi.fn(), getChainName: vi.fn() })),
}));

vi.mock('@/modules/core/common/use-locations', () => ({ useLocations: vi.fn(() => ({ getLocationData: vi.fn() })) }));

const stubs = {
  RuiCard: { template: '<div data-testid="dashboard-locations"><slot /></div>' },
  RuiSkeletonLoader: { template: '<div data-testid="tile-skeleton" />' },
};

function createWrapper(): VueWrapper<InstanceType<typeof DashboardLocations>> {
  return mount(DashboardLocations, { global: { stubs } });
}

describe('dashboardLocations', () => {
  beforeEach(() => {
    set(netWorthLoading, true);
  });

  it('should show skeleton tiles until the net worth has loaded', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=dashboard-locations]').exists()).toBe(true);
    expect(wrapper.findAll('[data-testid=tile-skeleton]').length).toBeGreaterThan(0);
  });

  it('should hide the card once the load settles with no holdings', async () => {
    const wrapper = createWrapper();
    set(netWorthLoading, false);
    await nextTick();

    expect(wrapper.find('[data-testid=dashboard-locations]').exists()).toBe(false);
  });
});
