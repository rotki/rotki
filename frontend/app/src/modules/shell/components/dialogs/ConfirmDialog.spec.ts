import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import ConfirmDialog from '@/modules/shell/components/dialogs/ConfirmDialog.vue';

function createWrapper(props: { alternativeAction?: string; secondaryAction?: string } = {}): VueWrapper<InstanceType<typeof ConfirmDialog>> {
  return mount(ConfirmDialog, {
    global: { stubs: { RuiDialog: { template: '<div data-testid="dialog"><slot /></div>' } } },
    props: { display: true, message: 'message', title: 'title', ...props },
  });
}

describe('modules/shell/components/dialogs/ConfirmDialog', () => {
  it('should offer no alternative unless one is labelled', () => {
    expect(createWrapper().find('[data-testid=button-alternative]').exists()).toBe(false);
  });

  it('should emit the alternative from its own button, labelled as asked', async () => {
    const wrapper = createWrapper({ alternativeAction: 'Exclude from Accounting', secondaryAction: 'Keep it' });

    const button = wrapper.find('[data-testid=button-alternative]');
    expect(button.text()).toBe('Exclude from Accounting');
    expect(wrapper.find('[data-testid=button-cancel]').text()).toBe('Keep it');

    await button.trigger('click');

    expect(wrapper.emitted('alternative')).toHaveLength(1);
    expect(wrapper.emitted('cancel')).toBeUndefined();
  });

  it('should back out on the dismiss button and on Escape without taking the alternative', async () => {
    const wrapper = createWrapper({ alternativeAction: 'Exclude from Accounting' });

    await wrapper.find('[data-testid=button-cancel]').trigger('click');
    await wrapper.find('[data-testid=dialog]').trigger('keydown', { key: 'Escape' });

    expect(wrapper.emitted('cancel')).toHaveLength(2);
    expect(wrapper.emitted('alternative')).toBeUndefined();
  });
});
