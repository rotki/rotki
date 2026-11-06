import type { ConfirmQuestion } from './confirm-question';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import InlineConfirm from './InlineConfirm.vue';

function createWrapper(
  question: Partial<ConfirmQuestion> = {},
  layout?: 'strip' | 'panel',
): VueWrapper<InstanceType<typeof InlineConfirm>> {
  return mount(InlineConfirm, {
    attachTo: document.body,
    props: { layout, question: { confirmLabel: 'Delete', message: 'Delete this tag?', ...question } },
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
    expect(createWrapper({ title: 'Delete tag' }, 'panel').text()).toContain('Delete tag');
    expect(createWrapper({ title: 'Delete tag' }, 'strip').text()).not.toContain('Delete tag');
  });

  it('should colour the accept button by the question tone, warning unless it destroys data', () => {
    const accept = (wrapper: VueWrapper): unknown =>
      wrapper.findAllComponents({ name: 'RuiButton' }).find(button => button.attributes('data-testid') === 'inline-confirm-accept')?.props('color');

    expect(accept(createWrapper())).toBe('warning');
    expect(accept(createWrapper({ tone: 'error' }))).toBe('error');
  });

  it('should name the question for assistive technology', () => {
    const wrapper = createWrapper({ title: 'Delete tag' });

    const root = wrapper.find('[data-testid=inline-confirm]');
    expect(root.attributes('role')).toBe('alertdialog');
    expect(root.attributes('aria-label')).toBe('Delete tag');
  });
});
