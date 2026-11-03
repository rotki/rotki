import type { UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Component, defineComponent, h, type VNode } from 'vue';
import MatchAssetMovementsContent from '@/modules/history/events/MatchAssetMovementsContent.vue';
import MatchBridgeTransactionsContent from '@/modules/history/events/MatchBridgeTransactionsContent.vue';
import { UNMATCHED_ACTIONS } from '@/modules/history/events/unmatched-actions';

/** One set of fakes in words both kinds share; each kind's mocked composables rename them. */
const { actions, source } = await vi.hoisted(async () => {
  const { ref, shallowRef } = await import('vue');
  return {
    actions: {
      actionFailure: shallowRef<unknown>(),
      confirmCreateCounterpart: vi.fn<(item: unknown) => void>(),
      confirmIgnoreAllFiat: vi.fn<() => void>(),
      confirmIgnoreSelected: vi.fn<() => void>(),
      confirmRestoreSelected: vi.fn<() => void>(),
      dismissResolution: vi.fn<() => void>(),
      fiat: ref<unknown[]>([]),
      ignore: vi.fn<(item: unknown) => Promise<void>>(async () => Promise.resolve()),
      ignoreLoading: ref<boolean>(false),
      markExternal: vi.fn<(item: unknown) => Promise<void>>(async () => Promise.resolve()),
      modelSelectedIgnored: ref<string[]>([]),
      modelSelectedUnmatched: ref<string[]>([]),
      resolutionNotice: ref<{ message: string } | undefined>(),
      restore: vi.fn<(item: unknown) => Promise<void>>(async () => Promise.resolve()),
      undoResolution: vi.fn<() => Promise<void>>(async () => Promise.resolve()),
    },
    source: {
      autoMatch: vi.fn<() => void>(),
      autoMatchLoading: ref<boolean>(false),
      autoMatchMinimumTier: ref<string>('premium'),
      ignored: ref<unknown[]>([]),
      ignoredError: ref<unknown>(),
      ignoredLoading: ref<boolean>(false),
      isAutoMatchAllowed: ref<boolean>(true),
      loading: ref<boolean>(false),
      refresh: vi.fn<() => Promise<void>>(async () => Promise.resolve()),
      unmatched: ref<unknown[]>([]),
      unmatchedError: ref<unknown>(),
    },
  };
});

function sharedSource(): Record<string, unknown> {
  const { autoMatchLoading, autoMatchMinimumTier, ignoredError, ignoredLoading, isAutoMatchAllowed, loading, unmatchedError } = source;
  return { autoMatchLoading, autoMatchMinimumTier, ignoredError, ignoredLoading, isAutoMatchAllowed, loading, unmatchedError };
}

function sharedActions(): Record<string, unknown> {
  const { actionFailure, confirmIgnoreSelected, confirmRestoreSelected, dismissResolution, ignoreLoading, markExternal, modelSelectedIgnored, modelSelectedUnmatched, resolutionNotice, undoResolution } = actions;
  return { actionFailure, confirmIgnoreSelected, confirmRestoreSelected, dismissResolution, ignoreLoading, markExternal, modelSelectedIgnored, modelSelectedUnmatched, resolutionNotice, undoResolution };
}

vi.mock('@/modules/history/events/use-unmatched-asset-movements', () => ({
  useUnmatchedAssetMovements: (): Record<string, unknown> => ({
    ...sharedSource(),
    ignoredMovements: source.ignored,
    refreshUnmatchedAssetMovements: source.refresh,
    triggerAssetMovementAutoMatching: source.autoMatch,
    unmatchedMovements: source.unmatched,
  }),
}));

vi.mock('@/modules/history/events/use-asset-movement-actions', () => ({
  useAssetMovementActions: (): Record<string, unknown> => ({
    ...sharedActions(),
    confirmIgnoreAllFiat: actions.confirmIgnoreAllFiat,
    fiatMovements: actions.fiat,
    ignoreMovement: actions.ignore,
    restoreMovement: actions.restore,
  }),
}));

vi.mock('@/modules/history/events/use-unmatched-bridge-transactions', () => ({
  useUnmatchedBridgeTransactions: (): Record<string, unknown> => ({
    ...sharedSource(),
    ignoredTransactions: source.ignored,
    refreshUnmatchedBridgeTransactions: source.refresh,
    triggerBridgeAutoMatching: source.autoMatch,
    unmatchedTransactions: source.unmatched,
  }),
}));

vi.mock('@/modules/history/events/use-bridge-transaction-actions', () => ({
  useBridgeTransactionActions: (): Record<string, unknown> => ({
    ...sharedActions(),
    confirmCreateCounterpart: actions.confirmCreateCounterpart,
    ignoreTransaction: actions.ignore,
    restoreTransaction: actions.restore,
  }),
}));

