import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import HistoryEventsActionRow from '@/modules/history/events/actions-center/HistoryEventsActionRow.vue';
import { HISTORY_ISSUE_IDS, type HistoryEventIssue } from '@/modules/history/events/actions-center/use-history-event-issues';
import { DIALOG_TYPES } from '@/modules/history/events/dialog-types';

function createIssue(overrides: Partial<HistoryEventIssue> = {}): HistoryEventIssue {
  return {
    actionLabel: 'Match',
    checkTarget: { kind: 'dialog', options: { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS } },
    count: 11,
    description: 'description',
    icon: 'lu-arrow-left-right',
    id: HISTORY_ISSUE_IDS.UNMATCHED_MOVEMENTS,
    ignoredOnly: false,
    loading: false,
    locked: false,
    minimumTier: null,
    severity: 'warning',
    target: { kind: 'dialog', options: { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS } },
    title: 'Unmatched asset movements',
    ...overrides,
  };
}

function mountRow(issue: HistoryEventIssue): VueWrapper<InstanceType<typeof HistoryEventsActionRow>> {
  return mount(HistoryEventsActionRow, { props: { issue } });
}

describe('modules/history/events/actions-center/HistoryEventsActionRow', () => {
  it('should render the count, the description and the action', async () => {
    const issue = createIssue();
    const wrapper = mountRow(issue);

    expect(wrapper.find('[data-testid=actions-center-row-count]').text()).toBe('11');
    expect(wrapper.text()).toContain('description');

    await wrapper.find('[data-testid=actions-center-row-action]').trigger('click');

    expect(wrapper.emitted('action')).toEqual([[issue]]);
  });

  it('should replace the action with a premium gate when locked', () => {
    const wrapper = mountRow(createIssue({ locked: true, minimumTier: 'Basic' }));

    expect(wrapper.find('[data-testid=actions-center-row-action]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=actions-center-row-locked]').text()).toContain('transactions.alerts.locked');
    // the tier hint replaces the description, which no longer describes anything actionable
    expect(wrapper.text()).toContain('transactions.alerts.locked_hint::Basic');
    expect(wrapper.text()).not.toContain('description');
  });

  it('should fall back to a generic hint when the tier is unknown', () => {
    const wrapper = mountRow(createIssue({ locked: true }));

    expect(wrapper.text()).toContain('transactions.alerts.locked_hint_generic');
  });

  it('should keep a muted issue out of the warning treatment', () => {
    const wrapper = mountRow(createIssue({ id: HISTORY_ISSUE_IDS.INTERNAL_CONFLICTS, severity: 'muted' }));

    expect(wrapper.find('[data-testid=actions-center-row][data-key=unmatched-movements]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=actions-center-row][data-key=internal-conflicts]').classes()).not.toContain('opacity-60');
    expect(wrapper.find('.text-rui-warning').exists()).toBe(false);
  });
});
