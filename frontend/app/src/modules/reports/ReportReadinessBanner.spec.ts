import type { ReportReadiness } from '@/modules/reports/readiness-types';
import type { IssueGroup } from '@/modules/reports/use-report-readiness';
import { mount, type VueWrapper } from '@vue/test-utils';
import { get, set } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref, shallowRef } from 'vue';
import { IssueKind } from '@/modules/history/data-issues/constants';
import ReportReadinessBanner from '@/modules/reports/ReportReadinessBanner.vue';
import { createRuiPlugin } from '@/plugins/rui';

const state = await vi.hoisted(async () => {
  const { ref: refFn, shallowRef: shallowRefFn } = await import('vue');
  return {
    enabled: true,
    error: shallowRefFn<unknown>(),
    groupedIssues: refFn<IssueGroup[]>([]),
    modelExpanded: shallowRefFn<boolean>(false),
    readiness: refFn<ReportReadiness | undefined>(),
    refresh: vi.fn().mockResolvedValue(undefined),
    runRemediation: vi.fn().mockResolvedValue(undefined),
  };
});

vi.mock('@/modules/reports/use-report-readiness', () => ({
  useReportReadiness: (): Record<string, unknown> => ({
    enabled: state.enabled,
    error: state.error,
    groupedIssues: state.groupedIssues,
    issuesError: shallowRef(undefined),
    issuesLoading: shallowRef(false),
    loading: shallowRef(false),
    modelExpanded: state.modelExpanded,
    readiness: state.readiness,
    refresh: state.refresh,
  }),
}));

vi.mock('@/modules/history/data-issues/use-data-issue-remediation-actions', () => ({
  useDataIssueRemediationActions: (): Record<string, unknown> => ({
    actionFailure: shallowRef(undefined),
    busy: shallowRef(false),
    clearFailure: vi.fn(),
    hasModalOpen: shallowRef(false),
    modelEventForm: ref(undefined),
    modelMatchingOpen: shallowRef(false),
    modelPriceUpdate: ref(undefined),
    modelSubModalOpen: shallowRef(false),
    onModalSaved: vi.fn(),
    runRemediation: state.runRemediation,
  }),
}));

function mountBanner(): VueWrapper<InstanceType<typeof ReportReadinessBanner>> {
  return mount(ReportReadinessBanner, {
    global: {
      plugins: [createPinia(), createRuiPlugin({})],
      stubs: {
        DataIssueRemediationModals: true,
        ReportReadinessChecklist: { template: '<div data-testid="checklist-stub" />' },
        RouterLink: { props: ['to'], template: '<a :data-to="JSON.stringify(to)"><slot /></a>' },
      },
    },
    props: { endTs: 1710000000, startTs: 1700000000 },
  });
}

describe('reportReadinessBanner', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    state.enabled = true;
    set(state.error, undefined);
    set(state.groupedIssues, []);
    set(state.modelExpanded, false);
    set(state.readiness, {
      evaluatedThroughTs: 1710000000000,
      numUnpricedEvents: 0,
      numUnruledEvents: 0,
      openIssuesByKind: {},
      openIssuesCount: 0,
      ready: true,
      stale: false,
    });
  });

  it('should render the green Report Ready badge and hide the checklist toggle when ready', () => {
    const wrapper = mountBanner();

    expect(wrapper.get('[data-testid="report-readiness-banner"]').attributes('data-status')).toBe('ready');
    expect(wrapper.get('[data-testid="report-readiness-badge"]').text()).toContain('profit_loss_report.readiness.ready_badge');
    expect(wrapper.find('[data-testid="report-readiness-toggle"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="report-readiness-unruled-pill"]').exists()).toBe(false);
  });

  it('should show stale status when cost basis is stale even if openIssuesCount is 0', () => {
    set(state.readiness, {
      evaluatedThroughTs: 1710000000000,
      numUnpricedEvents: 0,
      numUnruledEvents: 0,
      openIssuesByKind: {},
      openIssuesCount: 0,
      ready: false,
      stale: true,
    });
    const wrapper = mountBanner();

    expect(wrapper.get('[data-testid="report-readiness-banner"]').attributes('data-status')).toBe('stale');
    expect(wrapper.get('[data-testid="report-readiness-badge"]').text()).toContain('profit_loss_report.readiness.stale_badge');
  });

  it('should keep ready status while showing a non-blocking unruled-events pill linking to Accounting Rules', () => {
    set(state.readiness, {
      evaluatedThroughTs: 1710000000000,
      numUnpricedEvents: 0,
      numUnruledEvents: 5,
      openIssuesByKind: {},
      openIssuesCount: 0,
      ready: true,
      stale: false,
    });
    const wrapper = mountBanner();

    expect(wrapper.get('[data-testid="report-readiness-banner"]').attributes('data-status')).toBe('ready');
    const pill = wrapper.get('[data-testid="report-readiness-unruled-pill"]');
    expect(pill.attributes('data-to')).toBe(JSON.stringify({ name: '/settings/accounting/' }));
  });

  it('should toggle the collapsible checklist when open issues exist', async () => {
    set(state.readiness, {
      evaluatedThroughTs: 1710000000000,
      numUnpricedEvents: 2,
      numUnruledEvents: 0,
      openIssuesByKind: { [IssueKind.MISSING_PRICE]: 2 },
      openIssuesCount: 2,
      ready: false,
      stale: false,
    });
    const wrapper = mountBanner();

    expect(wrapper.get('[data-testid="report-readiness-banner"]').attributes('data-status')).toBe('blocked');
    expect(wrapper.find('[data-testid="checklist-stub"]').exists()).toBe(false);

    await wrapper.get('[data-testid="report-readiness-toggle"]').trigger('click');

    expect(get(state.modelExpanded)).toBe(true);
    expect(wrapper.find('[data-testid="checklist-stub"]').exists()).toBe(true);
  });

  it('should link to the Confirmed issues audit view', () => {
    const wrapper = mountBanner();

    const link = wrapper.find('[data-testid="report-readiness-confirmed-link"]').element.closest('a');
    expect(link?.getAttribute('data-to')).toBe(JSON.stringify({
      name: '/history/data-issues/[[tab]]',
      params: { tab: 'issues' },
      query: { manualOnly: 'true' },
    }));
  });
});
