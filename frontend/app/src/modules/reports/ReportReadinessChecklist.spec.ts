import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { IssueGroup } from '@/modules/reports/use-report-readiness';
import { mount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { describe, expect, it } from 'vitest';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';
import ReportReadinessChecklist from '@/modules/reports/ReportReadinessChecklist.vue';
import { createRuiPlugin } from '@/plugins/rui';

function createIssue(overrides: Partial<DataIssue> = {}): DataIssue {
  return {
    asset: 'ETH',
    autoRemediationAttempts: [],
    createdAt: 1710000100,
    eventIdentifier: 10,
    groupIdentifier: 'grp-1',
    id: 1,
    kind: IssueKind.MISSING_PRICE,
    location: 'ethereum',
    locationLabel: null,
    payload: { amount: '1', direction: 'spend', eventIdentifier: 10, groupIdentifier: 'grp-1', toAsset: 'USD' },
    protocol: null,
    resolvedAt: null,
    severity: IssueSeverity.WARNING,
    state: IssueState.OPEN,
    suggestedActions: [],
    tsEnd: 1710000000000,
    tsStart: 1710000000000,
    ...overrides,
  };
}

describe('reportReadinessChecklist', () => {
  it('should render one group per IssueKind with its count badge and forward inline actions', async () => {
    const issue = createIssue({ id: 7, kind: IssueKind.MISSING_PRICE });
    const groups: IssueGroup[] = [
      { issues: [issue], kind: IssueKind.MISSING_PRICE, totalCount: 3 },
      { issues: [createIssue({ id: 8, kind: IssueKind.MISSING_COST_BASIS })], kind: IssueKind.MISSING_COST_BASIS, totalCount: 1 },
    ];

    const wrapper = mount(ReportReadinessChecklist, {
      global: {
        plugins: [createPinia(), createRuiPlugin({})],
        stubs: {
          AssetDetails: true,
          DataIssueDescription: true,
          DataIssueKindChip: true,
          DateDisplay: true,
          HistoryEventAccount: true,
          LocationDisplay: true,
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
      props: { groups },
    });

    const renderedGroups = wrapper.findAll('[data-testid="report-readiness-group"]');
    expect(renderedGroups).toHaveLength(2);
    expect(renderedGroups[0]?.attributes('data-kind')).toBe(IssueKind.MISSING_PRICE);
    expect(renderedGroups[0]?.get('[data-testid="report-readiness-group-count"]').text()).toBe('3');

    await wrapper.get('[data-testid="data-issue-inline-set_manual_price"]').trigger('click');
    expect(wrapper.emitted('action')?.[0]).toStrictEqual([{ action: 'set_manual_price', issue }]);
  });

  it('should show an error strip with retry when loading issues failed', async () => {
    const wrapper = mount(ReportReadinessChecklist, {
      global: { plugins: [createRuiPlugin({})] },
      props: { error: new Error('boom'), groups: [] },
    });

    await wrapper.get('[data-testid="failure-strip-retry"]').trigger('click');
    expect(wrapper.emitted('retry')).toHaveLength(1);
  });
});
