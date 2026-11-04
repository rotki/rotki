import type { ImportLocationResolution } from './import-location-types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { nextTick } from 'vue';
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
      global: { plugins: [pinia], stubs: { LocationFormDialog: { name: 'LocationFormDialog', props: ['modelValue'], template: '<div />' }, LocationIcon: true } },
      props: { locations, modelValue, saveAsAliases: true },
    });
  }

  it('should map the original CSV value without mutating existing mappings', async () => {
    const mappings = { Existing: 'custom:other' };
    const wrapper = createWrapper([unknown], mappings);
    const row = wrapper.get('[data-testid="import-location-mapping"]');

    expect(row.attributes('data-key')).toBe(unknown.value);
    expect(row.text()).toContain(unknown.value);
    expect(row.text()).toContain('import_data.location_mapping.unknown');
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();

    await row.get('input').setValue('custom:exchange');

    expect(wrapper.emitted('update:modelValue')).toEqual([[{
      Existing: 'custom:other',
      [unknown.value]: 'custom:exchange',
    }]]);
    expect(mappings).toEqual({ Existing: 'custom:other' });
  });

  it('should leave every value unmapped until the user chooses, without picking a candidate', () => {
    const wrapper = createWrapper([unknown, ambiguous]);
    const rows = wrapper.findAll('[data-testid="import-location-mapping"]');

    expect(rows.map(row => row.attributes('data-key'))).toEqual([unknown.value, ambiguous.value]);
    expect(rows.map(row => row.get<HTMLInputElement>('input').element.value)).toEqual(['', '']);
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });

  it('should keep empty CSV values addressable and label their chooser', async () => {
    const wrapper = createWrapper([{ ...unknown, value: '' }]);
    const row = wrapper.get('[data-testid="import-location-mapping"]');

    expect(row.attributes('data-key')).toBe('');
    expect(row.text()).toContain('import_data.location_mapping.empty_value');
    await row.get('input').setValue('custom:other');
    expect(wrapper.emitted('update:modelValue')).toEqual([[{ '': 'custom:other' }]]);
  });

  it('should offer only the candidates of an ambiguous value, and every location for an unknown one', () => {
    const wrapper = createWrapper([unknown, ambiguous]);
    const [unknownRow, ambiguousRow] = wrapper.findAll('[data-testid="import-location-mapping"]');

    expect(unknownRow?.findComponent(LocationSelector).props('items')).toEqual([]);
    expect(ambiguousRow?.findComponent(LocationSelector).props('items')).toEqual(ambiguous.candidates);
    expect(ambiguousRow?.get('[data-testid="import-location-status"]').text()).toBe('import_data.location_mapping.ambiguous::2');
  });

  it('should choose a location created for a value, and offer it next to an ambiguous value\'s candidates', async () => {
    const wrapper = createWrapper([ambiguous]);
    await wrapper.get('[data-testid="import-location-create"]').trigger('click');
    expect(wrapper.findComponent({ name: 'LocationFormDialog' }).props('modelValue')).toEqual({ mode: 'add', name: 'Exchange', parentIdentifier: '' });

    wrapper.findComponent({ name: 'LocationFormDialog' }).vm.$emit('saved', 'custom:new');
    await nextTick();

    expect(wrapper.emitted('update:modelValue')).toEqual([[{ Exchange: 'custom:new' }]]);
    expect(wrapper.findComponent(LocationSelector).props('items')).toEqual([...ambiguous.candidates, 'custom:new']);
  });

  it('should count the values that have a location chosen', async () => {
    const wrapper = createWrapper([unknown, ambiguous]);
    const progress = (): string => wrapper.get('[data-testid="import-location-progress"]').text();
    expect(progress()).toBe('import_data.location_mapping.progress::0, 2');

    await wrapper.setProps({ modelValue: { [unknown.value]: 'custom:exchange', [ambiguous.value]: '' } });

    expect(progress()).toBe('import_data.location_mapping.progress::1, 2');
  });

  it('should say a location was created for a value only while that location is the one chosen', async () => {
    const wrapper = createWrapper([unknown, ambiguous]);
    const statuses = (): string[] => wrapper.findAll('[data-testid="import-location-status"]').map(status => status.text());
    await wrapper.findAll('[data-testid="import-location-create"]')[0]?.trigger('click');
    wrapper.findComponent({ name: 'LocationFormDialog' }).vm.$emit('saved', 'custom:new');
    await wrapper.setProps({ modelValue: { [unknown.value]: 'custom:new' } });

    expect(statuses()[0]).toBe('import_data.location_mapping.created');
    expect(statuses()[1]).toBe('import_data.location_mapping.ambiguous::2');

    await wrapper.setProps({ modelValue: { [unknown.value]: 'custom:exchange' } });

    expect(statuses()[0]).toBe('import_data.location_mapping.unknown');
  });

  it('should keep an unknown value\'s options when another row is mapped, so its selector does not rebuild them', async () => {
    const wrapper = createWrapper([unknown, ambiguous]);
    const unknownItems = (): unknown => wrapper.findAllComponents(LocationSelector)[0]?.props('items');
    const before = unknownItems();

    await wrapper.setProps({ modelValue: { [ambiguous.value]: 'custom:other' } });

    expect(unknownItems()).toBe(before);
  });

  it('should bind whether the choices are remembered as aliases', async () => {
    const wrapper = createWrapper([unknown]);
    await wrapper.get('[data-testid="import-location-save-aliases"] input').setValue(false);

    expect(wrapper.emitted('update:saveAsAliases')).toEqual([[false]]);
  });
});
