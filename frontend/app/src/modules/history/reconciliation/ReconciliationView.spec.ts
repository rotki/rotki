import type { UseDataIssuesDetectionReturn } from '@/modules/history/data-issues/use-data-issues-detection';
import type { UseBucketReconciliationApiReturn } from '@/modules/history/reconciliation/api/use-bucket-reconciliation-api';
import type { ReconciliationAccount, ReconciliationResponse, StatusCounts } from '@/modules/history/reconciliation/schemas';
import type { NamedFailure } from '@/modules/shell/components/named-failure';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { FetchError } from 'ofetch';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useRouter } from 'vue-router';
import { createStatusError } from '@/modules/core/api/response-handlers';
import { useDataIssuesAutoReload } from '@/modules/history/data-issues/use-data-issues-auto-reload';
import ReconciliationView from '@/modules/history/reconciliation/ReconciliationView.vue';
import { useBucketReconciliationStore } from '@/modules/history/reconciliation/use-bucket-reconciliation-store';
import { createRuiPlugin } from '@/plugins/rui';

const { fetchAccount, fetchSummary } = vi.hoisted(() => ({
  fetchAccount: vi.fn<() => Promise<ReconciliationAccount | undefined>>(),
  fetchSummary: vi.fn<(asset?: string) => Promise<ReconciliationResponse>>(),
}));

vi.mock('@/modules/history/reconciliation/api/use-bucket-reconciliation-api', () => ({
  ACCOUNT_PAGE_SIZE: 50,
  MAX_ACCOUNT_BUCKETS: 500,
  useBucketReconciliationApi: (): UseBucketReconciliationApiReturn => ({ fetchAccount, fetchSummary }),
}));

vi.mock('@/modules/history/data-issues/use-data-issues-auto-reload', () => ({
  useDataIssuesAutoReload: vi.fn(),
}));

vi.mock('@/modules/history/data-issues/use-data-issues-detection', async () => {
  const { ref } = await import('vue');
  return {
    useDataIssuesDetection: (): UseDataIssuesDetectionReturn => ({
      detect: vi.fn(async () => ({ conflict: false, success: true })),
      detectFailure: ref<NamedFailure | undefined>(undefined),
      detecting: ref<boolean>(false),
    }),
  };
});

function counts(overrides: Partial<StatusCounts> = {}): StatusCounts {
  return { blocked: 0, mismatch: 0, notCompared: 0, pending: 0, reconciled: 0, ...overrides };
}

function account(overrides: Partial<ReconciliationAccount> = {}): ReconciliationAccount {
  return {
    counts: counts({ reconciled: 1 }),
    historySyncedTo: 100,
    isExchange: false,
    lastComparedAt: 100,
    lastEventTs: 1000,
    location: 'ethereum',
    locationLabel: '0x0000000000000000000000000000000000000001',
    ...overrides,
  };
}

function report(stale = false, overrides: Partial<ReconciliationResponse> = {}): ReconciliationResponse {
  const totals = counts(stale ? { pending: 1 } : { reconciled: 1 });
  return {
    accounts: [account({ counts: totals })],
    bucketsTotal: 1,
    processing: false,
    stale,
    totals,
    ...overrides,
  };
}

