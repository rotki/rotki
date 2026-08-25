import type { useReportDetail } from '@/pages/reports/use-report-detail';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { createAccountingSettings, createReport, LATEST_REPORT_ID } from '@test/utils/reports-test-data';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';
import AccountingSettingsDisplay from '@/modules/reports/AccountingSettingsDisplay.vue';
import ExportReportCsv from '@/modules/reports/ExportReportCsv.vue';
import ProfitLossOverview from '@/modules/reports/ProfitLossOverview.vue';
import ReportActionable from '@/modules/reports/ReportActionable.vue';
import ReportHeader from '@/modules/reports/ReportHeader.vue';
import ReportDetailPage from '@/pages/reports/[id].vue';

type ReportDetail = ReturnType<typeof useReportDetail>;

const regenerateReport = vi.fn(async (): Promise<void> => {});

/**
 * The page is a seam: it owns no logic beyond handing the composable's output to its children, so
 * the composable is mocked and the assertions are about what reaches each child.
 */
const detailState = vi.hoisted(() => ({
  eventsSkipped: 0,
  latest: true,
  loading: false,
  missingAcquisitions: 0,
  missingPrices: 0,
  showCompletenessWarning: false,
  showStaleDetails: false,
}));

vi.mock('@/pages/reports/use-report-detail', () => ({
  useReportDetail: (): ReportDetail => ({
    eventsSkippedCount: computed(() => detailState.eventsSkipped),
    hasActionableIssues: computed(() => detailState.missingAcquisitions > 0 || detailState.missingPrices > 0),
    initialOpenReportActionable: computed(() => true),
    latest: computed(() => detailState.latest),
    loading: computed(() => detailState.loading),
    missingAcquisitionsCount: computed(() => detailState.missingAcquisitions),
    missingPricesCount: computed(() => detailState.missingPrices),
    modelReportEvents: ref({ data: [], found: 0, limit: 0, total: 0 }),
    refreshing: computed(() => false),
    regenerateReport,
    reportId: LATEST_REPORT_ID,
    selectedReport: computed(() => createReport({ endTs: 456, startTs: 123 })),
    settings: computed(() => createReport().settings),
    showCompletenessWarning: computed(() => detailState.showCompletenessWarning),
    showStaleDetails: computed(() => detailState.showStaleDetails),
  }),
}));

describe('pages/reports/[id]', () => {
  let wrapper: VueWrapper<InstanceType<typeof ReportDetailPage>>;

  function mountPage(): VueWrapper<InstanceType<typeof ReportDetailPage>> {
    return mount(ReportDetailPage, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: {
          AccountingSettingsDisplay: { props: ['accountingSettings'], template: '<div data-testid="settings-stub" />' },
          ExportReportCsv: { props: ['reportId'], template: '<div data-testid="export-stub" />' },
          ProfitLossEvents: { props: ['report', 'refreshing', 'reportEvents'], template: '<div data-testid="events-stub" />' },
          ProfitLossOverview: { props: ['report', 'symbol', 'loading'], template: '<div data-testid="overview-stub" />' },
          ProgressScreen: { template: '<div data-testid="progress-stub"><slot /></div>' },
          ReportActionable: { emits: ['regenerate'], props: ['report', 'initialOpen'], template: '<div data-testid="actionable-stub" />' },
          ReportHeader: { props: ['period'], template: '<div data-testid="header-stub" />' },
        },
      },
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    detailState.eventsSkipped = 0;
    detailState.latest = true;
    detailState.loading = false;
    detailState.missingAcquisitions = 0;
    detailState.missingPrices = 0;
    detailState.showCompletenessWarning = false;
    detailState.showStaleDetails = false;
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should show only the progress screen while loading', () => {
    detailState.loading = true;

    wrapper = mountPage();

    expect(wrapper.find('[data-testid=progress-stub]').exists()).toBe(true);
    expect(wrapper.findComponent(ReportHeader).exists()).toBe(false);
  });

  it('should hand the report period to the header and the id to the csv export', () => {
    wrapper = mountPage();

    expect(wrapper.findComponent(ReportHeader).props('period')).toEqual({ end: 456, start: 123 });
    expect(wrapper.findComponent(ExportReportCsv).props('reportId')).toBe(LATEST_REPORT_ID);
  });

  it('should hand the accounting settings down and the report to the overview', () => {
    wrapper = mountPage();

    expect(wrapper.findComponent(AccountingSettingsDisplay).props('accountingSettings')).toEqual(createAccountingSettings());
    expect(wrapper.findComponent(ProfitLossOverview).props('report').identifier).toBe(LATEST_REPORT_ID);
  });

  it('should offer the actionable panel only for the latest report', () => {
    wrapper = mountPage();
    expect(wrapper.findComponent(ReportActionable).exists()).toBe(true);
    wrapper.unmount();

    detailState.latest = false;
    wrapper = mountPage();

    expect(wrapper.findComponent(ReportActionable).exists()).toBe(false);
  });

  it('should regenerate from the button and from the actionable panel alike', async () => {
    wrapper = mountPage();

    await wrapper.find('[data-testid=regenerate-report]').trigger('click');
    expect(regenerateReport).toHaveBeenCalledTimes(1);

    wrapper.findComponent(ReportActionable).vm.$emit('regenerate');
    expect(regenerateReport).toHaveBeenCalledTimes(2);
  });

  it('should show the completeness warning and never the stale notice alongside it', () => {
    detailState.showCompletenessWarning = true;
    detailState.showStaleDetails = true;

    wrapper = mountPage();

    expect(wrapper.find('[data-testid=completeness-warning]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=stale-details]').exists()).toBe(false);
  });

  it('should fall back to the stale notice when there is no completeness warning', () => {
    detailState.showStaleDetails = true;

    wrapper = mountPage();

    expect(wrapper.find('[data-testid=stale-details]').exists()).toBe(true);
  });
});
