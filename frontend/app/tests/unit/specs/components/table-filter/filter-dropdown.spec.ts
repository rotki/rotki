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

  describe('strictMatching', () => {
    const strictMatchingMatchers: StringSuggestionMatcher<any>[] = [
      {
        key: 'account',
        description: 'filter by account',
        string: true,
        strictMatching: true,
        suggestions: () => [
          'vitalik.eth (0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045)',
          '0x1234567890abcdef1234567890abcdef12345678',
          'my-wallet (0xabcdef1234567890abcdef1234567890abcdef12)',
        ],
        validate: () => true,
      },
    ];

    it('filters suggestions by substring match when strictMatching is enabled', async () => {
      const props = {
        matches: {},
        matchers: strictMatchingMatchers,
        selectedSuggestion: 0,
        keyword: '',
      };

      const wrapper = createWrapper({ props });

      await wrapper.setProps({
        selectedMatcher: strictMatchingMatchers[0],
        keyword: 'account=vitalik',
      });

      await nextTick();

      // Should only show the vitalik.eth suggestion
      expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(1);
      expect(wrapper.find('[data-cy=suggestions] > button:first-child').text()).toContain('vitalik.eth');
    });

    it('shows no suggestions when keyword does not match any item with strictMatching', async () => {
      const props = {
        matches: {},
        matchers: strictMatchingMatchers,
        selectedSuggestion: 0,
        keyword: '',
      };

      const wrapper = createWrapper({ props });

      await wrapper.setProps({
        selectedMatcher: strictMatchingMatchers[0],
        keyword: 'account=nonexistent',
      });

      await nextTick();

      // Should show no suggestions
      expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(0);
    });

    it('filters by address when typing partial address with strictMatching', async () => {
      const props = {
        matches: {},
        matchers: strictMatchingMatchers,
        selectedSuggestion: 0,
        keyword: '',
      };

      const wrapper = createWrapper({ props });

      await wrapper.setProps({
        selectedMatcher: strictMatchingMatchers[0],
        keyword: 'account=d8da6bf',
      });

      await nextTick();

      // Should match the vitalik.eth entry by address (case-insensitive via getTextToken)
      expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(1);
      expect(wrapper.find('[data-cy=suggestions] > button:first-child').text()).toContain('vitalik.eth');
    });

    it('shows all suggestions when keyword is empty with strictMatching', async () => {
      const props = {
        matches: {},
        matchers: strictMatchingMatchers,
        selectedSuggestion: 0,
        keyword: '',
      };

      const wrapper = createWrapper({ props });

      await wrapper.setProps({
        selectedMatcher: strictMatchingMatchers[0],
        keyword: 'account=',
      });

      await nextTick();

      // Should show all suggestions when no keyword value
      expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(3);
    });
  });
});
