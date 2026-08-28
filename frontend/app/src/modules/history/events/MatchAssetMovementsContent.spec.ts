import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import { createMock } from '@test/utils/create-mock';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import MatchAssetMovementsContent from '@/modules/history/events/MatchAssetMovementsContent.vue';
import { UNMATCHED_ACTIONS } from '@/modules/history/events/unmatched-actions';

const movementsApi = {
  autoMatchLoading: ref<boolean>(false),
  autoMatchMinimumTier: ref<string>('premium'),
  ignoredLoading: ref<boolean>(false),
  ignoredMovements: ref<UnmatchedAssetMovement[]>([]),
  isAutoMatchAllowed: ref<boolean>(true),
  loading: ref<boolean>(false),
  refreshUnmatchedAssetMovements: vi.fn(async () => Promise.resolve()),
  triggerAssetMovementAutoMatching: vi.fn(),
  unmatchedMovements: ref<UnmatchedAssetMovement[]>([]),
};

const actionsApi = {
  confirmIgnoreAllFiat: vi.fn(),
  confirmIgnoreSelected: vi.fn(),
  confirmRestoreSelected: vi.fn(),
  dismissResolution: vi.fn(),
  fiatMovements: ref<UnmatchedAssetMovement[]>([]),
  ignoreLoading: ref<boolean>(false),
  ignoreMovement: vi.fn(async () => Promise.resolve()),
  markExternal: vi.fn(async () => Promise.resolve()),
  modelSelectedIgnored: ref<UnmatchedAssetMovement[]>([]),
  modelSelectedUnmatched: ref<UnmatchedAssetMovement[]>([]),
  resolutionNotice: ref<{ message: string } | undefined>(),
  restoreMovement: vi.fn(async () => Promise.resolve()),
  undoResolution: vi.fn(async () => Promise.resolve()),
};

vi.mock('@/modules/history/events/use-unmatched-asset-movements', () => ({
  useUnmatchedAssetMovements: (): typeof movementsApi => movementsApi,
}));

vi.mock('@/modules/history/events/use-asset-movement-actions', () => ({
  useAssetMovementActions: (): typeof actionsApi => actionsApi,
}));

const UnmatchedMovementsListStub = defineComponent({
  emits: ['action', 'pin'],
  name: 'UnmatchedMovementsList',
  props: { movements: { default: () => [], type: Array } },
  setup(_, { emit }): () => VNode {
    return (): VNode => h('div', {
      'data-testid': 'movements-list',
      'onClick': () => emit('pin'),
    });
  },
});

const stubs = {
  AssetMovementMatchingSettingsMenu: true,
  UnmatchedMovementsList: UnmatchedMovementsListStub,
  UnmatchedResolutionStrip: true,
};

const wrappers: VueWrapper[] = [];

const movements = new Map<number, UnmatchedAssetMovement>();

function movement(identifier: number): UnmatchedAssetMovement {
  const existing = movements.get(identifier);
  if (existing)
    return existing;

  const created = createMock<UnmatchedAssetMovement>({ identifier });
  movements.set(identifier, created);
  return created;
}

async function mountContent(props: Record<string, unknown> = {}): Promise<VueWrapper> {
  const wrapper = mount(MatchAssetMovementsContent, { global: { stubs }, props });
  wrappers.push(wrapper);
  await flushPromises();
  return wrapper;
}

function triggerAction(wrapper: VueWrapper, action: string, item: UnmatchedAssetMovement): void {
  wrapper.findComponent(UnmatchedMovementsListStub).vm.$emit('action', { action, item });
}

