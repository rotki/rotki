import type { SpamPrediction, SpamPredictionResponse, SpamPredictionToken } from '@/modules/assets/api/use-asset-spam-prediction-api';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { DetectionResult } from '@/modules/history/data-issues/use-data-issues-detection';
import type { NamedFailure } from '@/modules/shell/components/named-failure';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { err } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { nextTick, type Ref, ref, shallowRef } from 'vue';
import { RequestFailed, type RequestFailure } from '@/modules/core/api/request-result';
import { beginSession, endSession } from '@/modules/core/session/session-lifecycle';
import DataIssueDetailDrawer from '@/modules/history/data-issues/components/DataIssueDetailDrawer.vue';
import DataIssuesTable from '@/modules/history/data-issues/components/DataIssuesTable.vue';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';
import DataIssuesView from '@/modules/history/data-issues/DataIssuesView.vue';
import NoDataScreen from '@/modules/shell/components/NoDataScreen.vue';

/**
 * Backs the mocked composables with plain values a case sets before it mounts the view.
 *
 * @remarks
 * The mock factories snapshot these into refs at mount time, so writing one afterwards does not
 * reach the mounted view.
 */
interface MockState {
  baselineTotal: number;
  detectFailure?: NamedFailure;
  error?: RequestFailure;
  filters: Record<string, unknown>;
  isLoading: boolean;
  rows: DataIssue[];
  summaryFailed: boolean;
}

const state = vi.hoisted((): MockState => ({
  baselineTotal: 0,
  filters: {},
  isLoading: false,
  rows: [],
  summaryFailed: false,
}));

interface Collection {
  data: DataIssue[];
  found: number;
  limit: number;
  total: number;
}

interface Table {
  collection?: Ref<Collection>;
  dismissInlinePanels?: Mock;
  isLoading?: Ref<boolean>;
  refetch?: Mock;
}

/** Filled in when the view mounts, so a test can drive the table and observe its reloads. */
const table = vi.hoisted((): Table => ({}));

function mounted<T>(value: T | undefined): T {
  if (value === undefined)
    throw new Error('the view has not been mounted yet');
  return value;
}

function collectionOf(rows: DataIssue[]): Collection {
  return { data: rows, found: rows.length, limit: 10, total: rows.length };
}

vi.mock('@/modules/core/table/use-server-table', () => ({
  routeWhen: (): { mode: 'route' } => ({ mode: 'route' }),
  useServerTable: (): Record<string, unknown> => {
    table.collection = ref(collectionOf(state.rows));
    table.isLoading = ref(state.isLoading);
    table.refetch = vi.fn().mockResolvedValue(undefined);
    return {
      collection: table.collection,
      error: shallowRef(state.error),
      filter: ref(state.filters),
      isLoading: table.isLoading,
      pagination: ref({}),
      refetch: table.refetch,
      setFilter: vi.fn(),
    };
  },
}));

/* The account pill's options are fetched from the backend when the bar is built, which this spec
   neither stubs nor asserts on, so without this every mount made a real request. */
vi.mock('@/modules/history/use-history-data-fetching', () => ({
  useHistoryDataFetching: (): Record<string, unknown> => ({
    fetchAssociatedLocations: vi.fn().mockResolvedValue(undefined),
    fetchLocationLabels: vi.fn().mockResolvedValue(undefined),
  }),
}));

const spies = vi.hoisted(() => ({
  detect: vi.fn<() => Promise<DetectionResult>>(),
  dismiss: vi.fn<(id: number) => Promise<unknown>>(),
  predictSpam: vi.fn<(tokens: SpamPredictionToken[]) => Promise<SpamPredictionResponse>>(),
}));

vi.mock(import('@/modules/assets/api/use-asset-spam-prediction-api'), async importOriginal => ({
  ...await importOriginal(),
  useAssetSpamPredictionApi: (): { predictSpam: typeof spies.predictSpam } => ({ predictSpam: spies.predictSpam }),
}));

