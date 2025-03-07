import type { StringSuggestionMatcher } from '@/types/filtering';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { setActivePinia } from 'pinia';
import { afterEach, describe, expect, it } from 'vitest';
import { createCustomPinia } from '../../../utils/create-pinia';

describe('table-filter/TableFilter.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof TableFilter>>;
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

  const matchers: StringSuggestionMatcher<FilterKeys, FilterKeyValues>[] = [
    {
      key: FilterKeys.START,
      keyValue: FilterKeyValues.START,
      description: 'filter by start date',
      string: true,
      suggestions: () => [],
      validate: () => true,
    },
    {
      key: FilterKeys.TYPE,
      keyValue: FilterKeyValues.TYPE,
      description: 'filter by type',
      string: true,
      allowExclusion: true,
      multiple: true,
      suggestions: () => ['type 1', 'type 2', 'type 3'],
      validate: () => true,
    },
  ];

  afterEach(() => {
    wrapper.unmount();
  });

  it('filter matchers', async () => {
    wrapper = createWrapper({
      props: {
        matchers,
        matches: {},
      },
    });
    await nextTick();
    await flushPromises();

    await wrapper.find('[data-id=activator]').trigger('click');
    await nextTick();
    await flushPromises();

    expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(matchers.length);

    await wrapper.find('input').setValue('ty');
    await nextTick();
    await flushPromises();

    expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(1);
    expect(wrapper.find('[data-cy=suggestions] > button:first-child').text()).toBe(
      `${matchers[1].key}: ${matchers[1].description}`,
    );

    await wrapper.find('[data-cy=suggestions] > button:first-child').trigger('click');
    await nextTick();
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(`${matchers[1].key}=`);
  });

  it('choose suggestions', async () => {
    wrapper = createWrapper({
      props: {
        matchers,
        matches: {},
      },
    });
    await nextTick();
    await flushPromises();

    await wrapper.find('[data-id=activator]').trigger('click');
    await nextTick();
    await flushPromises();

    // Set matcher to `type`
    await wrapper.find('input').setValue('type');
    await nextTick();

    // When no symbol, then we don't show the suggestions yet
    expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(1);

    // Suggestions for `type`
    await wrapper.find('input').setValue('type=');
    await nextTick();
    const suggestions = matchers[1].suggestions();
    expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(suggestions.length);

    suggestions.forEach((item, index) => {
      expect(wrapper.find(`[data-cy=suggestions] > button:nth-child(${index + 1})`).text()).toBe(`type=${item}`);
    });

    // Choose first suggestions (type 1)
    await wrapper.find('[data-cy=suggestions] > button:first-child').trigger('click');
    await nextTick();

    expect(wrapper.find('[data-id="activator"] .flex:nth-child(1) > [role=button]> span').text()).toBe('type=type 1');

    expect(wrapper.emitted('update:matches')?.at(-1)).toEqual([{ type: ['type 1'] }]);

    // Choose second suggestion (type 2)
    await wrapper.find('input').setValue('type = type 2');
    await nextTick();

    await wrapper.find('[data-cy=suggestions] > button:first-child').trigger('click');
    await nextTick();

    expect(wrapper.find('[data-id="activator"] .flex:nth-child(2) > [role=button] > span').text()).toBe('type=type 2');

    expect(wrapper.emitted('update:matches')?.at(-1)).toEqual([{ type: ['type 1', 'type 2'] }]);

    // Remove first selected item (type 1)
    await wrapper.find('[data-id="activator"] .flex:nth-child(1) > [role=button] > button').trigger('click');

    await nextTick();

    expect(wrapper.emitted('update:matches')?.at(-1)).toEqual([{ type: ['type 2'] }]);

    // Click selected item remains (type 2), set it to text field
    await wrapper.find('[data-id="activator"] .flex:nth-child(1) > [role=button]').trigger('click');

    await nextTick();

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

    await nextTick();
    await flushPromises();

    await wrapper.find('[data-id=activator]').trigger('click');
    await nextTick();
    await flushPromises();

    // Set matcher to `type`
    await wrapper.find('input').setValue('type !=');
    await nextTick();

    // Suggestions for `type`
    const suggestions = matchers[1].suggestions();
    expect(wrapper.findAll('[data-cy=suggestions] > button')).toHaveLength(suggestions.length);

    suggestions.forEach((item, index) => {
      expect(wrapper.find(`[data-cy=suggestions] > button:nth-child(${index + 1})`).text()).toBe(`type!=${item}`);
    });

    // Choose first suggestions with exclusion (type 1)
    await wrapper.find('[data-cy=suggestions] > button:first-child').trigger('click');
    await nextTick();

    expect(wrapper.find('[data-id="activator"] .flex:nth-child(1) > [role=button] > span').text()).toBe('type!=type 1');

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

    await nextTick();
    await flushPromises();

    expect(wrapper.find('[data-id="activator"] .flex:nth-child(1) > [role=button] > span').text()).toBe('type=type 1');
    expect(wrapper.find('[data-id="activator"] .flex:nth-child(2) > [role=button] > span').text()).toBe('type=type 2');
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

    await nextTick();
    await flushPromises();

    expect(wrapper.find('[data-id="activator"] .flex:nth-child(1) > [role=button] > span').text()).toBe('type!=type 1');
  });
});
