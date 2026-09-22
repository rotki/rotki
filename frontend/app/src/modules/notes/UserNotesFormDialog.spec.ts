import type { UserNote, UserNoteDraft } from '@/modules/core/common/notes';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import UserNotesFormDialog from '@/modules/notes/UserNotesFormDialog.vue';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const { spies } = vi.hoisted(() => ({
  spies: {
    addUserNote: vi.fn<(payload: Partial<UserNote>) => Promise<number>>(),
    updateUserNote: vi.fn<(payload: Partial<UserNote>) => Promise<boolean>>(),
    validate: vi.fn<() => boolean>(),
  },
}));

vi.mock('@/modules/notes/use-user-notes-api', () => ({
  useUserNotesApi: (): object => ({ addUserNote: spies.addUserNote, updateUserNote: spies.updateUserNote }),
}));

const UserNotesFormStub = defineComponent({
  name: 'UserNotesForm',
  setup(_props, { expose }) {
    expose({ validate: spies.validate });
    return {};
  },
  template: '<div />',
});

const DRAFT: UserNoteDraft = { content: 'watch the unlock', title: 'LDO' };

describe('userNotesFormDialog', () => {
  let wrapper: VueWrapper<InstanceType<typeof UserNotesFormDialog>>;

  function createWrapper(editMode: boolean, modelValue: UserNoteDraft = DRAFT): VueWrapper<InstanceType<typeof UserNotesFormDialog>> {
    return mount(UserNotesFormDialog, {
      global: {
        stubs: {
          BigDialog: {
            emits: ['confirm', 'cancel'],
            props: ['display', 'loading'],
            template: '<div><slot /></div>',
          },
          UserNotesForm: UserNotesFormStub,
        },
      },
      props: { editMode, location: 'dashboard', modelValue, open: true },
    });
  }

  async function confirm(): Promise<void> {
    wrapper.findComponent(BigDialog).vm.$emit('confirm');
    await flushPromises();
  }

  beforeEach(() => {
    vi.clearAllMocks();
    spies.validate.mockReturnValue(true);
    spies.addUserNote.mockResolvedValue(4);
    spies.updateUserNote.mockResolvedValue(true);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should add a new note to the page it was written on', async () => {
    wrapper = createWrapper(false);

    await confirm();

    expect(spies.addUserNote).toHaveBeenCalledExactlyOnceWith({ ...DRAFT, location: 'dashboard' });
    expect(spies.updateUserNote).not.toHaveBeenCalled();
    expect(wrapper.emitted('reset')).toHaveLength(1);
    expect(wrapper.emitted('refresh')).toHaveLength(1);
  });

  it('should update an edited note where it already lives', async () => {
    const edited: UserNoteDraft = { ...DRAFT, identifier: 9, location: 'history' };
    wrapper = createWrapper(true, edited);

    await confirm();

    expect(spies.updateUserNote).toHaveBeenCalledExactlyOnceWith(edited);
    expect(spies.addUserNote).not.toHaveBeenCalled();
    expect(wrapper.emitted('refresh')).toHaveLength(1);
  });

  it('should save nothing while the form is invalid', async () => {
    spies.validate.mockReturnValue(false);
    wrapper = createWrapper(false);

    await confirm();

    expect(spies.addUserNote).not.toHaveBeenCalled();
    expect(wrapper.emitted('refresh')).toBeUndefined();
  });

  it('should keep the form open when the note could not be saved', async () => {
    spies.updateUserNote.mockResolvedValue(false);
    wrapper = createWrapper(true);

    await confirm();

    expect(spies.updateUserNote).toHaveBeenCalledOnce();
    expect(wrapper.emitted('reset')).toBeUndefined();
    expect(wrapper.emitted('refresh')).toBeUndefined();
  });

  it('should keep the form open when saving throws', async () => {
    spies.addUserNote.mockRejectedValue(new Error('offline'));
    wrapper = createWrapper(false);

    await confirm();

    expect(spies.addUserNote).toHaveBeenCalledOnce();
    expect(wrapper.emitted('reset')).toBeUndefined();
    expect(wrapper.findComponent(BigDialog).props('loading')).toBe(false);
  });

  it('should reset the form on cancel without saving', async () => {
    wrapper = createWrapper(false);

    wrapper.findComponent(BigDialog).vm.$emit('cancel');

    expect(wrapper.emitted('reset')).toHaveLength(1);
    expect(spies.addUserNote).not.toHaveBeenCalled();
  });
});
