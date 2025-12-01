import { createCustomPinia } from '@test/utils/create-pinia';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import TagInput from '@/components/inputs/TagInput.vue';
import TagForm from '@/components/tags/TagForm.vue';
import { useTagStore } from '@/store/session/tags';

vi.mock('@/composables/api/tags', () => ({
  useTagsApi: () => {
    const createTag = (name: string) => ({
      name,
      description: '',
      backgroundColor: 'red',
      foregroundColor: 'white',
    });
    return {
      queryTags: vi.fn().mockResolvedValue({
        tag1: createTag('tag1'),
      }),
      queryAddTag: vi.fn().mockResolvedValue({
        tag1: createTag('tag1'),
        tag2: createTag('tag2'),
      }),
      queryEditTag: vi.fn(),
      queryDeleteTag: vi.fn().mockResolvedValue({
        tag1: createTag('tag1'),
      }),
    };
  },
}));

describe('tagInput.vue', () => {
  let store: ReturnType<typeof useTagStore>;
  let wrapper: VueWrapper<InstanceType<typeof TagInput>>;

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper.unmount();
    useTagStore().$reset();
    vi.useRealTimers();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof TagInput>) => {
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
    store = useTagStore();
    await store.fetchTags();

    await wrapper.find('input[type=text]').setValue('tag1');
    await vi.runOnlyPendingTimersAsync();
    await wrapper.find('[data-id=activator]').trigger('keydown.enter');

    const emitted: string[] = ['tag1'];
    expect(wrapper.emitted()).toHaveProperty('update:modelValue');
    expect(wrapper.emitted('update:modelValue')![0]).toEqual([emitted]);
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-id=activator]').trigger('click');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[role=menu-content] button').text()).toBe('tag1');
  });

  it('should remove a tag', async () => {
    wrapper = createWrapper({
      props: {
        modelValue: [],
      },
    });
    store = useTagStore();
    await store.fetchTags();

    await wrapper.find('input[type=text]').setValue('tag2');
    await vi.runOnlyPendingTimersAsync();
    await wrapper.find('[data-id=activator]').trigger('keydown.enter');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('.group div[role=button] span').text()).toBe('tag2');
    await store.deleteTag('tag2');
    await vi.advanceTimersToNextTimerAsync();

    const emitted: string[] = [];
    expect(wrapper.emitted()).toHaveProperty('update:modelValue');
    expect(wrapper.emitted('update:modelValue')![1]).toEqual([emitted]);
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[role=menu-content]').exists()).toBeTruthy();
    expect(wrapper.find('[role=menu-content] button:nth-child(2)').exists()).toBeFalsy();
  });
});
