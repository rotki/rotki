import type { NarrowSuggestion } from '@/modules/core/table/pill/core/narrowing';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import PillNarrowList from '@/modules/core/table/pill/PillNarrowList.vue';

const field: FieldDef = {
  allowExclusion: false,
  binding: { kind: 'filter' },
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
  const scrollIntoView = vi.fn();

  beforeAll(() => {
    Element.prototype.scrollIntoView = scrollIntoView;
  });

  it('should bring the highlighted row into view when the bar moves the highlight', async () => {
    const wrapper = createWrapper();
    scrollIntoView.mockClear();

    await wrapper.setProps({ highlighted: 2 });

    expect(scrollIntoView).toHaveBeenCalledWith({ block: 'nearest' });
  });

  it('should not scroll when the bar echoes back a highlight the pointer moved, which would pull the list out from under the cursor', async () => {
    const wrapper = createWrapper();
    scrollIntoView.mockClear();

    await wrapper.findAll('button')[2].trigger('mousemove');
    await wrapper.setProps({ highlighted: 2 });

    expect(wrapper.emitted('update:highlighted')?.[0]).toStrictEqual([2]);
    expect(scrollIntoView).not.toHaveBeenCalled();
  });

  it('should scroll again on the next keyboard move after a hover, the echo clearing the flag', async () => {
    const wrapper = createWrapper();

    await wrapper.findAll('button')[1].trigger('mousemove');
    await wrapper.setProps({ highlighted: 1 });
    scrollIntoView.mockClear();

    await wrapper.setProps({ highlighted: 2 });

    expect(scrollIntoView).toHaveBeenCalledWith({ block: 'nearest' });
  });

  it('should show the typeable examples in the footer', () => {
    const wrapper = mount(PillNarrowList, {
      props: {
        examples: ['after 15/01/2024', '>100'],
        examplesLabel: 'Type directly:',
        suggestions,
      },
    });

    const footer = wrapper.find('[data-testid=pill-narrow-syntax]');
    expect(footer.text()).toContain('Type directly:');
    // As `code`, so they read as text to type rather than as a sentence about typing.
    expect(footer.findAll('code').map(chip => chip.text())).toStrictEqual(['after 15/01/2024', '>100']);
  });

  it('should emit the example that was clicked', async () => {
    const wrapper = mount(PillNarrowList, {
      props: { examples: ['after 15/01/2024', '>100'], suggestions },
    });

    await wrapper.findAll('[data-testid=pill-narrow-syntax-chip]')[1].trigger('click');

    expect(wrapper.emitted('example')).toStrictEqual([['>100']]);
  });

  it('should render each example as a button rather than text that happens to respond to a click', () => {
    const wrapper = mount(PillNarrowList, {
      props: { examples: ['>100'], suggestions },
    });

    const chip = wrapper.find('[data-testid=pill-narrow-syntax-chip]');
    expect(chip.element.tagName).toBe('BUTTON');
    expect(chip.attributes('type')).toBe('button');
  });

  it('should name the example the index past the last row points at as a highlighted menuitem, the only way the footer is keyboard-reachable', () => {
    const wrapper = mount(PillNarrowList, {
      props: { examples: ['after 15/01/2024', '>100'], highlighted: suggestions.length + 1, suggestions },
    });

    const chips = wrapper.findAll('[data-testid=pill-narrow-syntax-chip]');
    expect(chips[1].attributes('id')).toBe('pill-narrow-example-1');
    expect(chips[1].attributes('role')).toBe('menuitem');
    expect(chips[1].classes()).toContain('text-rui-primary');
    // And only that one: a highlight in two places names neither.
    expect(chips[0].classes()).not.toContain('text-rui-primary');
    const rowHighlights = wrapper.findAll('[data-testid=pill-narrow-row]')
      .map(row => row.classes().includes('text-rui-primary'));
    expect(rowHighlights).not.toContain(true);
  });

  it('should show no footer when there is nothing typeable to offer', () => {
    expect(createWrapper().find('[data-testid=pill-narrow-syntax]').exists()).toBe(false);
  });

  it('should keep the footer outside the scrolling row area, so the hint cannot scroll out of sight', () => {
    const wrapper = mount(PillNarrowList, {
      props: { examples: ['>100'], suggestions },
    });

    const scroller = wrapper.find('.overflow-y-auto');
    expect(scroller.find('[data-testid=pill-narrow-syntax]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=pill-narrow-syntax]').exists()).toBe(true);
  });
});
