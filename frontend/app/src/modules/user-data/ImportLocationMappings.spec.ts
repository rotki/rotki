import type { ImportLocationResolution } from './import-location-types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import ImportLocationMappings from './ImportLocationMappings.vue';
import '@test/i18n';

const unknown: ImportLocationResolution = {
  candidates: [],
  location: null,
  status: 'unresolved',
  value: 'My CSV exchange',
};

const ambiguous: ImportLocationResolution = {
  candidates: ['custom:exchange', 'custom:other'],
  location: null,
  status: 'ambiguous',
  value: 'Exchange',
};

const resolved: ImportLocationResolution = {
  candidates: [],
  location: 'kraken',
  status: 'resolved',
  value: 'Kraken',
};

describe('importLocationMappings', () => {
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    useLocationTreeStore().setNodes([
      node('total', null, 'Total'),
      node('exchanges', 'total', 'Exchanges'),
      node('custom:exchange', 'exchanges', 'My Exchange', { isBuiltin: false }),
      node('custom:other', 'exchanges', 'Other Exchange', { isBuiltin: false }),
      node('custom:archived', 'exchanges', 'Archived Exchange', { isActive: false, isBuiltin: false }),
    ]);
  });

  function createWrapper(locations: ImportLocationResolution[], modelValue: Record<string, string> = {}): VueWrapper<InstanceType<typeof ImportLocationMappings>> {
    return mount(ImportLocationMappings, {
      global: { plugins: [pinia], stubs: { LocationIcon: true } },
      props: { locations, modelValue },
    });
  }

  it('should map the original CSV value without mutating existing mappings', async () => {
    const mappings = { Existing: 'custom:other' };
    const wrapper = createWrapper([unknown], mappings);
    const row = wrapper.get('[data-testid="import-location-mapping"]');

    expect(row.attributes('data-key')).toBe(unknown.value);
    expect(row.findComponent(LocationSelector).attributes('label')).toBe(unknown.value);
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();

    await row.get('input').setValue('custom:exchange');

    expect(wrapper.emitted('update:modelValue')).toEqual([[{
      Existing: 'custom:other',
      [unknown.value]: 'custom:exchange',
    }]]);
    expect(mappings).toEqual({ Existing: 'custom:other' });
  });

  it('should ask only for unresolved and ambiguous values without choosing a candidate automatically', () => {
    const wrapper = createWrapper([resolved, unknown, ambiguous]);
    const rows = wrapper.findAll('[data-testid="import-location-mapping"]');

    expect(rows.map(row => row.attributes('data-key'))).toEqual([unknown.value, ambiguous.value]);
    expect(rows.map(row => row.get<HTMLInputElement>('input').element.value)).toEqual(['', '']);
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });

  it('should hide the mapping section when every location is resolved', () => {
    const wrapper = createWrapper([resolved]);

    expect(wrapper.find('section').exists()).toBe(false);
    expect(wrapper.findComponent(LocationSelector).exists()).toBe(false);
  });

  it('should keep empty CSV values addressable and label their chooser', async () => {
    const wrapper = createWrapper([{ ...unknown, value: '' }]);
    const row = wrapper.get('[data-testid="import-location-mapping"]');

    expect(row.attributes('data-key')).toBe('');
    expect(row.findComponent(LocationSelector).attributes('label')).toBeTruthy();
    await row.get('input').setValue('custom:other');
    expect(wrapper.emitted('update:modelValue')).toEqual([[{ '': 'custom:other' }]]);
  });
});
