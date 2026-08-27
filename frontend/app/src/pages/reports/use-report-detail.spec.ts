import type { Collection } from '@/modules/core/common/collection';
import type { ProfitLossEvent, ReportActionableItem, Reports } from '@/modules/reports/report-types';
import {
  createActionableItems,
  createMissingAcquisitions,
  createMissingPrices,
  createReport,
  createReports,
  LATEST_REPORT_ID,
  OLDER_REPORT_ID,
} from '@test/utils/reports-test-data';
import { withSetup } from '@test/utils/with-setup';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, type ComputedRef, type Ref } from 'vue';
import { useReportDetail } from './use-report-detail';

interface RouteState {
  params: { id: string };
  query: Record<string, string>;
}

interface StoreState {
  actionableItems: ReportActionableItem;
  lastGenerated: number | null;
  reports: Reports;
}

const { fetchReports, getActionableItems, pushMock, replaceMock, routeState, storeState } = vi.hoisted(() => {
  const routeState: RouteState = { params: { id: '' }, query: {} };
  const storeState: StoreState = {
    actionableItems: { eventsSkippedNoRule: 0, missingAcquisitions: [], missingPrices: [] },
    lastGenerated: null,
    reports: { entries: [], entriesFound: 0, entriesLimit: 0 },
  };
  return {
    fetchReports: vi.fn(async (): Promise<void> => {}),
    getActionableItems: vi.fn(async (): Promise<void> => {}),
    pushMock: vi.fn(async (): Promise<void> => {}),
    replaceMock: vi.fn(async (): Promise<void> => {}),
    routeState,
    storeState,
  };
});

vi.mock('vue-router', () => ({
  useRoute: (): ComputedRef<RouteState> => computed(() => ({ params: routeState.params, query: routeState.query })),
  useRouter: (): { push: typeof pushMock; replace: typeof replaceMock } => ({ push: pushMock, replace: replaceMock }),
}));

vi.mock('@/modules/reports/use-report-operations', () => ({
  useReportOperations: (): { fetchReports: typeof fetchReports; getActionableItems: typeof getActionableItems } => ({
    fetchReports,
    getActionableItems,
  }),
}));

vi.mock('@/modules/reports/use-reports-store', async () => {
  const { computed: computedFn, ref: refFn } = await import('vue');
  return {
    defaultReportEvents: (): Collection<ProfitLossEvent> => ({ data: [], found: 0, limit: 0, total: 0 }),
    useReportsStore: (): {
      actionableItems: Ref<ReportActionableItem>;
      isLatestReport: (id: number) => ComputedRef<boolean>;
      reports: Ref<Reports>;
    } => ({
      actionableItems: refFn<ReportActionableItem>(storeState.actionableItems),
      isLatestReport: (id: number): ComputedRef<boolean> => computedFn(() => storeState.lastGenerated === id),
      reports: refFn<Reports>(storeState.reports),
    }),
  };
});

vi.mock('pinia', async importOriginal => ({
  ...(await importOriginal<typeof import('pinia')>()),
  storeToRefs: (store: Record<string, unknown>): Record<string, unknown> => store,
}));