vi.mock('@/modules/history/data-issues/use-data-issues', () => ({
  useDataIssues: (): Record<string, unknown> => ({
    dismiss: spies.dismiss,
    fetchData: vi.fn(),
    fetchIssue: vi.fn(),
    resolveManually: vi.fn(),
    retry: vi.fn(),
  }),
}));

vi.mock('@/modules/history/data-issues/use-data-issues-detection', () => ({
  useDataIssuesDetection: (): Record<string, unknown> => ({
    detect: spies.detect,
    detectFailure: shallowRef(state.detectFailure),
    detecting: ref(false),
  }),
}));

vi.mock('@/modules/history/data-issues/use-data-issues-summary', () => ({
  useDataIssuesSummary: (): Record<string, unknown> => {
    table.dismissInlinePanels = vi.fn();
    return {
      actionableCount: ref(0),
      baselineTotal: ref(state.baselineTotal),
      counts: ref({}),
      dismissInlinePanels: table.dismissInlinePanels,
      refreshSummary: vi.fn().mockResolvedValue(undefined),
      summaryFailed: ref(state.summaryFailed),
    };
  },
}));

function createIssue(id: number, issueState: IssueState): DataIssue {
  return {
    asset: 'ETH',
    autoRemediationAttempts: [],
    createdAt: 1710000100,
    groupIdentifier: null,
    id,
    kind: IssueKind.NEGATIVE_BALANCE,
    location: 'ethereum',
    locationLabel: '0x0000000000000000000000000000000000000001',
    payload: {},
    protocol: null,
    resolvedAt: null,
    severity: IssueSeverity.WARNING,
    state: issueState,
    tsEnd: 1710000000,
    tsStart: 1710000000,
  };
}

async function createWrapper(mainPage = true): Promise<VueWrapper<InstanceType<typeof DataIssuesView>>> {
  const wrapper = mount(DataIssuesView, {
    global: {
      plugins: [createPinia()],
      stubs: {
        DataIssueDetailDrawer: true,
        DataIssuesTable: true,
        DataIssuesTabs: true,
        DataIssueSummaryBar: true,
        NoDataScreen: true,
        PillFilterBar: true,
        ResolveManuallyDialog: true,
        TablePageLayout: { template: '<div><slot /></div>' },
      },
    },
    props: {
      mainPage,
    },
  });
  await flushPromises();
  return wrapper;
}

describe('data-issues view empty states', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    spies.predictSpam.mockResolvedValue({});
    state.baselineTotal = 0;
    state.detectFailure = undefined;
    state.error = undefined;
    state.filters = {};
    state.isLoading = false;
    state.rows = [];
    state.summaryFailed = false;
  });

  it('should show the table, not the all-clear screen, when counting the issues failed', async () => {
    state.baselineTotal = 0;
    state.summaryFailed = true;
    const wrapper = await createWrapper();

    expect(wrapper.findComponent(NoDataScreen).exists()).toBe(false);
    expect(wrapper.findComponent(DataIssuesTable).exists()).toBe(true);
  });

  it('should show the table, not the all-clear screen, when reading the issues failed', async () => {
    state.baselineTotal = 0;
    state.error = RequestFailed({ cause: undefined, message: 'backend is down' });
    const wrapper = await createWrapper();

    expect(wrapper.findComponent(NoDataScreen).exists()).toBe(false);
    expect(wrapper.findComponent(DataIssuesTable).exists()).toBe(true);
  });

  it('should show the reassuring all-clear screen when no issues exist at all', async () => {
    state.baselineTotal = 0;
    const wrapper = await createWrapper();

    expect(wrapper.findComponent(NoDataScreen).exists()).toBe(true);
    expect(wrapper.findComponent(DataIssuesTable).exists()).toBe(false);
  });

  it('should keep the all-clear screen (not flash the table) while an empty inbox is refreshing', async () => {
    state.baselineTotal = 0;
    state.isLoading = true;
    const wrapper = await createWrapper();

    expect(wrapper.findComponent(NoDataScreen).exists()).toBe(true);
    expect(wrapper.findComponent(DataIssuesTable).exists()).toBe(false);
  });

  it('should show the table (not the all-clear screen) once any issue exists', async () => {
    state.baselineTotal = 4;
    const wrapper = await createWrapper();

    expect(wrapper.findComponent(NoDataScreen).exists()).toBe(false);
    expect(wrapper.findComponent(DataIssuesTable).exists()).toBe(true);
  });

  it('should use the "no match" empty copy when filters are active but the list is empty', async () => {
    state.baselineTotal = 4;
    state.rows = [];
    state.filters = { state: ['open'] };
    const wrapper = await createWrapper();

    const table = wrapper.findComponent(DataIssuesTable);
    expect(table.props('emptyDescription')).toBe('data_issues.empty.filtered');
    expect(table.props('showClearFilters')).toBe(true);
  });

  it('should use the "none" empty copy when there are no active filters', async () => {
    state.baselineTotal = 4;
    state.rows = [];
    state.filters = {};
    const wrapper = await createWrapper();

    const table = wrapper.findComponent(DataIssuesTable);
    expect(table.props('emptyDescription')).toBe('data_issues.empty.none');
    expect(table.props('showClearFilters')).toBe(false);
  });
});

