import type { StringSuggestionMatcher } from '@/types/filtering';
import { createCustomPinia } from '@test/utils/create-pinia';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import TableFilter from '@/components/table-filter/TableFilter.vue';

describe('table-filter/TableFilter.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof TableFilter>>;

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper.unmount();
    vi.useRealTimers();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof TableFilter> = {}) => {
    const pinia = createCustomPinia();
    setActivePinia(pinia);
    return mount(TableFilter, {
      global: {
        plugins: [pinia],
        stubs: {
          RuiAutoComplete: false,
          Transition: false,
          TransitionGroup: false,
          Teleport: true,
        },
      },
      ...options,
    });
  };

  enum FilterKeys {
    START = 'start',
    TYPE = 'type',
  }

  enum FilterKeyValues {
    START = 'start',
    TYPE = 'type',
  }

  const createMatchers = (startValidate: (value: string) => boolean = () => true, typeSuggestions: string[] = ['type 1', 'type 2', 'type 3']): StringSuggestionMatcher<FilterKeys, FilterKeyValues>[] => [
    {
      key: FilterKeys.START,
      keyValue: FilterKeyValues.START,
      description: 'filter by start date',
      string: true,
      suggestions: () => [],
      validate: startValidate,
    },
    {
      key: FilterKeys.TYPE,
      keyValue: FilterKeyValues.TYPE,
      description: 'filter by type',
      string: true,
      allowExclusion: true,
      multiple: true,
      suggestions: () => typeSuggestions,
      validate: () => true,
    },
  ];

  const matchers = createMatchers();

  it('filter matchers', async () => {
    wrapper = createWrapper({
      props: {
        matchers,
        matches: {},
      },
    });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-id=activator]').trigger('click');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(matchers.length);

    await wrapper.find('input').setValue('ty');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(1);
    expect(wrapper.find('[data-cy=suggestions] > button:first-child').text()).toBe(
      `${matchers[1].key}: ${matchers[1].description}`,
    );

    await wrapper.find('[data-cy=suggestions] > button:first-child').trigger('click');
    await vi.advanceTimersToNextTimerAsync();
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(`${matchers[1].key}=`);
  });

  it('choose suggestions', async () => {
    wrapper = createWrapper({
      props: {
        matchers,
        matches: {},
      },
    });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-id=activator]').trigger('click');
    await vi.advanceTimersToNextTimerAsync();

    // Set matcher to `type`
    await wrapper.find('input').setValue('type');
    await vi.advanceTimersToNextTimerAsync();

    // When no symbol, then we don't show the suggestions yet
    expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(1);

    // Suggestions for `type`
    await wrapper.find('input').setValue('type=');
    await vi.advanceTimersToNextTimerAsync();
    const suggestions = matchers[1].suggestions();
    expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(suggestions.length);

    suggestions.forEach((item, index) => {
      expect(wrapper.find(`[data-cy=suggestions] > button:nth-child(${index + 1})`).text()).toBe(`type=${item}`);
    });

    // Choose first suggestions (type 1)
    await wrapper.find('[data-cy=suggestions] > button:first-child').trigger('click');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-id="activator"] .contents:nth-child(1) > [role=button] > span').text()).toBe('type=type 1');

    expect(wrapper.emitted('update:matches')?.at(-1)).toEqual([{ type: ['type 1'] }]);

    // Choose second suggestion (type 2)
    await wrapper.find('input').setValue('type = type 2');
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-cy=suggestions] > button:first-child').trigger('click');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-id="activator"] .contents:nth-child(2) > [role=button] > span').text()).toBe('type=type 2');

    expect(wrapper.emitted('update:matches')?.at(-1)).toEqual([{ type: ['type 1', 'type 2'] }]);

    // Remove first selected item (type 1)
    await wrapper.find('[data-id="activator"] .contents:nth-child(1) > [role=button] > button').trigger('click');

    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.emitted('update:matches')?.at(-1)).toEqual([{ type: ['type 2'] }]);

    // Click selected item remains (type 2), set it to text field
    await wrapper.find('[data-id="activator"] .contents:nth-child(1) > [role=button]').trigger('click');

    await vi.advanceTimersToNextTimerAsync();

    expect((wrapper.find('input.edit-input').element as HTMLInputElement).value).toBe('');
    expect((wrapper.find('input:not(.edit-input)').element as HTMLInputElement).value).toBe('type=');
  });

  it('choose suggestions with exclusion', async () => {
    wrapper = createWrapper({
      props: {
        matchers,
        matches: {},
      },
    });

    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-id=activator]').trigger('click');
    await vi.advanceTimersToNextTimerAsync();

    // Set matcher to `type`
    await wrapper.find('input').setValue('type !=');
    await vi.advanceTimersToNextTimerAsync();

    // Suggestions for `type`
    const suggestions = matchers[1].suggestions();
    expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(suggestions.length);

    suggestions.forEach((item, index) => {
      expect(wrapper.find(`[data-cy=suggestions] > button:nth-child(${index + 1})`).text()).toBe(`type!=${item}`);
    });

    // Choose first suggestions with exclusion (type 1)
    await wrapper.find('[data-cy=suggestions] > button:first-child').trigger('click');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-id="activator"] .contents:nth-child(1) > [role=button] > span').text()).toBe('type!=type 1');

    expect(wrapper.emitted('update:matches')?.at(-1)).toEqual([{ type: ['!type 1'] }]);
  });

  it('restore selection', async () => {
    wrapper = createWrapper({
      props: {
        matchers,
        matches: {
          type: ['type 1', 'type 2'],
        },
      },
    });

    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-id="activator"] .contents:nth-child(1) > [role=button] > span').text()).toBe('type=type 1');
    expect(wrapper.find('[data-id="activator"] .contents:nth-child(2) > [role=button] > span').text()).toBe('type=type 2');
  });

  it('restore selection with exclusion', async () => {
    wrapper = createWrapper({
      props: {
        matchers,
        matches: {
          type: '!type 1',
        },
      },
    });

    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-id="activator"] .contents:nth-child(1) > [role=button] > span').text()).toBe('type!=type 1');
  });

  it('shakes and keeps search when validation fails', async () => {
    const matchersWithValidation = createMatchers(value => value === 'valid');

    wrapper = createWrapper({
      props: {
        matchers: matchersWithValidation,
        matches: {},
      },
    });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-id=activator]').trigger('click');
    await vi.advanceTimersToNextTimerAsync();

    // Set matcher to `start` with invalid value
    await wrapper.find('input').setValue('start=invalid_value');
    await vi.advanceTimersToNextTimerAsync();

    const autocomplete = wrapper.findComponent({ name: 'RuiAutoComplete' });

    // Press enter to apply the filter
    await wrapper.find('input').trigger('keydown.enter');
    await vi.advanceTimersToNextTimerAsync();

    // The search should be kept because validation failed
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('start=invalid_value');

    // The shake class should be applied (CSS module creates hashed class name containing 'shake')
    expect(autocomplete.classes().some(c => c.includes('shake'))).toBe(true);

    // Advance timers to clear the shake animation (500ms timeout)
    await vi.advanceTimersByTimeAsync(500);

    // The shake class should be removed after timeout
    expect(autocomplete.classes().some(c => c.includes('shake'))).toBe(false);

    // The filter should not contain 'start' because validation failed
    const lastEmit = wrapper.emitted('update:matches')?.at(-1)?.[0] as Record<string, unknown> | undefined;
    expect(lastEmit?.start).toBeUndefined();
  });

  it('applies filter when validation passes', async () => {
    const matchersWithValidation = createMatchers(value => value === 'valid');

    wrapper = createWrapper({
      props: {
        matchers: matchersWithValidation,
        matches: {},
      },
    });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-id=activator]').trigger('click');
    await vi.advanceTimersToNextTimerAsync();

    // Set matcher to `start` with valid value
    await wrapper.find('input').setValue('start=valid');
    await vi.advanceTimersToNextTimerAsync();

    // Press enter to apply the filter
    await wrapper.find('input').trigger('keydown.enter');
    await vi.advanceTimersToNextTimerAsync();

    // The search should be cleared because validation passed
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('');

    // Filter should be emitted
    expect(wrapper.emitted('update:matches')?.at(-1)).toEqual([{ start: 'valid' }]);
  });

  describe('strictMatching', () => {
    const createStrictMatchingMatchers = (): StringSuggestionMatcher<FilterKeys, FilterKeyValues>[] => [
      {
        key: FilterKeys.START,
        keyValue: FilterKeyValues.START,
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

    it('rejects filter when keyword does not match any suggestion with strictMatching', async () => {
      const strictMatchers = createStrictMatchingMatchers();
      wrapper = createWrapper({
        props: {
          matchers: strictMatchers,
          matches: {},
        },
      });
      await vi.advanceTimersToNextTimerAsync();

      await wrapper.find('[data-id=activator]').trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      // Set matcher to `start` with non-matching value
      await wrapper.find('input').setValue('start=nonexistent');
      await vi.advanceTimersToNextTimerAsync();

      const autocomplete = wrapper.findComponent({ name: 'RuiAutoComplete' });

      // Press enter to apply the filter
      await wrapper.find('input').trigger('keydown.enter');
      await vi.advanceTimersToNextTimerAsync();

      // The search should be kept because no matching suggestions exist
      expect((wrapper.find('input').element as HTMLInputElement).value).toBe('start=nonexistent');

      // The shake class should be applied
      expect(autocomplete.classes().some(c => c.includes('shake'))).toBe(true);

      // Advance timers to clear the shake animation
      await vi.advanceTimersByTimeAsync(500);

      // The filter should not be applied - no emission with 'start' key
      const emissions = wrapper.emitted('update:matches') ?? [];
      const hasStartFilter = emissions.some(([matches]) => Object.prototype.hasOwnProperty.call(matches, 'start'));
      expect(hasStartFilter).toBe(false);
    });

    it('applies filter when keyword matches a suggestion with strictMatching', async () => {
      const strictMatchers = createStrictMatchingMatchers();
      wrapper = createWrapper({
        props: {
          matchers: strictMatchers,
          matches: {},
        },
      });
      await vi.advanceTimersToNextTimerAsync();

      await wrapper.find('[data-id=activator]').trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      // Set matcher to `start` and select a suggestion
      await wrapper.find('input').setValue('start=vitalik');
      await vi.advanceTimersToNextTimerAsync();

      // Should show the matching suggestion
      expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(1);

      // Click the suggestion to apply
      await wrapper.find('[data-cy=suggestions] > button:first-child').trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      // The search should be cleared
      expect((wrapper.find('input').element as HTMLInputElement).value).toBe('');

      // Filter should be emitted with the full suggestion value
      expect(wrapper.emitted('update:matches')?.at(-1)).toEqual([
        { start: 'vitalik.eth (0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045)' },
      ]);
    });

    it('filters suggestions using getTextToken normalization with strictMatching', async () => {
      const strictMatchers = createStrictMatchingMatchers();
      wrapper = createWrapper({
        props: {
          matchers: strictMatchers,
          matches: {},
        },
      });
      await vi.advanceTimersToNextTimerAsync();

      await wrapper.find('[data-id=activator]').trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      // Search with different case and special characters stripped
      await wrapper.find('input').setValue('start=D8DA6BF');
      await vi.advanceTimersToNextTimerAsync();

      // Should match the vitalik.eth entry (getTextToken normalizes both)
      expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(1);
      expect(wrapper.find('[data-cy=suggestions] > button:first-child').text()).toContain('vitalik.eth');
    });
  });

  describe('chip grouping', () => {
    it('groups chips when more than 3 items with same key', async () => {
      wrapper = createWrapper({
        props: {
          matchers,
          matches: {
            type: ['type 1', 'type 2', 'type 3', 'type 4', 'type 5'],
          },
        },
      });

      await vi.advanceTimersToNextTimerAsync();

      // Should show the first item with overflow badge
      const firstChip = wrapper.find('[data-id="activator"] .contents:nth-child(1) [role=button]');
      expect(firstChip.exists()).toBe(true);

      // Should show overflow count badge (4+ since first item is shown separately)
      const badge = wrapper.find('[data-id="activator"] .contents:nth-child(1) span.bg-rui-primary');
      expect(badge.exists()).toBe(true);
      expect(badge.text()).toBe('4+');

      // Hidden items should have element [data-testid="hidden-selection-chip"]
      const hiddenItems = wrapper.findAll('[data-id="activator"] .contents > [data-testid=hidden-selection-chip]');
      expect(hiddenItems.length).toBe(4);
    });

    it('does not group chips when 3 or fewer items with same key', async () => {
      wrapper = createWrapper({
        props: {
          matchers,
          matches: {
            type: ['type 1', 'type 2', 'type 3'],
          },
        },
      });

      await vi.advanceTimersToNextTimerAsync();

      // Should show all 3 items as normal chips
      expect(wrapper.find('[data-id="activator"] .contents:nth-child(1) > [role=button] > span').text()).toBe('type=type 1');
      expect(wrapper.find('[data-id="activator"] .contents:nth-child(2) > [role=button] > span').text()).toBe('type=type 2');
      expect(wrapper.find('[data-id="activator"] .contents:nth-child(3) > [role=button] > span').text()).toBe('type=type 3');

      // Should not have overflow badge
      const badge = wrapper.find('[data-id="activator"] span.bg-rui-primary');
      expect(badge.exists()).toBe(false);
    });

    it('opens menu when clicking overflow badge', async () => {
      wrapper = createWrapper({
        props: {
          matchers,
          matches: {
            type: ['type 1', 'type 2', 'type 3', 'type 4'],
          },
        },
      });

      await vi.advanceTimersToNextTimerAsync();

      // Click the overflow badge to open menu
      const badge = wrapper.find('[data-id="activator"] .contents:nth-child(1) span.bg-rui-primary');
      await badge.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      // Menu should be open with all items
      const menuItems = wrapper.findAll('.flex.flex-wrap.gap-1.p-2 [role=button]');
      expect(menuItems.length).toBe(4);
    });

    it('removes all items for key when close button clicked', async () => {
      wrapper = createWrapper({
        props: {
          matchers,
          matches: {
            type: ['type 1', 'type 2', 'type 3', 'type 4'],
          },
        },
      });

      await vi.advanceTimersToNextTimerAsync();

      // Click the close button (remove all)
      const closeButton = wrapper.find('[data-id="activator"] .contents:nth-child(1) [role=button] button[type=button]');
      await closeButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      // Should emit empty matches for type
      expect(wrapper.emitted('update:matches')?.at(-1)).toEqual([{}]);
    });

    it('removes individual item from group menu', async () => {
      wrapper = createWrapper({
        props: {
          matchers,
          matches: {
            type: ['type 1', 'type 2', 'type 3', 'type 4'],
          },
        },
      });

      await vi.advanceTimersToNextTimerAsync();

      // Click the overflow badge to open menu
      const badge = wrapper.find('[data-id="activator"] .contents:nth-child(1) span.bg-rui-primary');
      await badge.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      // Remove the first item from the menu
      const menuItemCloseButton = wrapper.find('.flex.flex-wrap.gap-1.p-2 [role=button] button');
      await menuItemCloseButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      // Should emit matches without the removed item
      expect(wrapper.emitted('update:matches')?.at(-1)).toEqual([{ type: ['type 2', 'type 3', 'type 4'] }]);
    });
  });
});
