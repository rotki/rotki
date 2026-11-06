import { createCustomPinia } from '@test/utils/create-pinia';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import TagInput from '@/modules/shell/components/inputs/TagInput.vue';
import TagForm from '@/modules/tags/TagForm.vue';
import { useTagOperations } from '@/modules/tags/use-tag-operations';

function createTag(name: string): { name: string; description: string; backgroundColor: string; foregroundColor: string } {
  return {
    name,
    description: '',
    backgroundColor: 'red',
    foregroundColor: 'white',
  };
}

const { queryAddTag } = vi.hoisted(() => ({
  queryAddTag: vi.fn<(tag: object) => Promise<Record<string, object>>>(),
}));

vi.mock('@/modules/tags/use-tags-api', (): Record<string, unknown> => ({
  useTagsApi: (): Record<string, unknown> => ({
    queryTags: vi.fn().mockResolvedValue({
      tag1: createTag('tag1'),
    }),
    queryAddTag,
    queryEditTag: vi.fn(),
    queryDeleteTag: vi.fn().mockResolvedValue({
      tag1: createTag('tag1'),
    }),
  }),
}));

describe('tag-input', () => {
  let wrapper: VueWrapper<InstanceType<typeof TagInput>>;

  beforeEach((): void => {
    vi.useFakeTimers();
    queryAddTag.mockReset();
    queryAddTag.mockResolvedValue({
      tag1: createTag('tag1'),
      tag2: createTag('tag2'),
    });
  });

  afterEach((): void => {
    wrapper.unmount();
    useSessionMetadataStore().$reset();
    vi.useRealTimers();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof TagInput>): VueWrapper<InstanceType<typeof TagInput>> => {
    const pinia = createCustomPinia();
    setActivePinia(pinia);
    return mount(TagInput, {
      global: {
        plugins: [pinia],
        stubs: {
          TagForm,
          RuiAutoComplete: false,
          Teleport: true,
          Transition: false,
          TransitionGroup: false,
        },
      },
      ...options,
    });
  };

  it('should add a tag', async () => {
    wrapper = createWrapper({
      props: {
        modelValue: [],
      },
    });
    const { fetchTags } = useTagOperations();
    await fetchTags();

    await wrapper.find('input[type=text]').setValue('tag1');
    await vi.runOnlyPendingTimersAsync();
    await wrapper.find('[data-id=activator]').trigger('keydown.enter');

    const emitted: string[] = ['tag1'];
    expect(wrapper.emitted()).toHaveProperty('update:modelValue');
    expect(wrapper.emitted('update:modelValue')![0]).toEqual([emitted]);
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-id=activator]').trigger('click');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-id=content] button').text()).toBe('tag1');
  });

  it('should remove a tag', async () => {
    wrapper = createWrapper({
      props: {
        modelValue: [],
      },
    });
    const { fetchTags, deleteTag } = useTagOperations();
    await fetchTags();

    await wrapper.find('input[type=text]').setValue('tag2');
    await vi.runOnlyPendingTimersAsync();
    await wrapper.find('[data-id=activator]').trigger('keydown.enter');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('.group div[role=button] span').text()).toBe('tag2');
    await deleteTag('tag2');
    await vi.advanceTimersToNextTimerAsync();

    const emitted: string[] = [];
    expect(wrapper.emitted()).toHaveProperty('update:modelValue');
    expect(wrapper.emitted('update:modelValue')![1]).toEqual([emitted]);
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-id=content]').exists()).toBe(true);
    expect(wrapper.find('[data-id=content] button:nth-child(2)').exists()).toBe(false);
  });

  it('should name a failed tag creation under the field and drop the tag', async () => {
    queryAddTag.mockRejectedValueOnce(new Error('tag name is taken'));
    wrapper = createWrapper({
      props: {
        modelValue: [],
      },
    });
    const { fetchTags } = useTagOperations();
    await fetchTags();

    await wrapper.find('input[type=text]').setValue('tag2');
    await vi.runOnlyPendingTimersAsync();
    await wrapper.find('[data-id=activator]').trigger('keydown.enter');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.text()).toContain('tag name is taken');
    expect(wrapper.emitted('update:modelValue')!.at(-1)).toEqual([[]]);
  });

  it('should clear the creation failure on the next attempt', async () => {
    queryAddTag.mockRejectedValueOnce(new Error('tag name is taken'));
    wrapper = createWrapper({
      props: {
        modelValue: [],
      },
    });
    const { fetchTags } = useTagOperations();
    await fetchTags();

    await wrapper.find('input[type=text]').setValue('tag2');
    await vi.runOnlyPendingTimersAsync();
    await wrapper.find('[data-id=activator]').trigger('keydown.enter');
    await vi.advanceTimersToNextTimerAsync();
    expect(wrapper.text()).toContain('tag name is taken');

    await wrapper.find('input[type=text]').setValue('tag2');
    await vi.runOnlyPendingTimersAsync();
    await wrapper.find('[data-id=activator]').trigger('keydown.enter');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.text()).not.toContain('tag name is taken');
  });
});