function deferred<T>(): { promise: Promise<T>; resolve: (value: T) => void } {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

function mountView(options: { rui?: boolean; seed?: ReconciliationResponse; stubTable?: boolean } = {}): VueWrapper {
  const pinia = createPinia();
  setActivePinia(pinia);
  if (options.seed)
    useBucketReconciliationStore().setSummary(options.seed);
  return mount(ReconciliationView, {
    global: {
      plugins: options.rui === false ? [pinia] : [pinia, createRuiPlugin({})],
      stubs: {
        BucketTraceDrawer: true,
        DataIssuesTabs: true,
        ...(options.stubTable === false ? {} : { ReconciliationTable: true }),
        TablePageLayout: { template: '<main><slot /></main>' },
      },
    },
  });
}

describe('reconciliationView', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    fetchAccount.mockResolvedValue(undefined);
    await useRouter().replace({ query: {} });
  });

  it('should stop offering a check when returning to a cached view after history becomes stale', async () => {
    fetchSummary.mockResolvedValue(report(true));
    const wrapper = mountView({ rui: false, seed: report(false) });
    await flushPromises();

    expect(wrapper.get('[data-testid="reconciliation-check-now"]').attributes('disabled')).toBeDefined();
    expect(wrapper.find('[data-testid="reconciliation-recalculating"]').exists()).toBe(true);
  });

  it.each(['attention', 'all'])('should display a blocked exchange account in the %s view', async (view) => {
    await useRouter().replace({ query: { view } });
    const blocked = counts({ blocked: 1 });
    const summary = report(false, {
      accounts: [account({ counts: blocked, isExchange: true, lastComparedAt: null, location: 'kraken', locationLabel: 'Kraken 1' })],
      totals: blocked,
    });
    fetchSummary.mockResolvedValue(summary);

    const wrapper = mountView({ seed: summary, stubTable: false });
    await flushPromises();

    expect(wrapper.get('[data-testid="reconciliation-table"]').text()).toContain('Kraken 1');
    expect(wrapper.find('[data-testid="reconciliation-nothing-attention"]').exists()).toBe(false);
  });

  it('should explain that the report is unavailable on 404 instead of offering a retry or check', async () => {
    fetchSummary.mockRejectedValue(createStatusError(404, 'Historical balance reconciliation is disabled', {
      cause: 'not_found',
      message: 'Historical balance reconciliation is disabled',
      result: null,
    }));

    const wrapper = mountView({ rui: false });
    await flushPromises();

    expect(wrapper.find('[data-testid="reconciliation-unavailable"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="reconciliation-summary-error"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="reconciliation-check-now"]').exists()).toBe(false);
  });

  it('should name the backend reason without retry for an internal error', async () => {
    fetchSummary.mockRejectedValue(createStatusError(500, 'database is locked', {
      cause: 'internal',
      message: 'database is locked',
      result: null,
    }));

    const wrapper = mountView({ rui: false });
    await flushPromises();

    const strip = wrapper.get('[data-testid="reconciliation-summary-error"]');
    expect(strip.text()).toContain('data_issues.reconciliation.failure.load');
    expect(strip.text()).toContain('database is locked');
    expect(strip.find('[data-testid="failure-strip-retry"]').exists()).toBe(false);
  });

  it('should say the backend is unreachable and recover on retry', async () => {
    fetchSummary
      .mockRejectedValueOnce(new FetchError('[GET] "http://127.0.0.1/api": <no response>'))
      .mockResolvedValue(report(false));

    const wrapper = mountView({ rui: false });
    await flushPromises();

    const strip = wrapper.get('[data-testid="reconciliation-summary-error"]');
    expect(strip.text()).toContain('common.backend_unreachable');
    await strip.get('[data-testid="failure-strip-retry"]').trigger('click');
    await flushPromises();

    expect(fetchSummary).toHaveBeenCalledTimes(2);
    expect(wrapper.find('[data-testid="reconciliation-summary-error"]').exists()).toBe(false);
  });

  it('should stay on needs attention when a refresh clears the last mismatch', async () => {
    const mismatch = counts({ mismatch: 1 });
    fetchSummary
      .mockResolvedValueOnce(report(false, { accounts: [account({ counts: mismatch })], totals: mismatch }))
      .mockResolvedValue(report(false));

    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.find('[data-testid="reconciliation-nothing-attention"]').exists()).toBe(false);

    const [[reload]] = vi.mocked(useDataIssuesAutoReload).mock.calls;
    await reload();
    await flushPromises();

    expect(wrapper.find('[data-testid="reconciliation-nothing-attention"]').exists()).toBe(true);
  });

  it('should fetch an asset-filtered summary on deep link without overwriting global badge totals', async () => {
    const assetId = 'eip155:1/erc20:0x6df1C1E379bC5a00a7b4C6e67A203333772f45A8';
    const globalTotals = counts({ blocked: 2, mismatch: 1, pending: 10, reconciled: 5 });
    const filteredTotals = counts({ pending: 1 });
    const acc1 = account({ counts: globalTotals, locationLabel: '0x1111' });
    const acc2 = account({ counts: filteredTotals, locationLabel: '0x2222' });
    const globalReport = report(false, { accounts: [acc1, acc2], bucketsTotal: 18, totals: globalTotals });
    const filteredReport = report(false, { accounts: [acc2], bucketsTotal: 1, totals: filteredTotals });
    fetchSummary.mockImplementation(async (asset?: string) => (asset === assetId ? filteredReport : globalReport));

    await useRouter().replace({ query: { asset: assetId, view: 'all' } });
    const wrapper = mountView();
    await flushPromises();

    expect(useBucketReconciliationStore().attention).toBe(3);
    const table = wrapper.getComponent({ name: 'ReconciliationTable' });
    expect(table.props('autoExpand')).toBe(true);
    expect(table.props('accounts')).toEqual([acc2]);

    await wrapper.get('[data-testid="reconciliation-clear-filters"]').trigger('click');
    await flushPromises();
    expect(useRouter().currentRoute.value.query.asset).toBeUndefined();
    expect(table.props('autoExpand')).toBe(false);
    expect(table.props('accounts')).toHaveLength(2);
  });

  it('should ignore stale asset filter responses that resolve late', async () => {
    const acc = account({ locationLabel: '0x1111' });
    const base = report(false, { accounts: [acc] });
    const slow = deferred<ReconciliationResponse>();
    fetchSummary.mockImplementation(async (asset?: string) => (asset === 'ET' ? slow.promise : base));
    fetchAccount.mockResolvedValue({ ...acc, buckets: [], pagination: { limit: 50, offset: 0, total: 0 } });

    const wrapper = mountView();
    await flushPromises();
    wrapper.getComponent({ name: 'ReconciliationTable' }).vm.$emit('expand', acc);
    await flushPromises();
    fetchAccount.mockClear();

    await useRouter().replace({ query: { asset: 'ET', view: 'all' } });
    await useRouter().replace({ query: { asset: 'ETH', view: 'all' } });
    await flushPromises();
    expect(fetchAccount).toHaveBeenCalledTimes(1);
    expect(fetchAccount).toHaveBeenLastCalledWith(expect.objectContaining({ asset: 'ETH' }));

    slow.resolve(base);
    await flushPromises();
    expect(fetchAccount).toHaveBeenCalledTimes(1);
  });

  it('should isolate filtered summary failures from global summaryFailure and recover on retry', async () => {
    const globalReport = report(false);
    let failFilter = true;
    fetchSummary.mockImplementation(async (asset?: string) => {
      if (asset && failFilter)
        throw new FetchError('[GET] "http://127.0.0.1/api": <no response>');
      return globalReport;
    });

    await useRouter().replace({ query: { asset: 'USDC', view: 'all' } });
    const wrapper = mountView();
    await flushPromises();

    expect(useBucketReconciliationStore().summaryFailed).toBe(false);
    expect(wrapper.find('[data-testid="reconciliation-empty-filtered"]').exists()).toBe(false);
    const strip = wrapper.get('[data-testid="reconciliation-filter-error"]');

    failFilter = false;
    await strip.get('[data-testid="failure-strip-retry"]').trigger('click');
    await flushPromises();

    expect(wrapper.find('[data-testid="reconciliation-filter-error"]').exists()).toBe(false);
    expect(wrapper.getComponent({ name: 'ReconciliationTable' }).props('accounts')).toEqual(globalReport.accounts);
  });

  it('should filter accounts by human-readable chain name and show empty-filtered notice', async () => {
    const arb = account({ location: 'arbitrum_one', locationLabel: '0x1111' });
    const eth = account({ location: 'ethereum', locationLabel: '0x2222' });
    fetchSummary.mockResolvedValue(report(false, { accounts: [arb, eth] }));

    await useRouter().replace({ query: { account: 'arbitrum one', view: 'all' } });
    const wrapper = mountView();
    await flushPromises();

    const table = wrapper.getComponent({ name: 'ReconciliationTable' });
    expect(table.props('accounts')).toEqual([arb]);

    await useRouter().replace({ query: { account: 'no-such-account', view: 'all' } });
    await flushPromises();
    expect(table.props('accounts')).toEqual([]);
    expect(wrapper.find('[data-testid="reconciliation-empty-filtered"]').exists()).toBe(true);
  });

  it('should keep the table visible for deep links even when nothing has been compared yet', async () => {
    const pending = counts({ pending: 2 });
    fetchSummary.mockResolvedValue(report(false, {
      accounts: [account({ counts: pending, lastComparedAt: null })],
      bucketsTotal: 2,
      totals: pending,
    }));

    await useRouter().replace({ query: { asset: 'ETH', view: 'all' } });
    const wrapper = mountView();
    await flushPromises();

    expect(wrapper.find('[data-testid="reconciliation-never-checked"]').exists()).toBe(false);
    expect(wrapper.findComponent({ name: 'ReconciliationTable' }).exists()).toBe(true);
  });

  it('should open the trace drawer with the selected bucket when inspect-trace is emitted', async () => {
    const base = report(false);
    fetchSummary.mockResolvedValue(base);
    const wrapper = mountView();
    await flushPromises();

    const target = {
      account: base.accounts[0],
      bucket: {
        asset: 'ETH',
        check: null,
        derivedBalance: null,
        issueId: null,
        issueKind: null,
        lastEventTs: null,
        observedAt: null,
        observedBalance: null,
        protocol: null,
        reasons: [],
        status: 'pending' as const,
        stop: null,
      },
    };
    wrapper.getComponent({ name: 'ReconciliationTable' }).vm.$emit('inspect-trace', target);
    await flushPromises();

    const drawer = wrapper.getComponent({ name: 'BucketTraceDrawer' });
    expect(drawer.props('modelValue')).toBe(true);
    expect(drawer.props('target')).toEqual(target);
  });

  it('should reload open accounts only once when adding or clearing an asset filter flips the default view', async () => {
    const mismatch = counts({ mismatch: 1 });
    const acc = account({ counts: mismatch, locationLabel: '0x1111' });
    const globalReport = report(false, { accounts: [acc], totals: mismatch });
    const filtered = deferred<ReconciliationResponse>();
    fetchSummary.mockImplementation(async (asset?: string) => (asset ? filtered.promise : globalReport));
    fetchAccount.mockResolvedValue({ ...acc, buckets: [], pagination: { limit: 50, offset: 0, total: 0 } });

    const wrapper = mountView();
    await flushPromises();
    wrapper.getComponent({ name: 'ReconciliationTable' }).vm.$emit('expand', acc);
    await flushPromises();
    fetchAccount.mockClear();

    await useRouter().replace({ query: { asset: 'USDC' } });
    await flushPromises();
    expect(fetchAccount).not.toHaveBeenCalled();

    filtered.resolve(globalReport);
    await flushPromises();
    expect(fetchAccount).toHaveBeenCalledTimes(1);
    expect(fetchAccount).toHaveBeenLastCalledWith(expect.objectContaining({ asset: 'USDC', status: undefined }));

    fetchAccount.mockClear();
    await wrapper.get('[data-testid="reconciliation-clear-filters"]').trigger('click');
    await flushPromises();
    expect(fetchAccount).toHaveBeenCalledTimes(1);
    expect(fetchAccount).toHaveBeenLastCalledWith(expect.objectContaining({ asset: undefined, status: ['mismatch', 'blocked'] }));
  });

  it('should not show the nothing-needs-attention notice while an asset filter is loading or failed in attention view', async () => {
    const pending = deferred<ReconciliationResponse>();
    const globalReport = report(false);
    fetchSummary.mockImplementation(async (asset?: string) => (asset ? pending.promise : globalReport));

    await useRouter().replace({ query: { asset: 'USDC', view: 'attention' } });
    const wrapper = mountView();
    await flushPromises();

    expect(wrapper.find('[data-testid="reconciliation-nothing-attention"]').exists()).toBe(false);

    fetchSummary.mockImplementation(async (asset?: string) => {
      if (asset)
        throw new FetchError('[GET] "http://127.0.0.1/api": <no response>');
      return globalReport;
    });
    await useRouter().replace({ query: { asset: 'DAI', view: 'attention' } });
    await flushPromises();

    expect(wrapper.find('[data-testid="reconciliation-filter-error"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="reconciliation-nothing-attention"]').exists()).toBe(false);
  });
});
