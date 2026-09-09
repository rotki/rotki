import type { EvmSwapEvent, StandaloneEditableEvents } from '@/modules/history/events/schemas';
import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { createMock } from '@test/utils/create-mock';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, ref, type VNode } from 'vue';
import HistoryEventFormDialog from '@/modules/history/events/HistoryEventFormDialog.vue';

const save = vi.fn(async () => true);
const errorCount = ref<number>(0);

/**
 * The dialog reads the error count and saves through a template ref, so the stub exposes both. An
 * auto-stub would leave the ref pointing at a component with neither.
 */
const FormStub = defineComponent({
  name: 'HistoryEventForm',
  props: ['data', 'stateUpdated'],
  setup(_, { expose }): () => VNode {
    expose({ errorCount, save });
    return () => h('div');
  },
});

/** `BigDialog` teleports and owns the footer buttons; the two here stand for confirm and cancel. */
const BigDialogStub = {
  emits: ['confirm', 'cancel'],
  name: 'BigDialog',
  props: ['title', 'display', 'action', 'errors', 'loading', 'promptOnClose'],
  template: `<div>
    <slot />
    <button data-testid="stub-confirm" @click="$emit('confirm')" />
    <button data-testid="stub-cancel" @click="$emit('cancel')" />
  </div>`,
};

const addData: StandaloneEventData = { nextSequenceId: '1', type: 'add' };
const editData: StandaloneEventData = {
  event: createMock<StandaloneEditableEvents>({ identifier: 1 }),
  nextSequenceId: '2',
  type: 'edit',
};
const groupAddData: GroupEventData = {
  group: createMock<EvmSwapEvent>(),
  nextSequenceId: '1',
  type: 'group-add',
};

function createWrapper(modelValue: GroupEventData | StandaloneEventData | undefined): VueWrapper<any> {
  return mount(HistoryEventFormDialog, {
    global: {
      stubs: {
        BigDialog: BigDialogStub,
        HistoryEventForm: FormStub,
      },
    },
    props: { modelValue },
  });
}

async function confirm(wrapper: VueWrapper<any>): Promise<void> {
  await wrapper.find('[data-testid=stub-confirm]').trigger('click');
  await flushPromises();
}

function dialog(wrapper: VueWrapper<any>): VueWrapper<any> {
  return wrapper.findComponent({ name: 'BigDialog' });
}

describe('historyEventFormDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    save.mockResolvedValue(true);
    set(errorCount, 0);
  });

  describe('the heading', () => {
    it('should announce an addition', () => {
      expect(dialog(createWrapper(addData)).props('title')).toBe('transactions.events.dialog.add.title');
    });

    it('should announce adding into an existing group', () => {
      expect(dialog(createWrapper(groupAddData)).props('title')).toBe('transactions.events.dialog.add.title');
    });

    it('should announce an edit', () => {
      expect(dialog(createWrapper(editData)).props('title')).toBe('transactions.events.dialog.edit.title');
    });
  });

  describe('saving', () => {
    it('should close and ask for a refresh when the form saved', async () => {
      const wrapper = createWrapper(addData);

      await confirm(wrapper);

      expect(save).toHaveBeenCalledTimes(1);
      expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([undefined]);
      expect(wrapper.emitted('refresh')).toHaveLength(1);
    });

    it('should stay open when the form refused', async () => {
      save.mockResolvedValue(false);
      const wrapper = createWrapper(addData);

      await confirm(wrapper);

      expect(wrapper.emitted('update:modelValue')).toBeUndefined();
      expect(wrapper.emitted('refresh')).toBeUndefined();
    });

    /** A second press while the first save is in flight would submit the same event twice. */
    it('should ignore a second confirm while the first is still saving', async () => {
      let release: (value: boolean) => void = () => {};
      save.mockReturnValue(new Promise<boolean>((resolve) => {
        release = resolve;
      }));
      const wrapper = createWrapper(addData);

      await wrapper.find('[data-testid=stub-confirm]').trigger('click');
      await wrapper.find('[data-testid=stub-confirm]').trigger('click');
      release(true);
      await flushPromises();

      expect(save).toHaveBeenCalledTimes(1);
    });

    it('should discard the event when dismissed', async () => {
      const wrapper = createWrapper(addData);

      await wrapper.find('[data-testid=stub-cancel]').trigger('click');

      expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([undefined]);
      expect(save).not.toHaveBeenCalled();
    });
  });

  /**
   * The count drives the dialog's scroll-to-first-error, so it stays at zero until a save has
   * actually been refused: a form the user has not submitted yet should not be scrolled.
   */
  describe('the error count', () => {
    it('should report none before the first save', () => {
      set(errorCount, 3);

      expect(dialog(createWrapper(addData)).props('errors')).toMatchObject({ count: 0 });
    });

    it('should report the form errors once a save was refused', async () => {
      save.mockResolvedValue(false);
      set(errorCount, 3);
      const wrapper = createWrapper(addData);

      await confirm(wrapper);

      expect(dialog(wrapper).props('errors')).toMatchObject({ count: 3 });
    });

    it('should go quiet again once the dialog is closed', async () => {
      save.mockResolvedValue(false);
      set(errorCount, 3);
      const wrapper = createWrapper(addData);
      await confirm(wrapper);

      await wrapper.setProps({ modelValue: undefined });

      expect(dialog(wrapper).props('errors')).toMatchObject({ count: 0 });
    });
  });
});
