import {
  type ThisTypedMountOptions,
  type Wrapper,
  mount
} from '@vue/test-utils';
import Vuetify from 'vuetify';
import { setActivePinia } from 'pinia';
import TagInput from '@/components/inputs/TagInput.vue';
import createCustomPinia from '../../../utils/create-pinia';

vi.mock('@/composables/api/tags', () => ({
  useTagsApi: () => {
    const createTag = (name: string) => ({
      name,
      description: '',
      backgroundColor: 'red',
      foregroundColor: 'white'
    });
    return {
      queryTags: vi.fn().mockResolvedValue({
        tag1: createTag('tag1')
      }),
      queryAddTag: vi.fn().mockResolvedValue({
        tag1: createTag('tag1'),
        tag2: createTag('tag2')
      }),
      queryEditTag: vi.fn(),
      queryDeleteTag: vi.fn().mockResolvedValue({
        tag1: createTag('tag1')
      })
    };
  }
}));

describe('TagInput.vue', () => {
  let wrapper: Wrapper<TagInput>;
  let store: ReturnType<typeof useTagStore>;

  afterEach(() => {
    useTagStore().$reset();
  });

  const createWrapper = (options: ThisTypedMountOptions<any>) => {
    const vuetify = new Vuetify();
    const pinia = createCustomPinia();
    setActivePinia(pinia);
    return mount(TagInput, {
      pinia,
      vuetify,
      stubs: {
        VCombobox: {
          template: `
            <div>
              <input class="search-input" type="text" @input="$emit('input', [...value, $event.value])">
              <div class="selections">
                <span v-for="item in value"><slot name="selection" v-bind="{ item, selected: item }"/></span>
              </div>
              <span><slot name="no-data" /></span>
            </div>
          `,
          props: {
            value: { type: Array }
          }
        }
      },
      ...options
    });
  };

  test('should add a tag', async () => {
    const value = ref([]);
    const propsData = {
      value
    };
    wrapper = createWrapper({ propsData });
    store = useTagStore();
    await store.fetchTags();

    await wrapper.vm.$nextTick();

    await wrapper.find('input[type=text]').trigger('input', { value: 'tag1' });

    await wrapper.vm.$nextTick();

    const emitted: string[] = ['tag1'];
    expect(wrapper.emitted().input?.[0]?.[0]).toEqual(emitted);
    set(value, emitted);

    await wrapper.vm.$nextTick();

    expect(wrapper.find('.selections .v-chip').text()).toBe('tag1');
  });

  test('should remove a tag', async () => {
    const value = ref([]);
    const propsData = {
      value
    };
    wrapper = createWrapper({ propsData });
    store = useTagStore();
    await store.fetchTags();

    await wrapper.vm.$nextTick();

    await wrapper.find('input[type=text]').trigger('input', { value: 'tag2' });

    await wrapper.vm.$nextTick();

    set(value, ['tag2']);

    await wrapper.vm.$nextTick();

    expect(wrapper.find('.selections .v-chip').text()).toBe('tag2');

    await store.deleteTag('tag2');

    await wrapper.vm.$nextTick();

    const emitted: string[] = [];
    expect(wrapper.emitted().input?.[1]?.[0]).toEqual(emitted);

    set(value, emitted);

    await wrapper.vm.$nextTick();

    expect(wrapper.find('.selections .v-chip').exists()).toBeFalsy();
  });
});
