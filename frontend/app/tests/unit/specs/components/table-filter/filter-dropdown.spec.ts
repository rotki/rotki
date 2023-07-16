import {
  type ThisTypedMountOptions,
  type Wrapper,
  mount
} from '@vue/test-utils';
import Vuetify from 'vuetify';
import { setActivePinia } from 'pinia';
import { type StringSuggestionMatcher } from '@/types/filtering';
import FilterDropdown from '@/components/table-filter/FilterDropdown.vue';
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
    return mount(FilterDropdown, {
      pinia,
      vuetify,
      stubs: ['filter-entry', 'suggested-item', 'I18n'],
      ...options
    });
  };

  const matchers: StringSuggestionMatcher<any>[] = [
    {
      key: 'start',
      description: 'filter by start date',
      string: true,
      suggestions: () => [],
      validate: () => true
    },
    {
      key: 'type',
      description: 'filter by type',
      string: true,
      allowExclusion: true,
      suggestions: () => ['type 1', 'type 2'],
      validate: () => true
    }
  ];

  it('Show all matchers options', () => {
    const propsData = {
      matchers,
      selectedSuggestion: 1
    };

    wrapper = createWrapper({ propsData });

    expect(wrapper.findAll('.suggestions > div')).toHaveLength(matchers.length);
    expect(
      wrapper
        .find('.suggestions > div:nth-child(2)')
        .classes()
        .includes('highlightedMatcher')
    ).toBeTruthy();
  });

  it('Show unsupported filter message', () => {
    const propsData = {
      matchers: [],
      keyword: 'wrong_filter',
      selectedSuggestion: 0
    };

    wrapper = createWrapper({ propsData });

    expect(
      wrapper.find('div > div:first-child > span:first-child').text()
    ).toBe('table_filter.unsupported_filter');

    expect(wrapper.find('div > div:first-child > span:last-child').text()).toBe(
      propsData.keyword
    );
  });

  it('Show suggestions', async () => {
    const propsData = {
      matchers,
      selectedSuggestion: 0
    };

    const wrapper = createWrapper({ propsData });

    await wrapper.setProps({
      selectedMatcher: matchers[1],
      keyword: 'type='
    });

    await wrapper.vm.$nextTick();

    const suggestions = matchers[1].suggestions();
    expect(wrapper.findAll('.suggestions > div')).toHaveLength(
      suggestions.length
    );

    expect(wrapper.find('.suggestions > div:nth-child(1)').text()).toBe(
      'type = type 1'
    );
    expect(wrapper.find('.suggestions > div:nth-child(2)').text()).toBe(
      'type = type 2'
    );

    await wrapper.setProps({
      keyword: 'type !='
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.find('.suggestions > div:nth-child(1)').text()).toBe(
      'type != type 1'
    );
    expect(wrapper.find('.suggestions > div:nth-child(2)').text()).toBe(
      'type != type 2'
    );

    await wrapper.setProps({
      keyword: 'type=type 2'
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.find('.suggestions > div:nth-child(1)').text()).toBe(
      'type = type 2'
    );
    expect(wrapper.find('.suggestions > div:nth-child(2)').text()).toBe(
      'type = type 1'
    );
  });

  it('Show no suggestion message', async () => {
    const propsData = {
      matchers,
      selectedSuggestion: 0
    };

    const wrapper = createWrapper({ propsData });

    await wrapper.setProps({
      selectedMatcher: matchers[0],
      keyword: 'start='
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.find('I18n-stub').attributes().path).toBe(
      'table_filter.no_suggestions'
    );
  });
});
