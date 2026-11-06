import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import InlineConfirm from './InlineConfirm.vue';

function createWrapper(props: Partial<InstanceType<typeof InlineConfirm>['$props']> = {}): VueWrapper<InstanceType<typeof InlineConfirm>> {
  return mount(InlineConfirm, {
    attachTo: document.body,
    props: { confirmLabel: 'Delete', message: 'Delete this tag?', ...props },
  });
}

describe('inlineConfirm', () => {
  it('should emit confirm only from the confirm button', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');

    expect(wrapper.emitted('confirm')).toHaveLength(1);
    expect(wrapper.emitted('cancel')).toBeUndefined();
  });

  it('should emit cancel from the cancel button and from escape', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=inline-confirm-cancel]').trigger('click');
    await wrapper.find('[data-testid=inline-confirm]').trigger('keydown', { key: 'Escape' });

    expect(wrapper.emitted('cancel')).toHaveLength(2);
    expect(wrapper.emitted('confirm')).toBeUndefined();
  });

  it('should focus cancel when it appears, so enter cannot confirm by accident', () => {
    const wrapper = createWrapper();

    expect(document.activeElement).toBe(wrapper.find('[data-testid=inline-confirm-cancel]').element);
  });

  it('should show the title in the panel layout only', () => {
    expect(createWrapper({ layout: 'panel', title: 'Delete tag' }).text()).toContain('Delete tag');
    expect(createWrapper({ layout: 'strip', title: 'Delete tag' }).text()).not.toContain('Delete tag');
  });

  it('should name the question for assistive technology', () => {
    const wrapper = createWrapper({ title: 'Delete tag' });

    const root = wrapper.find('[data-testid=inline-confirm]');
    expect(root.attributes('role')).toBe('alertdialog');
    expect(root.attributes('aria-label')).toBe('Delete tag');
  });
});
