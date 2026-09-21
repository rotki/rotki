import type { AddCalendarEventResponse, CalendarEvent, CalendarEventPayload } from '@/modules/calendar/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { omit } from 'es-toolkit';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import CalendarFormDialog from '@/modules/calendar/CalendarFormDialog.vue';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const { spies } = vi.hoisted(() => ({
  spies: {
    addCalendarEvent: vi.fn<(payload: CalendarEventPayload) => Promise<AddCalendarEventResponse>>(),
    editCalendarEvent: vi.fn<(payload: CalendarEvent) => Promise<AddCalendarEventResponse>>(),
    reset: vi.fn<() => void>(),
    saveReminders: vi.fn<(eventId: number) => Promise<void>>(),
    validate: vi.fn<() => Promise<boolean>>(),
  },
}));

vi.mock('@/modules/calendar/use-calendar-api', () => ({
  useCalendarApi: (): object => ({ addCalendarEvent: spies.addCalendarEvent, editCalendarEvent: spies.editCalendarEvent }),
}));

const CalendarFormStub = defineComponent({
  name: 'CalendarForm',
  props: { errorMessages: { default: () => ({}), type: Object } },
  setup(_props, { expose }) {
    expose({ reset: spies.reset, saveReminders: spies.saveReminders, validate: spies.validate });
    return {};
  },
  template: '<div />',
});

const EVENT: CalendarEvent = {
  autoDelete: true,
  description: 'claim the airdrop',
  identifier: 21,
  name: 'ARB claim',
  timestamp: 1_760_000_000,
};

describe('calendarFormDialog', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof CalendarFormDialog>>;

  function createWrapper(editMode: boolean): VueWrapper<InstanceType<typeof CalendarFormDialog>> {
    return mount(CalendarFormDialog, {
      global: {
        plugins: [pinia],
        stubs: {
          BigDialog: {
            emits: ['confirm', 'cancel'],
            props: ['display', 'loading', 'title'],
            template: '<div v-if="display"><slot /><slot name="left-buttons" /></div>',
          },
          CalendarForm: CalendarFormStub,
        },
      },
      props: { editMode, loading: false, modelValue: { ...EVENT } },
    });
  }

  async function save(): Promise<void> {
    wrapper.findComponent(BigDialog).vm.$emit('confirm');
    await flushPromises();
  }

  beforeEach(() => {
    vi.clearAllMocks();
    pinia = createCustomPinia();
    setActivePinia(pinia);
    spies.validate.mockResolvedValue(true);
    spies.saveReminders.mockResolvedValue(undefined);
    spies.addCalendarEvent.mockResolvedValue({ entryId: 40 });
    spies.editCalendarEvent.mockResolvedValue({ entryId: 21 });
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  describe('save', () => {
    it('should add a new event without an identifier, then save its reminders under the new id', async () => {
      wrapper = createWrapper(false);

      await save();

      expect(spies.addCalendarEvent).toHaveBeenCalledExactlyOnceWith(omit(EVENT, ['identifier']));
      expect(spies.editCalendarEvent).not.toHaveBeenCalled();
      expect(spies.reset).toHaveBeenCalledOnce();
      expect(spies.saveReminders).toHaveBeenCalledExactlyOnceWith(40);
    });

    it('should update an edited event in place', async () => {
      wrapper = createWrapper(true);

      await save();

      expect(spies.editCalendarEvent).toHaveBeenCalledExactlyOnceWith(EVENT);
      expect(spies.addCalendarEvent).not.toHaveBeenCalled();
      expect(spies.saveReminders).toHaveBeenCalledExactlyOnceWith(21);
    });

    it('should close and ask for a reload once saved', async () => {
      wrapper = createWrapper(false);

      await save();

      expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
      expect(wrapper.emitted('refresh')).toHaveLength(1);
    });

    it('should save nothing while the form is invalid', async () => {
      spies.validate.mockResolvedValue(false);
      wrapper = createWrapper(false);

      await save();

      expect(spies.addCalendarEvent).not.toHaveBeenCalled();
      expect(wrapper.emitted('refresh')).toBeUndefined();
    });
  });

  describe('a rejected save', () => {
    it('should hand field errors back to the form and stay open', async () => {
      spies.addCalendarEvent.mockRejectedValue(new ApiValidationError(JSON.stringify({ name: ['already taken'] })));
      wrapper = createWrapper(false);

      await save();

      expect(wrapper.findComponent(CalendarFormStub).props('errorMessages')).toEqual({ name: ['already taken'] });
      expect(useMessageStore().message).toBeUndefined();
      expect(wrapper.emitted('update:modelValue')).toBeUndefined();
      expect(wrapper.emitted('refresh')).toBeUndefined();
      expect(spies.saveReminders).not.toHaveBeenCalled();
    });

    it('should report any other failure as an add error', async () => {
      spies.addCalendarEvent.mockRejectedValue(new Error('backend down'));
      wrapper = createWrapper(false);

      await save();

      expect(useMessageStore().message).toMatchObject({
        description: 'backend down',
        success: false,
        title: 'calendar.add_error',
      });
      expect(wrapper.emitted('update:modelValue')).toBeUndefined();
      expect(wrapper.findComponent(BigDialog).props('loading')).toBe(false);
    });

    it('should report any other failure of an edit as an edit error', async () => {
      spies.editCalendarEvent.mockRejectedValue(new Error('backend down'));
      wrapper = createWrapper(true);

      await save();

      expect(useMessageStore().message).toMatchObject({ title: 'calendar.edit_error' });
    });
  });

  describe('dialog', () => {
    it('should be titled for adding, with no way to delete', () => {
      wrapper = createWrapper(false);

      expect(wrapper.findComponent(BigDialog).props('title')).toBe('calendar.dialog.add.title');
      expect(wrapper.find('[data-testid=calendar-form-delete]').exists()).toBe(false);
    });

    it('should be titled for editing, and ask the parent to delete the event', async () => {
      wrapper = createWrapper(true);

      expect(wrapper.findComponent(BigDialog).props('title')).toBe('calendar.dialog.edit.title');

      await wrapper.find('[data-testid=calendar-form-delete]').trigger('click');

      expect(wrapper.emitted('delete')).toHaveLength(1);
    });

    it('should close without saving on cancel', () => {
      wrapper = createWrapper(false);

      wrapper.findComponent(BigDialog).vm.$emit('cancel');

      expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
      expect(spies.addCalendarEvent).not.toHaveBeenCalled();
    });
  });
});
