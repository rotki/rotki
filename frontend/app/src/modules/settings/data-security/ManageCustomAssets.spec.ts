import { Severity } from '@rotki/common';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import ManageCustomAssets from '@/modules/settings/data-security/ManageCustomAssets.vue';

const exportCustomAssets = vi.fn();
const notify = vi.fn();

vi.mock('@/modules/assets/use-assets', () => ({
  useAssets: (): Record<string, unknown> => ({
    exportCustomAssets,
    importCustomAssets: vi.fn(),
  }),
}));

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: (): Record<string, unknown> => ({ notify }),
}));

function createWrapper(): VueWrapper {
  return mount(ManageCustomAssets, {
    global: {
      stubs: {
        FileUpload: true,
        SettingsItem: { template: '<div><slot /></div>' },
      },
    },
  });
}

async function clickExport(wrapper: VueWrapper): Promise<void> {
  await wrapper.findAll('button')[0].trigger('click');
  await flushPromises();
}

describe('manageCustomAssets export', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('should report a failed export', async () => {
    exportCustomAssets.mockResolvedValue(err(TaskFailed({ message: 'disk full' })));

    await clickExport(createWrapper());

    expect(notify).toHaveBeenCalledOnce();
    expect(notify.mock.calls[0][0]).toMatchObject({ severity: Severity.ERROR });
  });

  it('should pass silently on a cancelled export', async () => {
    exportCustomAssets.mockResolvedValue(err(Cancelled({ message: '' })));

    await clickExport(createWrapper());

    expect(notify).not.toHaveBeenCalled();
  });

  it('should report where a desktop export wrote the file', async () => {
    exportCustomAssets.mockResolvedValue(ok({ directory: '/home/user', filePath: '/home/user/assets.zip' }));

    await clickExport(createWrapper());

    expect(notify).toHaveBeenCalledOnce();
    expect(notify.mock.calls[0][0]).toMatchObject({ severity: Severity.INFO });
  });

  it('should pass silently on a web export, which the browser prompt already confirms', async () => {
    exportCustomAssets.mockResolvedValue(ok({ filePath: 'assets.zip' }));

    await clickExport(createWrapper());

    expect(notify).not.toHaveBeenCalled();
  });
});
