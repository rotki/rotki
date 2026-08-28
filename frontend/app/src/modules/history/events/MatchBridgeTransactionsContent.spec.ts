import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { createMock } from '@test/utils/create-mock';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import MatchBridgeTransactionsContent from '@/modules/history/events/MatchBridgeTransactionsContent.vue';
import { UNMATCHED_ACTIONS } from '@/modules/history/events/unmatched-actions';

const transactionsApi = {
  autoMatchLoading: ref<boolean>(false),
  autoMatchMinimumTier: ref<string>('premium'),
  ignoredLoading: ref<boolean>(false),
  ignoredTransactions: ref<UnmatchedBridgeTransaction[]>([]),
  isAutoMatchAllowed: ref<boolean>(true),
  loading: ref<boolean>(false),
  refreshUnmatchedBridgeTransactions: vi.fn(async () => Promise.resolve()),
  triggerBridgeAutoMatching: vi.fn(),
  unmatchedTransactions: ref<UnmatchedBridgeTransaction[]>([]),
};

const actionsApi = {
  confirmCreateCounterpart: vi.fn(),
  confirmIgnoreSelected: vi.fn(),
  confirmRestoreSelected: vi.fn(),
  dismissResolution: vi.fn(),
  ignoreLoading: ref<boolean>(false),
  ignoreTransaction: vi.fn(async () => Promise.resolve()),
  markExternal: vi.fn(async () => Promise.resolve()),
  modelSelectedIgnored: ref<UnmatchedBridgeTransaction[]>([]),
  modelSelectedUnmatched: ref<UnmatchedBridgeTransaction[]>([]),
  resolutionNotice: ref<{ message: string } | undefined>(),
  restoreTransaction: vi.fn(async () => Promise.resolve()),
  undoResolution: vi.fn(async () => Promise.resolve()),
};

vi.mock('@/modules/history/events/use-unmatched-bridge-transactions', () => ({
  useUnmatchedBridgeTransactions: (): typeof transactionsApi => transactionsApi,
}));

vi.mock('@/modules/history/events/use-bridge-transaction-actions', () => ({
  useBridgeTransactionActions: (): typeof actionsApi => actionsApi,
}));

const UnmatchedBridgesListStub = defineComponent({
  emits: ['action', 'pin'],
  name: 'UnmatchedBridgesList',
  props: { transactions: { default: () => [], type: Array } },
  setup(_, { emit }): () => VNode {
    return (): VNode => h('div', {
      'data-testid': 'bridges-list',
      'onClick': () => emit('pin'),
    });
  },
});

const stubs = {
  AssetMovementMatchingSettingsMenu: true,
  UnmatchedBridgesList: UnmatchedBridgesListStub,
  UnmatchedResolutionStrip: true,
};

const wrappers: VueWrapper[] = [];
const transactions = new Map<number, UnmatchedBridgeTransaction>();

function transaction(identifier: number): UnmatchedBridgeTransaction {
  const existing = transactions.get(identifier);
  if (existing)
    return existing;

  const created = createMock<UnmatchedBridgeTransaction>({ identifier });
  transactions.set(identifier, created);
  return created;
}

async function mountContent(props: Record<string, unknown> = {}): Promise<VueWrapper> {
  const wrapper = mount(MatchBridgeTransactionsContent, { global: { stubs }, props });
  wrappers.push(wrapper);
  await flushPromises();
  return wrapper;
}

function triggerAction(wrapper: VueWrapper, action: string, item: UnmatchedBridgeTransaction): void {
  wrapper.findComponent(UnmatchedBridgesListStub).vm.$emit('action', { action, item });
}

