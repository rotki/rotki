import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useLocations } from '@/modules/core/common/use-locations';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import '@test/i18n';

describe('useLocations', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    useLocationStore().$patch({ allLocations: { kraken: { image: 'kraken.svg', label: 'Kraken' } } });
    useLocationTreeStore().setNodes([
      node('kraken', 'exchanges', 'Kraken'),
      node('custom:ing', 'banks', 'ING', { icon: 'lu-landmark', isBuiltin: false }),
      node('custom:old', 'exchanges', 'My old exchange', { icon: 'lu-rocket', image: 'custom%3Aold_ab12.png', isBuiltin: false }),
    ]);
  });

  it('should describe a built-in location by its packaged details only once', () => {
    const { tradeLocations } = useLocations();
    expect(get(tradeLocations).filter(x => x.identifier === 'kraken')).toHaveLength(1);
    expect(useLocations().getLocationData('kraken')).toMatchObject({ name: 'Kraken' });
  });

  it('should describe a custom location by its tree node, with a listed icon or the default', () => {
    const { getLocationData } = useLocations();
    expect(getLocationData('custom:ing')).toEqual({ icon: 'lu-landmark', identifier: 'custom:ing', image: null, name: 'ING' });
    const old = getLocationData('custom:old');
    expect(old).toMatchObject({ icon: 'lu-map-pin', name: 'My old exchange' });
    expect(old?.image).toMatch(/\/api\/1\/locations\/custom%3Aold\/image\?v=custom%253Aold_ab12\.png$/);
  });

  it('should follow a rename of a custom location', () => {
    const { useLocationData } = useLocations();
    const ing = useLocationData('custom:ing');
    useLocationTreeStore().setNodes([node('custom:ing', 'banks', 'ING DiBa', { isBuiltin: false })]);
    expect(get(ing)?.name).toBe('ING DiBa');
  });
});
