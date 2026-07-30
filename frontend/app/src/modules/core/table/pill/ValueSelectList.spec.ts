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
    expect(wrapper.findAll('[data-testid^=value-select-option-]')).toHaveLength(3);
  });

  it('should add a value on toggle when multiple', async () => {
    const wrapper = createWrapper(['aave']);
    await wrapper.get('[data-testid=value-select-option-uniswap]').trigger('click');
    expect(wrapper.emitted('update:modelValue')?.[0]).toStrictEqual([['aave', 'uniswap']]);
  });

  it('should remove an already-selected value on toggle', async () => {
    const wrapper = createWrapper(['aave', 'uniswap']);
    await wrapper.get('[data-testid=value-select-option-aave]').trigger('click');
    expect(wrapper.emitted('update:modelValue')?.[0]).toStrictEqual([['uniswap']]);
  });

  it('should replace the value for a single-select list', async () => {
    const wrapper = createWrapper(['aave'], false);
    await wrapper.get('[data-testid=value-select-option-curve]').trigger('click');
    expect(wrapper.emitted('update:modelValue')?.[0]).toStrictEqual([['curve']]);
  });

  it('should narrow the list by the search text', async () => {
    const wrapper = createWrapper([]);
    await wrapper.find('input').setValue('uni');
    const shown = wrapper.findAll('[data-testid^=value-select-option-]');
    expect(shown).toHaveLength(1);
    expect(shown[0].text()).toContain('Uniswap');
  });

  it('should toggle the highlighted option via keyboard', async () => {
    const wrapper = createWrapper([]);
    const input = wrapper.find('input');
    await input.trigger('keydown', { key: 'ArrowDown' }); // 0 -> 1 (Uniswap)
    await input.trigger('keydown', { key: 'Enter' });
    expect(wrapper.emitted('update:modelValue')?.[0]).toStrictEqual([['uniswap']]);
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
});