describe('modules/history/events/MatchAssetMovementsContent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(movementsApi.unmatchedMovements, []);
    set(movementsApi.ignoredMovements, []);
    set(actionsApi.resolutionNotice, undefined);
    set(actionsApi.modelSelectedUnmatched, []);
    set(actionsApi.modelSelectedIgnored, []);
  });

  afterEach(() => {
    while (wrappers.length > 0)
      wrappers.pop()?.unmount();
  });

  describe('what it does on mount', () => {
    it('should refresh the unmatched movements, so the pane is never empty by default', async () => {
      await mountContent();

      expect(movementsApi.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
    });
  });

  describe('where each row action goes', () => {
    it('should ask the parent to open the matcher rather than matching itself', async () => {
      const wrapper = await mountContent();

      triggerAction(wrapper, UNMATCHED_ACTIONS.FIND_MATCH, movement(1));

      expect(wrapper.emitted('select')?.[0]).toEqual([movement(1)]);
      expect(actionsApi.ignoreMovement).not.toHaveBeenCalled();
    });

    it('should ask the parent to show the row in events', async () => {
      const wrapper = await mountContent();

      triggerAction(wrapper, UNMATCHED_ACTIONS.SHOW_IN_EVENTS, movement(2));

      expect(wrapper.emitted('show-in-events')?.[0]).toEqual([movement(2)]);
    });

    it('should ignore exactly the row the action carried', async () => {
      const wrapper = await mountContent();

      triggerAction(wrapper, UNMATCHED_ACTIONS.IGNORE, movement(3));

      expect(actionsApi.ignoreMovement).toHaveBeenCalledExactlyOnceWith(movement(3));
      expect(actionsApi.restoreMovement).not.toHaveBeenCalled();
    });

    it('should restore exactly the row the action carried', async () => {
      const wrapper = await mountContent();

      triggerAction(wrapper, UNMATCHED_ACTIONS.RESTORE, movement(4));

      expect(actionsApi.restoreMovement).toHaveBeenCalledExactlyOnceWith(movement(4));
      expect(actionsApi.ignoreMovement).not.toHaveBeenCalled();
    });

    it('should mark exactly the row the action carried as external', async () => {
      const wrapper = await mountContent();

      triggerAction(wrapper, UNMATCHED_ACTIONS.MARK_EXTERNAL, movement(5));

      expect(actionsApi.markExternal).toHaveBeenCalledExactlyOnceWith(movement(5));
    });

    it('should do nothing for an action this pane does not offer', async () => {
      const wrapper = await mountContent();

      triggerAction(wrapper, UNMATCHED_ACTIONS.CREATE_COUNTERPART, movement(6));

      expect(actionsApi.ignoreMovement).not.toHaveBeenCalled();
      expect(actionsApi.restoreMovement).not.toHaveBeenCalled();
      expect(actionsApi.markExternal).not.toHaveBeenCalled();
      expect(wrapper.emitted('select')).toBeUndefined();
      expect(wrapper.emitted('show-in-events')).toBeUndefined();
    });
  });

  describe('what it forwards to its parent', () => {
    it('should pass a pin request straight up', async () => {
      const wrapper = await mountContent();

      await wrapper.find('[data-testid="movements-list"]').trigger('click');

      expect(wrapper.emitted('pin')).toHaveLength(1);
    });
  });

  describe('the bulk actions', () => {
    it('should confirm before ignoring the selection, rather than ignoring it outright', async () => {
      set(actionsApi.modelSelectedUnmatched, [movement(1)]);
      const wrapper = await mountContent();

      await wrapper.find('[data-testid="ignore-selected"]').trigger('click');

      expect(actionsApi.confirmIgnoreSelected).toHaveBeenCalledOnce();
      expect(actionsApi.ignoreMovement).not.toHaveBeenCalled();
    });

    it('should offer nothing to ignore when the selection is empty', async () => {
      const wrapper = await mountContent();

      expect(wrapper.find('[data-testid="ignore-selected"]').attributes('disabled')).toBeDefined();
    });

    it('should offer nothing to ignore while auto-match is not allowed', async () => {
      set(actionsApi.modelSelectedUnmatched, [movement(1)]);
      set(movementsApi.isAutoMatchAllowed, false);
      const wrapper = await mountContent();

      expect(wrapper.find('[data-testid="ignore-selected"]').attributes('disabled')).toBeDefined();

      set(movementsApi.isAutoMatchAllowed, true);
    });

    it('should confirm before ignoring every fiat movement', async () => {
      set(actionsApi.fiatMovements, [movement(1)]);
      const wrapper = await mountContent();

      await wrapper.find('[data-testid="ignore-fiat"]').trigger('click');

      expect(actionsApi.confirmIgnoreAllFiat).toHaveBeenCalledOnce();

      set(actionsApi.fiatMovements, []);
    });

    it('should start auto-matching only when there is something to match', async () => {
      const wrapper = await mountContent();
      expect(wrapper.find('[data-testid="auto-match"]').attributes('disabled')).toBeDefined();

      set(movementsApi.unmatchedMovements, [movement(1)]);
      await nextTick();

      await wrapper.find('[data-testid="auto-match"]').trigger('click');
      expect(movementsApi.triggerAssetMovementAutoMatching).toHaveBeenCalledOnce();
    });
  });

  describe('the ignored tab', () => {
    it('should confirm before restoring the selection', async () => {
      set(movementsApi.ignoredMovements, [movement(1)]);
      set(actionsApi.modelSelectedIgnored, [movement(1)]);
      const wrapper = await mountContent();

      await wrapper.findComponent({ name: 'RuiTabs' }).vm.$emit('update:model-value', 1);
      await nextTick();

      await wrapper.find('[data-testid="restore-selected"]').trigger('click');

      expect(actionsApi.confirmRestoreSelected).toHaveBeenCalledOnce();
      expect(actionsApi.restoreMovement).not.toHaveBeenCalled();
    });
  });

  describe('the pinned variant', () => {
    it('should not offer a close button, having no dialog to close', async () => {
      const wrapper = await mountContent({ isPinned: true });

      expect(wrapper.find('[data-testid="close"]').exists()).toBe(false);
    });

    it('should offer one in the dialog', async () => {
      const wrapper = await mountContent();

      await wrapper.find('[data-testid="close"]').trigger('click');

      expect(wrapper.emitted('close')).toHaveLength(1);
    });
  });

  describe('the resolution notice', () => {
    it('should stay hidden until something has been resolved', async () => {
      const wrapper = await mountContent();

      expect(wrapper.findComponent({ name: 'UnmatchedResolutionStrip' }).exists()).toBe(false);
    });

    it('should appear once a resolution is pending an undo', async () => {
      set(actionsApi.resolutionNotice, { message: 'ignored 2 movements' });

      const wrapper = await mountContent();

      expect(wrapper.findComponent({ name: 'UnmatchedResolutionStrip' }).exists()).toBe(true);
    });
  });
});