describe('pages/reports/useReportDetail', () => {
  function setup(): ReturnType<typeof useReportDetail> {
    return withSetup(() => useReportDetail()).result;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    routeState.params = { id: String(LATEST_REPORT_ID) };
    routeState.query = {};
    storeState.actionableItems = createActionableItems();
    storeState.lastGenerated = LATEST_REPORT_ID;
    storeState.reports = createReports([createReport()]);
  });

  it('should resolve the report named by the route param', async () => {
    storeState.reports = createReports([
      createReport({ identifier: OLDER_REPORT_ID, startTs: 1 }),
      createReport({ identifier: LATEST_REPORT_ID, startTs: 2 }),
    ]);

    const { reportId, selectedReport } = setup();
    await flushPromises();

    expect(reportId).toBe(LATEST_REPORT_ID);
    expect(get(selectedReport).identifier).toBe(LATEST_REPORT_ID);
    expect(get(selectedReport).startTs).toBe(2);
  });

  it('should fetch the reports on mount only when the store is empty', async () => {
    storeState.reports = createReports([]);

    setup();
    await flushPromises();

    expect(fetchReports).toHaveBeenCalledTimes(1);
  });

  it('should not refetch the reports when the store already holds them', async () => {
    setup();
    await flushPromises();

    expect(fetchReports).not.toHaveBeenCalled();
  });

  it('should load the actionable items only for the latest report', async () => {
    setup();
    await flushPromises();

    expect(getActionableItems).toHaveBeenCalledTimes(1);
  });

  it('should skip the actionable items for an older report', async () => {
    // The store still names LATEST_REPORT_ID as the last generated one, so this route is not it.
    routeState.params = { id: String(OLDER_REPORT_ID) };
    storeState.reports = createReports([createReport({ identifier: OLDER_REPORT_ID })]);

    setup();
    await flushPromises();

    expect(getActionableItems).not.toHaveBeenCalled();
  });

  it('should clear the loading flag once the mount work settles', async () => {
    const { loading } = setup();
    expect(get(loading)).toBe(true);

    await flushPromises();

    expect(get(loading)).toBe(false);
  });

  describe('the openReportActionable query written by reports/index', () => {
    it('should open the panel and clear the query when the param is present', async () => {
      routeState.query = { openReportActionable: 'true' };

      const { initialOpenReportActionable } = setup();
      await flushPromises();

      expect(get(initialOpenReportActionable)).toBe(true);
      expect(replaceMock).toHaveBeenCalledWith({ query: {} });
    });

    it('should leave the panel shut and navigate nowhere without the param', async () => {
      const { initialOpenReportActionable } = setup();
      await flushPromises();

      expect(get(initialOpenReportActionable)).toBe(false);
      expect(replaceMock).not.toHaveBeenCalled();
    });
  });

  describe('the regenerate query it writes back to reports/index', () => {
    it('should carry the selected report period as strings', async () => {
      storeState.reports = createReports([createReport({ endTs: 456, identifier: LATEST_REPORT_ID, startTs: 123 })]);

      const { regenerateReport } = setup();
      await flushPromises();
      await regenerateReport();

      expect(pushMock).toHaveBeenCalledWith({
        path: '/reports',
        query: { end: '456', regenerate: 'true', start: '123' },
      });
    });
  });

  describe('the completeness warning', () => {
    it('should show for the latest report with missing acquisitions', async () => {
      storeState.actionableItems = createActionableItems({ missingAcquisitions: createMissingAcquisitions(2) });

      const { hasActionableIssues, missingAcquisitionsCount, showCompletenessWarning } = setup();
      await flushPromises();

      expect(get(missingAcquisitionsCount)).toBe(2);
      expect(get(hasActionableIssues)).toBe(true);
      expect(get(showCompletenessWarning)).toBe(true);
    });

    it('should show for the latest report with missing prices', async () => {
      storeState.actionableItems = createActionableItems({ missingPrices: createMissingPrices(3) });

      const { hasActionableIssues, missingPricesCount } = setup();
      await flushPromises();

      expect(get(missingPricesCount)).toBe(3);
      expect(get(hasActionableIssues)).toBe(true);
    });

    it('should show for the latest report with skipped events but flag no actionable issues', async () => {
      storeState.actionableItems = createActionableItems({ eventsSkippedNoRule: 3 });

      const { eventsSkippedCount, hasActionableIssues, showCompletenessWarning } = setup();
      await flushPromises();

      expect(get(eventsSkippedCount)).toBe(3);
      expect(get(hasActionableIssues)).toBe(false);
      expect(get(showCompletenessWarning)).toBe(true);
    });

    it('should stay hidden for an older report even when issues are present', async () => {
      storeState.lastGenerated = LATEST_REPORT_ID;
      routeState.params = { id: String(OLDER_REPORT_ID) };
      storeState.reports = createReports([createReport({ identifier: OLDER_REPORT_ID })]);
      storeState.actionableItems = createActionableItems({ eventsSkippedNoRule: 3 });

      const { showCompletenessWarning } = setup();
      await flushPromises();

      expect(get(showCompletenessWarning)).toBe(false);
    });
  });

  describe('the stale-details notice', () => {
    it('should show for an older report that processed fewer actions than it held', async () => {
      routeState.params = { id: String(OLDER_REPORT_ID) };
      storeState.reports = createReports([
        createReport({ identifier: OLDER_REPORT_ID, processedActions: 4, totalActions: 10 }),
      ]);

      const { showStaleDetails } = setup();
      await flushPromises();

      expect(get(showStaleDetails)).toBe(true);
    });

    it('should stay hidden for an older report that processed everything', async () => {
      routeState.params = { id: String(OLDER_REPORT_ID) };
      storeState.reports = createReports([
        createReport({ identifier: OLDER_REPORT_ID, processedActions: 10, totalActions: 10 }),
      ]);

      const { showStaleDetails } = setup();
      await flushPromises();

      expect(get(showStaleDetails)).toBe(false);
    });

    it('should stay hidden for the latest report, which shows the detailed warning instead', async () => {
      storeState.reports = createReports([
        createReport({ identifier: LATEST_REPORT_ID, processedActions: 4, totalActions: 10 }),
      ]);

      const { showStaleDetails } = setup();
      await flushPromises();

      expect(get(showStaleDetails)).toBe(false);
    });
  });
});
