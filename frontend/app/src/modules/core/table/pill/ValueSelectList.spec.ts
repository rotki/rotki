import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import ValueSelectList, { type SelectOption } from '@/modules/core/table/pill/ValueSelectList.vue';

// jsdom gives the scroll container no height, so the real useVirtualList renders zero rows.
// Stub it as a pass-through that yields every item, so behaviour (toggle/search/keys) is testable.
vi.mock('@vueuse/core', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@vueuse/core')>();
  const { computed, ref, toValue } = await import('vue');
  return {
    ...actual,
    useVirtualList: (source: MaybeRefOrGetter<unknown[]>): Record<string, unknown> => ({
      containerProps: { onScroll: (): void => {}, ref: ref(), style: {} },
      list: computed(() => toValue(source).map((data, index) => ({ data, index }))),
      scrollTo: (): void => {},
      wrapperProps: { style: {} },
    }),
  };
});

const options: SelectOption[] = [
  { label: 'Aave', value: 'aave' },
  { label: 'Uniswap', value: 'uniswap' },
  { label: 'Curve', value: 'curve' },
];

function createWrapper(selected: string[], multiple = true, pinned = 0): VueWrapper<InstanceType<typeof ValueSelectList>> {
  return mount(ValueSelectList, {
    props: { emptyText: 'no match', modelValue: selected, multiple, options, pinned, searchPlaceholder: 'Search' },
  });
}