describe('data-issues view failures', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
    state.baselineTotal = 4;
    state.detectFailure = undefined;
    state.error = undefined;
    state.filters = {};
    state.isLoading = false;
    state.rows = [];
    state.summaryFailed = false;
    spies.detect.mockResolvedValue({ conflict: false, success: true });
  });

  it('should name a failed balance check on the page, with a retry that checks again', async () => {
    state.detectFailure = { failure: new Error('still processing'), title: 'data_issues.detect.error' };
    const wrapper = await createWrapper();

    const strip = wrapper.find('[data-testid="data-issues-detect-failure"]');
    expect(strip.text()).toContain('data_issues.detect.error');
    expect(strip.text()).toContain('still processing');

    await strip.find('[data-testid="failure-strip-retry"]').trigger('click');
    expect(spies.detect).toHaveBeenCalledOnce();
  });

  it('should name no balance check failure while there is none', async () => {
    const wrapper = await createWrapper();

    expect(wrapper.find('[data-testid="data-issues-detect-failure"]').exists()).toBe(false);
  });

  it('should name a failed row dismiss above the table without a retry, and keep it from a drawer with no issue open', async () => {
    spies.dismiss.mockResolvedValue(err({ cause: new Error('nope'), message: 'nope', type: 'conflict' }));
    const wrapper = await createWrapper();

    wrapper.findComponent(DataIssuesTable).vm.$emit('dismiss', { id: 5 });
    await flushPromises();

    const strip = wrapper.find('[data-testid="data-issues-action-failure"]');
    expect(strip.text()).toContain('data_issues.action.dismiss.error');
    expect(strip.text()).toContain('nope');
    expect(strip.find('[data-testid="failure-strip-retry"]').exists()).toBe(false);
    expect(wrapper.findComponent(DataIssueDetailDrawer).props('failure')).toBeUndefined();
  });
});

