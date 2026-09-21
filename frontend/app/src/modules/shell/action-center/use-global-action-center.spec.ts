import type { EffectScope } from 'vue';
import type { LocationQuery } from 'vue-router';
import type { HistoryEventIssue } from '@/modules/history/events/actions-center/use-history-event-issues';
import flushPromises from 'flush-promises';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type ActionItem, type ActionTarget, ActionUrgency, createActionItem } from '@/modules/core/action-center/types';
import { DIALOG_TYPES } from '@/modules/history/events/dialog-types';
import { useGlobalActionCenter } from '@/modules/shell/action-center/use-global-action-center';

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
};

vi.mock('@/modules/history/events/actions-center/use-history-event-issues', () => ({
  useHistoryEventIssues: (): object => ({
    checking: computed(() => get(state.historyChecking)),
    issues: computed(() => get(state.historyIssues)),
    refreshAll: state.refreshHistory,
    refreshing: computed(() => false),
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

vi.mock('@/modules/history/events/use-history-events-status', () => ({
  useHistoryEventsStatus: (): object => ({ processing: state.processing }),
}));

vi.mock('@/modules/history/events/use-unmatched-asset-movements', () => ({
  useUnmatchedAssetMovements: (): object => ({ autoMatchLoading: ref(false) }),
}));

vi.mock('@/modules/history/events/use-unmatched-bridge-transactions', () => ({
  useUnmatchedBridgeTransactions: (): object => ({ autoMatchLoading: ref(false) }),
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

let scope: EffectScope | undefined;

function center(): ReturnType<typeof useGlobalActionCenter> {
  scope = effectScope();
  const result = scope.run(() => useGlobalActionCenter());
  assert(result);
  return result;
}

describe('modules/shell/action-center/use-global-action-center', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    route.name = '/dashboard/';
    route.query = {};
    state.refreshAssets.mockResolvedValue();
    state.refreshHistory.mockResolvedValue();
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

  it('should lead the history section with the history sync row', async () => {
    set(state.historyIssues, [{ ...row('undecoded'), id: 'undecoded' }]);
    set(state.historySyncRows, [row('history-sync')]);
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

  it('should keep checking while the history counts are still pending', async () => {
    set(state.historyChecking, true);
    const { checking } = center();
    await flushPromises();

    expect(get(checking)).toBe(true);
  });
});
