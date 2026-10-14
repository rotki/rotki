import { type AssetBalanceWithPrice, bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import LocationAssets from '@/modules/balances/LocationAssets.vue';

const { breakdown, isInitialLoading, isRefreshing } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    breakdown: ref<AssetBalanceWithPrice[]>([]),
    isInitialLoading: ref<boolean>(false),
    isRefreshing: ref<boolean>(false),
  };
});

vi.mock('@/modules/balances/use-aggregated-balances', async () => {
  const { computed } = await import('vue');
  return {
    useAggregatedBalances: (): Record<string, unknown> => ({
      useLocationBreakdown: () => computed(() => breakdown.value),
    }),
  };
});

vi.mock('@/modules/balances/use-location-balance-status', async () => {
  const { computed } = await import('vue');
  return {
    useLocationBalanceStatus: (): Record<string, unknown> => ({
      isInitialLoading: computed(() => isInitialLoading.value),
      isRefreshing: computed(() => isRefreshing.value),
    }),
  };
});

vi.mock('@/modules/core/common/use-locations', async () => {
  const { computed } = await import('vue');
  return {
    useLocations: (): Record<string, unknown> => ({
      useLocationData: () => computed(() => ({ identifier: 'kraken', name: 'Kraken' })),
    }),
  };
});

function balance(asset: string): AssetBalanceWithPrice {
  return { amount: bigNumberify(1), asset, price: bigNumberify(2), value: bigNumberify(2) };
}

function createWrapper(): VueWrapper<any> {
  return mount(LocationAssets, {
    global: {
      stubs: {
        AssetBalances: true,
        AssetBalancesSkeleton: { template: '<div data-testid="asset-balances-skeleton" />' },
        LocationAssetsEmpty: { props: ['name'], template: '<div data-testid="location-assets-empty">{{ name }}</div>' },
        TableFrame: { template: '<section><slot name="toolbar" /><slot /></section>' },
        TableSearchField: true,
      },
    },
    props: { identifier: 'kraken' },
  });
}

describe('locationAssets', () => {
  beforeEach(() => {
    breakdown.value = [];
    isInitialLoading.value = false;
    isRefreshing.value = false;
  });

  it('shows skeleton rows while the first load runs', () => {
    isInitialLoading.value = true;
    const wrapper = createWrapper();
    expect(wrapper.find('[data-testid=asset-balances-skeleton]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=location-assets-empty]').exists()).toBe(false);
  });

  it('shows the empty state, named for the location, once nothing came back', () => {
    const wrapper = createWrapper();
    const empty = wrapper.find('[data-testid=location-assets-empty]');
    expect(empty.exists()).toBe(true);
    expect(empty.text()).toBe('Kraken');
  });

  it('keeps the rows usable during a refresh and says it is refreshing', () => {
    breakdown.value = [balance('BTC')];
    isRefreshing.value = true;
    const wrapper = createWrapper();
    const table = wrapper.findComponent({ name: 'AssetBalances' });
    expect(table.exists()).toBe(true);
    expect(table.attributes('loading')).not.toBe('true');
    expect(wrapper.find('[data-testid=location-assets-refreshing]').exists()).toBe(true);
  });

  it('hides the refreshing hint when nothing is running', () => {
    breakdown.value = [balance('BTC')];
    const wrapper = createWrapper();
    expect(wrapper.find('[data-testid=location-assets-refreshing]').exists()).toBe(false);
  });
});
