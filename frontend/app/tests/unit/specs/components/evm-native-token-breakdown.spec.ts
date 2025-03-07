import type { useAssetIconApi } from '@/composables/api/assets/icon';
import EvmNativeTokenBreakdown from '@/components/EvmNativeTokenBreakdown.vue';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { libraryDefaults } from '../../utils/provide-defaults';

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

vi.mock('@/composables/api/assets/icon', () => ({
  useAssetIconApi: vi.fn().mockReturnValue({
    checkAsset: vi.fn().mockResolvedValue(404),
    assetImageUrl: vi.fn(),
  } satisfies Partial<ReturnType<typeof useAssetIconApi>>),
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

vi.mock('@/store/balances/manual', async () => {
  const { computed, ref } = await import('vue');
  const { bigNumberify } = await import('@rotki/common');
  return ({
    useManualBalancesStore: vi.fn().mockReturnValue({
      manualBalanceByLocation: ref([]),
      assetBreakdown: vi.fn().mockReturnValue(computed(() => [{
        location: 'external',
        amount: bigNumberify(1000),
        usdValue: bigNumberify(2000),
        address: '',
        tags: null,
      }, {
        location: 'kraken',
        amount: bigNumberify(1000),
        usdValue: bigNumberify(2000),
        address: '',
        tags: null,
      }]),
      ),
      getLocationBreakdown: vi.fn().mockReturnValue(computed(() => ({
        ETH: {
          amount: bigNumberify(1000),
          usdValue: bigNumberify(2000),
        },
      }))),
    }),
  });
});

vi.mock('@/store/balances/exchanges', async () => {
  const { computed } = await import('vue');
  const { bigNumberify } = await import('@rotki/common');
  return ({
    useExchangeBalancesStore: vi.fn().mockReturnValue({
      getBreakdown: vi.fn().mockReturnValue(
        computed(() => [{
          location: 'kraken',
          amount: bigNumberify(1000),
          usdValue: bigNumberify(2000),
          address: '',
          tags: null,
        },
        ]),
      ),
      getLocationBreakdown: vi.fn().mockReturnValue(computed(() => ({
        ETH: {
          amount: bigNumberify(1000),
          usdValue: bigNumberify(2000),
        },
      }))),
      getByLocationBalances: vi.fn(),
    }),
  });
});

vi.mock('@/store/blockchain', async () => {
  const { computed } = await import('vue');
  const { bigNumberify } = await import('@rotki/common');
  return ({
    useBlockchainStore: vi.fn().mockReturnValue({
      assetBreakdown: vi.fn().mockReturnValue(computed(() => [{
        location: 'ethereum',
        address: '0xaddress1',
        amount: bigNumberify(1000),
        usdValue: bigNumberify(2000),
        tags: null,
      }, {
        location: 'ethereum',
        address: '0xaddress2',
        amount: bigNumberify(2000),
        usdValue: bigNumberify(4000),
        tags: null,
      }, {
        location: 'optimism',
        address: '0xaddress3',
        amount: bigNumberify(1000),
        usdValue: bigNumberify(2000),
        tags: null,
      }])),
    }),
  });
});

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
    const expectedResult = [{
      location: 'ethereum',
      amount: bigNumberify(3000),
      usdValue: bigNumberify(6000),
    }, {
      location: 'kraken',
      amount: bigNumberify(2000),
      usdValue: bigNumberify(4000),
    }, {
      location: 'optimism',
      amount: bigNumberify(1000),
      usdValue: bigNumberify(2000),
    }, {
      location: 'external',
      amount: bigNumberify(1000),
      usdValue: bigNumberify(2000),
    }];

    expectedResult.forEach((result, index) => {
      const tr = wrapper.find(`tbody tr:nth-child(${index + 1})`);
      expect(tr.find('td:first-child').text()).toBe(result.location);
      expect(tr.find('td:nth-child(3)').text()).toBe(result.amount.toFormat(2));
      expect(tr.find('td:nth-child(4)').text()).toContain(result.usdValue.toFormat(2));
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
        usdValue: bigNumberify(6000),
      },
      {
        location: 'optimism',
        amount: bigNumberify(1000),
        usdValue: bigNumberify(2000),
      },
    ];

    expectedResult.forEach((result, index) => {
      const tr = wrapper.find(`tbody tr:nth-child(${index + 1})`);
      expect(tr.find('td:first-child').text()).toBe(result.location);
      expect(tr.find('td:nth-child(3)').text()).toBe(result.amount.toFormat(2));
      expect(tr.find('td:nth-child(4)').text()).toContain(result.usdValue.toFormat(2));
    });
  });
});
