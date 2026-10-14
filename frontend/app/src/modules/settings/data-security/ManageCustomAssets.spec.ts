import type { ActionStatus } from '@/modules/core/common/action';
import { Severity } from '@rotki/common';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import ManageCustomAssets from '@/modules/settings/data-security/ManageCustomAssets.vue';

const { importCustomAssets, removeFile } = vi.hoisted(() => ({
  importCustomAssets: vi.fn<(file: File) => Promise<ActionStatus>>(),
  removeFile: vi.fn<() => void>(),
}));

const exportCustomAssets = vi.fn();
const notify = vi.fn();

vi.mock('@/modules/assets/use-assets', () => ({
  useAssets: (): Record<string, unknown> => ({
    exportCustomAssets,
    importCustomAssets,
  }),
}));

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: (): Record<string, unknown> => ({ notify }),
}));

/** Stands in for the library uploader, exposing the reset the component calls after an import. */
const FileUploadStub = defineComponent({
  emits: ['update:modelValue', 'error'],
  name: 'RuiFileUpload',
  props: {
    accept: { default: undefined, type: String },
    errorMessages: { default: (): string[] => [], type: Array },
    hint: { default: undefined, type: String },
    modelValue: { default: undefined, type: File },
    uploaded: { default: false, type: Boolean },
  },
  setup(_props, { expose }) {
    expose({ removeFile });
    return {};
  },
  template: '<div />',
});

function createWrapper(): VueWrapper {
  return mount(ManageCustomAssets, {
    global: {
      stubs: {
        RuiFileUpload: FileUploadStub,
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

describe('manageCustomAssets import', () => {
  const ZIP = new File(['zip'], 'assets.zip', { type: 'application/zip' });

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  function uploader(wrapper: VueWrapper): VueWrapper<InstanceType<typeof FileUploadStub>> {
    return wrapper.findComponent(FileUploadStub);
  }

  async function pick(wrapper: VueWrapper, file: File): Promise<void> {
    uploader(wrapper).vm.$emit('update:modelValue', file);
    await flushPromises();
  }

  async function importPicked(wrapper: VueWrapper): Promise<void> {
    await wrapper.find('[data-testid=user-assets-import]').trigger('click');
    await flushPromises();
  }

  it('should take only zip archives', () => {
    expect(uploader(createWrapper()).props('accept')).toBe('.zip');
  });

  it('should mark the upload done and empty the uploader on a successful import', async () => {
    importCustomAssets.mockResolvedValue({ success: true });
    const wrapper = createWrapper();
    await pick(wrapper, ZIP);

    await importPicked(wrapper);

    expect(importCustomAssets).toHaveBeenCalledExactlyOnceWith(ZIP);
    expect(uploader(wrapper).props('uploaded')).toBe(true);
    expect(uploader(wrapper).props('hint')).toBe('file_upload.import_complete');
    expect(removeFile).toHaveBeenCalledOnce();
  });

  it('should show why on the uploader and empty it on a failed import', async () => {
    importCustomAssets.mockResolvedValue({ message: 'bad archive', success: false });
    const wrapper = createWrapper();
    await pick(wrapper, ZIP);

    await importPicked(wrapper);

    expect(uploader(wrapper).props('uploaded')).toBe(false);
    expect(uploader(wrapper).props('errorMessages')).toEqual(['bad archive']);
    expect(removeFile).toHaveBeenCalledOnce();
  });

  it('should drop the last outcome once another archive is picked', async () => {
    importCustomAssets.mockResolvedValue({ message: 'bad archive', success: false });
    const wrapper = createWrapper();
    await pick(wrapper, ZIP);
    await importPicked(wrapper);

    await pick(wrapper, ZIP);

    expect(uploader(wrapper).props('errorMessages')).toEqual([]);
  });

  it('should drop the done mark once another archive is picked', async () => {
    importCustomAssets.mockResolvedValue({ success: true });
    const wrapper = createWrapper();
    await pick(wrapper, ZIP);
    await importPicked(wrapper);

    await pick(wrapper, ZIP);

    expect(uploader(wrapper).props('uploaded')).toBe(false);
  });
});
