import {
  type ComponentMountingOptions,
  mount,
} from '@vue/test-utils';
import { createVuetify } from 'vuetify';
import { setActivePinia } from 'pinia';
import TagInput from '@/components/inputs/TagInput.vue';
import createCustomPinia from '../../../utils/create-pinia';

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

  afterEach(() => {
    useTagStore().$reset();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof TagInput>) => {
    const vuetify = createVuetify();
    const pinia = createCustomPinia();
    setActivePinia(pinia);
    return mount(TagInput, {
      global: {
        plugins: [
          pinia,
          vuetify,
        ],
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
              value: { type: Array },
            },
          },
        },
      },
      ...options,
    });
  };

  it('should add a tag', async () => {
    const modelValue: string[] = [];
    const props = {
      modelValue,
    };
    const tagInput = createWrapper({ props });
    store = useTagStore();
    await store.fetchTags();

    await nextTick();

    await tagInput.find('input[type=text]').trigger('input', { value: 'tag1' });

    await nextTick();

    const emitted: string[] = ['tag1'];
    expect(tagInput.emitted()).toHaveProperty('update:model-value');
    expect(tagInput.emitted('update:model-value')[0]).toEqual([emitted]);

    await nextTick();

    expect(tagInput.find('.selections div[role=button] span').text()).toBe(
      'tag1',
    );
  });

  it('should remove a tag', async () => {
    const modelValue: string[] = [];
    const props = {
      modelValue,
    };
    const tagInput = createWrapper({ props });
    store = useTagStore();
    await store.fetchTags();

    await nextTick();

    await tagInput.find('input[type=text]').trigger('input', { value: 'tag2' });

    await nextTick();

    expect(tagInput.find('.selections div[role=button] span').text()).toBe(
      'tag2',
    );

    await store.deleteTag('tag2');

    await nextTick();

    const emitted: string[] = [];
    expect(tagInput.emitted()).toHaveProperty('update:model-value');
    expect(tagInput.emitted('update:model-value')[1]).toEqual([emitted]);

    await nextTick();

    expect(
      tagInput.find('.selections div[role=button] span').exists(),
    ).toBeFalsy();
  });
});
