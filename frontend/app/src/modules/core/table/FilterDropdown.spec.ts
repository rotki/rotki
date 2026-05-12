import type { StringSuggestionMatcher } from '@/modules/core/table/filtering';
import { createCustomPinia } from '@test/utils/create-pinia';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { afterEach, describe, expect, it } from 'vitest';
import FilterDropdown from '@/modules/core/table/FilterDropdown.vue';

describe('filter-dropdown', () => {
  let wrapper: VueWrapper<InstanceType<typeof FilterDropdown>>;
  const createWrapper = (options: ComponentMountingOptions<typeof FilterDropdown> = {}): VueWrapper<InstanceType<typeof FilterDropdown>> => {
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

  afterEach((): void => {
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

  it('should show all matchers options', () => {
    const props = {
      matches: {},
      matchers,
      selectedSuggestion: 1,
      keyword: '',
    };

    wrapper = createWrapper({ props });

    expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(matchers.length);
    expect(
      wrapper.find('[data-cy=suggestions] > button:nth-child(2)').classes(),
    ).toContain('highlightedMatcher');
  });

  it('should show unsupported filter message', () => {
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

  it('should show the default-matcher hint instead of "unsupported" when defaultMatcherKey is set', () => {
    wrapper = createWrapper({
      props: {
        matches: {},
        matchers: [],
        keyword: 'plain text search',
        selectedSuggestion: 0,
        defaultMatcherKey: 'notes',
      },
    });

    const hint = wrapper.find('div > div:first-child');
    expect(hint.find('span:first-child').text()).toBe('table_filter.press_enter_to_apply');
    expect(hint.find('span:last-child').text()).toBe('notes=plain text search');
    expect(wrapper.text()).not.toContain('table_filter.unsupported_filter');
  });

  it.each([
    ['foo=bar'],
    ['foo:bar'],
    ['foo!=bar'],
  ])('should still show "unsupported" when defaultMatcherKey is set but keyword has a key separator: %s', (keyword: string) => {
    wrapper = createWrapper({
      props: {
        matches: {},
        matchers: [],
        keyword,
        selectedSuggestion: 0,
        defaultMatcherKey: 'notes',
      },
    });

    expect(wrapper.find('div > div:first-child > span:first-child').text()).toBe('table_filter.unsupported_filter');
    expect(wrapper.text()).not.toContain('table_filter.press_enter_to_apply');
  });

  it('should show suggestions', async () => {
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

  it('should show no suggestion message', async () => {
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

    it('should filter suggestions by substring match when strictMatching is enabled', async () => {
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

    it('should show no suggestions when keyword does not match any item with strictMatching', async () => {
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

    it('should filter by address when typing partial address with strictMatching', async () => {
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

    it('should show all suggestions when keyword is empty with strictMatching', async () => {
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

  describe('suggestionsToShow', () => {
    const sourceMatchers: StringSuggestionMatcher<any>[] = [
      {
        key: 'source',
        description: 'filter by source',
        string: true,
        strictMatching: true,
        suggestionsToShow: -1,
        suggestions: () => ['alchemy', 'coingecko', 'cryptocompare', 'defillama', 'fiat'],
        validate: () => true,
      },
    ];

    it('should show the only matching suggestion when suggestionsToShow is -1', async () => {
      const props = {
        matches: {},
        matchers: sourceMatchers,
        selectedSuggestion: 0,
        keyword: '',
      };

      const wrapper = createWrapper({ props });

      await wrapper.setProps({
        selectedMatcher: sourceMatchers[0],
        keyword: 'source=de',
      });

      await nextTick();

      // Regression: with suggestionsToShow=-1, slice(0, -1) used to drop the last item,
      // leaving zero suggestions when only one matched.
      expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(1);
      expect(wrapper.find('[data-cy=suggestions] > button:first-child').text()).toContain('defillama');
    });

    it('should show all matching suggestions when suggestionsToShow is -1', async () => {
      const props = {
        matches: {},
        matchers: sourceMatchers,
        selectedSuggestion: 0,
        keyword: '',
      };

      const wrapper = createWrapper({ props });

      await wrapper.setProps({
        selectedMatcher: sourceMatchers[0],
        keyword: 'source=c',
      });

      await nextTick();

      // 'coingecko' and 'cryptocompare' both contain 'c' — both should appear, not be sliced.
      expect(wrapper.findAll('[data-cy=suggestions] > button').length).toBeGreaterThanOrEqual(2);
    });

    it('should not drop the last suggestion when suggestionsToShow is -1 without strictMatching', async () => {
      const allValues = ['alpha', 'beta', 'gamma', 'delta', 'epsilon'];
      const nonStrictMatcher: StringSuggestionMatcher<any>[] = [
        {
          key: 'type',
          description: 'filter by type',
          string: true,
          suggestionsToShow: -1,
          suggestions: () => allValues,
          validate: () => true,
        },
      ];

      const wrapper = createWrapper({
        props: {
          matches: {},
          matchers: nonStrictMatcher,
          selectedSuggestion: 0,
          keyword: '',
        },
      });

      await wrapper.setProps({
        selectedMatcher: nonStrictMatcher[0],
        keyword: 'type=',
      });

      await nextTick();

      // Regression: without strictMatching, slice(0, -1) silently dropped the last sorted item.
      // Every option must remain reachable in the dropdown.
      const buttons = wrapper.findAll('[data-cy=suggestions] > button');
      expect(buttons).toHaveLength(allValues.length);
      const renderedValues = buttons.map(b => b.text().replace('type=', '')).sort();
      expect(renderedValues).toEqual([...allValues].sort());
    });
  });
});
