import type { NarrowSuggestion } from '@/modules/core/table/pill/core/narrowing';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import PillNarrowList from '@/modules/core/table/pill/PillNarrowList.vue';

const field: FieldDef = {
  allowExclusion: false,
  binding: { kind: 'matcher' },
  key: 'protocols',
  label: 'Protocol',
  multiple: true,
  operators: ['is'],
  valueType: 'enum',
};

const suggestions: NarrowSuggestion[] = [
  { field, kind: 'field', label: 'Protocol' },
  { field, kind: 'value', label: 'Aave', value: 'aave' },
  { field, kind: 'value', label: 'Curve', value: 'curve' },
];

function createWrapper(highlighted = 0): VueWrapper<InstanceType<typeof PillNarrowList>> {
  return mount(PillNarrowList, { props: { emptyText: 'no match', highlighted, suggestions } });
}

describe('pillNarrowList', () => {
  // jsdom has no layout and no `scrollIntoView`, so the call itself is what can be asserted.
  const scrollIntoView = vi.fn();

  beforeAll(() => {
    Element.prototype.scrollIntoView = scrollIntoView;
  });

  // The bar owns the highlight and drives it from the input, so nothing else can bring a row that
  // has scrolled out of sight back into view.
  it('should bring the highlighted row into view when the bar moves the highlight', async () => {
    const wrapper = createWrapper();
    scrollIntoView.mockClear();

    await wrapper.setProps({ highlighted: 2 });

    expect(scrollIntoView).toHaveBeenCalledWith({ block: 'nearest' });
  });

  // Hovering moves the highlight too, via the same prop. Scrolling for that pulls the list out
  // from under the cursor, which puts a different row under it and moves the highlight again.
  it('should not scroll when the pointer moves the highlight', async () => {
    const wrapper = createWrapper();
    scrollIntoView.mockClear();

    await wrapper.findAll('button')[2].trigger('mousemove');
    // The bar echoes the emitted index straight back as the prop, which is what would otherwise
    // be indistinguishable from a keyboard move.
    await wrapper.setProps({ highlighted: 2 });

    expect(wrapper.emitted('update:highlighted')?.[0]).toStrictEqual([2]);
    expect(scrollIntoView).not.toHaveBeenCalled();
  });

  // The flag is cleared by the echo, so the next keyboard move still scrolls.
  it('should scroll again on the next keyboard move after a hover', async () => {
    const wrapper = createWrapper();

    await wrapper.findAll('button')[1].trigger('mousemove');
    await wrapper.setProps({ highlighted: 1 });
    scrollIntoView.mockClear();

    await wrapper.setProps({ highlighted: 2 });

    expect(scrollIntoView).toHaveBeenCalledWith({ block: 'nearest' });
  });
});
