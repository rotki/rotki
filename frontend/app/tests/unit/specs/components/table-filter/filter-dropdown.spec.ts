import {
  type ComponentMountingOptions,
  type VueWrapper,
  mount,
} from '@vue/test-utils';
import { createVuetify } from 'vuetify';
import { setActivePinia } from 'pinia';
import FilterDropdown from '@/components/table-filter/FilterDropdown.vue';
import createCustomPinia from '../../../utils/create-pinia';
import type { StringSuggestionMatcher } from '@/types/filtering';

describe('table-filter/FilterDropdown.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof FilterDropdown>>;
  const createWrapper = (options: ComponentMountingOptions<typeof FilterDropdown> = {}) => {
    const vuetify = createVuetify();
    const pinia = createCustomPinia();
    setActivePinia(pinia);
    return mount(FilterDropdown, {
      global: {
        stubs: ['filter-entry', 'suggested-item', 'i18n-t'],
        plugins: [
          pinia,
          vuetify,
        ],
      },
      ...options,
    });
  };

  const matchers: StringSuggestionMatcher<any>[] = [
    {
      key: 'start',
      description: 'filter by start date',
      string: true,
      suggestions: () => [],
      validate: () => true,
    },
    {
      key: 'type',
      description: 'filter by type',
      string: true,
      allowExclusion: true,
      suggestions: () => ['type 1', 'type 2'],
      validate: () => true,
    },
  ];

  it('show all matchers options', () => {
    const props = {
      matchers,
      selectedSuggestion: 1,
    };

    wrapper = createWrapper({ props });

    expect(wrapper.findAll('.suggestions > button')).toHaveLength(
      matchers.length,
    );
    expect(
      wrapper
        .find('.suggestions > button:nth-child(2)')
        .classes()
        .includes('highlightedMatcher'),
    ).toBeTruthy();
  });

  it('show unsupported filter message', () => {
    const props = {
      matchers: [],
      keyword: 'wrong_filter',
      selectedSuggestion: 0,
    };

    wrapper = createWrapper({ props });

    expect(
      wrapper.find('div > div:first-child > span:first-child').text(),
    ).toBe('table_filter.unsupported_filter');

    expect(wrapper.find('div > div:first-child > span:last-child').text()).toBe(
      props.keyword,
    );
  });

  it('show suggestions', async () => {
    const props = {
      matchers,
      selectedSuggestion: 0,
    };

    const wrapper = createWrapper({ props });

    await wrapper.setProps({
      selectedMatcher: matchers[1],
      keyword: 'type=',
    });

    await nextTick();

    const suggestions = matchers[1].suggestions();
    expect(wrapper.findAll('.suggestions > button')).toHaveLength(
      suggestions.length,
    );

    expect(wrapper.find('.suggestions > button:nth-child(1)').text()).toBe(
      'type = type 1',
    );
    expect(wrapper.find('.suggestions > button:nth-child(2)').text()).toBe(
      'type = type 2',
    );

    await wrapper.setProps({
      keyword: 'type !=',
    });

    await nextTick();

    expect(wrapper.find('.suggestions > button:nth-child(1)').text()).toBe(
      'type != type 1',
    );
    expect(wrapper.find('.suggestions > button:nth-child(2)').text()).toBe(
      'type != type 2',
    );

    await wrapper.setProps({
      keyword: 'type=type 2',
    });

    await nextTick();

    expect(wrapper.find('.suggestions > button:nth-child(1)').text()).toBe(
      'type = type 2',
    );
    expect(wrapper.find('.suggestions > button:nth-child(2)').text()).toBe(
      'type = type 1',
    );
  });

  it('show no suggestion message', async () => {
    const props = {
      matchers,
      selectedSuggestion: 0,
    };

    const wrapper = createWrapper({ props });

    await wrapper.setProps({
      selectedMatcher: matchers[0],
      keyword: 'start=',
    });

    await nextTick();

    expect(wrapper.find('I18n-stub').attributes().path).toBe(
      'table_filter.no_suggestions',
    );
  });
});
