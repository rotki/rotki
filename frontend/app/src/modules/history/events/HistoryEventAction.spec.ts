import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import HistoryEventAction from '@/modules/history/events/HistoryEventAction.vue';

vi.mock('vue-router', () => ({
  useRouter: (): object => ({ push: vi.fn() }),
}));

/** Opens through its model and renders its content only while open, as the real menu does. */
const RuiMenu = {
  name: 'RuiMenu',
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template: `<div>
    <slot name="activator" :attrs="{ onClick: () => $emit('update:modelValue', true) }" />
    <div v-if="modelValue"><slot /></div>
  </div>`,
};

const deleteConfirm: ConfirmQuestion = { confirmLabel: 'Delete', message: 'Delete the event?', title: 'Delete event', tone: 'error' };
const unlinkConfirm: ConfirmQuestion = { confirmLabel: 'Unlink', message: 'Unlink the match?', title: 'Unlink' };

function mountMenu(props: Record<string, unknown> = {}): VueWrapper<InstanceType<typeof HistoryEventAction>> {
  return mount(HistoryEventAction, {
    global: { stubs: { RuiMenu } },
    props: { deleteConfirm, event: createMock<HistoryEventEntry>({ identifier: 1 }), unlinkConfirm, ...props },
  });
}

async function open(wrapper: VueWrapper): Promise<void> {
  await wrapper.find('[data-testid=row-actions-menu]').trigger('click');
}

describe('modules/history/events/HistoryEventAction', () => {
  it('should ask in the menu before deleting, in place of its items', async () => {
    const wrapper = mountMenu();
    await open(wrapper);

    await wrapper.find('[data-testid=row-delete]').trigger('click');

    expect(wrapper.find('[data-testid=inline-confirm]').text()).toContain('Delete the event?');
    expect(wrapper.find('[data-testid=confirm-menu-entries]').attributes('style')).toContain('display: none');
    expect(wrapper.emitted('delete')).toBeUndefined();
  });

  it('should delete once the question is accepted, and close the menu', async () => {
    const wrapper = mountMenu();
    await open(wrapper);

    await wrapper.find('[data-testid=row-delete]').trigger('click');
    await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');

    expect(wrapper.emitted('delete')).toHaveLength(1);
    expect(wrapper.emitted('unlink')).toBeUndefined();
    expect(wrapper.find('[data-testid=inline-confirm]').exists()).toBe(false);
  });

  it('should unlink once its own question is accepted', async () => {
    const wrapper = mountMenu();
    await open(wrapper);

    await wrapper.find('[data-testid=row-unlink]').trigger('click');
    expect(wrapper.find('[data-testid=inline-confirm]').text()).toContain('Unlink the match?');
    await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');

    expect(wrapper.emitted('unlink')).toHaveLength(1);
    expect(wrapper.emitted('delete')).toBeUndefined();
  });

  it('should do nothing when cancelled, and list the items again next time', async () => {
    const wrapper = mountMenu();
    await open(wrapper);

    await wrapper.find('[data-testid=row-delete]').trigger('click');
    await wrapper.find('[data-testid=inline-confirm-cancel]').trigger('click');
    await open(wrapper);
    await nextTick();

    expect(wrapper.emitted('delete')).toBeUndefined();
    expect(wrapper.find('[data-testid=inline-confirm]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=row-delete]').exists()).toBe(true);
  });

  it('should offer neither delete nor unlink without a question for it', async () => {
    const wrapper = mountMenu({ deleteConfirm: undefined, unlinkConfirm: undefined });
    await open(wrapper);

    expect(wrapper.find('[data-testid=row-delete]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=row-unlink]').exists()).toBe(false);
  });
});
