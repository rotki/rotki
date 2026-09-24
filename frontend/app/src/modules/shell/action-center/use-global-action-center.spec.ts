import type { EffectScope } from 'vue';
import type { LocationQuery } from 'vue-router';
import type { HistoryEventIssue } from '@/modules/history/events/actions-center/use-history-event-issues';
import type { useGlobalActionCenter as UseGlobalActionCenter } from '@/modules/shell/action-center/use-global-action-center';
import flushPromises from 'flush-promises';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { type ActionItem, type ActionTarget, ActionUrgency, createActionItem } from '@/modules/core/action-center/types';
import { DIALOG_TYPES } from '@/modules/history/events/dialog-types';

const state = {
  assetRows: ref<ActionItem[]>([]),
  chainRows: ref<ActionItem[]>([]),
  historyChecking: ref<boolean>(false),
  historyIssues: ref<HistoryEventIssue[]>([]),
  historySyncRows: ref<ActionItem[]>([]),
  integrationRows: ref<ActionItem[]>([]),
  processing: ref<boolean>(false),
  refreshAssets: vi.fn<() => Promise<void>>(),
  refreshHistory: vi.fn<() => Promise<void>>(),
  rescanHistory: vi.fn<() => Promise<void>>(),
};

vi.mock('@/modules/history/events/actions-center/use-history-event-issues', () => ({
  useHistoryEventIssues: (): object => ({
    busy: computed(() => get(state.processing)),
    checking: computed(() => get(state.historyChecking)),
    issues: computed(() => get(state.historyIssues)),
    refreshAll: state.refreshHistory,
    refreshing: computed(() => false),
    rescan: state.rescanHistory,
  }),
}));

vi.mock('@/modules/shell/action-center/use-integration-rows', () => ({
  useIntegrationRows: (): object => computed(() => get(state.integrationRows)),
}));

vi.mock('@/modules/shell/action-center/use-history-sync-row', () => ({
  useHistorySyncRow: (): object => computed(() => get(state.historySyncRows)),
}));

vi.mock('@/modules/shell/action-center/use-chain-rows', () => ({
  useChainRows: (): object => computed(() => get(state.chainRows)),
}));

vi.mock('@/modules/shell/action-center/use-asset-rows', () => ({
  useAssetRows: (): object => ({ refresh: state.refreshAssets, rows: computed(() => get(state.assetRows)) }),
}));

const route = reactive<{ name: string; query: LocationQuery }>({ name: '/dashboard/', query: {} });

vi.mock('vue-router', () => ({
  useRoute: (): object => route,
}));

vi.mock('@/modules/core/common/use-ref-debounce', () => ({
  useRefWithDebounce: (source: Ref<boolean>): Ref<boolean> => source,
}));

function row(id: string, overrides: Partial<ActionItem> = {}): ActionItem {
  return {
    ...createActionItem<ActionTarget, string>({
      actionLabel: 'act',
      count: 1,
      description: 'description',
      icon: 'lu-key-round',
      id,
      urgency: ActionUrgency.DECISION,
      target: { kind: 'route', to: { name: '/accounts/' } },
      title: id,
    }),
    ...overrides,
  };
}

function runOption(item: ActionItem | undefined, id: string): void {
  const option = item?.options.find(candidate => candidate.id === id);
  assert(option?.target.kind === 'run');
  option.target.run();
}

let scope: EffectScope | undefined;

/** Reloaded per test: whether a center has scanned is module-level state, so one test's scan would decide the next one's. */
let useGlobalActionCenter: typeof UseGlobalActionCenter;

function center(): ReturnType<typeof UseGlobalActionCenter> {
  scope = effectScope();
  const result = scope.run(() => useGlobalActionCenter());
  assert(result);
  return result;
}

