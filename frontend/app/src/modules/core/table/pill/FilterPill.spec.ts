import type { ActiveFilter, FieldDef } from '@/modules/core/table/pill/core/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import FilterPill from '@/modules/core/table/pill/FilterPill.vue';

const field: FieldDef = {
  allowExclusion: true,
  binding: { kind: 'matcher' },
  key: 'protocols',
  label: 'Protocol',
  multiple: true,
  operators: ['is', 'is_not'],
  valueType: 'enum',
};

function createWrapper(filter: ActiveFilter, disabled = false): VueWrapper {
  return mount(FilterPill, { props: { disabled, field, filter, removeLabel: 'Remove' } });
}

/**
 * A pill for a field that renders an icon per value — the only kind that collapses to "+N".
 * `PillValueIcon` reads the scramble setting to render an address, so it needs a pinia even for
 * a counterparty.
 */
function createIconWrapper(values: string[]): VueWrapper {
  return mount(FilterPill, {
    global: { plugins: [createCustomPinia()] },
    props: { field: { ...field, display: 'counterparty' }, filter: { fieldKey: 'protocols', op: 'is', values }, removeLabel: 'Remove' },
  });
}

describe('filterPill', () => {
  it('should render the field label and value summary', () => {
    const wrapper = createWrapper({ fieldKey: 'protocols', op: 'is', values: ['aave', 'uniswap'] });
    expect(wrapper.text()).toContain('Protocol');
    expect(wrapper.get('[data-testid=filter-pill-value]').text()).toBe('aave, uniswap');
  });

  it('should hide the operator when it is the default', () => {
    const wrapper = createWrapper({ fieldKey: 'protocols', op: 'is', values: ['aave'] });
    expect(wrapper.text()).not.toContain('is not');
  });

  it('should show a non-default operator', () => {
    const wrapper = createWrapper({ fieldKey: 'protocols', op: 'is_not', values: ['aave'] });
    // Translations are stubbed as their key in unit tests.
    expect(wrapper.text()).toContain('table_filter.operators.is_not');
  });

  // Values past the cap collapse to a "+N" count, so a pill holding many values stays a fixed,
  // scannable width. Only a field that renders value icons collapses; a plain enum shows the
  // summary text instead.
  it('should collapse values past the icon cap', () => {
    const wrapper = createIconWrapper(['aave', 'uniswap', 'curve']);
    expect(wrapper.get('[data-testid=filter-pill-value]').text()).toContain('+1');
  });

  it('should not collapse when the values fit the icon cap', () => {
    const wrapper = createIconWrapper(['aave', 'uniswap']);
    expect(wrapper.get('[data-testid=filter-pill-value]').text()).not.toContain('+');
  });

  // A field with no display kind still renders value icons when it resolves one per value (the
  // event state markers, which are read by their glyph as much as their label).
  it('should render icons for a field that resolves them per value', () => {
    const iconField: FieldDef = {
      ...field,
      resolveIcon: () => ({ color: 'info', icon: 'lu-link' }),
    };
    const wrapper = mount(FilterPill, {
      global: { plugins: [createCustomPinia()] },
      props: { field: iconField, filter: { fieldKey: 'protocols', op: 'is', values: ['aave', 'uniswap', 'curve'] }, removeLabel: 'Remove' },
    });
    expect(wrapper.get('[data-testid=filter-pill-value]').text()).toContain('+1');
  });

  // A field whose values are not all of one kind resolves the kind per value: the data-issues
  // account is an address on a chain and an exchange account name elsewhere, and the exchange's
  // icon comes from its location rather than from the value being filtered on.
  it('should draw a value in its own display kind when the field resolves one', () => {
    const accountField: FieldDef = {
      ...field,
      resolveDisplay: (value: string) => (value.startsWith('0x')
        ? { kind: 'address' as const }
        : { kind: 'location' as const, source: 'kraken' }),
    };
    const wrapper = mount(FilterPill, {
      global: { plugins: [createCustomPinia()] },
      props: { field: accountField, filter: { fieldKey: 'protocols', op: 'is', values: ['Kraken 1'] }, removeLabel: 'Remove' },
    });

    expect(wrapper.findComponent({ name: 'LocationIcon' }).props('item')).toBe('kraken');
    expect(wrapper.findComponent({ name: 'EnsAvatar' }).exists()).toBe(false);
  });

  // The pill could not be reached by keyboard at all: its root is a div with a click handler, so
  // Tab skipped it and an existing filter could not be reopened without a mouse.
  it('should expose the editable region as a button so it can be tabbed to', () => {
    const wrapper = createWrapper({ fieldKey: 'protocols', op: 'is', values: ['aave'] });
    const open = wrapper.get('[data-testid=filter-pill-open]');
    expect(open.element.tagName).toBe('BUTTON');
    expect(open.attributes('disabled')).toBeUndefined();
  });

  // Activating it bubbles to the root, which carries the menu activator, so Enter and Space open
  // the editor exactly as a click does.
  it('should open the editor when the button is activated', async () => {
    const wrapper = createWrapper({ fieldKey: 'protocols', op: 'is', values: ['aave'] });
    await wrapper.get('[data-testid=filter-pill-open]').trigger('click');
    expect(wrapper.emitted('edit')).toHaveLength(1);
  });

  it('should not offer the editable region when disabled', () => {
    const wrapper = createWrapper({ fieldKey: 'protocols', op: 'is', values: ['aave'] }, true);
    expect(wrapper.get('[data-testid=filter-pill-open]').attributes('disabled')).toBeDefined();
  });

  // The remove control is an icon with no text, so it has no accessible name of its own.
  it('should give the remove control an accessible name', () => {
    const wrapper = mount(FilterPill, {
      props: { field, filter: { fieldKey: 'protocols', op: 'is', values: ['aave'] }, removeLabel: 'Remove filter' },
    });
    expect(wrapper.get('[data-testid=filter-pill-remove]').attributes('aria-label')).toBe('Remove filter');
  });

  it('should emit edit when the pill is clicked', async () => {
    const wrapper = createWrapper({ fieldKey: 'protocols', op: 'is', values: ['aave'] });
    await wrapper.get('[data-testid=filter-pill]').trigger('click');
    expect(wrapper.emitted('edit')).toHaveLength(1);
  });
});
