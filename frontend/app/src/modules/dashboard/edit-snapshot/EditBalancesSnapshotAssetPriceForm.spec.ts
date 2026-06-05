import { bigNumberify } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, ref } from 'vue';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import EditBalancesSnapshotAssetPriceForm from '@/modules/dashboard/edit-snapshot/EditBalancesSnapshotAssetPriceForm.vue';
import TwoFieldsAmountInput from '@/modules/shell/components/inputs/TwoFieldsAmountInput.vue';

// ETH priced at $2000 and €1800 at the timestamp -> historic USD->EUR rate 0.9.
const ETH_USD = 2000;
const ETH_EUR = 1800;

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: vi.fn().mockReturnValue({
    getHistoricPrice: vi.fn(),
  }),
}));

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: vi.fn().mockReturnValue({
    addHistoricalPrice: vi.fn(),
  }),
}));

// Direct USD->EUR forex rate 0.9 (matches ETH's 1800/2000 ratio).
vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: vi.fn(() => ({
    createKey: (fromAsset: string, ts: number): string => `${fromAsset}#${ts}`,
    getHistoricPrice: (): unknown => bigNumberify(0.9),
    getIsPending: (): boolean => false,
    resetHistoricalPricesData: vi.fn(),
  })),
}));

type FormInstance = InstanceType<typeof EditBalancesSnapshotAssetPriceForm>;

describe('edit-snapshot/EditBalancesSnapshotAssetPriceForm.vue', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<FormInstance>;

  const timestamp = 1700000000;

  function setCurrency(symbol: string): void {
    const { findCurrency } = useCurrencies();
    updateGeneralSettings({ mainCurrency: findCurrency(symbol) });
  }

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    vi.mocked(usePriceTaskManager().getHistoricPrice).mockImplementation(
      async ({ toAsset }: { toAsset: string }) => bigNumberify(toAsset === 'USD' ? ETH_USD : ETH_EUR),
    );
    vi.mocked(useAssetPricesApi().addHistoricalPrice).mockResolvedValue(true);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  function createWrapper(amount = '1.5', usdValue = '0'): VueWrapper<FormInstance> {
    const model = ref({ amount, asset: 'ETH', usdValue });
    return mount(EditBalancesSnapshotAssetPriceForm, {
      global: { plugins: [pinia] },
      props: {
        'amount': model.value.amount,
        'asset': model.value.asset,
        timestamp,
        'usdValue': model.value.usdValue,
        'onUpdate:amount': (v: string) => { model.value.amount = v; },
        'onUpdate:asset': (v: string) => { model.value.asset = v; },
        'onUpdate:usdValue': (v: string) => { model.value.usdValue = v; },
      },
    });
  }

  function lastUsdValue(): string | undefined {
    const updates = wrapper.emitted<[string]>('update:usdValue');
    return updates?.at(-1)?.[0];
  }

  it('should keep the fetched USD value on load in a non-USD currency', async () => {
    setCurrency('EUR');
    wrapper = createWrapper();
    await flushPromises();
    await nextTick();

    // fiatValue = 1.5 * 1800 = 2700; usdValue = 2700 / 0.9 = 3000 (consistent)
    expect(lastUsdValue()).toBe('3000');
  });

  it('should back-propagate a fiat value edit to the stored USD value', async () => {
    setCurrency('EUR');
    wrapper = createWrapper();
    await flushPromises();
    await nextTick();

    const twoFields = wrapper.findComponent(TwoFieldsAmountInput);
    // user focuses the value (secondary) field, then types a new fiat value
    twoFields.vm.$emit('update:reversed', true);
    twoFields.vm.$emit('update:secondaryValue', '3600');
    await flushPromises();
    await nextTick();

    // 3600 EUR / 0.9 = 4000 USD
    expect(lastUsdValue()).toBe('4000');
  });

  it('should not touch the historic FX path in a USD main currency', async () => {
    setCurrency('USD');
    wrapper = createWrapper();
    await flushPromises();
    await nextTick();

    // usdValue = amount * asset USD price = 1.5 * 2000
    expect(lastUsdValue()).toBe('3000');
  });
});
