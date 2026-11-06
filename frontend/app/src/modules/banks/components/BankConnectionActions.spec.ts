import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import BankConnectionActions from '@/modules/banks/components/BankConnectionActions.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

const deleteConfirm = { message: 'Remove the Qonto connection?', title: 'Remove connection' };

function createWrapper(): VueWrapper<InstanceType<typeof BankConnectionActions>> {
  return mount(BankConnectionActions, { props: { deleteConfirm } });
}

describe('modules/banks/components/BankConnectionActions', () => {
  it('should hand the delete button its question', () => {
    const wrapper = createWrapper();

    expect(wrapper.findComponent(RowActions).props('deleteConfirm')).toEqual(deleteConfirm);
  });

  it('should emit delete once the row actions report the question confirmed', () => {
    const wrapper = createWrapper();

    wrapper.findComponent(RowActions).vm.$emit('delete-click');

    expect(wrapper.emitted('delete')).toHaveLength(1);
  });
});
