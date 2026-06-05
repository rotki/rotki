import { bigNumberify } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type EffectScope, nextTick, ref, type Ref } from 'vue';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { BalanceType } from '@/modules/balances/types/balances';
import { BalanceSnapshot, LocationDataSnapshot } from '@/modules/dashboard/snapshots';
import { useSnapshotTotalInput } from '@/modules/dashboard/snapshots/composables/use-snapshot-total-input';

const getHistoricPrice = vi.fn();
const getIsPending = vi.fn();

// USD -> EUR historic rate of 0.9 at the snapshot timestamp.
vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: vi.fn(() => ({
    createKey: (fromAsset: string, timestamp: number): string => `${fromAsset}#${timestamp}`,
    getHistoricPrice,
    getIsPending,
  })),
}));

function balance(usdValue: string, category: BalanceType = BalanceType.ASSET, assetIdentifier = 'ETH'): BalanceSnapshot {
  return BalanceSnapshot.parse({ amount: '1', assetIdentifier, category, timestamp: 1700000000, usdValue });
}

function location(loc: string, usdValue: string): LocationDataSnapshot {
  return LocationDataSnapshot.parse({ location: loc, timestamp: 1700000000, usdValue });
}

describe('modules/dashboard/snapshots/composables/use-snapshot-total-input', () => {
  const timestamp = 1700000000;
  let scope: EffectScope;

  function setCurrency(symbol: string): void {
    const { findCurrency } = useCurrencies();
    updateGeneralSettings({ mainCurrency: findCurrency(symbol) });
  }

  function setup(modelValue: Ref<LocationDataSnapshot[]>, balances: BalanceSnapshot[] = []): ReturnType<typeof useSnapshotTotalInput> {
    let api!: ReturnType<typeof useSnapshotTotalInput>;
    scope = effectScope();
    scope.run(() => {
      api = useSnapshotTotalInput({ balancesSnapshot: () => balances, modelValue, timestamp: () => timestamp });
    });
    return api;
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    getHistoricPrice.mockReturnValue(bigNumberify(0.9));
    getIsPending.mockReturnValue(false);
  });

  afterEach(() => {
    scope?.stop();
  });

  it('should seed the field from the stored USD total at the historic rate', () => {
    setCurrency('EUR');
    const model = ref([location('total', '1000')]);
    const { total } = setup(model);
    // 1000 USD * 0.9 = 900 EUR
    expect(get(total)).toBe('900');
  });

  it('should convert the entered fiat total back to USD in numericTotal', () => {
    setCurrency('EUR');
    const model = ref([location('total', '0')]);
    const { numericTotal, total } = setup(model);
    set(total, '900');
    // 900 EUR / 0.9 = 1000 USD
    expect(get(numericTotal).toNumber()).toBe(1000);
  });

  it('should treat the entered total as USD in a USD currency', () => {
    setCurrency('USD');
    const model = ref([location('total', '0')]);
    const { numericTotal, total } = setup(model);
    set(total, '1000');
    expect(get(numericTotal).toNumber()).toBe(1000);
  });

  it('should seed the field from a USD value via setTotal', () => {
    setCurrency('EUR');
    const model = ref([location('total', '0')]);
    const { setTotal, total } = setup(model);
    setTotal(bigNumberify(1000));
    expect(get(total)).toBe('900');
  });

  it('should persist numericTotal into the total row via applyTotal', async () => {
    setCurrency('EUR');
    const model = ref([location('blockchain', '700'), location('total', '0')]);
    const { applyTotal, total } = setup(model);
    set(total, '900');
    await nextTick();
    applyTotal();
    const totalRow = get(model).find(item => item.location === 'total');
    expect(totalRow?.usdValue.toNumber()).toBe(1000);
  });

  it('should suggest a single total when asset and location totals agree', () => {
    setCurrency('USD');
    const model = ref([location('blockchain', '100'), location('total', '100')]);
    const { suggestions } = setup(model, [balance('100')]);
    expect(get(suggestions)).toEqual({ total: expect.anything() });
    expect(get(suggestions).total?.toNumber()).toBe(100);
  });

  it('should suggest asset and location separately when they disagree (USD)', () => {
    setCurrency('USD');
    const model = ref([location('blockchain', '70'), location('total', '70')]);
    const { suggestions } = setup(model, [balance('100')]);
    expect(get(suggestions).asset?.toNumber()).toBe(100);
    expect(get(suggestions).location?.toNumber()).toBe(70);
  });
});
