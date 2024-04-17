import {
  type ThisTypedMountOptions,
  type Wrapper,
  mount,
} from '@vue/test-utils';
import Vuetify from 'vuetify';
import { setActivePinia } from 'pinia';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import { createCustomPinia } from '../../../utils/create-pinia';
import type { StringSuggestionMatcher } from '@/types/filtering';

vi.mocked(useCssModule).mockReturnValue({
  suggestions: 'suggestions',
});

describe('table-filter/FilterDropdown.vue', () => {
  let wrapper: Wrapper<any>;
  const createWrapper = (options: ThisTypedMountOptions<any> = {}) => {
    const vuetify = new Vuetify();
    const pinia = createCustomPinia();
    setActivePinia(pinia);
    return mount(TableFilter, {
      pinia,
      vuetify,
      stubs: {
        VCombobox: {
          template: `
            <div>
              <input :value="searchInput" class="search-input" type="text" @input="$emit('update:search-input', $event.value)">
              <div class="selections">
                <span v-for="item in value"><slot name="selection" v-bind="{ item, selection: item }"/></span>
              </div>
              <span><slot name="no-data" /></span>
            </div>
          `,
          props: {
            value: { type: Array },
            searchInput: { type: String },
          },
        },
      },
      ...options,
    });
  };

  const matchers: StringSuggestionMatcher<any, any>[] = [
    {
      key: 'start',
      keyValue: 'start',
      description: 'filter by start date',
      string: true,
      suggestions: () => [],
      validate: () => true,
    },
    {
      key: 'type',
      keyValue: 'type',
      description: 'filter by type',
      string: true,
      allowExclusion: true,
      multiple: true,
      suggestions: () => ['type 1', 'type 2', 'type 3'],
      validate: () => true,
    },
  ];

  it('filter matchers', async () => {
    const propsData = {
      matchers,
      matches: {},
    };

    wrapper = createWrapper({ propsData });

    expect(wrapper.findAll('.suggestions > button')).toHaveLength(
      matchers.length,
    );

    await wrapper.find('.search-input').trigger('input', { value: 'ty' });

    await nextTick();

    expect(wrapper.findAll('.suggestions > button')).toHaveLength(1);
    expect(wrapper.find('.suggestions > button:first-child').text()).toBe(
      `${matchers[1].key}:  ${matchers[1].description}`,
    );
  });

  it('choose suggestions', async () => {
    const propsData = {
      matchers,
      matches: {},
    };

    wrapper = createWrapper({ propsData });

    // Set matcher to `type`
    await wrapper.find('.search-input').trigger('input', { value: 'type' });

    await nextTick();

    // Suggestions for `type`
    const suggestions = matchers[1].suggestions();
    expect(wrapper.findAll('.suggestions > button')).toHaveLength(
      suggestions.length,
    );

    suggestions.forEach((item, index) => {
      expect(
        wrapper.find(`.suggestions > button:nth-child(${index + 1})`).text(),
      ).toBe(`type = ${item}`);
    });

    // Choose first suggestions (type 1)
    await wrapper.find('.suggestions > button:first-child').trigger('click');

    await nextTick();

    expect(
      wrapper
        .find('.selections > span:nth-child(1) div[role=button] span')
        .text(),
    ).toBe('type = type 1');

    expect(wrapper.emitted()['update:matches']?.[0]).toEqual([
      { type: ['type 1'] },
    ]);

    // Choose second suggestion (type 2)
    await wrapper
      .find('.search-input')
      .trigger('input', { value: 'type = type 2' });

    await nextTick();

    await wrapper.find('.suggestions > button:first-child').trigger('click');

    await nextTick();

    expect(
      wrapper
        .find('.selections > span:nth-child(2) div[role=button] span')
        .text(),
    ).toBe('type = type 2');

    expect(wrapper.emitted()['update:matches']?.[1]).toEqual([
      { type: ['type 1', 'type 2'] },
    ]);

    // Remove first selected item (type 1)
    await wrapper
      .find('.selections > span:nth-child(1) div[role=button] button')
      .trigger('click');

    await nextTick();

    expect(wrapper.emitted()['update:matches']?.[2]).toEqual([
      { type: ['type 2'] },
    ]);

    // Click selected item remains (type 2), set it to text field
    await wrapper
      .find('.selections > span:nth-child(1) div[role=button] span')
      .trigger('click');

    await nextTick();

    expect(wrapper.emitted()['update:matches']?.[3]).toEqual([{}]);
    expect(
      (wrapper.find('.search-input').element as HTMLInputElement).value,
    ).toBe('type=type 2');
  });

  it('choose suggestions with exclusion', async () => {
    const propsData = {
      matchers,
      matches: {},
    };

    wrapper = createWrapper({ propsData });

    // Set matcher to `type`
    await wrapper.find('.search-input').trigger('input', { value: 'type !=' });

    await nextTick();

    // Suggestions for `type`
    const suggestions = matchers[1].suggestions();
    expect(wrapper.findAll('.suggestions > button')).toHaveLength(
      suggestions.length,
    );

    suggestions.forEach((item, index) => {
      expect(
        wrapper.find(`.suggestions > button:nth-child(${index + 1})`).text(),
      ).toBe(`type != ${item}`);
    });

    // Choose first suggestions with exclusion (type 1)
    await wrapper.find('.suggestions > button:first-child').trigger('click');

    await nextTick();

    expect(
      wrapper
        .find('.selections > span:nth-child(1) div[role=button] span')
        .text(),
    ).toBe('type != type 1');

    expect(wrapper.emitted()['update:matches']?.[0]).toEqual([
      { type: ['!type 1'] },
    ]);
  });

  it('restore selection', async () => {
    const propsData = {
      matchers,
      matches: {
        type: ['type 1', 'type 2'],
      },
    };

    wrapper = createWrapper({ propsData });

    await nextTick();

    expect(
      wrapper
        .find('.selections > span:nth-child(1) div[role=button] span')
        .text(),
    ).toBe('type = type 1');
    expect(
      wrapper
        .find('.selections > span:nth-child(2) div[role=button] span')
        .text(),
    ).toBe('type = type 2');
  });

  it('restore selection with exclusion', async () => {
    const propsData = {
      matchers,
      matches: {
        type: '!type 1',
      },
    };

    wrapper = createWrapper({ propsData });

    await nextTick();

    expect(
      wrapper
        .find('.selections > span:nth-child(1) div[role=button] span')
        .text(),
    ).toBe('type != type 1');
  });
});
