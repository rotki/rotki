import { bigNumberify, Zero } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AssetsBySource from '@/modules/dashboard/holdings/components/AssetsBySource.vue';
import { type SourceContribution, SourceKind } from '@/modules/dashboard/holdings/core/holdings-types';
import { summarizeSources } from '@/modules/dashboard/holdings/core/source-summary';
import '@test/i18n';

const netWorthLoading = ref<boolean>(true);
const contributions = ref<SourceContribution[]>([]);
const tracksNothing = ref<boolean>(false);

vi.mock('@/modules/accounts/use-tracked-accounts-row', () => ({
  useTrackedAccountsRow: (): object => ({
    raised: computed<boolean>(() => get(tracksNothing)),
    row: computed(() => ({ id: 'no-tracked-accounts' })),
  }),
}));

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
  ActionEmptyState: { props: ['item'], template: '<div data-testid="empty-state" :data-key="item.id" />' },
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
    set(tracksNothing, false);
  });

  it('should hold a skeleton, not the empty state, until the net worth has loaded', () => {
    const wrapper = createWrapper();

    expect(wrapper.findAll('[data-testid=legend-skeleton]').length).toBeGreaterThan(0);
    expect(wrapper.find('[data-testid=dashboard-holdings-empty]').exists()).toBe(false);
  });

  it('should render the tracked accounts row in place of the legend when nothing is added', async () => {
    set(netWorthLoading, false);
    set(tracksNothing, true);
    const wrapper = createWrapper();
    await nextTick();

    expect(wrapper.find('[data-testid=dashboard-holdings-empty] [data-testid=empty-state]').attributes('data-key')).toBe('no-tracked-accounts');
    expect(wrapper.find('[data-testid=dashboard-source-legend]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=add-source-menu]').exists()).toBe(false);
  });

  it('should keep the legend, not the getting-started row, when a source is added but holds nothing', async () => {
    set(netWorthLoading, false);
    set(contributions, [{ kind: SourceKind.EXCHANGE, loading: false, location: 'kraken', value: Zero }]);
    const wrapper = createWrapper();
    await nextTick();

    expect(wrapper.find('[data-testid=dashboard-holdings-empty]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=add-source-menu]').exists()).toBe(true);
  });

  it('should drop the row for the legend once a source is added', async () => {
    set(netWorthLoading, false);
    set(tracksNothing, true);
    const wrapper = createWrapper();
    await nextTick();
    expect(wrapper.find('[data-testid=dashboard-holdings-empty]').exists()).toBe(true);

    set(tracksNothing, false);
    set(contributions, [{ kind: SourceKind.MANUAL, loading: false, location: 'external', value: bigNumberify(50) }]);
    await nextTick();

    expect(wrapper.find('[data-testid=dashboard-holdings-empty]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=source-bar]').exists()).toBe(true);
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
