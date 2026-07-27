import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import HistoryEventsActionsList from '@/modules/history/events/actions-center/HistoryEventsActionsList.vue';
import { HISTORY_ISSUE_IDS, type HistoryEventIssue, type HistoryIssueTarget } from '@/modules/history/events/actions-center/use-history-event-issues';
import { DIALOG_TYPES } from '@/modules/history/events/dialog-types';

// Declared at module scope (not `vi.hoisted`): the mock factories below only
// dereference `state` from inside their inner arrows, which run once the tests do.
const state = {
  issues: ref<HistoryEventIssue[]>([]),
  refreshAll: vi.fn<() => Promise<void>>(),
};

vi.mock('@/modules/history/events/actions-center/use-history-event-issues', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/modules/history/events/actions-center/use-history-event-issues')>();
  return {
    ...original,
    useHistoryEventIssues: (): object => ({
      checking: computed(() => false),
      reviewIssues: computed(() => get(state.issues).filter(issue => issue.count > 0 && issue.ignoredOnly && !issue.locked)),
      lockedIssues: computed(() => get(state.issues).filter(issue => issue.locked && issue.count > 0)),
      activeIssues: computed(() => get(state.issues).filter(issue => issue.count > 0 && !issue.locked && !issue.ignoredOnly)),
      categoryCount: computed(() => get(state.issues).filter(issue => issue.count > 0 && !issue.locked).length),
      clearedIssues: computed(() => get(state.issues).filter(issue => issue.count === 0)),
      hasIssues: computed(() => get(state.issues).some(issue => issue.count > 0 && !issue.locked)),
      issues: state.issues,
      refreshAll: state.refreshAll,
      refreshing: computed(() => false),
    }),
  };
});

function createIssue(overrides: Partial<HistoryEventIssue> = {}): HistoryEventIssue {
  return {
    actionLabel: 'match',
    count: 3,
    description: 'description',
    icon: 'lu-git-compare-arrows',
    id: HISTORY_ISSUE_IDS.UNMATCHED_BRIDGES,
    checkTarget: { kind: 'dialog', options: { type: DIALOG_TYPES.MATCH_BRIDGE_TRANSACTIONS } },
    ignoredOnly: false,
    loading: false,
    locked: false,
    minimumTier: null,
    severity: 'warning',
    target: { kind: 'dialog', options: { type: DIALOG_TYPES.MATCH_BRIDGE_TRANSACTIONS } },
    title: 'Unmatched bridge transactions',
    ...overrides,
  };
}

function mountList(): VueWrapper<InstanceType<typeof HistoryEventsActionsList>> {
  return mount(HistoryEventsActionsList);
}

describe('modules/history/events/actions-center/HistoryEventsActionsList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    state.refreshAll.mockResolvedValue();
    set(state.issues, []);
  });

  it('should render a row per active issue and the cleared ones as a summary', () => {
    set(state.issues, [
      createIssue(),
      createIssue({ count: 0, id: HISTORY_ISSUE_IDS.UNDECODED, title: 'Undecoded transactions' }),
    ]);

    const wrapper = mountList();

    expect(wrapper.findAll('[data-testid^=actions-center-row-unmatched]')).toHaveLength(1);
    expect(wrapper.find('[data-testid=actions-center-row-count]').text()).toBe('3');
    expect(wrapper.find('[data-testid=actions-center-cleared]').text()).toContain('Undecoded transactions');
  });

  it('should hand the row target up when a row is actioned', async () => {
    set(state.issues, [createIssue()]);

    const wrapper = mountList();
    await wrapper.find('[data-testid=actions-center-row-action]').trigger('click');

    expect(wrapper.emitted('open')).toEqual([[{ kind: 'dialog', options: { type: DIALOG_TYPES.MATCH_BRIDGE_TRANSACTIONS } }]]);
  });

  it('should hand up the duplicates target with its groups', async () => {
    const target: HistoryIssueTarget = { groupIds: ['a', 'b'], kind: 'duplicates', status: DuplicateHandlingStatus.AUTO_FIX };
    set(state.issues, [createIssue({ id: HISTORY_ISSUE_IDS.AUTO_FIX_DUPLICATES, target })]);

    const wrapper = mountList();
    await wrapper.find('[data-testid=actions-center-row-action]').trigger('click');

    expect(wrapper.emitted('open')).toEqual([[target]]);
  });

  it('should show a premium gate instead of the action on a locked row', () => {
    set(state.issues, [createIssue({ locked: true, minimumTier: 'Basic' })]);

    const wrapper = mountList();

    expect(wrapper.find('[data-testid=actions-center-row-count]').text()).toBe('3');
    expect(wrapper.find('[data-testid=actions-center-row-locked]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=actions-center-row-action]').exists()).toBe(false);
  });

  it('should open a cleared category from its chip', async () => {
    set(state.issues, [createIssue({
      checkTarget: { kind: 'dialog', options: { type: DIALOG_TYPES.CUSTOMIZED_EVENT_DUPLICATES } },
      count: 0,
      id: HISTORY_ISSUE_IDS.AUTO_FIX_DUPLICATES,
    })]);

    const wrapper = mountList();
    await wrapper.find(`[data-testid=actions-center-cleared-${HISTORY_ISSUE_IDS.AUTO_FIX_DUPLICATES}]`).trigger('click');

    expect(wrapper.emitted('open')).toEqual([[{ kind: 'dialog', options: { type: DIALOG_TYPES.CUSTOMIZED_EVENT_DUPLICATES } }]]);
  });

  it('should re-scan every issue source on demand', async () => {
    set(state.issues, [createIssue({ count: 0 })]);

    const wrapper = mountList();
    await wrapper.find('[data-testid=actions-center-rescan]').trigger('click');

    expect(state.refreshAll).toHaveBeenCalledOnce();
  });
});
