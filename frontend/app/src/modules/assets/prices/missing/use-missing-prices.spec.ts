import type { EffectScope } from 'vue';
import type { AssetPrices } from '@/modules/assets/prices/price-types';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useMissingPrices } from '@/modules/assets/prices/missing/use-missing-prices';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';

const assetsHadOraclePrice = vi.fn<(identifiers: string[]) => Promise<Record<string, boolean>>>();

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: (): Record<string, unknown> => ({ assetsHadOraclePrice }),
}));

function missing(): AssetPrices[string] {
  return { isManualPrice: false, oracle: 'blockchain', priceMissing: true, usdPrice: null, value: bigNumberify(0) };
}

let scope: EffectScope | undefined;

/** The shared instance lives as long as its scope, so each case starts from an empty cache. */
function missingPrices(): ReturnType<typeof useMissingPrices> {
  scope = effectScope();
  const result = scope.run(() => useMissingPrices());
  assert(result);
  return result;
}

describe('useMissingPrices', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    assetsHadOraclePrice.mockReset();
    assetsHadOraclePrice.mockImplementation(async identifiers =>
      Object.fromEntries(identifiers.map(id => [id, true])));
  });

  afterEach(() => {
    scope?.stop();
  });

  it('should count only the assets an oracle priced before', async () => {
    assetsHadOraclePrice.mockResolvedValue({ ETH: true, FOO: false });
    useBalancePricesStore().prices = { ETH: missing(), FOO: missing() };

    const { missingPriceIdentifiers, missingPricesCount } = missingPrices();
    await flushPromises();

    expect(get(missingPricesCount)).toBe(1);
    expect(get(missingPriceIdentifiers)).toEqual(['ETH']);
  });

  it('should leave ignored assets out without asking about them', async () => {
    useAssetsStore().addIgnoredAsset('ETH');
    useBalancePricesStore().prices = { ETH: missing() };

    const { missingPricesCount } = missingPrices();
    await flushPromises();

    expect(get(missingPricesCount)).toBe(0);
    expect(assetsHadOraclePrice).not.toHaveBeenCalled();
  });

  it('should ask about each asset once, and only about the newly seen ones', async () => {
    const store = useBalancePricesStore();
    store.prices = { ETH: missing() };

    const { missingPricesCount } = missingPrices();
    await flushPromises();

    expect(assetsHadOraclePrice).toHaveBeenCalledExactlyOnceWith(['ETH']);

    store.prices = { BTC: missing(), ETH: missing() };
    await flushPromises();

    expect(assetsHadOraclePrice).toHaveBeenCalledTimes(2);
    expect(assetsHadOraclePrice).toHaveBeenLastCalledWith(['BTC']);
    expect(get(missingPricesCount)).toBe(2);
  });

  it('should ask again about assets whose request failed, on the next price change', async () => {
    assetsHadOraclePrice.mockRejectedValueOnce(new Error('colibri is starting'));
    const store = useBalancePricesStore();
    store.prices = { ETH: missing() };

    const { missingPricesCount } = missingPrices();
    await flushPromises();
    expect(get(missingPricesCount)).toBe(0);

    store.prices = { BTC: missing(), ETH: missing() };
    await flushPromises();

    expect(assetsHadOraclePrice).toHaveBeenLastCalledWith(['BTC', 'ETH']);
    expect(get(missingPricesCount)).toBe(2);
  });
});
