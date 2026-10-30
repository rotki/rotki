import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useLocations } from '@/modules/core/common/use-locations';
import '@test/i18n';

describe('useLocations', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    useLocationStore().allLocations = { kraken: { isExchange: true, label: 'Kraken' } };
  });

  it('should look a location up by its identifier', () => {
    const { getExchangeName, getLocationData } = useLocations();

    expect(getLocationData('kraken')).toMatchObject({ identifier: 'kraken', name: 'Kraken' });
    expect(getExchangeName('kraken')).toBe('Kraken');
    expect(getLocationData('nowhere')).toBeUndefined();
    expect(getExchangeName('nowhere')).toBe('');
  });

  it('should follow the location details when they are reloaded', () => {
    const { useLocationData } = useLocations();
    const kraken = useLocationData('kraken');
    expect(get(kraken)?.name).toBe('Kraken');

    useLocationStore().allLocations = { kraken: { isExchange: true, label: 'Kraken Pro' } };

    expect(get(kraken)?.name).toBe('Kraken Pro');
  });
});
