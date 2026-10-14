import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, describe, expect, it } from 'vitest';
import { nextTick } from 'vue';
import ReportsTableMoreAction from './ReportsTableMoreAction.vue';

describe('reportsTableMoreAction', () => {
  let wrapper: VueWrapper<InstanceType<typeof ReportsTableMoreAction>>;

  function createWrapper(): VueWrapper<InstanceType<typeof ReportsTableMoreAction>> {
    return mount(ReportsTableMoreAction, {
      global: {
        stubs: {
          ExportReportCsv: { template: '<button data-testid="export-stub" />' },
          // Rendered eagerly, so the menu contents are reachable without driving the popper.
          RuiMenu: {
            name: 'RuiMenu',
            props: ['modelValue'],
            template: '<div><slot name="activator" :attrs="{}" /><slot /></div>',
          },
        },
      },
      props: { reportId: 7 },
    });
  }

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should ask in place before deleting', async () => {
    wrapper = createWrapper();

    await wrapper.find('[data-testid=report-delete]').trigger('click');

    expect(wrapper.find('[data-testid=report-delete-confirm]').exists()).toBe(true);
    expect(wrapper.emitted('delete')).toBeUndefined();
  });

  it('should delete once confirmed', async () => {
    wrapper = createWrapper();

    await wrapper.find('[data-testid=report-delete]').trigger('click');
    await wrapper.find('[data-testid=report-delete-confirm-button]').trigger('click');

    expect(wrapper.emitted('delete')).toHaveLength(1);
  });

  it('should not delete when cancelled, and offer the actions again next time', async () => {
    wrapper = createWrapper();
    // the menu opens through its model, which is what closing it then resets
    wrapper.findComponent({ name: 'RuiMenu' }).vm.$emit('update:modelValue', true);
    await nextTick();

    await wrapper.find('[data-testid=report-delete]').trigger('click');
    await wrapper.find('[data-testid=report-delete-cancel]').trigger('click');

    expect(wrapper.emitted('delete')).toBeUndefined();
    expect(wrapper.find('[data-testid=report-delete-confirm]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=report-delete]').exists()).toBe(true);
  });
});
