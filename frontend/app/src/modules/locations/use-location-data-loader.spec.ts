import type { ExchangeConnector } from '@/modules/balances/types/exchanges';
import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { flushPromises } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useLocationDataLoader } from '@/modules/locations/use-location-data-loader';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';

const { fetchAllLocations, fetchLocationTree, getSupportedExchanges } = vi.hoisted(() => ({
  fetchAllLocations: vi.fn<() => Promise<{ locations: Record<string, { label?: string }> }>>(),
  fetchLocationTree: vi.fn<() => Promise<LocationNode[]>>(),
  getSupportedExchanges: vi.fn<() => Promise<ExchangeConnector[]>>(),
}));

vi.mock('@/modules/balances/api/use-exchange-api', () => ({
  useExchangeApi: (): Record<string, unknown> => ({ getSupportedExchanges }),
}));

vi.mock('@/modules/history/api/use-history-api', () => ({
  useHistoryApi: (): Record<string, unknown> => ({ fetchAllLocations }),
}));

vi.mock('@/modules/locations/use-location-tree-api', () => ({
  useLocationTreeApi: (): Record<string, unknown> => ({ fetchLocationTree }),
}));
const connector: ExchangeConnector = {
  connector: 'kraken',
  experimental: false,
  isExchangeWithPassphrase: false,
  isExchangeWithoutApiSecret: false,
  location: 'kraken',
};

describe('useLocationDataLoader', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    fetchAllLocations.mockResolvedValue({ locations: { kraken: { label: 'Kraken' } } });
    fetchLocationTree.mockResolvedValue([node('total', null, 'Total'), node('banks', 'total', 'Banks')]);
    getSupportedExchanges.mockResolvedValue([connector]);
  });

  it('should fill the location details and the tree the backend serves', async () => {
    useLocationDataLoader().loadLocations();
    await flushPromises();

    expect(useLocationStore().allLocations).toEqual({ kraken: { label: 'Kraken' } });
    expect(useLocationTreeStore().nodes.map(node => node.identifier)).toEqual(['total', 'banks']);
  });

  it('should fill the exchange connectors', async () => {
    useLocationDataLoader().loadLocations();
    await flushPromises();

    expect(useLocationStore().exchangeConnectors).toEqual([connector]);
  });
});
