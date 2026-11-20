import type { AssetComparison } from '@/modules/balances/view/history-comparison';
import type { SourceDifference } from '@/modules/dashboard/holdings/use-history-holdings-contributions';
import { type AssetBalanceWithPriceAndChains, bigNumberify } from '@rotki/common';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import BalanceViewPanel from '@/modules/balances/components/BalanceViewPanel.vue';
import { useHistoricalSnapshotStore } from '@/modules/balances/use-historical-snapshot-store';

const h = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    balances: ref<AssetBalanceWithPriceAndChains[]>([]),
    comparisons: ref<Map<string, AssetComparison>>(new Map()),
    getAssetComparison: vi.fn<(identifier: string, groupCollection?: boolean) => AssetComparison>(),
    getAssetField: vi.fn<(asset: string, field: string) => string | undefined>(),
    liabilityComparisons: ref<Map<string, AssetComparison>>(new Map()),
    processing: ref<boolean>(false),
    push: vi.fn<(...args: unknown[]) => Promise<void>>(),
    refresh: vi.fn<() => Promise<void>>(),
    setView: vi.fn<(view: string) => Promise<void>>(),
    sources: ref<SourceDifference[]>([]),
    totals: ref({ blocked: 0, mismatch: 0, notCompared: 0, pending: 0, reconciled: 0 }),
    triggerProcessing: vi.fn<() => Promise<void>>(),
  };
});

vi.mock('@/modules/core/common/feature-flags', () => ({ isAccountingUpdateEnabled: (): boolean => true }));
vi.mock('@/modules/balances/view/use-balance-view', async () => {
  const { ref } = await import('vue');
  return { useBalanceView: (): object => ({ setView: h.setView, view: ref('queried') }) };
});
vi.mock('@/modules/balances/view/use-balance-view-data', async () => {
  const { computed } = await import('vue');
  const { bigNumberify: big } = await import('@rotki/common');
  return {
    useBalanceViewData: (): object => ({
      balances: h.balances,
      comparisons: h.comparisons,
      getAssetComparison: h.getAssetComparison,
      liabilityComparisons: h.liabilityComparisons,
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
  useAssetInfoRetrieval: (): object => ({ getAssetField: h.getAssetField }),
}));

const RouterLinkStub = { props: ['to'], template: '<a><slot /></a>' };
vi.mock('vue-router', () => ({ useRouter: (): object => ({ push: h.push }) }));

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

function reconciliationTo(asset: string): object {
  return { name: '/history/data-issues/[[tab]]', params: { tab: 'reconciliation' }, query: { asset, view: 'all' } };
}

function gapReconcileTo(wrapper: VueWrapper): unknown {
  return wrapper.findAllComponents(RouterLinkStub)
    .find(link => link.attributes('data-testid') === 'balance-view-panel-gap-reconcile')
    ?.props('to');
}

function mountPanel(props?: { asset?: string; isCollectionParent?: boolean }): VueWrapper {
  return mount(BalanceViewPanel, {
    global: { stubs: { FiatDisplay: true, RouterLink: RouterLinkStub, ValueDisplay: true } },
    props,
  });
}

describe('balanceViewPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    h.balances.value = [];
    h.comparisons.value = new Map();
    h.liabilityComparisons.value = new Map();
    h.processing.value = false;
    h.sources.value = [];
    h.totals.value = { blocked: 0, mismatch: 0, notCompared: 0, pending: 0, reconciled: 0 };
    h.getAssetComparison.mockReset().mockReturnValue(comparison(0, 0));
    h.getAssetField.mockReset().mockImplementation((asset: string) => asset);
    h.push.mockReset().mockResolvedValue(undefined);
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

  it('should surface liability gaps even when the same asset agrees on the asset side', () => {
    useHistoricalSnapshotStore().setSnapshot({ entries: ENTRIES, processingRequired: false, stale: false });
    h.comparisons.value = new Map([['DAI', comparison(0, 0)]]);
    h.liabilityComparisons.value = new Map([['DAI', comparison(-500, -500)]]);

    const wrapper = mountPanel();

    expect(wrapper.findAll('[data-testid="balance-view-panel-gap"]').map(link => link.text())).toStrictEqual(['DAI']);
    expect(gapReconcileTo(wrapper)).toEqual(reconciliationTo('DAI'));
  });

  it('should link folded collection gaps to reconciliation by symbol', () => {
    const usdcMain = 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48';
    useHistoricalSnapshotStore().setSnapshot({ entries: ENTRIES, processingRequired: false, stale: false });
    const row = { amount: bigNumberify(100), asset: usdcMain, price: bigNumberify(1), value: bigNumberify(100) };
    h.balances.value = [{ ...row, breakdown: [row] }];
    h.comparisons.value = new Map([[usdcMain, comparison(-50, -50)]]);
    h.getAssetField.mockImplementation((asset: string) => (asset === usdcMain ? 'USDC' : asset));

    expect(gapReconcileTo(mountPanel())).toEqual(reconciliationTo('USDC'));
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

    expect(mountPanel().get('[data-testid="balance-view-panel-reconciliation-summary"]').text())
      .toBe('balance_view.reconciliation_issues::1, 4');
  });

  it('should show only the scoped asset comparison, omit portfolio issue counts, and link review to that asset', async () => {
    const debtToken = 'eip155:1/erc20:0x6df1C1E379bC5a00a7b4C6e67A203333772f45A8';
    useHistoricalSnapshotStore().setSnapshot({ entries: ENTRIES, processingRequired: false, stale: false });
    h.comparisons.value = new Map([['BTC', comparison(-1.31, -93000)]]);
    h.sources.value = [{ basis: 'derived', delta: bigNumberify(-20548), kind: 'blockchain' }];
    h.totals.value = { blocked: 1, mismatch: 4, notCompared: 0, pending: 0, reconciled: 0 };
    h.getAssetComparison.mockReturnValue(comparison(-6.22, -6.22, 2));

    const wrapper = mountPanel({ asset: debtToken });

    expect(h.getAssetComparison).toHaveBeenCalledWith(debtToken, false);
    expect(wrapper.find('[data-testid="balance-view-panel-asset-figures"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="balance-view-panel-asset-manual"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="balance-view-panel-figures"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="balance-view-panel-reconciliation-summary"]').text())
      .toBe('data_issues.tabs.reconciliation');

    await wrapper.get('[data-testid="balance-view-panel-review"]').trigger('click');
    expect(h.push).toHaveBeenCalledExactlyOnceWith(reconciliationTo(debtToken));
  });

  it('should link review by symbol and forward isCollectionParent on a collection parent page', async () => {
    const usdcMain = 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48';
    useHistoricalSnapshotStore().setSnapshot({ entries: ENTRIES, processingRequired: false, stale: false });
    h.getAssetField.mockReturnValue('USDC');
    h.getAssetComparison.mockReturnValue(comparison(0, 0, 5));

    const wrapper = mountPanel({ asset: usdcMain, isCollectionParent: true });

    expect(h.getAssetComparison).toHaveBeenCalledWith(usdcMain, true);
    expect(wrapper.find('[data-testid="balance-view-panel-asset-manual"]').exists()).toBe(false);

    await wrapper.get('[data-testid="balance-view-panel-review"]').trigger('click');
    expect(h.push).toHaveBeenCalledExactlyOnceWith(reconciliationTo('USDC'));
  });
});
