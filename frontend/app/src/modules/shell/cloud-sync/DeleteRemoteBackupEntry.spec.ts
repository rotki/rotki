import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import DeleteRemoteBackupEntry from '@/modules/shell/cloud-sync/DeleteRemoteBackupEntry.vue';

const stubs = {
  RuiButton: {
    inheritAttrs: false,
    props: { disabled: { default: false, type: Boolean }, loading: { default: false, type: Boolean } },
    template: '<button v-bind="$attrs" :disabled="disabled"><slot /></button>',
  },
  RuiIcon: true,
  RuiTooltip: {
    props: { disabled: { default: false, type: Boolean }, text: { default: '', type: String } },
    template: '<div :data-tooltip="disabled ? undefined : text"><slot name="activator" /></div>',
  },
};

function createWrapper(props: { checkFailed?: boolean; checking?: boolean; noBackup?: boolean } = {}): VueWrapper {
  return mount(DeleteRemoteBackupEntry, { global: { stubs }, props });
}

function tooltip(wrapper: VueWrapper): string | undefined {
  return wrapper.attributes('data-tooltip');
}

describe('modules/shell/cloud-sync/DeleteRemoteBackupEntry', () => {
  it('should be enabled with no explanation while a backup is known', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('button').attributes('disabled')).toBeUndefined();
    expect(tooltip(wrapper)).toBeUndefined();
  });

  it('should say there is no backup when the server answered so', () => {
    const wrapper = createWrapper({ noBackup: true });

    expect(wrapper.find('button').attributes('disabled')).toBeDefined();
    expect(tooltip(wrapper)).toBe('delete_remote_backup.empty');
  });

  it('should not claim there is no backup when the check failed', () => {
    const wrapper = createWrapper({ checkFailed: true, noBackup: true });

    expect(wrapper.find('button').attributes('disabled')).toBeDefined();
    expect(tooltip(wrapper)).toBe('delete_remote_backup.check_failed');
  });

  it('should say it is checking while the server is asked', () => {
    const wrapper = createWrapper({ checking: true, noBackup: true });

    expect(wrapper.find('button').attributes('disabled')).toBeDefined();
    expect(tooltip(wrapper)).toBe('delete_remote_backup.checking');
  });
});