type ButtonState = 'hidden' | 'disabled' | 'enabled';

/** The kind-specific parts of a matching panel's content that a spec over both kinds has to know. */
interface ContentKind {
  name: string;
  content: Component;
  listName: string;
  /** The list prop that carries the unmatched or ignored items. */
  itemsProp: string;
  actionErrorTestId: string;
  actionFailedTitle: string;
  autoMatchTooltip: string;
  /** Whether a row can create its missing counterpart from this panel. */
  createsCounterpart: boolean;
  /** What the bulk ignore and restore buttons do while nothing is selected. */
  emptySelection: ButtonState;
  /** Whether ignoring and restoring in bulk needs the auto-match tier. */
  gatesBulkOnTier: boolean;
  /** Whether the panel offers to ignore every fiat item at once. */
  ignoresFiat: boolean;
}

const CONTENT_KINDS: ContentKind[] = [
  {
    actionErrorTestId: 'unmatched-bridge-action-error',
    actionFailedTitle: 'bridge_matching.action_failed',
    autoMatchTooltip: 'bridge_matching.actions.auto_match_tooltip',
    content: MatchBridgeTransactionsContent,
    createsCounterpart: true,
    gatesBulkOnTier: false,
    emptySelection: 'hidden',
    ignoresFiat: false,
    itemsProp: 'transactions',
    listName: 'UnmatchedBridgesList',
    name: 'bridge',
  },
  {
    actionErrorTestId: 'unmatched-movement-action-error',
    actionFailedTitle: 'asset_movement_matching.action_failed',
    autoMatchTooltip: 'asset_movement_matching.actions.auto_match_tooltip',
    content: MatchAssetMovementsContent,
    createsCounterpart: false,
    gatesBulkOnTier: true,
    emptySelection: 'disabled',
    ignoresFiat: true,
    itemsProp: 'movements',
    listName: 'UnmatchedMovementsList',
    name: 'asset movement',
  },
];

function buttonState(wrapper: VueWrapper, testId: string): ButtonState {
  const button = wrapper.find(`[data-testid="${testId}"]`);
  if (!button.exists())
    return 'hidden';
  return button.attributes('disabled') === undefined ? 'enabled' : 'disabled';
}

const items = new Map<number, UnmatchedEventGroup>();

/** The same object for the same number, so a test can find an item again in what a list was given. */
function item(identifier: number): UnmatchedEventGroup {
  const existing = items.get(identifier);
  if (existing)
    return existing;
  const created: UnmatchedEventGroup = { asset: 'ETH', events: [], groupIdentifier: `group-${identifier}`, identifier };
  items.set(identifier, created);
  return created;
}

