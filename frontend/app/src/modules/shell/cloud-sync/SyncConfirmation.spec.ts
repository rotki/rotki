import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import SyncConfirmation from '@/modules/shell/cloud-sync/SyncConfirmation.vue';

const stubs = {
  AskUserUponSizeDiscrepancySetting: { template: '<div data-testid="size-discrepancy-setting" />' },
  RuiButton: {
    inheritAttrs: false,
    props: { disabled: { default: false, type: Boolean }, loading: { default: false, type: Boolean } },
    template: '<button v-bind="$attrs" :disabled="disabled" :data-loading="loading"><slot /></button>',
  },
  RuiCheckbox: {
    emits: ['update:modelValue'],
    props: { modelValue: { default: false, type: Boolean } },
    template: '<label><input type="checkbox" v-bind="$attrs" :checked="modelValue" @change="$emit(\'update:modelValue\', $event.target.checked)" /><slot /></label>',
    inheritAttrs: false,
  },
  RuiIcon: true,
};

function createWrapper(props: { checked?: boolean; download?: boolean; syncing?: boolean; sizeDiscrepancy?: boolean } = {}): VueWrapper<InstanceType<typeof SyncConfirmation>> {
  return mount(SyncConfirmation, {
    global: { stubs },
    props: { checked: false, download: false, ...props },
  });
}

describe('modules/shell/cloud-sync/SyncConfirmation', () => {
  it('should keep the action disabled until the overwrite is acknowledged', async () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=sync-confirm-action]').attributes('disabled')).toBeDefined();

    await wrapper.find('[data-testid=sync-confirm-check]').setValue(true);

    expect(wrapper.emitted('update:checked')).toEqual([[true]]);

    await wrapper.setProps({ checked: true });

    expect(wrapper.find('[data-testid=sync-confirm-action]').attributes('disabled')).toBeUndefined();
  });

  it('should confirm from the action and cancel from the cancel button', async () => {
    const wrapper = createWrapper({ checked: true });
    await wrapper.find('[data-testid=sync-confirm-action]').trigger('click');
    await wrapper.find('[data-testid=sync-confirm-cancel]').trigger('click');

    expect(wrapper.emitted('confirm')).toEqual([[]]);
    expect(wrapper.emitted('cancel')).toEqual([[]]);
  });

  it('should word an upload as replacing the server backup', () => {
    const wrapper = createWrapper();
    const text = wrapper.find('[data-testid=sync-confirmation]').text();

    expect(text).toContain('sync_indicator.upload_confirmation.message_upload');
    expect(text).not.toContain('message_download');
  });

  it('should word a download as replacing the local database and logging out', () => {
    const wrapper = createWrapper({ download: true });
    const text = wrapper.find('[data-testid=sync-confirmation]').text();

    expect(text).toContain('sync_indicator.upload_confirmation.message_download');
    expect(text).toContain('sync_indicator.upload_confirmation.message_download_relogin');
    expect(text).not.toContain('message_upload');
  });

  it('should spin the action and hold off cancel while syncing', () => {
    const wrapper = createWrapper({ checked: true, syncing: true });

    expect(wrapper.find('[data-testid=sync-confirm-action]').attributes('data-loading')).toBe('true');
    expect(wrapper.find('[data-testid=sync-confirm-cancel]').attributes('disabled')).toBeDefined();
  });

  it('should offer the size discrepancy setting only after a size discrepancy', async () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=size-discrepancy-setting]').exists()).toBe(false);

    await wrapper.setProps({ sizeDiscrepancy: true });

    expect(wrapper.find('[data-testid=size-discrepancy-setting]').exists()).toBe(true);
  });
});
