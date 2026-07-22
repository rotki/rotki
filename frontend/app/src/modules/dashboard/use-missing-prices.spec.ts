import type { AssetPrices } from '@/modules/assets/prices/price-types';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { useMissingPrices } from '@/modules/dashboard/use-missing-prices';

const assetsHadOraclePrice = vi.fn<(identifiers: string[]) => Promise<Record<string, boolean>>>();

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: (): Record<string, unknown> => ({ assetsHadOraclePrice }),
}));

function missing(): AssetPrices[string] {
  return { isManualPrice: false, oracle: 'blockchain', priceMissing: true, usdPrice: null, value: bigNumberify(0) };
}

describe('useMissingPrices', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    assetsHadOraclePrice.mockReset();
    // Default: every queried asset had an oracle price in the past.
    assetsHadOraclePrice.mockImplementation(async identifiers =>
      Object.fromEntries(identifiers.map(id => [id, true])));
  });

  it('should count only assets that had an oracle price before', async () => {
    assetsHadOraclePrice.mockResolvedValue({ ETH: true, FOO: false });
    useBalancePricesStore().prices = { ETH: missing(), FOO: missing() };

    const { missingPricesCount } = useMissingPrices();
    await flushPromises();

    expect(get(missingPricesCount)).toBe(1);
  });

  it('should exclude ignored assets from the count', async () => {
    useAssetsStore().addIgnoredAsset('ETH');
    useBalancePricesStore().prices = { ETH: missing() };

    const { missingPricesCount } = useMissingPrices();
    await flushPromises();

    expect(get(missingPricesCount)).toBe(0);
    expect(assetsHadOraclePrice).not.toHaveBeenCalled();
  });

  it('should cache results and only query newly seen assets', async () => {
    const store = useBalancePricesStore();
    store.prices = { ETH: missing() };

    const { missingPricesCount } = useMissingPrices();
    await flushPromises();

    expect(assetsHadOraclePrice).toHaveBeenCalledTimes(1);
    expect(assetsHadOraclePrice).toHaveBeenLastCalledWith(['ETH']);

    store.prices = { BTC: missing(), ETH: missing() };
    await flushPromises();

    // ETH is cached, so only BTC is queried the second time.
    expect(assetsHadOraclePrice).toHaveBeenCalledTimes(2);
    expect(assetsHadOraclePrice).toHaveBeenLastCalledWith(['BTC']);
    expect(get(missingPricesCount)).toBe(2);
  });
});
