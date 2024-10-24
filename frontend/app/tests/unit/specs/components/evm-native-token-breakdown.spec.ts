import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type ComponentMountingOptions, type VueWrapper, mount } from '@vue/test-utils';
import { computed, ref } from 'vue';
import EvmNativeTokenBreakdown from '@/components/EvmNativeTokenBreakdown.vue';
import { libraryDefaults } from '../../utils/provide-defaults';
import type { AssetBreakdown } from '@/types/blockchain/accounts';
import type { AssetBalances } from '@/types/balances';

vi.mock('vue-router', () => ({
  useRoute: vi.fn(),
  useRouter: vi.fn().mockReturnValue({
    push: vi.fn(),
  }),
  createRouter: vi.fn().mockImplementation(() => ({
    beforeEach: vi.fn(),
  })),
  createWebHashHistory: vi.fn(),
}));

vi.mock('@/composables/locations', () => ({
  useLocations: vi.fn().mockReturnValue({
    locationData: vi.fn().mockImplementation((identifier) => {
      const val = get(identifier);
      return computed(() => ({
        identifier: val,
        name: val,
      }));
    }),
  }),
}));

vi.mock('@/store/balances/manual', () => ({
  useManualBalancesStore: vi.fn().mockReturnValue({
    manualBalanceByLocation: ref([]),
    assetBreakdown: vi.fn().mockReturnValue(
      computed<AssetBreakdown[]>(() => [
        {
          location: 'external',
          amount: bigNumberify(1000),
          value: bigNumberify(2000),
          address: '',
        },
        {
          location: 'kraken',
          amount: bigNumberify(1000),
          value: bigNumberify(2000),
          address: '',
        },
      ]),
    ),
    getLocationBreakdown: vi.fn().mockReturnValue(
      computed<AssetBalances>(() => ({
        ETH: {
          amount: bigNumberify(1000),
          value: bigNumberify(2000),
        },
      })),
    ),
  }),
}));

vi.mock('@/store/balances/exchanges', () => ({
  useExchangeBalancesStore: vi.fn().mockReturnValue({
    getBreakdown: vi.fn().mockReturnValue(
      computed<AssetBreakdown[]>(() => [
        {
          location: 'kraken',
          amount: bigNumberify(1000),
          value: bigNumberify(2000),
          address: '',
        },
      ]),
    ),
    getLocationBreakdown: vi.fn().mockReturnValue(
      computed<AssetBalances>(() => ({
        ETH: {
          amount: bigNumberify(1000),
          value: bigNumberify(2000),
        },
      })),
    ),
    getByLocationBalances: vi.fn(),
  }),
}));

vi.mock('@/store/blockchain/index', () => ({
  useBlockchainStore: vi.fn().mockReturnValue({
    assetBreakdown: vi.fn().mockReturnValue(
      computed<AssetBreakdown[]>(() => [
        {
          location: 'ethereum',
          address: '0xaddress1',
          amount: bigNumberify(1000),
          value: bigNumberify(2000),
        },
        {
          location: 'ethereum',
          address: '0xaddress2',
          amount: bigNumberify(2000),
          value: bigNumberify(4000),
        },
        {
          location: 'optimism',
          address: '0xaddress3',
          amount: bigNumberify(1000),
          value: bigNumberify(2000),
        },
      ]),
    ),
  }),
}));

describe('evmNativeTokenBreakdown.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof EvmNativeTokenBreakdown>>;
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  afterEach(() => {
    wrapper.unmount();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof EvmNativeTokenBreakdown>) =>
    mount(EvmNativeTokenBreakdown, {
      global: {
        plugins: [pinia],
        provide: libraryDefaults,
      },
      ...options,
    });

  it('should show correct entries', async () => {
    wrapper = createWrapper({ props: { identifier: 'ETH', assets: [] } });
    await nextTick();
    const expectedResult = [
      {
        location: 'ethereum',
        amount: bigNumberify(3000),
        value: bigNumberify(6000),
      },
      {
        location: 'kraken',
        amount: bigNumberify(2000),
        value: bigNumberify(4000),
      },
      {
        location: 'optimism',
        amount: bigNumberify(1000),
        value: bigNumberify(2000),
      },
      {
        location: 'external',
        amount: bigNumberify(1000),
        value: bigNumberify(2000),
      },
    ];

    expectedResult.forEach((result, index) => {
      const tr = wrapper.find(`tbody tr:nth-child(${index + 1})`);
      expect(tr.find('td:first-child').text()).toBe(result.location);
      expect(tr.find('td:nth-child(3)').text()).toBe(result.amount.toFormat(2));
      expect(tr.find('td:nth-child(4)').text()).toContain(result.value.toFormat(2));
    });
  });

  it('should show correct entries for blockchainOnly=true', async () => {
    wrapper = createWrapper({
      props: { identifier: 'ETH', blockchainOnly: true, assets: [] },
    });
    await nextTick();
    const expectedResult = [
      {
        location: 'ethereum',
        amount: bigNumberify(3000),
        value: bigNumberify(6000),
      },
      {
        location: 'optimism',
        amount: bigNumberify(1000),
        value: bigNumberify(2000),
      },
    ];

    expectedResult.forEach((result, index) => {
      const tr = wrapper.find(`tbody tr:nth-child(${index + 1})`);
      expect(tr.find('td:first-child').text()).toBe(result.location);
      expect(tr.find('td:nth-child(3)').text()).toBe(result.amount.toFormat(2));
      expect(tr.find('td:nth-child(4)').text()).toContain(result.value.toFormat(2));
    });
  });
});