describe('data-issues view loading and polling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
    // `flushPromises` waits on `setImmediate`, so only the timers the view schedules are faked.
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval'] });
    spies.predictSpam.mockResolvedValue({});
    state.baselineTotal = 4;
    state.detectFailure = undefined;
    state.error = undefined;
    state.filters = {};
    state.isLoading = false;
    state.rows = [createIssue(1, IssueState.OPEN)];
    state.summaryFailed = false;
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should keep the loading indicator up for 500 ms when a load finishes sooner', async () => {
    const wrapper = await createWrapper();
    const isLoading = mounted(table.isLoading);
    const loadingShown = (): boolean | undefined => wrapper.findComponent(DataIssuesTable).props('loading');
    expect(loadingShown()).toBe(false);

    isLoading.value = true;
    await nextTick();
    expect(loadingShown()).toBe(true);

    await vi.advanceTimersByTimeAsync(100);
    isLoading.value = false;
    await nextTick();
    expect(loadingShown()).toBe(true);

    await vi.advanceTimersByTimeAsync(399);
    expect(loadingShown()).toBe(true);

    await vi.advanceTimersByTimeAsync(1);
    expect(loadingShown()).toBe(false);
  });

  it('should refetch every 10 s while rows remediate, and stop once none do', async () => {
    await createWrapper();
    const refetch = mounted(table.refetch);
    const collection = mounted(table.collection);
    expect(refetch).toHaveBeenCalledOnce();
    refetch.mockClear();

    collection.value = collectionOf([createIssue(1, IssueState.AUTO_REMEDIATING)]);
    await nextTick();

    await vi.advanceTimersByTimeAsync(9_999);
    expect(refetch).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(refetch).toHaveBeenCalledOnce();
    await vi.advanceTimersByTimeAsync(10_000);
    expect(refetch).toHaveBeenCalledTimes(2);

    collection.value = collectionOf([createIssue(1, IssueState.OPEN)]);
    await nextTick();
    await vi.advanceTimersByTimeAsync(30_000);
    expect(refetch).toHaveBeenCalledTimes(2);
  });

  it('should dismiss the inline panels when shown as the main page', async () => {
    await createWrapper();

    expect(mounted(table.dismissInlinePanels)).toHaveBeenCalledOnce();
  });

  it('should leave the inline panels alone when embedded', async () => {
    await createWrapper(false);

    expect(mounted(table.dismissInlinePanels)).not.toHaveBeenCalled();
  });
});

describe('data-issues view spam estimates', () => {
  const token = 'eip155:1/erc20:0x1111111111111111111111111111111111111111';
  const prediction: SpamPrediction = {
    flagged: true,
    modelReasons: [],
    observedSignals: [],
    spamProbability: 0.93,
    threshold: 0.5,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
    beginSession();
    state.baselineTotal = 1;
    state.detectFailure = undefined;
    state.error = undefined;
    state.filters = {};
    state.isLoading = false;
    state.summaryFailed = false;
    state.rows = [{
      asset: token,
      autoRemediationAttempts: [],
      createdAt: 1710000100,
      groupIdentifier: null,
      id: 10,
      kind: IssueKind.NEGATIVE_BALANCE,
      location: 'ethereum',
      locationLabel: '0x0000000000000000000000000000000000000001',
      payload: {},
      protocol: null,
      resolvedAt: null,
      severity: IssueSeverity.WARNING,
      state: IssueState.OPEN,
      tsEnd: 1710000000,
      tsStart: 1710000000,
    }];
    spies.predictSpam.mockResolvedValue({ [token]: prediction });
  });

  afterEach(() => {
    endSession();
  });

  it('should pass page spam assessments to the table and selected drawer without re-fetching on row open', async () => {
    const wrapper = await createWrapper();
    const expected = { prediction, status: 'ready' };

    expect(spies.predictSpam).toHaveBeenCalledExactlyOnceWith([{ identifier: token }]);
    expect(wrapper.findComponent(DataIssuesTable).props('spamAssessments')).toStrictEqual({ [token]: expected });

    wrapper.findComponent(DataIssuesTable).vm.$emit('open', state.rows[0]);
    await flushPromises();

    expect(spies.predictSpam).toHaveBeenCalledOnce();
    expect(wrapper.findComponent(DataIssueDetailDrawer).props('spamAssessment')).toStrictEqual(expected);
    expect(wrapper.findComponent(DataIssuesTable).props('spamUnavailable')).toBe(false);
  });

  it('should mark spam predictions unavailable on the table when prediction fails', async () => {
    spies.predictSpam.mockRejectedValueOnce(new Error('colibri unavailable'));
    const wrapper = await createWrapper();

    expect(wrapper.findComponent(DataIssuesTable).props('spamUnavailable')).toBe(true);
  });
});
