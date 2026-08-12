import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import HistoryEventsActionsCenter from '@/modules/history/events/actions-center/HistoryEventsActionsCenter.vue';
import { DIALOG_TYPES } from '@/modules/history/events/dialog-types';
import { PinnedNames, toPinned } from '@/modules/session/types';

// Declared at module scope (not `vi.hoisted`): the mock factories below only
// dereference `state` from inside their inner arrows, which run once the tests do.
const state = {
  categoryCount: ref(0),
  checking: ref(false),
  fetchUndecodedTransactionsBreakdown: vi.fn<() => Promise<void>>(),
  push: vi.fn<(to: unknown) => Promise<void>>(),
  refreshAll: vi.fn<() => Promise<void>>(),
};

vi.mock('@/modules/history/events/actions-center/use-history-event-issues', () => ({
  useHistoryEventIssues: (): object => ({
    activeItems: computed(() => []),
    categoryCount: state.categoryCount,
    checking: state.checking,
    clearedItems: computed(() => []),
    hasItems: computed(() => get(state.categoryCount) > 0),
    lockedItems: computed(() => []),
    refreshAll: state.refreshAll,
    refreshing: computed(() => false),
    reviewItems: computed(() => []),
  }),
}));

vi.mock('@/modules/history/events/tx/use-undecoded-transactions-count', () => ({
  useUndecodedTransactionsCount: (): object => ({
    fetchUndecodedTransactionsBreakdown: state.fetchUndecodedTransactionsBreakdown,
  }),
}));

vi.mock('@/modules/history/events/use-history-events-status', () => ({
  useHistoryEventsStatus: (): object => ({ processing: ref(false) }),
}));

vi.mock('@/modules/history/events/use-unmatched-asset-movements', () => ({
  useUnmatchedAssetMovements: (): object => ({ autoMatchLoading: ref(false) }),
}));

vi.mock('@/modules/history/events/use-unmatched-bridge-transactions', () => ({
  useUnmatchedBridgeTransactions: (): object => ({ autoMatchLoading: ref(false) }),
}));

vi.mock('vue-router', () => ({
  useRouter: (): object => ({ push: state.push }),
}));

function mountCenter(): VueWrapper<InstanceType<typeof HistoryEventsActionsCenter>> {
  return mount(HistoryEventsActionsCenter, { attachTo: document.body });
}

// The menu owns its open state internally, so tests drive it the way the menu
// itself would: through the v-model the center binds to it.
async function openMenu(
  wrapper: VueWrapper<InstanceType<typeof HistoryEventsActionsCenter>>,
): Promise<VueWrapper> {
  wrapper.findComponent({ name: 'RuiMenu' }).vm.$emit('update:modelValue', true);
  await flushPromises();
  // the menu teleports its content, which lands a tick or two after it opens.
  // Found by name rather than by component: a generic SFC does not resolve as a
  // constructor, so `findComponent(ActionCenterList)` types as a DOM wrapper.
  return vi.waitFor(() => {
    const list = wrapper.findComponent({ name: 'ActionCenterList' });
    expect(list.exists()).toBe(true);
    return list;
  });
}

describe('modules/history/events/actions-center/HistoryEventsActionsCenter', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    vi.clearAllMocks();
    state.fetchUndecodedTransactionsBreakdown.mockResolvedValue();
    state.push.mockResolvedValue();
    state.refreshAll.mockResolvedValue();
    set(state.categoryCount, 0);
    set(state.checking, false);
  });

  it('should show the category count when there is something to act on', () => {
    set(state.categoryCount, 3);

    const wrapper = mountCenter();

    expect(wrapper.find('[data-testid=actions-center-button-count]').text()).toBe('3');
    expect(wrapper.text()).toContain('action_center.button');
  });

  it('should stay countless and quiet while the counts are still pending', () => {
    set(state.checking, true);

    const wrapper = mountCenter();

    expect(wrapper.find('[data-testid=actions-center-button-count]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=actions-center-button]').attributes('aria-label')).toBe('action_center.button_checking');
  });

  it('should report all clear once a scan has landed with nothing to do', () => {
    const wrapper = mountCenter();

    expect(wrapper.find('[data-testid=actions-center-button-count]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=actions-center-button]').attributes('aria-label')).toBe('action_center.button_clear');
  });

  it('should hang the menu off the trigger and start closed', () => {
    const wrapper = mountCenter();
    const menu = wrapper.findComponent({ name: 'RuiMenu' });

    expect(menu.props('modelValue')).toBe(false);
    expect(menu.find('[data-testid=actions-center-button]').exists()).toBe(true);
  });

  it('should scan as soon as the history work is settled', () => {
    mountCenter();

    expect(state.refreshAll).toHaveBeenCalledOnce();
    expect(state.fetchUndecodedTransactionsBreakdown).toHaveBeenCalledOnce();
  });

  it('should forward a dialog target and close the menu', async () => {
    const wrapper = mountCenter();
    const list = await openMenu(wrapper);

    list.vm.$emit('open', {
      kind: 'dialog',
      options: { type: DIALOG_TYPES.MATCH_BRIDGE_TRANSACTIONS },
    });
    await nextTick();

    expect(wrapper.emitted('show:dialog')).toEqual([[{ type: DIALOG_TYPES.MATCH_BRIDGE_TRANSACTIONS }]]);
    expect(wrapper.findComponent({ name: 'RuiMenu' }).props('modelValue')).toBe(false);
  });

  it('should open a pin target in the rail beside the table', async () => {
    const store = useAreaVisibilityStore();
    const wrapper = mountCenter();
    const list = await openMenu(wrapper);

    list.vm.$emit('open', { kind: 'pin', panel: toPinned(PinnedNames.DATA_ISSUES, {}) });
    await nextTick();

    // The panel is pinned, focused and the rail revealed, without leaving the page.
    expect(get(store.pinnedPanels).map(panel => panel.name)).toEqual([PinnedNames.DATA_ISSUES]);
    expect(get(store.activePinnedId)).toBe(PinnedNames.DATA_ISSUES);
    expect(get(store.showPinned)).toBe(true);
    expect(state.push).not.toHaveBeenCalled();
    expect(wrapper.emitted('show:dialog')).toBeUndefined();
  });

  it('should route a duplicates target to the filtered events list', async () => {
    const wrapper = mountCenter();
    const list = await openMenu(wrapper);

    list.vm.$emit('open', {
      groupIds: ['a', 'b'],
      kind: 'duplicates',
      status: DuplicateHandlingStatus.AUTO_FIX,
    });
    await nextTick();

    expect(wrapper.emitted('show:dialog')).toBeUndefined();
    expect(state.push).toHaveBeenCalledWith({
      name: '/history/events/',
      query: {
        duplicateHandlingStatus: DuplicateHandlingStatus.AUTO_FIX,
        groupIdentifiers: 'a,b',
      },
    });
  });

  it('should navigate on a plain route target', async () => {
    const wrapper = mountCenter();
    const list = await openMenu(wrapper);

    list.vm.$emit('open', { kind: 'route', to: { name: '/accounts/' } });
    await nextTick();

    expect(state.push).toHaveBeenCalledWith({ name: '/accounts/' });
    expect(wrapper.emitted('show:dialog')).toBeUndefined();
  });
});
