import type { ExchangeConnector } from '@/modules/balances/types/exchanges';
import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { DEFAULT_LOCATION_ICON } from '@/modules/locations/location-icons';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';

function connector(name: string, overrides: Partial<ExchangeConnector> = {}): ExchangeConnector {
  return {
    connector: name,
    experimental: false,
    isExchangeWithPassphrase: false,
    isExchangeWithoutApiSecret: false,
    location: name,
    ...overrides,
  };
}

describe('useLocationStore', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
  });

  describe('exchange connectors', () => {
    beforeEach(() => {
      useLocationStore().exchangeConnectors = [
        connector('kraken'),
        connector('coinbaseprime', { isExchangeWithPassphrase: true, location: 'coinbase' }),
        connector('bitpanda', { isExchangeWithoutApiSecret: true }),
        connector('newdex', { experimental: true }),
      ];
    });

    it('should list the connectors, not their locations, as the exchanges a key can be set up for', () => {
      expect(useLocationStore().exchangesWithKey).toEqual(['kraken', 'coinbaseprime', 'bitpanda', 'newdex']);
    });

    it('should split the connectors by what their key needs', () => {
      const store = useLocationStore();
      expect(store.exchangesWithPassphrase).toEqual(['coinbaseprime']);
      expect(store.exchangesWithoutApiSecret).toEqual(['bitpanda']);
      expect(store.experimentalExchanges).toEqual(['newdex']);
    });

    it('should tell an experimental connector by its connector name', () => {
      const store = useLocationStore();
      expect(get(store.useIsExperimentalExchange('newdex'))).toBe(true);
      expect(get(store.useIsExperimentalExchange('kraken'))).toBe(false);
    });
  });

  it('should list only built-in locations flagged as exchanges among all exchanges', () => {
    const store = useLocationStore();
    store.allLocations = {
      external: { icon: 'lu-globe', label: 'External' },
      kraken: { image: 'kraken.svg', isExchange: true, label: 'Kraken' },
    };

    expect(store.allExchanges).toEqual(['kraken']);
  });

  it('should append the custom locations of the tree to the built-in ones, not the built-in tree nodes', () => {
    const store = useLocationStore();
    store.allLocations = { kraken: { image: 'kraken.svg', isExchange: true, label: 'Kraken' } };
    useLocationTreeStore().setNodes([
      node('total', null, 'Total'),
      node('kraken', 'total', 'Kraken'),
      node('custom:desk', 'total', 'Desk', { icon: 'lu-landmark', isBuiltin: false }),
      node('custom:odd', 'total', 'Odd', { icon: 'not-an-icon', isBuiltin: false }),
      node('custom:logo', 'total', 'Logo', { image: 'logo.png', isBuiltin: false }),
    ]);

    const byIdentifier = new Map(store.tradeLocations.map(item => [item.identifier, item]));

    expect([...byIdentifier.keys()]).toEqual(['kraken', 'custom:desk', 'custom:odd', 'custom:logo']);
    expect(byIdentifier.get('custom:desk')).toEqual({ icon: 'lu-landmark', identifier: 'custom:desk', image: null, name: 'Desk' });
    expect(byIdentifier.get('custom:odd')?.icon).toBe(DEFAULT_LOCATION_ICON);
    expect(byIdentifier.get('custom:logo')?.image).toContain('custom%3Alogo/image');
  });
});
