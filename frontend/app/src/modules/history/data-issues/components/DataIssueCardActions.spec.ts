import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import DataIssueCardActions from '@/modules/history/data-issues/components/DataIssueCardActions.vue';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';

function createIssue(state: IssueState): DataIssue {
  return {
    asset: 'ETH',
    autoRemediationAttempts: [],
    createdAt: 1710000100,
    groupIdentifier: null,
    id: 1,
    kind: IssueKind.REBASING_TOKEN,
    location: 'ethereum',
    locationLabel: '0x0000000000000000000000000000000000000001',
    payload: {},
    protocol: null,
    resolvedAt: null,
    severity: IssueSeverity.WARNING,
    state,
    tsEnd: 1710000000,
    tsStart: 1710000000,
  };
}

describe('dataIssueCardActions', () => {
  it('should keep retry visible but disabled while remediation is running', () => {
    const wrapper = mount(DataIssueCardActions, {
      props: { issue: createIssue(IssueState.AUTO_REMEDIATING) },
    });

    const retry = wrapper.find('[data-testid=data-issues-panel-retry]');
    expect(retry.exists()).toBe(true);
    expect(retry.attributes('disabled')).toBeDefined();
  });
});
