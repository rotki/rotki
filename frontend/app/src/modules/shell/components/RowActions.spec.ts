import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import ConfirmPopover from './ConfirmPopover.vue';
import RowActions from './RowActions.vue';

/** Opens through its activator and renders its content only while open, as the real menu does. */
const RuiMenu = {
  name: 'RuiMenu',
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template: `<div>
    <slot name="activator" :attrs="{ onClick: () => $emit('update:modelValue', true) }" />
    <div v-if="modelValue"><slot /></div>
  </div>`,
};

function createWrapper(props: Partial<InstanceType<typeof RowActions>['$props']> = {}): VueWrapper<InstanceType<typeof RowActions>> {
  return mount(RowActions, { global: { stubs: { RuiMenu } }, props });
}

describe('rowActions', () => {
  it('should emit delete-click straight away when no confirmation is asked for', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=row-delete]').trigger('click');

    expect(wrapper.emitted('delete-click')).toHaveLength(1);
  });

  describe('with deleteConfirm', () => {
    const deleteConfirm = { message: 'Delete the tag "work"?', title: 'Delete tag' };

    it('should ask beside the button before emitting', async () => {
      const wrapper = createWrapper({ deleteConfirm });

      await wrapper.find('[data-testid=row-delete]').trigger('click');

      expect(wrapper.find('[data-testid=inline-confirm]').text()).toContain('Delete the tag "work"?');
      expect(wrapper.emitted('delete-click')).toBeUndefined();
    });

    it('should emit delete-click once confirmed, and close the question', async () => {
      const wrapper = createWrapper({ deleteConfirm });

      await wrapper.find('[data-testid=row-delete]').trigger('click');
      await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');

      expect(wrapper.emitted('delete-click')).toHaveLength(1);
      expect(wrapper.find('[data-testid=inline-confirm]').exists()).toBe(false);
    });

    it('should not emit when cancelled', async () => {
      const wrapper = createWrapper({ deleteConfirm });

      await wrapper.find('[data-testid=row-delete]').trigger('click');
      await wrapper.find('[data-testid=inline-confirm-cancel]').trigger('click');

      expect(wrapper.emitted('delete-click')).toBeUndefined();
      expect(wrapper.find('[data-testid=inline-confirm]').exists()).toBe(false);
    });

    it('should ask in the error tone with a Delete button when the question names neither', () => {
      const wrapper = createWrapper({ deleteConfirm });

      expect(wrapper.findComponent(ConfirmPopover).props('question')).toEqual({
        ...deleteConfirm,
        confirmLabel: 'common.actions.delete',
        tone: 'error',
      });
    });

    it('should keep the confirm label and tone the question names', async () => {
      const wrapper = createWrapper({ deleteConfirm: { ...deleteConfirm, confirmLabel: 'Remove', tone: 'warning' } });

      await wrapper.find('[data-testid=row-delete]').trigger('click');

      expect(wrapper.find('[data-testid=inline-confirm-accept]').text()).toBe('Remove');
      expect(wrapper.findComponent(ConfirmPopover).props('question')).toMatchObject({ tone: 'warning' });
    });
  });
});
