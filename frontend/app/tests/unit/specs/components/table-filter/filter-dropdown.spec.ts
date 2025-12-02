import type { StringSuggestionMatcher } from '@/types/filtering';
import { createCustomPinia } from '@test/utils/create-pinia';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { afterEach, describe, expect, it } from 'vitest';
import FilterDropdown from '@/components/table-filter/FilterDropdown.vue';

describe('table-filter/FilterDropdown.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof FilterDropdown>>;
  const createWrapper = (options: ComponentMountingOptions<typeof FilterDropdown> = {}) => {
    const pinia = createCustomPinia();
    setActivePinia(pinia);
    return mount(FilterDropdown, {
      global: {
        stubs: ['I18nT'],
        plugins: [pinia],
      },
      ...options,
    });
  };

  afterEach(() => {
    wrapper.unmount();
  });

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
      matches: {},
      matchers,
      selectedSuggestion: 1,
      keyword: '',
    };

    wrapper = createWrapper({ props });

    expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(matchers.length);
    expect(
      wrapper.find('[data-cy=suggestions] > button:nth-child(2)').classes().includes('highlightedMatcher'),
    ).toBeTruthy();
  });

  it('show unsupported filter message', () => {
    const props = {
      matches: {},
      matchers: [],
      keyword: 'wrong_filter',
      selectedSuggestion: 0,
    };

    wrapper = createWrapper({ props });

    expect(wrapper.find('div > div:first-child > span:first-child').text()).toBe('table_filter.unsupported_filter');

    expect(wrapper.find('div > div:first-child > span:last-child').text()).toBe(props.keyword);
  });

  it('show suggestions', async () => {
    const props = {
      matches: {},
      matchers,
      selectedSuggestion: 0,
      keyword: '',
    };

    const wrapper = createWrapper({ props });

    await wrapper.setProps({
      selectedMatcher: matchers[1],
      keyword: 'type=',
    });

    await nextTick();

    const suggestions = matchers[1].suggestions();
    expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(suggestions.length);

    expect(wrapper.find('[data-cy=suggestions] > button:nth-child(1)').text()).toBe('type=type 1');
    expect(wrapper.find('[data-cy=suggestions] > button:nth-child(2)').text()).toBe('type=type 2');

    await wrapper.setProps({
      keyword: 'type!=',
    });

    await nextTick();

    expect(wrapper.find('[data-cy=suggestions] > button:nth-child(1)').text()).toBe('type!=type 1');
    expect(wrapper.find('[data-cy=suggestions] > button:nth-child(2)').text()).toBe('type!=type 2');

    await wrapper.setProps({
      keyword: 'type=type 2',
    });

    await nextTick();

    expect(wrapper.find('[data-cy=suggestions] > button:nth-child(1)').text()).toBe('type=type 2');
    expect(wrapper.find('[data-cy=suggestions] > button:nth-child(2)').text()).toBe('type=type 1');
  });

  it('show no suggestion message', async () => {
    const props = {
      matches: {},
      matchers,
      selectedSuggestion: 0,
      keyword: '',
    };

    const wrapper = createWrapper({ props });

    await wrapper.setProps({
      selectedMatcher: matchers[0],
      keyword: 'start=',
    });

    await nextTick();

    expect(wrapper.find('i18n-t-stub').attributes('keypath')).toBe('table_filter.start_typing');
  });
});
