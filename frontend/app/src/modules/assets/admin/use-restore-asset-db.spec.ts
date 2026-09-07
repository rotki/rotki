import { flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type Ref, ref } from 'vue';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useRestoreAssetDb } from './use-restore-asset-db';

let loading: Ref<boolean>;

const { notify, reload, restoreAssetsDatabase } = vi.hoisted(() => ({
  notify: vi.fn(),
  reload: vi.fn(async () => Promise.resolve()),
  restoreAssetsDatabase: vi.fn(),
}));

vi.mock('@/modules/assets/use-assets', () => ({
  useAssets: (): Record<string, unknown> => ({ restoreAssetsDatabase }),
}));

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: (): Record<string, unknown> => ({ notify }),
}));

vi.mock('@/modules/shell/app/use-backend-reload', () => ({
  useBackendReload: (): Record<string, unknown> => ({ reload }),
}));

vi.mock('@/modules/task-center/use-task-center', async () => {
  const actual = await vi.importActual<typeof import('@/modules/task-center/use-task-center')>(
    '@/modules/task-center/use-task-center',
  );
  return {
    ...actual,
    useTaskCenter: (): Record<string, unknown> => ({ useIsActive: (): Ref<boolean> => loading }),
  };
});

let scope: ReturnType<typeof effectScope>;

function restore(): ReturnType<typeof useRestoreAssetDb> {
  scope = effectScope();
  return scope.run(() => useRestoreAssetDb())!;
}

describe('modules/assets/admin/useRestoreAssetDb', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    loading = ref<boolean>(false);
    restoreAssetsDatabase.mockResolvedValue({ success: true });
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('before it resets anything', () => {
    it.each(['soft', 'hard'] as const)('should reset nothing until the %s dialog is confirmed', (type) => {
      const { showRestoreConfirmation } = restore();
      showRestoreConfirmation(type);

      expect(get(useConfirmStore().visible)).toBe(true);
      expect(restoreAssetsDatabase).not.toHaveBeenCalled();
    });

    it('should reset nothing when the dialog is dismissed', async () => {
      const { showRestoreConfirmation } = restore();
      showRestoreConfirmation('hard');
      await useConfirmStore().dismiss();
      await flushPromises();

      expect(restoreAssetsDatabase).not.toHaveBeenCalled();
    });

    it.each([
      ['soft', 'asset_update.restore.delete_confirmation.soft_reset_message'],
      ['hard', 'asset_update.restore.delete_confirmation.hard_reset_message'],
    ] as const)('should warn about what a %s reset costs', (type, expected) => {
      const { showRestoreConfirmation } = restore();
      showRestoreConfirmation(type);

      expect(get(useConfirmStore().confirmation).message).toBe(expected);
    });

    it('should refuse to start a second reset while one is running', async () => {
      set(loading, true);

      const { showRestoreConfirmation } = restore();
      showRestoreConfirmation('hard');
      await useConfirmStore().confirm();
      await flushPromises();

      expect(restoreAssetsDatabase).not.toHaveBeenCalled();
    });
  });

  describe('a reset that lands', () => {
    it.each(['soft', 'hard'] as const)('should run the %s reset the dialog named', async (type) => {
      const { showRestoreConfirmation } = restore();
      showRestoreConfirmation(type);
      await useConfirmStore().confirm();
      await flushPromises();

      expect(restoreAssetsDatabase).toHaveBeenCalledWith(type);
    });

    it('should ask to restart, and reload only once that is confirmed', async () => {
      const { showRestoreConfirmation } = restore();
      showRestoreConfirmation('soft');
      await useConfirmStore().confirm();
      await flushPromises();

      expect(get(useConfirmStore().confirmation).message).toBe('asset_update.restore.success.description');
      expect(reload).not.toHaveBeenCalled();

      await useConfirmStore().confirm();
      await flushPromises();

      expect(reload).toHaveBeenCalledOnce();
    });

    it('should report nothing when it succeeds', async () => {
      const { showRestoreConfirmation } = restore();
      showRestoreConfirmation('soft');
      await useConfirmStore().confirm();
      await flushPromises();

      expect(notify).not.toHaveBeenCalled();
    });
  });

  describe('a reset that fails', () => {
    it('should report the reason and not offer a restart', async () => {
      restoreAssetsDatabase.mockResolvedValue({ message: 'the database is locked', success: false });

      const { showRestoreConfirmation } = restore();
      showRestoreConfirmation('soft');
      await useConfirmStore().confirm();
      await flushPromises();

      expect(notify).toHaveBeenCalledWith(expect.objectContaining({ message: 'the database is locked' }));
      expect(reload).not.toHaveBeenCalled();
    });

    it('should escalate to a second confirmation when assets would be lost', async () => {
      restoreAssetsDatabase.mockResolvedValue({
        message: 'There are assets that can not be deleted. Check logs for more details.',
        success: false,
      });

      const { showRestoreConfirmation } = restore();
      showRestoreConfirmation('hard');
      await useConfirmStore().confirm();
      await flushPromises();

      expect(get(useConfirmStore().confirmation).message)
        .toBe('asset_update.restore.hard_restore_confirmation.message');
      expect(notify).toHaveBeenCalledOnce();
    });

    it('should retry with the same reset type once the escalation is confirmed', async () => {
      restoreAssetsDatabase.mockResolvedValue({
        message: 'There are assets that can not be deleted. Check logs for more details.',
        success: false,
      });

      const { showRestoreConfirmation } = restore();
      showRestoreConfirmation('hard');
      await useConfirmStore().confirm();
      await flushPromises();

      restoreAssetsDatabase.mockClear();
      await useConfirmStore().confirm();
      await flushPromises();

      expect(restoreAssetsDatabase).toHaveBeenCalledWith('hard');
    });

    it('should not escalate for an unrelated failure', async () => {
      restoreAssetsDatabase.mockResolvedValue({ message: 'the database is locked', success: false });

      const { showRestoreConfirmation } = restore();
      showRestoreConfirmation('hard');
      await useConfirmStore().confirm();
      await flushPromises();

      expect(get(useConfirmStore().visible)).toBe(false);
    });
  });
});