describe('modules/shell/action-center/use-global-action-center', () => {
  beforeEach(async () => {
    vi.resetModules();
    ({ useGlobalActionCenter } = await import('@/modules/shell/action-center/use-global-action-center'));
    localStorage.clear();
    setActivePinia(createPinia());
    vi.clearAllMocks();
    route.name = '/dashboard/';
    route.query = {};
    state.refreshAssets.mockResolvedValue();
    state.refreshHistory.mockResolvedValue();
    state.rescanHistory.mockResolvedValue();
    set(state.assetRows, []);
    set(state.chainRows, []);
    set(state.historyChecking, false);
    set(state.historyIssues, []);
    set(state.historySyncRows, []);
    set(state.integrationRows, []);
    set(state.processing, false);
  });

  afterEach(() => {
    scope?.stop();
  });

  it('should group raised rows by module in module order, leaving out a module with nothing raised', async () => {
    set(state.integrationRows, [row('missing-api-key-etherscan')]);
    set(state.assetRows, [row('missing-exchange-mappings', { count: 0 })]);
    set(state.chainRows, [row('no-available-indexers-base')]);
    const { sections } = center();
    await flushPromises();

    expect(get(sections).map(section => section.id)).toEqual(['chains', 'integrations']);
    expect(get(sections)[0].title).toBe('action_center.sections.chains');
  });

  it('should list a checked category with nothing pending as cleared', async () => {
    set(state.assetRows, [row('missing-exchange-mappings', { count: 0 })]);
    const { cleared } = center();
    await flushPromises();

    expect(get(cleared).map(item => item.id)).toEqual(['missing-exchange-mappings']);
  });

  it('should order a section by what needs doing, then what was set aside, then what is locked', async () => {
    set(state.integrationRows, [
      row('locked', { locked: true }),
      row('set-aside', { informational: true }),
      row('to-do'),
    ]);
    const { sections } = center();
    await flushPromises();

    expect(get(sections)[0].items.map(item => item.id)).toEqual(['to-do', 'set-aside', 'locked']);
  });

  it('should put decisions before work that resolves itself, and that before what rotki retries', async () => {
    set(state.integrationRows, [
      row('automatic', { urgency: ActionUrgency.AUTOMATIC }),
      row('todo', { urgency: ActionUrgency.TODO }),
      row('decision', { urgency: ActionUrgency.DECISION }),
    ]);
    const { sections } = center();
    await flushPromises();

    expect(get(sections)[0].items.map(item => item.id)).toEqual(['decision', 'todo', 'automatic']);
  });

  it('should count only the categories that ask for something now', async () => {
    set(state.integrationRows, [row('to-do'), row('set-aside', { informational: true }), row('locked', { locked: true })]);
    set(state.chainRows, [row('no-available-indexers-base')]);
    const { count } = center();
    await flushPromises();

    expect(get(count)).toBe(2);
  });

  it('should turn a history dialog target into a route that opens it from any page', async () => {
    set(state.historyIssues, [{
      ...row('unmatched-movements'),
      checkTarget: { kind: 'dialog', options: { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS } },
      id: 'unmatched-movements',
      target: { kind: 'dialog', options: { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS } },
    }]);
    const { sections } = center();
    await flushPromises();

    expect(get(sections)[0].items[0].target).toEqual({
      kind: 'route',
      to: { name: '/history/events/', query: { openMatchAssetMovementsDialog: 'true' } },
    });
  });

  it('should open a history dialog over the history page the user is on, keeping its filters', async () => {
    route.name = '/history/events/';
    route.query = { location: 'kraken', page: '3' };
    set(state.historyIssues, [{
      ...row('unmatched-movements'),
      checkTarget: { kind: 'dialog', options: { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS } },
      id: 'unmatched-movements',
      target: { kind: 'dialog', options: { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS } },
    }]);
    const { sections } = center();
    await flushPromises();

    expect(get(sections)[0].items[0].target).toEqual({
      kind: 'route',
      to: {
        name: '/history/events/',
        query: { location: 'kraken', openMatchAssetMovementsDialog: 'true', page: '3' },
        replace: true,
      },
    });
  });

  it('should turn a history option dialog target into a route as well', async () => {
    set(state.historyIssues, [{
      ...row('unmatched-bridges'),
      checkTarget: { kind: 'route', to: { name: '/history/events/' } },
      id: 'unmatched-bridges',
      options: [{
        icon: 'lu-eye-off',
        id: 'review-ignored',
        label: 'review',
        target: { kind: 'dialog', options: { type: DIALOG_TYPES.MATCH_BRIDGE_TRANSACTIONS } },
      }],
      target: { kind: 'route', to: { name: '/history/events/' } },
    }]);
    const { sections } = center();
    await flushPromises();

    expect(get(sections)[0].items[0].options[0].target).toEqual({
      kind: 'route',
      to: { name: '/history/events/', query: { openMatchBridgesDialog: 'true' } },
    });
  });

  it('should lead the history section with the history sync row, ahead of more urgent rows', async () => {
    set(state.historyIssues, [{ ...row('undecoded'), id: 'undecoded' }]);
    set(state.historySyncRows, [row('history-sync', { urgency: ActionUrgency.TODO })]);
    const { sections } = center();
    await flushPromises();

    const [history] = get(sections);
    expect(history.id).toBe('history');
    expect(history.items.map(item => item.id)).toEqual(['history-sync', 'undecoded']);
  });

  it('should scan every source as soon as it starts on a settled session', async () => {
    center();
    await flushPromises();

    expect(state.refreshHistory).toHaveBeenCalledOnce();
    expect(state.refreshAssets).toHaveBeenCalledOnce();
  });

  it('should scan again when the history work settles, and not while it runs', async () => {
    set(state.processing, true);
    center();
    await flushPromises();

    expect(state.refreshHistory).not.toHaveBeenCalled();

    set(state.processing, false);
    await flushPromises();

    expect(state.refreshHistory).toHaveBeenCalledOnce();
  });

  it('should re-read history with the lighter rescan when it settles after the first scan', async () => {
    center();
    await flushPromises();

    set(state.processing, true);
    await flushPromises();
    set(state.processing, false);
    await flushPromises();

    expect(state.refreshHistory).toHaveBeenCalledOnce();
    expect(state.rescanHistory).toHaveBeenCalledOnce();
  });

  it('should stop counting a snoozed row and set it aside at the end of its section', async () => {
    set(state.integrationRows, [row('snoozed'), row('other')]);
    const { count, sections } = center();
    await flushPromises();

    runOption(get(sections)[0].items[0], 'remind-later');
    await nextTick();

    expect(get(count)).toBe(1);
    expect(get(sections)[0].items.map(item => item.id)).toEqual(['other', 'snoozed']);
  });

  it('should mark a snoozed row as new once it is brought back, though it was seen before', async () => {
    set(state.integrationRows, [row('snoozed')]);
    const { markSeen, newIds, sections } = center();
    await flushPromises();
    markSeen();
    await nextTick();
    expect(get(newIds)).toEqual([]);

    runOption(get(sections)[0].items[0], 'remind-later');
    await nextTick();
    runOption(get(sections)[0].items[0], 'remind-now');
    await nextTick();

    expect(get(newIds)).toEqual(['snoozed']);
  });

  it('should await the first scan while the history counts are still pending', async () => {
    const { awaitingFirstScan, refreshAll, refreshing } = center();
    await flushPromises();

    const auth = useSessionAuthStore();
    auth.logged = true;
    await nextTick();
    auth.logged = false;
    await nextTick();

    set(state.historyChecking, true);
    await refreshAll();

    expect(get(awaitingFirstScan)).toBe(true);
    expect(get(refreshing)).toBe(true);

    set(state.historyChecking, false);
    await refreshAll();

    expect(get(awaitingFirstScan)).toBe(false);
  });

  it('should keep a row that is re-reading listed through a re-scan', async () => {
    set(state.historySyncRows, [row('history-sync', { urgency: ActionUrgency.TODO })]);
    const { awaitingFirstScan, count, refreshing, sections } = center();
    await flushPromises();

    set(state.historySyncRows, [row('history-sync', { loading: true, urgency: ActionUrgency.TODO })]);
    set(state.historyChecking, true);
    await nextTick();

    expect(get(awaitingFirstScan)).toBe(false);
    expect(get(refreshing)).toBe(true);
    expect(get(count)).toBe(1);
    expect(get(sections).flatMap(section => section.items.map(item => item.id))).toEqual(['history-sync']);
  });
});
