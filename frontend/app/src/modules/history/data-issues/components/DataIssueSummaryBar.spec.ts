import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import DataIssueSummaryBar from '@/modules/history/data-issues/components/DataIssueSummaryBar.vue';
import { IssueState } from '@/modules/history/data-issues/constants';
import { emptyCounts, type StateCounts } from '@/modules/history/data-issues/use-data-issues-inbox-store';
import { createRuiPlugin } from '@/plugins/rui';

function counts(overrides: Partial<StateCounts> = {}): StateCounts {
  return { ...emptyCounts(), ...overrides };
}

function createWrapper(props: { counts: StateCounts; activeStates: string[] }): VueWrapper<InstanceType<typeof DataIssueSummaryBar>> {
  return mount(DataIssueSummaryBar, {
    global: {
      plugins: [createRuiPlugin({})],
    },
    props,
  });
}

describe('dataIssueSummaryBar', () => {
  it('should render one card per non-terminal summary state', () => {
    const wrapper = createWrapper({ activeStates: [], counts: counts() });

    expect(wrapper.find(`[data-testid="data-issue-summary-${IssueState.OPEN}"]`).exists()).toBe(true);
    expect(wrapper.find(`[data-testid="data-issue-summary-${IssueState.AUTO_REMEDIATING}"]`).exists()).toBe(true);
    expect(wrapper.find(`[data-testid="data-issue-summary-${IssueState.UNRESOLVED}"]`).exists()).toBe(true);
    // terminal states never get a card.
    expect(wrapper.find(`[data-testid="data-issue-summary-${IssueState.RESOLVED}"]`).exists()).toBe(false);
  });

  it('should show the per-state counts', () => {
    const wrapper = createWrapper({ activeStates: [], counts: counts({ [IssueState.OPEN]: 4 }) });

    expect(wrapper.find(`[data-testid="data-issue-summary-${IssueState.OPEN}"]`).text()).toContain('4');
  });

  it('should mark a card active only when it is the single selected state', () => {
    const wrapper = createWrapper({ activeStates: [IssueState.OPEN], counts: counts() });

    expect(wrapper.find(`[data-testid="data-issue-summary-${IssueState.OPEN}"]`).classes()).toContain('!border-rui-primary');
    expect(wrapper.find(`[data-testid="data-issue-summary-${IssueState.UNRESOLVED}"]`).classes()).not.toContain('!border-rui-primary');
  });

  it('should not mark any card active when several states are selected', () => {
    const wrapper = createWrapper({ activeStates: [IssueState.OPEN, IssueState.UNRESOLVED], counts: counts() });

    expect(wrapper.find(`[data-testid="data-issue-summary-${IssueState.OPEN}"]`).classes()).not.toContain('!border-rui-primary');
  });

  it('should emit the state when a card is clicked', async () => {
    const wrapper = createWrapper({ activeStates: [], counts: counts() });

    await wrapper.find(`[data-testid="data-issue-summary-${IssueState.UNRESOLVED}"]`).trigger('click');

    expect(wrapper.emitted('select')?.[0]).toStrictEqual([IssueState.UNRESOLVED]);
  });

  it('should show the all-clear hint only when every summary count is zero', async () => {
    const wrapper = createWrapper({ activeStates: [], counts: counts() });
    expect(wrapper.text()).toContain('data_issues.summary.all_clear');

    await wrapper.setProps({ counts: counts({ [IssueState.OPEN]: 1 }) });
    expect(wrapper.text()).not.toContain('data_issues.summary.all_clear');
  });
});
