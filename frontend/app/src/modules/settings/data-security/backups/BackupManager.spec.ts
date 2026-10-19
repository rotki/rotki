import type { UserDbBackupWithId } from '@/modules/session/backup';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import BackupManager from '@/modules/settings/data-security/backups/BackupManager.vue';

const { backups, modelSelected, showMassDeleteConfirmation } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    backups: ref<UserDbBackupWithId[]>([]),
    modelSelected: ref<UserDbBackupWithId[]>([]),
    showMassDeleteConfirmation: vi.fn<() => void>(),
  };
});

vi.mock('@/modules/settings/data-security/backups/use-database-backups', async () => {
  const { ref } = await import('vue');
  return {
    useDatabaseBackups: (): Record<string, unknown> => ({
      backup: vi.fn(),
      backups,
      directory: ref<string>('/backups'),
      loadInfo: vi.fn(),
      loading: ref<boolean>(false),
      modelSelected,
      remove: vi.fn(),
      saving: ref<boolean>(false),
      showMassDeleteConfirmation,
    }),
  };
});

const BackupsTableStub = defineComponent({
  props: ['selected', 'selectionMode', 'loading', 'items', 'directory'],
  template: '<div />',
});

function backupRow(id: number): UserDbBackupWithId {
  return { id, size: 1024, time: 1700000000 + id, version: 50 };
}

function createWrapper(): VueWrapper<any> {
  return mount(BackupManager, {
    global: {
      provide: libraryDefaults,
      stubs: { DatabaseBackups: BackupsTableStub, SettingCategoryHeader: true },
    },
  });
}

async function createSelectingWrapper(): Promise<VueWrapper<any>> {
  const wrapper = createWrapper();
  await wrapper.find('[data-testid=backups-select]').trigger('click');
  return wrapper;
}

describe('modules/settings/data-security/backups/BackupManager', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(backups, [backupRow(1), backupRow(2)]);
    set(modelSelected, []);
  });

  it('should keep the checkboxes and the bar hidden until the user presses select', () => {
    const wrapper = createWrapper();

    expect(wrapper.findComponent(BackupsTableStub).props('selectionMode')).toBe(false);
    expect(wrapper.find('[data-testid=table-selection-bar]').exists()).toBe(false);
  });

  it('should not offer select while there are no backups', () => {
    set(backups, []);

    expect(createWrapper().find('[data-testid=backups-select]').attributes('disabled')).toBeDefined();
  });

  it('should show the checkboxes and a disabled delete once select is pressed', async () => {
    const wrapper = await createSelectingWrapper();

    expect(wrapper.findComponent(BackupsTableStub).props('selectionMode')).toBe(true);
    expect(wrapper.find('[data-testid=backups-select]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=backups-delete-selected]').attributes('disabled')).toBeDefined();
  });

  it('should ask to delete the picked backups', async () => {
    const wrapper = await createSelectingWrapper();
    set(modelSelected, [backupRow(1)]);
    await nextTick();

    await wrapper.find('[data-testid=backups-delete-selected]').trigger('click');

    expect(showMassDeleteConfirmation).toHaveBeenCalledOnce();
  });

  it('should drop the selection and the checkboxes on done', async () => {
    const wrapper = await createSelectingWrapper();
    set(modelSelected, [backupRow(1)]);
    await nextTick();

    await wrapper.find('[data-testid=table-selection-exit]').trigger('click');

    expect(get(modelSelected)).toEqual([]);
    expect(wrapper.findComponent(BackupsTableStub).props('selectionMode')).toBe(false);
    expect(wrapper.find('[data-testid=backups-select]').exists()).toBe(true);
  });
});
