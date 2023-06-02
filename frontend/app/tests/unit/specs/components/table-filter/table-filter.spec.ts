import {
  type ThisTypedMountOptions,
  type Wrapper,
  mount
} from '@vue/test-utils';
import Vuetify from 'vuetify';
import { setActivePinia } from 'pinia';
import { type StringSuggestionMatcher } from '@/types/filtering';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import createCustomPinia from '../../../utils/create-pinia';

vi.mocked(useCssModule).mockReturnValue({
  suggestions: 'suggestions'
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
            searchInput: { type: String }
          }
        }
      },
      ...options
    });
  };

  const matchers: StringSuggestionMatcher<any, any>[] = [
    {
      key: 'start',
      keyValue: 'start',
      description: 'filter by start date',
      string: true,
      suggestions: () => [],
      validate: () => true
    },
    {
      key: 'type',
      keyValue: 'type',
      description: 'filter by type',
      string: true,
      allowExclusion: true,
      multiple: true,
      suggestions: () => ['type 1', 'type 2', 'type 3'],
      validate: () => true
    }
  ];

  it('Filter matchers', async () => {
    const propsData = {
      matchers,
      matches: {}
    };

    wrapper = createWrapper({ propsData });

    expect(wrapper.findAll('.suggestions > div')).toHaveLength(matchers.length);

    await wrapper.find('.search-input').trigger('input', { value: 'ty' });

    await wrapper.vm.$nextTick();

    expect(wrapper.findAll('.suggestions > div')).toHaveLength(1);
    expect(wrapper.find('.suggestions > div:first-child').text()).toBe(
      `${matchers[1].key}:  ${matchers[1].description}`
    );
  });

  it('Choose suggestions', async () => {
    const propsData = {
      matchers,
      matches: {}
    };

    wrapper = createWrapper({ propsData });

    // Set matcher to `type`
    await wrapper.find('.search-input').trigger('input', { value: 'type' });

    await wrapper.vm.$nextTick();

    // Suggestions for `type`
    const suggestions = matchers[1].suggestions();
    expect(wrapper.findAll('.suggestions > div')).toHaveLength(
      suggestions.length
    );

    suggestions.forEach((item, index) => {
      expect(
        wrapper.find(`.suggestions > div:nth-child(${index + 1})`).text()
      ).toBe(`type = ${item}`);
    });

    // Choose first suggestions (type 1)
    await wrapper
      .find('.suggestions > div:first-child button')
      .trigger('click');

    await wrapper.vm.$nextTick();

    expect(wrapper.find('.selections > span:nth-child(1) .v-chip').text()).toBe(
      'type = type 1'
    );

    expect(wrapper.emitted()['update:matches']?.[0]).toEqual([
      { type: ['type 1'] }
    ]);

    // Choose second suggestion (type 2)
    await wrapper
      .find('.search-input')
      .trigger('input', { value: 'type = type 2' });

    await wrapper.vm.$nextTick();

    await wrapper
      .find('.suggestions > div:first-child button')
      .trigger('click');

    await wrapper.vm.$nextTick();

    expect(wrapper.find('.selections > span:nth-child(2) .v-chip').text()).toBe(
      'type = type 2'
    );

    expect(wrapper.emitted()['update:matches']?.[1]).toEqual([
      { type: ['type 1', 'type 2'] }
    ]);

    // Remove first selected item (type 1)
    await wrapper
      .find('.selections > span:nth-child(1) .v-chip .v-chip__close')
      .trigger('click');

    await wrapper.vm.$nextTick();

    expect(wrapper.emitted()['update:matches']?.[2]).toEqual([
      { type: ['type 2'] }
    ]);

    // Click selected item remains (type 2), set it to text field
    await wrapper
      .find('.selections > span:nth-child(1) .v-chip')
      .trigger('click');

    await wrapper.vm.$nextTick();

    expect(wrapper.emitted()['update:matches']?.[3]).toEqual([{}]);
    expect(
      (wrapper.find('.search-input').element as HTMLInputElement).value
    ).toBe('type=type 2');
  });

  it('Choose suggestions with exclusion', async () => {
    const propsData = {
      matchers,
      matches: {}
    };

    wrapper = createWrapper({ propsData });

    // Set matcher to `type`
    await wrapper.find('.search-input').trigger('input', { value: 'type !=' });

    await wrapper.vm.$nextTick();

    // Suggestions for `type`
    const suggestions = matchers[1].suggestions();
    expect(wrapper.findAll('.suggestions > div')).toHaveLength(
      suggestions.length
    );

    suggestions.forEach((item, index) => {
      expect(
        wrapper.find(`.suggestions > div:nth-child(${index + 1})`).text()
      ).toBe(`type != ${item}`);
    });

    // Choose first suggestions with exclusion (type 1)
    await wrapper
      .find('.suggestions > div:first-child button')
      .trigger('click');

    await wrapper.vm.$nextTick();

    expect(wrapper.find('.selections > span:nth-child(1) .v-chip').text()).toBe(
      'type != type 1'
    );

    expect(wrapper.emitted()['update:matches']?.[0]).toEqual([
      { type: ['!type 1'] }
    ]);
  });

  it('Restore selection', async () => {
    const propsData = {
      matchers,
      matches: {
        type: ['type 1', 'type 2']
      }
    };

    wrapper = createWrapper({ propsData });

    await wrapper.vm.$nextTick();

    expect(wrapper.find('.selections > span:nth-child(1) .v-chip').text()).toBe(
      'type = type 1'
    );
    expect(wrapper.find('.selections > span:nth-child(2) .v-chip').text()).toBe(
      'type = type 2'
    );
  });

  it('Restore selection with exclusion', async () => {
    const propsData = {
      matchers,
      matches: {
        type: '!type 1'
      }
    };

    wrapper = createWrapper({ propsData });

    await wrapper.vm.$nextTick();

    expect(wrapper.find('.selections > span:nth-child(1) .v-chip').text()).toBe(
      'type != type 1'
    );
  });
});