describe('valueSelectList', () => {
  it('should render an option per choice', () => {
    const wrapper = createWrapper([]);
    expect(wrapper.findAll('[data-testid=value-select-option]')).toHaveLength(3);
  });

  it('should add a value on toggle when multiple', async () => {
    const wrapper = createWrapper(['aave']);
    await wrapper.get('[data-testid=value-select-option][data-key=uniswap]').trigger('click');
    expect(wrapper.emitted('update:modelValue')?.[0]).toStrictEqual([['aave', 'uniswap']]);
  });

  it('should remove an already-selected value on toggle', async () => {
    const wrapper = createWrapper(['aave', 'uniswap']);
    await wrapper.get('[data-testid=value-select-option][data-key=aave]').trigger('click');
    expect(wrapper.emitted('update:modelValue')?.[0]).toStrictEqual([['uniswap']]);
  });

  it('should replace the value for a single-select list', async () => {
    const wrapper = createWrapper(['aave'], false);
    await wrapper.get('[data-testid=value-select-option][data-key=curve]').trigger('click');
    expect(wrapper.emitted('update:modelValue')?.[0]).toStrictEqual([['curve']]);
  });

  it('should narrow the list by the search text', async () => {
    const wrapper = createWrapper([]);
    await wrapper.find('input').setValue('uni');
    const shown = wrapper.findAll('[data-testid=value-select-option]');
    expect(shown).toHaveLength(1);
    expect(shown[0].text()).toContain('Uniswap');
  });

  // An address is the case that needs it: the option's keywords come straight from a checksummed
  // value, while the search box lowercases what is typed, so matching had to lowercase both.
  it('should match the search text against keywords regardless of case', async () => {
    const wrapper = mount(ValueSelectList, {
      props: {
        emptyText: 'no match',
        modelValue: [],
        multiple: true,
        options: [
          { keywords: '0xAbCdEf', label: 'My wallet', value: 'My wallet (0xAbCdEf)' },
          { label: 'Uniswap', value: 'uniswap' },
        ],
        searchPlaceholder: 'Search',
      },
    });
    await wrapper.find('input').setValue('0xabcdef');
    const shown = wrapper.findAll('[data-testid=value-select-option]');
    expect(shown).toHaveLength(1);
    expect(shown[0].text()).toContain('My wallet');
  });

  it('should toggle the highlighted option via keyboard', async () => {
    const wrapper = createWrapper([]);
    const input = wrapper.find('input');
    await input.trigger('keydown', { key: 'ArrowDown' }); // 0 -> 1 (Uniswap)
    await input.trigger('keydown', { key: 'Enter' });
    expect(wrapper.emitted('update:modelValue')?.[0]).toStrictEqual([['uniswap']]);
  });

  it('should move the highlight to a hovered option', async () => {
    const wrapper = createWrapper([]);
    const rows = wrapper.findAll('[data-testid="value-select-option"]');
    await rows[2].trigger('mousemove', { clientX: 10, clientY: 10 });
    await wrapper.find('input').trigger('keydown', { key: 'Enter' });
    expect(wrapper.emitted('update:modelValue')?.[0]).toStrictEqual([['curve']]);
  });

  // The list is virtualized and the arrows scroll it, so a row the user never pointed at arrives
  // under a cursor that has not moved. The browser reports that as a mousemove at the same
  // coordinates; obeying it hands the highlight straight back and the arrows cannot advance.
  it('should ignore a row that slid under a still cursor', async () => {
    const wrapper = createWrapper([]);
    const rows = wrapper.findAll('[data-testid="value-select-option"]');
    const input = wrapper.find('input');

    await rows[0].trigger('mousemove', { clientX: 10, clientY: 10 });
    await input.trigger('keydown', { key: 'ArrowDown' }); // 0 -> 1 (Uniswap)
    // Hovering a row the keyboard did NOT move to: hovering row 1 here would agree with the buggy
    // behaviour and the test could not fail.
    await rows[2].trigger('mousemove', { clientX: 10, clientY: 10 });
    await input.trigger('keydown', { key: 'Enter' });

    expect(wrapper.emitted('update:modelValue')?.[0]).toStrictEqual([['uniswap']]);
  });

  it('should hand the highlight back once the pointer genuinely moves', async () => {
    const wrapper = createWrapper([]);
    const rows = wrapper.findAll('[data-testid="value-select-option"]');
    const input = wrapper.find('input');

    await rows[0].trigger('mousemove', { clientX: 10, clientY: 10 });
    await input.trigger('keydown', { key: 'ArrowDown' });
    await rows[2].trigger('mousemove', { clientX: 10, clientY: 40 });
    await input.trigger('keydown', { key: 'Enter' });

    expect(wrapper.emitted('update:modelValue')?.[0]).toStrictEqual([['curve']]);
  });

  // Searching 'a' keeps Aave and Uniswap. With no pinned rows the highlight lands on the first of
  // them, which is the baseline the pinned cases below are contrasted against.
  it('should highlight the first result after a search', async () => {
    const wrapper = createWrapper([]);
    const input = wrapper.find('input');
    await input.setValue('a');
    await input.trigger('keydown', { key: 'Enter' });
    expect(wrapper.emitted('update:modelValue')?.[0]).toStrictEqual([['aave']]);
  });

  // The asset list pins the already-selected asset above the results. Enter after typing has to
  // pick the first *result*; landing on the pinned row would silently un-toggle what the user is
  // already filtering on instead of applying what they searched for.
  it('should highlight past the pinned rows after a search', async () => {
    const wrapper = createWrapper(['aave'], true, 1);
    const input = wrapper.find('input');
    await input.setValue('a');
    await input.trigger('keydown', { key: 'Enter' });
    expect(wrapper.emitted('update:modelValue')?.[0]).toStrictEqual([['aave', 'uniswap']]);
  });

  // Picking a value pins it, which reorders the rows without changing which rows they are. That
  // must not read as a new list: the highlight would jump off the row just picked (search BTC,
  // select BTC, and the list moves to the next row under the cursor).
  it('should keep the highlight when the list is only reordered', async () => {
    const wrapper = createWrapper([], true, 0);
    const input = wrapper.find('input');
    await input.setValue('a');
    // Same three values, reordered as a selection would pin one — and now one row is pinned.
    await wrapper.setProps({
      options: [options[1], options[0], options[2]],
      pinned: 1,
      search: 'a',
    });
    await input.trigger('keydown', { key: 'Enter' });
    // Still on the row it was on, rather than pushed past the newly pinned one.
    expect(wrapper.emitted('update:modelValue')?.[0]).toStrictEqual([['uniswap']]);
  });

  it('should highlight the first row when the pinned rows are all there is', async () => {
    const wrapper = createWrapper(['aave'], true, 5);
    const input = wrapper.find('input');
    await input.setValue('a');
    await input.trigger('keydown', { key: 'Enter' });
    expect(wrapper.emitted('update:modelValue')?.[0]).toStrictEqual([[]]);
  });
  // Escape used to be nobody's job here: the list left dismissal to the surrounding menu, which
  // only closes while its own content has focus, so what Escape did depended on the editor.
  it('should emit close on escape', async () => {
    const wrapper = createWrapper([]);

    await wrapper.get('[data-testid=value-select-search]').trigger('keydown', { key: 'Escape' });

    expect(wrapper.emitted('close')).toHaveLength(1);
  });

  it('should emit close on escape even with nothing left to pick', async () => {
    const wrapper = createWrapper([]);
    await wrapper.get('[data-testid=value-select-search]').setValue('zzz');

    await wrapper.get('[data-testid=value-select-search]').trigger('keydown', { key: 'Escape' });

    expect(wrapper.emitted('close')).toHaveLength(1);
  });

  // An IME confirms its candidate with Enter and walks the candidate list with the arrows, so
  // acting on either would commit a row and close the list mid-word.
  it('should ignore keys while an IME is composing', async () => {
    const wrapper = createWrapper([]);
    const input = wrapper.find('input');

    await input.trigger('keydown', { isComposing: true, key: 'ArrowDown' });
    await input.trigger('keydown', { isComposing: true, key: 'Enter' });

    expect(wrapper.emitted('update:modelValue')).toBeUndefined();

    // And the highlight never moved: committing after composition picks the first row, not the
    // second. Asserting only that nothing was emitted would also pass if the arrow had moved it.
    await input.trigger('keydown', { key: 'Enter' });
    expect(wrapper.emitted('update:modelValue')?.[0]).toStrictEqual([['aave']]);
  });
});