describe('modules/history/events/MatchBridgeTransactionsContent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(transactionsApi.unmatchedTransactions, []);
    set(transactionsApi.ignoredTransactions, []);
    set(transactionsApi.isAutoMatchAllowed, true);
    set(actionsApi.resolutionNotice, undefined);
    set(actionsApi.modelSelectedUnmatched, []);
    set(actionsApi.modelSelectedIgnored, []);
  });

  afterEach(() => {
    while (wrappers.length > 0)
      wrappers.pop()?.unmount();
  });

  describe('what it does on mount', () => {
    it('should refresh the unmatched transactions', async () => {
      await mountContent();

      expect(transactionsApi.refreshUnmatchedBridgeTransactions).toHaveBeenCalledOnce();
    });
  });

  describe('where each row action goes', () => {
    it('should ask the parent to open the matcher rather than matching itself', async () => {
      const wrapper = await mountContent();

      triggerAction(wrapper, UNMATCHED_ACTIONS.FIND_MATCH, transaction(1));

      expect(wrapper.emitted('select')?.[0]).toEqual([transaction(1)]);
    });

    it('should ask the parent to show the row in events', async () => {
      const wrapper = await mountContent();

      triggerAction(wrapper, UNMATCHED_ACTIONS.SHOW_IN_EVENTS, transaction(2));

      expect(wrapper.emitted('show-in-events')?.[0]).toEqual([transaction(2)]);
    });

    it('should ignore exactly the row the action carried', async () => {
      const wrapper = await mountContent();

      triggerAction(wrapper, UNMATCHED_ACTIONS.IGNORE, transaction(3));

      expect(actionsApi.ignoreTransaction).toHaveBeenCalledExactlyOnceWith(transaction(3));
      expect(actionsApi.restoreTransaction).not.toHaveBeenCalled();
    });

    it('should restore exactly the row the action carried', async () => {
      const wrapper = await mountContent();

      triggerAction(wrapper, UNMATCHED_ACTIONS.RESTORE, transaction(4));

      expect(actionsApi.restoreTransaction).toHaveBeenCalledExactlyOnceWith(transaction(4));
      expect(actionsApi.ignoreTransaction).not.toHaveBeenCalled();
    });

    it('should mark exactly the row the action carried as external', async () => {
      const wrapper = await mountContent();

      triggerAction(wrapper, UNMATCHED_ACTIONS.MARK_EXTERNAL, transaction(5));

      expect(actionsApi.markExternal).toHaveBeenCalledExactlyOnceWith(transaction(5));
    });

    it('should confirm before creating a counterpart, unlike the asset movements pane', async () => {
      const wrapper = await mountContent();

      triggerAction(wrapper, UNMATCHED_ACTIONS.CREATE_COUNTERPART, transaction(6));

      expect(actionsApi.confirmCreateCounterpart).toHaveBeenCalledExactlyOnceWith(transaction(6));
    });
  });

  describe('the bulk actions', () => {
    it('should confirm before ignoring the selection', async () => {
      set(actionsApi.modelSelectedUnmatched, [transaction(1)]);
      const wrapper = await mountContent();

      await wrapper.find('[data-testid="ignore-selected"]').trigger('click');

      expect(actionsApi.confirmIgnoreSelected).toHaveBeenCalledOnce();
      expect(actionsApi.ignoreTransaction).not.toHaveBeenCalled();
    });

    it('should hide the ignore button entirely when nothing is selected', async () => {
      const wrapper = await mountContent();
      expect(wrapper.find('[data-testid="ignore-selected"]').exists()).toBe(false);

      set(actionsApi.modelSelectedUnmatched, [transaction(1)]);
      await nextTick();

      expect(wrapper.find('[data-testid="ignore-selected"]').exists()).toBe(true);
    });

    it('should hide the restore button entirely when nothing is selected', async () => {
      set(transactionsApi.ignoredTransactions, [transaction(1)]);
      const wrapper = await mountContent();
      await wrapper.findComponent({ name: 'RuiTabs' }).vm.$emit('update:model-value', 1);
      await nextTick();
      expect(wrapper.find('[data-testid="restore-selected"]').exists()).toBe(false);

      set(actionsApi.modelSelectedIgnored, [transaction(1)]);
      await nextTick();

      expect(wrapper.find('[data-testid="restore-selected"]').exists()).toBe(true);
    });

    it('should start auto-matching only when there is something to match', async () => {
      const wrapper = await mountContent();
      expect(wrapper.find('[data-testid="auto-match"]').attributes('disabled')).toBeDefined();

      set(transactionsApi.unmatchedTransactions, [transaction(1)]);
      await nextTick();

      await wrapper.find('[data-testid="auto-match"]').trigger('click');
      expect(transactionsApi.triggerBridgeAutoMatching).toHaveBeenCalledOnce();
    });
  });

  describe('what it forwards to its parent', () => {
    it('should pass a pin request straight up', async () => {
      const wrapper = await mountContent();

      await wrapper.find('[data-testid="bridges-list"]').trigger('click');

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
});
