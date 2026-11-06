import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import SnapshotImportDialog from '@/modules/dashboard/SnapshotImportDialog.vue';

function createWrapper(failure?: string): VueWrapper<InstanceType<typeof SnapshotImportDialog>> {
  return mount(SnapshotImportDialog, {
    global: {
      stubs: {
        RuiDialog: { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' },
        RuiFileUpload: true,
      },
    },
    props: { failure, modelValue: true },
  });
}

describe('snapshotImportDialog', () => {
  it('should name a failed import above the file pickers', () => {
    const wrapper = createWrapper('bad csv');

    const strip = wrapper.find('[data-testid=snapshot-import-failure]');
    expect(strip.text()).toContain('snapshot_action_button.messages.title');
    expect(strip.text()).toContain('bad csv');
    expect(strip.find('[data-testid=failure-strip-retry]').exists()).toBe(false);
  });

  it('should show no failure when there is none', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=snapshot-import-failure]').exists()).toBe(false);
  });

  it('should clear the failure when the dialog closes', async () => {
    const wrapper = createWrapper('bad csv');

    await wrapper.setProps({ modelValue: false });

    expect(wrapper.emitted('update:failure')).toEqual([[undefined]]);
  });

  it('should keep the failure while the dialog stays open', async () => {
    const wrapper = createWrapper('bad csv');

    await wrapper.setProps({ loading: true });

    expect(wrapper.emitted('update:failure')).toBeUndefined();
  });
});
