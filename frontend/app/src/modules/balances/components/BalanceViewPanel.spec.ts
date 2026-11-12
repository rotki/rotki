import type { AssetComparison } from '@/modules/balances/view/history-comparison';
import type { SourceDifference } from '@/modules/dashboard/holdings/use-history-holdings-contributions';
import { bigNumberify } from '@rotki/common';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import BalanceViewPanel from '@/modules/balances/components/BalanceViewPanel.vue';
import { useHistoricalSnapshotStore } from '@/modules/balances/use-historical-snapshot-store';

const h = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    comparisons: ref<Map<string, AssetComparison>>(new Map()),
    refresh: vi.fn<() => Promise<void>>(),
    setView: vi.fn<(view: string) => Promise<void>>(),
    sources: ref<SourceDifference[]>([]),
    processing: ref<boolean>(false),
    totals: ref({ blocked: 0, mismatch: 0, notCompared: 0, pending: 0, reconciled: 0 }),
    triggerProcessing: vi.fn<() => Promise<void>>(),
  };
});

vi.mock('@/modules/balances/view/use-balance-view', async () => {
  const { ref } = await import('vue');
  return { useBalanceView: (): object => ({ setView: h.setView, view: ref('queried') }) };
});
vi.mock('@/modules/balances/view/use-balance-view-data', async () => {
  const { computed } = await import('vue');
  const { bigNumberify: big } = await import('@rotki/common');
  return {
    useBalanceViewData: (): object => ({
      comparisons: h.comparisons,
      netWorthDifference: computed(() => big(-500)),
      queriedNetWorth: computed(() => big(1500)),
    }),
  };
});
vi.mock('@/modules/dashboard/holdings/use-history-holdings-contributions', () => ({
  useSourceDifferences: (): object => h.sources,
}));
vi.mock('@/modules/history/reconciliation/use-bucket-reconciliation', () => ({
  useBucketReconciliation: (): object => ({ totals: h.totals }),
}));
vi.mock('@/modules/balances/use-current-historical-balances', () => ({
  useCurrentHistoricalBalances: (): object => ({ refresh: h.refresh, triggerProcessing: h.triggerProcessing }),
}));
vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): object => ({ useIsActive: (): object => h.processing }),
}));
vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): object => ({ getAssetField: (asset: string): string => asset }),
}));

const RouterLinkStub = { props: ['to'], template: '<a><slot /></a>' };
vi.mock('vue-router', () => ({ useRouter: (): object => ({ push: vi.fn() }) }));

const ENTRIES = [{ amount: bigNumberify(1), asset: 'ETH', location: 'ethereum', locationLabel: '0xA', protocol: null }];

function comparison(delta: number, valueDelta: number, manual = 0): AssetComparison {
  return {
    delta: bigNumberify(delta),
    history: bigNumberify(0),
    manual: bigNumberify(manual),
    queried: bigNumberify(0),
    valueDelta: bigNumberify(valueDelta),
  };
}

function mountPanel(): VueWrapper {
  return mount(BalanceViewPanel, {
    global: { stubs: { FiatDisplay: true, RouterLink: RouterLinkStub, ValueDisplay: true } },
  });
}

