import { bigNumberify, NoPrice } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import SnapshotDeltaDisplay from '@/modules/dashboard/snapshots/components/SnapshotDeltaDisplay.vue';

const getHistoricPrice = vi.fn();
const getIsPending = vi.fn();

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: vi.fn(() => ({
    createKey: (fromAsset: string, timestamp: number): string => `${fromAsset}#${timestamp}`,
    getHistoricPrice,
    getIsPending,
  })),
}));

describe('modules/dashboard/snapshots/components/SnapshotDeltaDisplay', () => {
  const day1 = 1_600_000_000;
  const day2 = 1_600_086_400;

  let wrapper: VueWrapper<InstanceType<typeof SnapshotDeltaDisplay>>;
  let pinia: ReturnType<typeof createPinia>;

  function createWrapper(props: InstanceType<typeof SnapshotDeltaDisplay>['$props']): VueWrapper<InstanceType<typeof SnapshotDeltaDisplay>> {
    return mount(SnapshotDeltaDisplay, {
      global: {
        plugins: [pinia],
        provide: libraryDefaults,
      },
      props,
    });
  }

  function setCurrency(symbol: string): void {
    const { findCurrency } = useCurrencies();
    updateGeneralSettings({ mainCurrency: findCurrency(symbol) });
  }

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();
    getHistoricPrice.mockReturnValue(NoPrice);
    getIsPending.mockReturnValue(false);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should render a dash for the oldest snapshot (no predecessor)', () => {
    setCurrency('USD');
    wrapper = createWrapper({ timestamp: day1, value: bigNumberify(100) });

    expect(wrapper.text()).toContain('—');
    expect(wrapper.findComponent(FiatDisplay).exists()).toBe(false);
  });

  it('should compute the delta directly when the display currency is USD', () => {
    setCurrency('USD');
    wrapper = createWrapper({
      previousTimestamp: day1,
      previousUsdValue: bigNumberify(90),
      timestamp: day2,
      value: bigNumberify(100),
    });

    // USD needs no historic conversion.
    expect(getHistoricPrice).not.toHaveBeenCalled();
    expect(wrapper.findComponent(FiatDisplay).props('value')?.toNumber()).toBe(10);
  });

  it('should convert each side at its own historic rate for a non-USD currency', () => {
    setCurrency('EUR');
    getHistoricPrice.mockImplementation((_asset: string, ts: number) =>
      ts === day1 ? bigNumberify(0.8) : bigNumberify(0.9));

    wrapper = createWrapper({
      previousTimestamp: day1,
      previousUsdValue: bigNumberify(100),
      timestamp: day2,
      value: bigNumberify(200),
    });

    // (200 * 0.9) - (100 * 0.8) = 180 - 80 = 100
    expect(wrapper.findComponent(FiatDisplay).props('value')?.toNumber()).toBe(100);
  });

  it('should render a skeleton while either historic rate is loading', () => {
    setCurrency('EUR');
    getIsPending.mockImplementation((key: string) => key === `USD#${day2}`);

    wrapper = createWrapper({
      previousTimestamp: day1,
      previousUsdValue: bigNumberify(100),
      timestamp: day2,
      value: bigNumberify(200),
    });

    expect(wrapper.find('.animate-pulse').exists()).toBe(true);
    expect(wrapper.findComponent(FiatDisplay).exists()).toBe(false);
  });

  it('should render a dash when a historic rate is permanently missing', () => {
    setCurrency('EUR');
    getHistoricPrice.mockImplementation((_asset: string, ts: number) =>
      ts === day1 ? bigNumberify(0.8) : NoPrice);

    wrapper = createWrapper({
      previousTimestamp: day1,
      previousUsdValue: bigNumberify(100),
      timestamp: day2,
      value: bigNumberify(200),
    });

    expect(wrapper.text()).toContain('—');
    expect(wrapper.findComponent(FiatDisplay).exists()).toBe(false);
  });
});
