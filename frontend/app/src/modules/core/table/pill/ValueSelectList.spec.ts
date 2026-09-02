import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import ValueSelectList, { type SelectOption } from '@/modules/core/table/pill/ValueSelectList.vue';

vi.mock('@vueuse/core', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@vueuse/core')>();
  const { computed, ref, toValue } = await import('vue');

  /** Renders every row, where the real `useVirtualList` renders none: jsdom gives nothing a height. */
  function renderEveryRow(source: MaybeRefOrGetter<unknown[]>): Record<string, unknown> {
    return {
      containerProps: { onScroll: (): void => {}, ref: ref(), style: {} },
      list: computed(() => toValue(source).map((data, index) => ({ data, index }))),
      scrollTo: (): void => {},
      wrapperProps: { style: {} },
    };
  }

  return { ...actual, useVirtualList: renderEveryRow };
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

  it('should match the search text against keywords regardless of case, since an address keyword stays checksummed while the search box lowercases what is typed', async () => {
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
    await input.trigger('keydown', { key: 'ArrowDown' });
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

  it('should ignore a row that slid under a still cursor, since the arrows scroll the virtualized list and the browser reports the new row as a mousemove at unchanged coordinates', async () => {
    const wrapper = createWrapper([]);
    const rows = wrapper.findAll('[data-testid="value-select-option"]');
    const input = wrapper.find('input');
    const rowTheKeyboardDidNotMoveTo = rows[2];

    await rows[0].trigger('mousemove', { clientX: 10, clientY: 10 });
    await input.trigger('keydown', { key: 'ArrowDown' });
    await rowTheKeyboardDidNotMoveTo.trigger('mousemove', { clientX: 10, clientY: 10 });
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

  it('should highlight the first result after a search', async () => {
    const wrapper = createWrapper([]);
    const input = wrapper.find('input');
    await input.setValue('a');
    await input.trigger('keydown', { key: 'Enter' });
    expect(wrapper.emitted('update:modelValue')?.[0]).toStrictEqual([['aave']]);
  });

  it('should highlight past the pinned rows after a search, so enter applies the search instead of un-toggling the already-selected value pinned above it', async () => {
    const wrapper = createWrapper(['aave'], true, 1);
    const input = wrapper.find('input');
    await input.setValue('a');
    await input.trigger('keydown', { key: 'Enter' });
    expect(wrapper.emitted('update:modelValue')?.[0]).toStrictEqual([['aave', 'uniswap']]);
  });

  it('should keep the highlight when the list is only reordered, since picking a value pins it without changing which rows are on offer', async () => {
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

  it('should ignore keys while an IME is composing, and leave the highlight where it was, since enter confirms a candidate and the arrows walk the candidate list', async () => {
    const wrapper = createWrapper([]);
    const input = wrapper.find('input');

    await input.trigger('keydown', { isComposing: true, key: 'ArrowDown' });
    await input.trigger('keydown', { isComposing: true, key: 'Enter' });

    expect(wrapper.emitted('update:modelValue')).toBeUndefined();

    await input.trigger('keydown', { key: 'Enter' });
    expect(wrapper.emitted('update:modelValue')?.[0]).toStrictEqual([['aave']]);
  });
});
