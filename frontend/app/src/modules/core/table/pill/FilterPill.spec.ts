import type { ActiveFilter, FieldDef } from '@/modules/core/table/pill/core/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import FilterPill from '@/modules/core/table/pill/FilterPill.vue';

const field: FieldDef = {
  allowExclusion: true,
  binding: { kind: 'filter' },
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
 * A pill for a field that renders an icon per value, the only kind that collapses to "+N".
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

  it('should collapse values past the icon cap into a "+N" count so the pill keeps a fixed width', () => {
    const wrapper = createIconWrapper(['aave', 'uniswap', 'curve']);
    expect(wrapper.get('[data-testid=filter-pill-value]').text()).toContain('+1');
  });

  it('should not collapse when the values fit the icon cap', () => {
    const wrapper = createIconWrapper(['aave', 'uniswap']);
    expect(wrapper.get('[data-testid=filter-pill-value]').text()).not.toContain('+');
  });

  it('should render icons for a field that has no display kind but resolves one icon per value', () => {
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

  it('should draw a value in the display kind the field resolves for it, so an exchange account gets its location icon and not an address avatar', () => {
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

  it('should expose the editable region as a button so it can be tabbed to', () => {
    const wrapper = createWrapper({ fieldKey: 'protocols', op: 'is', values: ['aave'] });
    const open = wrapper.get('[data-testid=filter-pill-open]');
    expect(open.element.tagName).toBe('BUTTON');
    expect(open.attributes('disabled')).toBeUndefined();
  });

  it('should open the editor when the button is activated, since activation bubbles to the root that carries the menu activator', async () => {
    const wrapper = createWrapper({ fieldKey: 'protocols', op: 'is', values: ['aave'] });
    await wrapper.get('[data-testid=filter-pill-open]').trigger('click');
    expect(wrapper.emitted('edit')).toHaveLength(1);
  });

  it('should not offer the editable region when disabled', () => {
    const wrapper = createWrapper({ fieldKey: 'protocols', op: 'is', values: ['aave'] }, true);
    expect(wrapper.get('[data-testid=filter-pill-open]').attributes('disabled')).toBeDefined();
  });

  it('should give the remove control an accessible name, it being an icon with no text', () => {
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
