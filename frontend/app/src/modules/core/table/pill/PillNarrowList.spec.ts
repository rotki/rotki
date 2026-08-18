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

  // The footer is the only place the typed syntax is ever stated: nothing else on screen says a
  // date or an amount can be written into the bar at all.
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

  // The footer demonstrates rather than describes: clicking an example is what puts it in the bar,
  // where the row it produces appears directly above it.
  it('should emit the example that was clicked', async () => {
    const wrapper = mount(PillNarrowList, {
      props: { examples: ['after 15/01/2024', '>100'], suggestions },
    });

    await wrapper.findAll('[data-testid=pill-narrow-syntax-chip]')[1].trigger('click');

    expect(wrapper.emitted('example')).toStrictEqual([['>100']]);
  });

  // A chip is an action, so it has to be reachable and announced as one rather than being text
  // that happens to respond to a click.
  it('should render each example as a button', () => {
    const wrapper = mount(PillNarrowList, {
      props: { examples: ['>100'], suggestions },
    });

    const chip = wrapper.find('[data-testid=pill-narrow-syntax-chip]');
    expect(chip.element.tagName).toBe('BUTTON');
    expect(chip.attributes('type')).toBe('button');
  });

  // Being a `button` is what the tag says, not what the user can do: nothing in the popover is ever
  // focused (the caret stays in the bar's input) and the popover is teleported, so Tab never
  // arrives here and a chip was mouse-only. It is reachable because the highlight runs on past the
  // last row into the footer, which means the chip has to carry the id the input points its
  // `aria-activedescendant` at, and be a `menuitem` like the rows in the same `role="menu"`.
  it('should highlight the example the index past the last row names', () => {
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

  // The rows scroll and the footer does not: a hint that scrolls out of sight is one you have to
  // already know about in order to find.
  it('should keep the footer outside the scrolling row area', () => {
    const wrapper = mount(PillNarrowList, {
      props: { examples: ['>100'], suggestions },
    });

    const scroller = wrapper.find('.overflow-y-auto');
    expect(scroller.find('[data-testid=pill-narrow-syntax]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=pill-narrow-syntax]').exists()).toBe(true);
  });
});
