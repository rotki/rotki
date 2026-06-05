import { bigNumberify } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import flushPromises from 'flush-promises';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type EffectScope, nextTick, ref, type Ref } from 'vue';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { useSnapshotAssetPrice } from '@/modules/dashboard/snapshots/composables/use-snapshot-asset-price';

// ETH priced at $2000 and €1800 at the timestamp -> historic USD->EUR rate 0.9.
const ETH_USD = 2000;
const ETH_EUR = 1800;

// The direct USD -> display-currency forex rate (the one SnapshotFiatDisplay uses).
const directHistoricPrice = vi.fn();

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: vi.fn().mockReturnValue({ getHistoricPrice: vi.fn() }),
}));

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: vi.fn().mockReturnValue({ addHistoricalPrice: vi.fn() }),
}));

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: vi.fn(() => ({
    createKey: (fromAsset: string, ts: number): string => `${fromAsset}#${ts}`,
    getHistoricPrice: directHistoricPrice,
    getIsPending: (): boolean => false,
    resetHistoricalPricesData: vi.fn(),
  })),
}));

describe('modules/dashboard/snapshots/composables/use-snapshot-asset-price', () => {
  const timestamp = 1700000000;
  let scope: EffectScope;

  function setCurrency(symbol: string): void {
    const { findCurrency } = useCurrencies();
    updateGeneralSettings({ mainCurrency: findCurrency(symbol) });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(usePriceTaskManager().getHistoricPrice).mockImplementation(
      async ({ toAsset }: { toAsset: string }) => bigNumberify(toAsset === 'USD' ? ETH_USD : ETH_EUR),
    );
    vi.mocked(useAssetPricesApi().addHistoricalPrice).mockResolvedValue(true);
    // Direct USD->EUR forex rate 0.9 (matches ETH's 1800/2000 ratio here).
    directHistoricPrice.mockReturnValue(bigNumberify(0.9));
  });

  afterEach(() => {
    scope?.stop();
  });

  async function setup(amountValue = '1.5', usdValueValue = '0'): Promise<{
    amount: Ref<string>;
    api: ReturnType<typeof useSnapshotAssetPrice>;
    asset: Ref<string>;
    usdValue: Ref<string>;
  }> {
    const amount = ref<string>(amountValue);
    const usdValue = ref<string>(usdValueValue);
    const asset = ref<string>('ETH');
    let api!: ReturnType<typeof useSnapshotAssetPrice>;
    scope = effectScope();
    scope.run(() => {
      api = useSnapshotAssetPrice({ amount, asset, timestamp: () => timestamp, usdValue });
    });
    await flushPromises();
    await nextTick();
    return { amount, api, asset, usdValue };
  }

  it('should derive a consistent USD value on load in a non-USD currency', async () => {
    setCurrency('EUR');
    const { usdValue } = await setup();
    // fiatValue = 1.5 * 1800 = 2700; usdValue = 2700 / 0.9 = 3000
    expect(get(usdValue)).toBe('3000');
  });

  it('should back-propagate a fiat value edit to the stored USD value', async () => {
    setCurrency('EUR');
    const { api, usdValue } = await setup();

    set(api.fiatValueFocused, true);
    set(api.fiatValue, '3600');
    await nextTick();

    // 3600 EUR / 0.9 = 4000 USD
    expect(get(usdValue)).toBe('4000');
  });

  it('should derive the USD value from the asset USD price in a USD currency', async () => {
    setCurrency('USD');
    const { api, usdValue } = await setup();
    expect(get(api.isCurrentCurrencyUsd)).toBe(true);
    // usdValue = 1.5 * 2000
    expect(get(usdValue)).toBe('3000');
  });

  it('should store usdValue against the direct forex rate, not the asset price ratio', async () => {
    setCurrency('EUR');
    // EUR-pegged asset: oracle says $1.25 / €1.00 (ratio 0.8), but the forex
    // USD->EUR rate is 1.0 — the divergence that bit aGnoEURe.
    vi.mocked(usePriceTaskManager().getHistoricPrice).mockImplementation(
      async ({ toAsset }: { toAsset: string }) => bigNumberify(toAsset === 'USD' ? 1.25 : 1),
    );
    directHistoricPrice.mockReturnValue(bigNumberify(1));

    const { usdValue } = await setup('1000');

    // fiatValue = 1000 * 1 = 1000 EUR; stored = 1000 / 1.0 (direct) = 1000,
    // NOT 1000 / 0.8 (asset ratio) = 1250.
    expect(get(usdValue)).toBe('1000');
  });

  it('should apply the same direct-rate logic for any non-USD currency (GBP-pegged)', async () => {
    setCurrency('GBP');
    // GBP-pegged asset: oracle $1.25 / £1.00 (ratio 0.8), forex USD->GBP = 1.0.
    vi.mocked(usePriceTaskManager().getHistoricPrice).mockImplementation(
      async ({ toAsset }: { toAsset: string }) => bigNumberify(toAsset === 'USD' ? 1.25 : 1),
    );
    directHistoricPrice.mockReturnValue(bigNumberify(1));

    const { usdValue } = await setup('1000');

    // 1000 GBP / 1.0 (direct) = 1000, not 1000 / 0.8 (ratio) = 1250.
    expect(get(usdValue)).toBe('1000');
  });
});
