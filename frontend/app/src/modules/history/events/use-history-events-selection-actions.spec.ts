import type { HistoryEventEntry, HistoryEventRow } from '@/modules/history/events/schemas';
import { createMock } from '@test/utils/create-mock';
import { err, ok } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistoryEventsActionFailure } from './use-history-events-action-failure';
import { useHistoryEventsSelectionActions } from './use-history-events-selection-actions';
import { useHistoryEventsSelectionMode } from './use-selection-mode';

const { spies } = vi.hoisted(() => ({
  spies: {
    ignore: vi.fn(),
  },
}));

vi.mock('@/modules/history/use-ignore', () => ({
  useIgnore: (): object => ({ ignore: spies.ignore }),
}));

function historyEvent(overrides: Partial<HistoryEventEntry>): HistoryEventEntry {
  return createMock<HistoryEventEntry>({ eventSubtype: 'fee', eventType: 'spend', ignoredInAccounting: false, ...overrides });
}

function setup(events: HistoryEventEntry[]): {
  actions: ReturnType<typeof useHistoryEventsSelectionActions>;
  selectionMode: ReturnType<typeof useHistoryEventsSelectionMode>;
  deleteSelected: ReturnType<typeof vi.fn>;
  refreshCallback: ReturnType<typeof vi.fn>;
} {
  const selectionMode = useHistoryEventsSelectionMode();
  const deleteSelected = vi.fn().mockResolvedValue(undefined);
  const refreshCallback = vi.fn().mockResolvedValue(undefined);
  const originalGroups = ref<HistoryEventRow[]>(events);
  const actions = useHistoryEventsSelectionActions({
    deletion: { deleteSelected },
    originalGroups,
    refreshCallback,
    selectionMode,
  });
  return { actions, deleteSelected, refreshCallback, selectionMode };
}

function select(selectionMode: ReturnType<typeof useHistoryEventsSelectionMode>, ...ids: number[]): void {
  ids.forEach(id => selectionMode.actions.toggleEvent(id));
}

const { failure: actionFailure, clear: clearActionFailure, report: reportActionFailure } = useHistoryEventsActionFailure();

describe('useHistoryEventsSelectionActions', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    clearActionFailure();
    spies.ignore.mockResolvedValue(ok(undefined));
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should delegate the delete action to the deletion handler', async () => {
    const { actions, deleteSelected } = setup([]);
    await actions.handleSelectionAction('delete');
    expect(deleteSelected).toHaveBeenCalledOnce();
  });

  it('should name a failed bulk exclusion above the table', async () => {
    spies.ignore.mockResolvedValue(err('boom'));
    const { actions, selectionMode } = setup([historyEvent({ identifier: 1 })]);
    select(selectionMode, 1);

    await actions.handleSelectionAction('ignore');

    expect(spies.ignore).toHaveBeenCalledWith(true);
    expect(get(actionFailure)).toEqual({ failure: 'boom', title: 'actions.ignore.error.title' });
  });

  it('should name a failed bulk inclusion under its own title', async () => {
    spies.ignore.mockResolvedValue(err('boom'));
    const { actions, selectionMode } = setup([historyEvent({ identifier: 1, ignoredInAccounting: true })]);
    select(selectionMode, 1);

    await actions.handleSelectionAction('unignore');

    expect(spies.ignore).toHaveBeenCalledWith(false);
    expect(get(actionFailure)).toEqual({ failure: 'boom', title: 'actions.unignore.error.title' });
  });

  it('should drop the last failure when the next exclusion starts', async () => {
    reportActionFailure('actions.ignore.error.title', 'boom');
    const { actions, selectionMode } = setup([historyEvent({ identifier: 1 })]);
    select(selectionMode, 1);

    await actions.handleSelectionAction('ignore');

    expect(get(actionFailure)).toBeUndefined();
  });

  it('should drive selection-mode toggles', async () => {
    const { actions, selectionMode } = setup([]);
    await actions.handleSelectionAction('toggle-mode');
    expect(get(selectionMode.isSelectionMode)).toBe(true);
    await actions.handleSelectionAction('exit');
    expect(get(selectionMode.isSelectionMode)).toBe(false);
    await actions.handleSelectionAction('toggle-select-all-matching');
    expect(get(selectionMode.isSelectAllMatching)).toBe(true);
  });

  it('should report the ignored/not-ignored split of the selection', () => {
    const events = [
      historyEvent({ identifier: 1, ignoredInAccounting: true }),
      historyEvent({ identifier: 2, ignoredInAccounting: false }),
      historyEvent({ identifier: 3, ignoredInAccounting: false }),
    ];
    const { actions, selectionMode } = setup(events);
    select(selectionMode, 1, 2, 3);
    expect(get(actions.ignoreStatus)).toEqual({ ignoredCount: 1, notIgnoredCount: 2 });
  });

  it('should name no rule blocker while nothing is selected', () => {
    const { actions } = setup([]);
    expect(get(actions.ruleCreationBlocker)).toBeUndefined();
  });

  it('should block rule creation, seeding nothing, when no selected event is loaded', async () => {
    const { actions, selectionMode } = setup([historyEvent({ identifier: 1 })]);
    select(selectionMode, 7);
    expect(get(actions.ruleCreationBlocker)).toBe('transactions.events.accounting_rule.no_events_found');

    await actions.handleSelectionAction('create-rule');
    expect(get(actions.modelAccountingRuleToEdit)).toBeUndefined();
  });

  it('should block rule creation, seeding nothing, when the selected events have differing types', async () => {
    const events = [
      historyEvent({ eventSubtype: 'fee', eventType: 'spend', identifier: 1 }),
      historyEvent({ eventSubtype: 'reward', eventType: 'receive', identifier: 2 }),
    ];
    const { actions, selectionMode } = setup(events);
    select(selectionMode, 1, 2);
    expect(get(actions.ruleCreationBlocker)).toBe('transactions.events.accounting_rule.different_types_error');

    await actions.handleSelectionAction('create-rule');
    expect(get(actions.modelAccountingRuleToEdit)).toBeUndefined();
  });

  it('should seed an accounting rule when the selection shares a type', async () => {
    const events = [
      historyEvent({ eventSubtype: 'fee', eventType: 'spend', identifier: 1 }),
      historyEvent({ eventSubtype: 'fee', eventType: 'spend', identifier: 2 }),
    ];
    const { actions, selectionMode } = setup(events);
    select(selectionMode, 1, 2);
    expect(get(actions.ruleCreationBlocker)).toBeUndefined();
    await actions.handleSelectionAction('create-rule');
    expect(get(actions.selectedEventIds)).toEqual([1, 2]);
    expect(get(actions.modelAccountingRuleToEdit)).toMatchObject({ eventSubtype: 'fee', eventType: 'spend' });
  });

  it('should ignore and unignore the selected events', async () => {
    const events = [historyEvent({ identifier: 1 })];
    const { actions, selectionMode } = setup(events);
    select(selectionMode, 1);

    await actions.handleSelectionAction('ignore');
    expect(spies.ignore).toHaveBeenLastCalledWith(true);

    await actions.handleSelectionAction('unignore');
    expect(spies.ignore).toHaveBeenLastCalledWith(false);
  });

  it('should exit selection mode after an accounting-rule refresh', () => {
    const { actions, selectionMode } = setup([]);
    selectionMode.actions.toggle();
    actions.handleAccountingRuleRefresh();
    expect(get(selectionMode.isSelectionMode)).toBe(false);
  });
});
