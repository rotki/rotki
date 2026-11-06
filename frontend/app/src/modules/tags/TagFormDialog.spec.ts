import type { ActionStatus } from '@/modules/core/common/action';
import type { Tag } from '@/modules/tags/tags';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';
import TagFormDialog from '@/modules/tags/TagFormDialog.vue';

const { spies } = vi.hoisted(() => ({
  spies: {
    addTag: vi.fn<(tag: Tag) => Promise<ActionStatus>>(),
    editTag: vi.fn<(tag: Tag, originalName: string) => Promise<ActionStatus>>(),
    validate: vi.fn<() => boolean>(),
  },
}));

vi.mock('@/modules/tags/use-tag-operations', () => ({
  useTagOperations: (): object => ({ addTag: spies.addTag, editTag: spies.editTag }),
}));

const FormStub = defineComponent({
  name: 'TagForm',
  setup(_props, { expose }) {
    expose({ validate: spies.validate });
    return {};
  },
  template: '<div />',
});

const TAG: Tag = {
  backgroundColor: 'ffffff',
  description: '',
  foregroundColor: '000000',
  name: 'defi',
};

function createWrapper(editMode = false): VueWrapper<InstanceType<typeof TagFormDialog>> {
  return mount(TagFormDialog, {
    global: {
      stubs: {
        BigDialog: {
          emits: ['confirm', 'cancel'],
          props: ['display', 'failure', 'failureTitle', 'loading', 'title'],
          template: '<div v-if="display"><slot /></div>',
        },
        TagForm: FormStub,
      },
    },
    props: { editMode, modelValue: { ...TAG }, originalName: editMode ? 'old' : '' },
  });
}

async function save(wrapper: VueWrapper): Promise<void> {
  wrapper.findComponent(BigDialog).vm.$emit('confirm');
  await flushPromises();
}

describe('tagFormDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    spies.validate.mockReturnValue(true);
    spies.addTag.mockResolvedValue({ success: true });
    spies.editTag.mockResolvedValue({ success: true });
  });

  it('should close and emit saved once the tag is added', async () => {
    const wrapper = createWrapper();

    await save(wrapper);

    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
    expect(wrapper.emitted('saved')).toEqual([[{ originalName: 'defi', tag: TAG }]]);
    expect(wrapper.findComponent(BigDialog).props('failure')).toBeUndefined();
  });

  it('should name an add failure in the dialog, which stays open', async () => {
    spies.addTag.mockResolvedValue({ message: 'tag exists', success: false });
    const wrapper = createWrapper();

    await save(wrapper);

    const dialog = wrapper.findComponent(BigDialog);
    expect(dialog.props('failure')).toBe('tag exists');
    expect(dialog.props('failureTitle')).toBe('actions.session.tag_add.error.title');
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
    expect(wrapper.emitted('saved')).toBeUndefined();
  });

  it('should title an edit failure as an edit', async () => {
    spies.editTag.mockResolvedValue({ message: 'not found', success: false });
    const wrapper = createWrapper(true);

    await save(wrapper);

    expect(spies.editTag).toHaveBeenCalledWith(TAG, 'old');
    const dialog = wrapper.findComponent(BigDialog);
    expect(dialog.props('failure')).toBe('not found');
    expect(dialog.props('failureTitle')).toBe('actions.session.tag_edit.error.title');
  });

  it('should drop the failure when the next save starts', async () => {
    spies.addTag.mockResolvedValueOnce({ message: 'tag exists', success: false });
    let resolveSecond: (status: ActionStatus) => void = () => {};
    spies.addTag.mockReturnValueOnce(new Promise<ActionStatus>((resolve) => {
      resolveSecond = resolve;
    }));
    const wrapper = createWrapper();

    await save(wrapper);
    await save(wrapper);

    expect(wrapper.findComponent(BigDialog).props('failure')).toBeUndefined();
    resolveSecond({ success: true });
    await flushPromises();
  });

  it('should drop the failure when the dialog is cancelled', async () => {
    spies.addTag.mockResolvedValue({ message: 'tag exists', success: false });
    const wrapper = createWrapper();

    await save(wrapper);
    wrapper.findComponent(BigDialog).vm.$emit('cancel');
    await flushPromises();

    expect(wrapper.findComponent(BigDialog).props('failure')).toBeUndefined();
    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
  });
});