describe('balanceViewPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    h.comparisons.value = new Map();
    h.processing.value = false;
    h.sources.value = [];
    h.totals.value = { blocked: 0, mismatch: 0, notCompared: 0, pending: 0, reconciled: 0 };
    h.setView.mockReset().mockResolvedValue(undefined);
    h.refresh.mockReset().mockResolvedValue(undefined);
    h.triggerProcessing.mockReset().mockResolvedValue(undefined);
  });

  it('should ask for the history view when From history is picked', async () => {
    useHistoricalSnapshotStore().setSnapshot({ entries: ENTRIES, processingRequired: false, stale: false });
    await mountPanel().get('[data-testid="balance-view-history"]').trigger('click');

    expect(h.setView).toHaveBeenCalledExactlyOnceWith('history');
  });

  it('should describe both views in one cell, showing the selected one, so the panel keeps its height', () => {
    const description = mountPanel().get('[data-testid="balance-view-panel-description"]');
    const [queried, history] = description.findAll('span');

    expect(queried.text()).toBe('balance_view.live_description');
    expect(queried.classes()).not.toContain('invisible');
    expect(history.text()).toBe('balance_view.history_description');
    expect(history.classes()).toContain('invisible');
  });

  it('should disable History and offer processing before history has been processed', async () => {
    useHistoricalSnapshotStore().setSnapshot({ entries: [], processingRequired: true, stale: false });
    const wrapper = mountPanel();

    expect(wrapper.get('[data-testid="balance-view-history"]').attributes('disabled')).toBeDefined();
    expect(wrapper.find('[data-testid="balance-view-panel-difference"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="balance-view-panel-behind"]').text()).toContain('balance_view.not_processed');
    await wrapper.get('[data-testid="balance-view-panel-process"]').trigger('click');
    expect(h.triggerProcessing).toHaveBeenCalledOnce();
  });

  it('should say there is nothing to derive, and offer no processing, without history events', () => {
    useHistoricalSnapshotStore().setSnapshot({ entries: [], processingRequired: false, stale: false });
    const wrapper = mountPanel();

    expect(wrapper.find('[data-testid="balance-view-panel-no-events"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="balance-view-panel-process"]').exists()).toBe(false);
  });

  it('should show processing in progress instead of offering it again', () => {
    useHistoricalSnapshotStore().setSnapshot({ entries: [], processingRequired: true, stale: false });
    h.processing.value = true;
    const wrapper = mountPanel();

    expect(wrapper.find('[data-testid="balance-view-panel-processing"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="balance-view-panel-process"]').exists()).toBe(false);
  });

  it('should hold the comparison back until the snapshot has loaded', () => {
    expect(mountPanel().find('[data-testid="balance-view-panel-difference"]').exists()).toBe(false);
  });

  it('should list the three largest gaps by value, not by amount', () => {
    useHistoricalSnapshotStore().setSnapshot({ entries: ENTRIES, processingRequired: false, stale: false });
    h.comparisons.value = new Map([
      ['SPAM', comparison(-1000000, -1)],
      ['BTC', comparison(-1.31, -93000, 1.5)],
      ['ETH', comparison(-13.51, -27000, 3)],
      ['DAI', comparison(498, 498)],
      ['USDC', comparison(0, 0)],
    ]);

    const assets = mountPanel().findAll('[data-testid="balance-view-panel-gap"]').map(link => link.text());

    expect(assets).toStrictEqual(['BTC', 'ETH', 'DAI']);
  });

  it('should name how each source relates to history', () => {
    useHistoricalSnapshotStore().setSnapshot({ entries: ENTRIES, processingRequired: false, stale: false });
    h.sources.value = [
      { basis: 'derived', delta: bigNumberify(-20548), kind: 'blockchain' },
      { basis: 'queried', delta: bigNumberify(0), kind: 'bank' },
      { basis: 'excluded', delta: bigNumberify(-112160), kind: 'manual' },
    ];

    const bases = mountPanel().get('[data-testid="balance-view-panel-figures"]').findAll('[data-basis]').map(cell => cell.text());

    expect(bases).toStrictEqual(['balance_view.basis_derived', 'balance_view.basis_live', 'balance_view.not_in_history']);
  });

  it('should offer processing when the snapshot is behind recent event edits', async () => {
    useHistoricalSnapshotStore().setSnapshot({ entries: ENTRIES, processingRequired: false, stale: true });
    const wrapper = mountPanel();
    await wrapper.get('[data-testid="balance-view-panel-process"]').trigger('click');

    expect(h.triggerProcessing).toHaveBeenCalledOnce();
  });

  it('should offer a retry, and no processing, when the snapshot failed to load', async () => {
    useHistoricalSnapshotStore().setError('backend down');
    const wrapper = mountPanel();
    await flushPromises();

    expect(wrapper.find('[data-testid="balance-view-panel-process"]').exists()).toBe(false);
    await wrapper.get('[data-testid="balance-view-panel-error"]').find('button').trigger('click');
    expect(h.refresh).toHaveBeenCalledOnce();
  });

  it('should count reconciliation issues next to the review link', () => {
    h.totals.value = { blocked: 1, mismatch: 4, notCompared: 0, pending: 0, reconciled: 0 };

    expect(mountPanel().text()).toContain('balance_view.reconciliation_issues');
  });
});
