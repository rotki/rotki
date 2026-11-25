import type { RemoteBackup } from '@/modules/session/sync';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { set } from '@vueuse/shared';
import { createPinia, setActivePinia, storeToRefs } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import { FailureCause } from '@/modules/core/api/failure-cause';
import { ApiRequestError } from '@/modules/core/api/types/errors';
import { usePremiumStore } from '@/modules/premium/use-premium-store';
import DeleteRemoteBackupPanel from '@/modules/shell/cloud-sync/DeleteRemoteBackupPanel.vue';

const { deleteRemoteBackup, fetchRemoteBackup } = vi.hoisted(() => ({
  deleteRemoteBackup: vi.fn(),
  fetchRemoteBackup: vi.fn(),
}));

vi.mock('@/modules/session/api/use-sync-api', () => ({
  useSyncApi: (): Record<string, unknown> => ({ deleteRemoteBackup, fetchRemoteBackup }),
}));

const BACKUP: RemoteBackup = { dataHash: 'abc', dataSize: 4242, lastModifyTs: 1760882400, uploadTs: 1760882460 };

const stubs = {
  DateDisplay: { props: ['timestamp'], template: '<span>{{ timestamp }}</span>' },
  FailureStrip: { props: ['title', 'failure'], template: '<div v-bind="$attrs">{{ title }}</div>' },
  RuiButton: {
    inheritAttrs: false,
    props: { disabled: { default: false, type: Boolean }, loading: { default: false, type: Boolean } },
    template: '<button v-bind="$attrs" :disabled="disabled || loading" :data-loading="loading"><slot /></button>',
  },
  RuiCheckbox: {
    emits: ['update:modelValue'],
    inheritAttrs: false,
    props: { modelValue: { default: false, type: Boolean }, disabled: { default: false, type: Boolean } },
    template: '<label><input type="checkbox" v-bind="$attrs" :disabled="disabled" :checked="modelValue" @change="$emit(\'update:modelValue\', $event.target.checked)" /><slot /></label>',
  },
  RuiIcon: true,
  RuiSkeletonLoader: true,
  TimeAgoDisplay: { props: ['timestamp'], template: '<span>{{ timestamp }}</span>' },
};

function createWrapper(): VueWrapper<InstanceType<typeof DeleteRemoteBackupPanel>> {
  return mount(DeleteRemoteBackupPanel, { global: { stubs } });
}

function confirmButton(wrapper: VueWrapper): ReturnType<VueWrapper['find']> {
  return wrapper.find('[data-testid=delete-remote-backup-confirm]');
}

describe('modules/shell/cloud-sync/DeleteRemoteBackupPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    fetchRemoteBackup.mockResolvedValue(BACKUP);
    deleteRemoteBackup.mockResolvedValue({ premiumShouldSync: false });
  });

  it('should hold the deletion until the server says which backup it stores', async () => {
    let resolve: (backup: RemoteBackup) => void = () => {};
    fetchRemoteBackup.mockReturnValue(new Promise((r) => {
      resolve = r;
    }));
    const wrapper = createWrapper();
    await nextTick();

    expect(wrapper.find('[data-testid=delete-remote-backup-loading]').exists()).toBe(true);
    expect(confirmButton(wrapper).attributes('disabled')).toBeDefined();

    resolve(BACKUP);
    await flushPromises();

    expect(confirmButton(wrapper).attributes('disabled')).toBeUndefined();
  });

  it('should show which backup will be deleted', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    const details = wrapper.find('[data-testid=delete-remote-backup-details]');
    expect(details.text()).toContain('1760882400');
    expect(details.text()).toContain('1760882460');
    expect(wrapper.find('[data-testid=delete-remote-backup-size]').text()).toContain('4.14');
  });

  it('should offer to turn off automatic backup only while it is on', async () => {
    const wrapper = createWrapper();
    await flushPromises();
    expect(wrapper.find('[data-testid=delete-remote-backup-disable-sync]').exists()).toBe(false);

    set(storeToRefs(usePremiumStore()).premiumSync, true);
    await nextTick();
    expect(wrapper.find('[data-testid=delete-remote-backup-disable-sync]').exists()).toBe(true);
  });

  it('should delete in one step and say that automatic backup is off', async () => {
    set(storeToRefs(usePremiumStore()).premiumSync, true);
    const wrapper = createWrapper();
    await flushPromises();

    await confirmButton(wrapper).trigger('click');
    await flushPromises();

    expect(deleteRemoteBackup).toHaveBeenCalledWith({ dataHash: 'abc', disableSync: true });
    expect(wrapper.find('[data-testid=delete-remote-backup-deleted]').text()).toContain('delete_remote_backup.deleted.sync_off');
  });

  it('should not claim the deletion turned off automatic backup that was already off', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    await confirmButton(wrapper).trigger('click');
    await flushPromises();

    const deleted = wrapper.find('[data-testid=delete-remote-backup-deleted]').text();
    expect(deleted).toContain('delete_remote_backup.deleted.others');
    expect(deleted).not.toContain('sync_off');
  });

  it('should report busy while deleting, so the menu stays open', async () => {
    let finish: (value: { premiumShouldSync: boolean }) => void = () => {};
    deleteRemoteBackup.mockReturnValue(new Promise((r) => {
      finish = r;
    }));
    const wrapper = createWrapper();
    await flushPromises();

    await confirmButton(wrapper).trigger('click');

    expect(wrapper.emitted('update:busy')?.at(-1)).toEqual([true]);

    finish({ premiumShouldSync: false });
    await flushPromises();

    expect(wrapper.emitted('update:busy')?.at(-1)).toEqual([false]);
  });

  it('should show the newer backup the server kept', async () => {
    deleteRemoteBackup.mockRejectedValue(new ApiRequestError('changed', { failureCause: FailureCause.CONFLICT, status: 502 }));
    const wrapper = createWrapper();
    await flushPromises();

    fetchRemoteBackup.mockResolvedValue({ ...BACKUP, dataHash: 'def', uploadTs: 1760882999 });
    await confirmButton(wrapper).trigger('click');
    await flushPromises();

    expect(wrapper.find('[data-testid=delete-remote-backup-changed]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=delete-remote-backup-details]').text()).toContain('1760882999');
  });

  it('should say when there is nothing to delete and close on done', async () => {
    fetchRemoteBackup.mockResolvedValue(null);
    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('[data-testid=delete-remote-backup-empty]').exists()).toBe(true);
    expect(confirmButton(wrapper).exists()).toBe(false);

    await wrapper.find('[data-testid=delete-remote-backup-close]').trigger('click');

    expect(wrapper.emitted('close')).toEqual([[]]);
  });

  it('should close from cancel without deleting', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    await wrapper.find('[data-testid=delete-remote-backup-cancel]').trigger('click');

    expect(wrapper.emitted('close')).toEqual([[]]);
    expect(deleteRemoteBackup).not.toHaveBeenCalled();
  });
});
