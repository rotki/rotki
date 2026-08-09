import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import PillMenu from '@/modules/core/table/pill/PillMenu.vue';

function field(key: string, label: string): FieldDef {
  return {
    allowExclusion: false,
    binding: { kind: 'filter' },
    key,
    label,
    multiple: true,
    operators: ['is'],
    valueType: 'enum',
  };
}

const fields = [field('protocols', 'Protocol'), field('assets', 'Asset'), field('location', 'Location')];

function createWrapper(): VueWrapper<InstanceType<typeof PillMenu>> {
  return mount(PillMenu, { props: { emptyText: 'no match', fields, searchPlaceholder: 'Search' } });
}

describe('pillMenu', () => {
  // jsdom has no layout and no `scrollIntoView`, so the call itself is what can be asserted.
  const scrollIntoView = vi.fn();

  beforeAll(() => {
    Element.prototype.scrollIntoView = scrollIntoView;
  });

  it('should list every field by default', () => {
    const wrapper = createWrapper();
    expect(wrapper.findAll('[data-testid^=pill-menu-field-]')).toHaveLength(3);
  });

  it('should emit the picked field', async () => {
    const wrapper = createWrapper();
    await wrapper.get('[data-testid=pill-menu-field-assets]').trigger('click');
    expect(wrapper.emitted('select')?.[0]?.[0]).toMatchObject({ key: 'assets' });
  });

  it('should narrow the list by the search text', async () => {
    const wrapper = createWrapper();
    await wrapper.find('input').setValue('loc');
    const shown = wrapper.findAll('[data-testid^=pill-menu-field-]');
    expect(shown).toHaveLength(1);
    expect(shown[0].text()).toBe('Location');
  });

  it('should show the empty text when nothing matches', async () => {
    const wrapper = createWrapper();
    await wrapper.find('input').setValue('zzz');
    expect(wrapper.get('[data-testid=pill-menu-empty]').text()).toBe('no match');
  });

  it('should move the highlight with arrow keys and pick it with enter', async () => {
    const wrapper = createWrapper();
    const input = wrapper.find('input');
    await input.trigger('keydown', { key: 'ArrowDown' }); // 0 -> 1 (Asset)
    await input.trigger('keydown', { key: 'ArrowDown' }); // 1 -> 2 (Location)
    await input.trigger('keydown', { key: 'Enter' });
    expect(wrapper.emitted('select')?.[0]?.[0]).toMatchObject({ key: 'location' });
  });

  it('should wrap the highlight from the first item upward', async () => {
    const wrapper = createWrapper();
    const input = wrapper.find('input');
    await input.trigger('keydown', { key: 'ArrowUp' }); // 0 -> last (Location)
    await input.trigger('keydown', { key: 'Enter' });
    expect(wrapper.emitted('select')?.[0]?.[0]).toMatchObject({ key: 'location' });
  });
  // The list scrolls past its height (history has 15 fields) and the arrow keys live on the search
  // box, so nothing else can pull the highlighted row back into view: it used to walk off the
  // bottom while the list stayed put, leaving the user arrowing through rows they could not see.
  it('should bring the highlighted row into view as the arrows move it', async () => {
    const wrapper = createWrapper();
    scrollIntoView.mockClear();

    await wrapper.find('input').trigger('keydown', { key: 'ArrowDown' });

    expect(scrollIntoView).toHaveBeenCalledWith({ block: 'nearest' });
  });

  // Hovering moves the highlight as well. Scrolling for that pulls the list out from under the
  // cursor, which puts a different row under it and moves the highlight again.
  it('should not scroll when the pointer moves the highlight', async () => {
    const wrapper = createWrapper();
    scrollIntoView.mockClear();

    await wrapper.findAll('[data-testid^=pill-menu-field-]')[2].trigger('mousemove');

    expect(scrollIntoView).not.toHaveBeenCalled();
  });
});