describe.each(CONTENT_KINDS)('unmatched matching content ($name)', (kind) => {
  const ListStub = defineComponent({
    emits: ['action', 'pin', 'retry'],
    name: kind.listName,
    props: { error: { default: undefined, type: null }, [kind.itemsProp]: { default: () => [], type: Array } },
    setup(_, { emit }): () => VNode {
      return (): VNode => h('div', { 'data-testid': 'unmatched-list', 'onClick': () => emit('pin') });
    },
  });

  const TooltipStub = defineComponent({
    name: 'RuiTooltip',
    setup: (_, { slots }) => (): VNode[] => [...(slots.activator?.() ?? []), h('span', { 'data-testid': 'tooltip' }, slots.default?.())],
  });

  const counterpartCalls: unknown[][] = kind.createsCounterpart ? [[item(6)]] : [];

  async function mountContent(props: Record<string, unknown> = {}): Promise<VueWrapper> {
    const wrapper = mount(kind.content, {
      global: {
        stubs: {
          AssetMovementMatchingSettingsMenu: true,
          RuiTooltip: TooltipStub,
          UnmatchedResolutionStrip: true,
          [kind.listName]: ListStub,
        },
      },
      props,
    });
    await flushPromises();
    return wrapper;
  }

  function triggerAction(wrapper: VueWrapper, action: string, target: UnmatchedEventGroup): void {
    wrapper.findComponent(ListStub).vm.$emit('action', { action, item: target });
  }

  async function openIgnoredTab(wrapper: VueWrapper): Promise<void> {
    wrapper.findComponent({ name: 'RuiTabs' }).vm.$emit('update:modelValue', 1);
    await nextTick();
  }

  beforeEach(() => {
    vi.clearAllMocks();
    set(source.unmatched, []);
    set(source.ignored, []);
    set(source.unmatchedError, undefined);
    set(source.ignoredError, undefined);
    set(source.isAutoMatchAllowed, true);
    set(actions.actionFailure, undefined);
    set(actions.fiat, []);
    set(actions.modelSelectedIgnored, []);
    set(actions.modelSelectedUnmatched, []);
    set(actions.resolutionNotice, undefined);
  });

  it('should refresh its items on mount, so the pane is never empty by default', async () => {
    await mountContent();

    expect(source.refresh).toHaveBeenCalledOnce();
  });

  it('should hand each list the failure of its own fetch', async () => {
    const unmatchedFailure = new Error('unmatched down');
    const ignoredFailure = new Error('ignored down');
    set(source.unmatched, [item(1)]);
    set(source.ignored, [item(2)]);
    set(source.unmatchedError, unmatchedFailure);
    set(source.ignoredError, ignoredFailure);
    const wrapper = await mountContent();

    const lists = wrapper.findAllComponents(ListStub);
    expect(lists.length).toBeGreaterThan(0);
    for (const list of lists) {
      const shown: unknown[] = list.props(kind.itemsProp) ?? [];
      expect(list.props('error')).toBe(shown.includes(item(1)) ? unmatchedFailure : ignoredFailure);
    }
  });

  it('should refresh again when a list asks for a retry', async () => {
    const wrapper = await mountContent();

    wrapper.findComponent(ListStub).vm.$emit('retry');

    expect(source.refresh).toHaveBeenCalledTimes(2);
  });

  describe('where each row action goes', () => {
    it('should ask the parent to open the matcher rather than matching itself', async () => {
      const wrapper = await mountContent();

      triggerAction(wrapper, UNMATCHED_ACTIONS.FIND_MATCH, item(1));

      expect(wrapper.emitted('select')?.[0]).toEqual([item(1)]);
      expect(actions.ignore).not.toHaveBeenCalled();
    });

    it('should ask the parent to show the row in events', async () => {
      const wrapper = await mountContent();

      triggerAction(wrapper, UNMATCHED_ACTIONS.SHOW_IN_EVENTS, item(2));

      expect(wrapper.emitted('show-in-events')?.[0]).toEqual([item(2)]);
    });

    it('should ignore exactly the row the action carried', async () => {
      const wrapper = await mountContent();

      triggerAction(wrapper, UNMATCHED_ACTIONS.IGNORE, item(3));

      expect(actions.ignore).toHaveBeenCalledExactlyOnceWith(item(3));
      expect(actions.restore).not.toHaveBeenCalled();
    });

    it('should restore exactly the row the action carried', async () => {
      const wrapper = await mountContent();

      triggerAction(wrapper, UNMATCHED_ACTIONS.RESTORE, item(4));

      expect(actions.restore).toHaveBeenCalledExactlyOnceWith(item(4));
      expect(actions.ignore).not.toHaveBeenCalled();
    });

    it('should mark exactly the row the action carried as external', async () => {
      const wrapper = await mountContent();

      triggerAction(wrapper, UNMATCHED_ACTIONS.MARK_EXTERNAL, item(5));

      expect(actions.markExternal).toHaveBeenCalledExactlyOnceWith(item(5));
    });

    it(`should ${kind.createsCounterpart ? 'confirm before creating' : 'ignore a request to create'} a counterpart`, async () => {
      const wrapper = await mountContent();

      triggerAction(wrapper, UNMATCHED_ACTIONS.CREATE_COUNTERPART, item(6));

      expect(actions.confirmCreateCounterpart.mock.calls).toEqual(counterpartCalls);
      expect(actions.ignore).not.toHaveBeenCalled();
      expect(actions.restore).not.toHaveBeenCalled();
      expect(actions.markExternal).not.toHaveBeenCalled();
      expect(wrapper.emitted('select')).toBeUndefined();
      expect(wrapper.emitted('show-in-events')).toBeUndefined();
    });
  });

  describe('the bulk actions', () => {
    it('should confirm before ignoring the selection, rather than ignoring it outright', async () => {
      set(actions.modelSelectedUnmatched, ['1']);
      const wrapper = await mountContent();

      await wrapper.find('[data-testid="ignore-selected"]').trigger('click');

      expect(actions.confirmIgnoreSelected).toHaveBeenCalledOnce();
      expect(actions.ignore).not.toHaveBeenCalled();
    });

    it(`should keep the ignore button ${kind.emptySelection} while nothing is selected`, async () => {
      const wrapper = await mountContent();
      expect(buttonState(wrapper, 'ignore-selected')).toBe(kind.emptySelection);

      set(actions.modelSelectedUnmatched, ['1']);
      await nextTick();

      expect(buttonState(wrapper, 'ignore-selected')).toBe('enabled');
    });

    it(`should ${kind.gatesBulkOnTier ? 'disable' : 'still offer'} ignoring the selection while auto-match is not allowed`, async () => {
      set(actions.modelSelectedUnmatched, ['1']);
      set(source.isAutoMatchAllowed, false);
      const wrapper = await mountContent();

      expect(buttonState(wrapper, 'ignore-selected')).toBe(kind.gatesBulkOnTier ? 'disabled' : 'enabled');
    });

    it.runIf(kind.ignoresFiat)('should confirm before ignoring every fiat item', async () => {
      set(actions.fiat, [item(1)]);
      const wrapper = await mountContent();

      await wrapper.find('[data-testid="ignore-fiat"]').trigger('click');

      expect(actions.confirmIgnoreAllFiat).toHaveBeenCalledOnce();
    });

    it.skipIf(kind.ignoresFiat)('should offer no fiat ignore', async () => {
      set(actions.fiat, [item(1)]);
      const wrapper = await mountContent();

      expect(buttonState(wrapper, 'ignore-fiat')).toBe('hidden');
    });

    it('should start auto-matching only when there is something to match', async () => {
      const wrapper = await mountContent();
      expect(wrapper.find('[data-testid="auto-match"]').attributes('disabled')).toBeDefined();

      set(source.unmatched, [item(1)]);
      await nextTick();

      await wrapper.find('[data-testid="auto-match"]').trigger('click');
      expect(source.autoMatch).toHaveBeenCalledOnce();
    });

    it('should explain auto-matching in its own words', async () => {
      const wrapper = await mountContent();

      const tooltips = wrapper.findAll('[data-testid="tooltip"]').map(tooltip => tooltip.text());
      expect(tooltips).toContain(kind.autoMatchTooltip);
    });
  });

  describe('the ignored tab', () => {
    it('should confirm before restoring the selection', async () => {
      set(source.ignored, [item(1)]);
      set(actions.modelSelectedIgnored, ['1']);
      const wrapper = await mountContent();
      await openIgnoredTab(wrapper);

      await wrapper.find('[data-testid="restore-selected"]').trigger('click');

      expect(actions.confirmRestoreSelected).toHaveBeenCalledOnce();
      expect(actions.restore).not.toHaveBeenCalled();
    });

    it(`should keep the restore button ${kind.emptySelection} while nothing is selected`, async () => {
      set(source.ignored, [item(1)]);
      const wrapper = await mountContent();
      await openIgnoredTab(wrapper);
      expect(buttonState(wrapper, 'restore-selected')).toBe(kind.emptySelection);

      set(actions.modelSelectedIgnored, ['1']);
      await nextTick();

      expect(buttonState(wrapper, 'restore-selected')).toBe('enabled');
    });
  });

  describe('what it forwards to its parent', () => {
    it('should pass a pin request straight up', async () => {
      const wrapper = await mountContent();

      await wrapper.find('[data-testid="unmatched-list"]').trigger('click');

      expect(wrapper.emitted('pin')).toHaveLength(1);
    });

    it('should offer a close button only in the dialog', async () => {
      const pinned = await mountContent({ isPinned: true });
      expect(pinned.find('[data-testid="close"]').exists()).toBe(false);

      const dialog = await mountContent();
      await dialog.find('[data-testid="close"]').trigger('click');
      expect(dialog.emitted('close')).toHaveLength(1);
    });
  });

  describe('the resolution notice', () => {
    it('should stay hidden until something has been resolved', async () => {
      const wrapper = await mountContent();

      expect(wrapper.findComponent({ name: 'UnmatchedResolutionStrip' }).exists()).toBe(false);
    });

    it('should appear once a resolution is pending an undo', async () => {
      set(actions.resolutionNotice, { message: 'ignored 2 items' });

      const wrapper = await mountContent();

      expect(wrapper.findComponent({ name: 'UnmatchedResolutionStrip' }).exists()).toBe(true);
    });
  });

  describe('a failed action', () => {
    it('should name the failure in the panel under its own title, without a retry', async () => {
      set(actions.actionFailure, new Error('backend down'));

      const wrapper = await mountContent();

      const strip = wrapper.find(`[data-testid=${kind.actionErrorTestId}]`);
      expect(strip.text()).toContain('backend down');
      expect(strip.text()).toContain(kind.actionFailedTitle);
      expect(strip.find('[data-testid=failure-strip-retry]').exists()).toBe(false);
    });

    it('should show nothing while no action failed', async () => {
      const wrapper = await mountContent();

      expect(wrapper.find(`[data-testid=${kind.actionErrorTestId}]`).exists()).toBe(false);
    });
  });
});
