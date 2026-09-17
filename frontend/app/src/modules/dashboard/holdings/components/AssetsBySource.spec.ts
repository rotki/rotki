import { bigNumberify, Zero } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AssetsBySource from '@/modules/dashboard/holdings/components/AssetsBySource.vue';
import { type SourceContribution, SourceKind } from '@/modules/dashboard/holdings/core/holdings-types';
import { summarizeSources } from '@/modules/dashboard/holdings/core/source-summary';
import '@test/i18n';

const netWorthLoading = ref<boolean>(true);
const contributions = ref<SourceContribution[]>([]);

vi.mock('@/modules/dashboard/use-net-worth-loading', () => ({
  useNetWorthLoading: vi.fn(() => computed<boolean>(() => get(netWorthLoading))),
}));

vi.mock('@/modules/dashboard/holdings/use-dashboard-holdings', () => ({
  useDashboardHoldings: vi.fn(() => ({
    holdings: computed(() => []),
    summary: computed(() => summarizeSources(get(contributions), { liabilities: Zero, nfts: undefined })),
  })),
}));

vi.mock('@/modules/settings/use-setting', () => ({ useSetting: vi.fn(() => ref(true)) }));

const stubs = {
  AddSourceMenu: { template: '<div data-testid="add-source-menu" />' },
  FiatDisplay: true,
  PercentageDisplay: true,
  RuiIcon: true,
  RuiSkeletonLoader: { template: '<div data-testid="legend-skeleton" />' },
  SourceBar: { template: '<div data-testid="source-bar" />' },
};

function createWrapper(): VueWrapper<InstanceType<typeof AssetsBySource>> {
  return mount(AssetsBySource, { global: { stubs } });
}

describe('assetsBySource', () => {
  beforeEach(() => {
    set(netWorthLoading, true);
    set(contributions, []);
  });

  it('should hold a skeleton, not the empty state, until the net worth has loaded', () => {
    const wrapper = createWrapper();

    expect(wrapper.findAll('[data-testid=legend-skeleton]').length).toBeGreaterThan(0);
    expect(wrapper.find('[data-testid=add-source-menu]').exists()).toBe(false);
  });

  it('should offer to add a source once the load settles with none', async () => {
    const wrapper = createWrapper();
    set(netWorthLoading, false);
    await nextTick();

    expect(wrapper.find('[data-testid=legend-skeleton]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=add-source-menu]').exists()).toBe(true);
  });

  it('should hold the bar back until every source is priced, since its shares are partial until then', async () => {
    set(netWorthLoading, false);
    set(contributions, [
      { chain: 'btc', kind: SourceKind.BLOCKCHAIN, loading: true, value: Zero },
      { kind: SourceKind.MANUAL, loading: false, location: 'external', value: bigNumberify(50) },
    ]);
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=source-bar]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=legend-skeleton]').exists()).toBe(true);

    set(contributions, [
      { chain: 'btc', kind: SourceKind.BLOCKCHAIN, loading: false, value: bigNumberify(150) },
      { kind: SourceKind.MANUAL, loading: false, location: 'external', value: bigNumberify(50) },
    ]);
    await nextTick();

    expect(wrapper.find('[data-testid=source-bar]').exists()).toBe(true);
  });
});
