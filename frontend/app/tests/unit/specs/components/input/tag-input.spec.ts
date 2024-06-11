import {
  type ThisTypedMountOptions,
  type Wrapper,
  mount,
} from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import TagInput from '@/components/inputs/TagInput.vue';
import { createCustomPinia } from '../../../utils/create-pinia';

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
  let wrapper: Wrapper<TagInput>;
  let store: ReturnType<typeof useTagStore>;

  afterEach(() => {
    useTagStore().$reset();
  });

  const createWrapper = (options: ThisTypedMountOptions<any>) => {
    const pinia = createCustomPinia();
    setActivePinia(pinia);
    return mount(TagInput, {
      pinia,
      stubs: {
        RuiAutoComplete: false,
      },
      ...options,
    });
  };

  it('should add a tag', async () => {
    const value = ref([]);
    const propsData = {
      value,
    };
    wrapper = createWrapper({ propsData });
    store = useTagStore();
    await store.fetchTags();

    await nextTick();

    await wrapper.find('input[type=text]').setValue('tag1');
    await wrapper.find('[data-id=activator]').trigger('keydown.enter');

    await nextTick();

    const emitted: string[] = ['tag1'];
    expect(wrapper.emitted().input?.at(-1)?.[0]).toEqual(emitted);

    await nextTick();

    await wrapper.find('[data-id=activator]').trigger('click');
    await vi.delay();

    expect(wrapper.find('[role=menu-content] button').text()).toBe(
      'tag1',
    );
  });

  it('should remove a tag', async () => {
    const value = ref([]);
    const propsData = {
      value,
    };
    wrapper = createWrapper({ propsData });
    store = useTagStore();
    await store.fetchTags();

    await nextTick();

    await wrapper.find('input[type=text]').setValue('tag2');
    await wrapper.find('[data-id=activator]').trigger('keydown.enter');

    await nextTick();

    set(value, ['tag2']);

    await wrapper.find('[data-id=activator]').trigger('click');
    await vi.delay();

    expect(wrapper.find('[role=menu-content] button:nth-child(2)').text()).toBe(
      'tag2',
    );

    await store.deleteTag('tag2');

    await nextTick();

    const emitted: string[] = [];
    expect(wrapper.emitted().input?.at(-1)?.[0]).toEqual(emitted);

    set(value, emitted);

    await vi.delay();

    expect(wrapper.find('[role=menu-content]').exists()).toBeTruthy();
    expect(
      wrapper.find('[role=menu-content] button:nth-child(2)').exists(),
    ).toBeFalsy();
  });
});
