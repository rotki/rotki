import { type Pinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import {
  type ThisTypedMountOptions,
  type Wrapper,
  mount
} from '@vue/test-utils';
import { computed, ref } from 'vue';
import { expect } from 'vitest';
import EvmNativeTokenBreakdown from '@/components/EvmNativeTokenBreakdown.vue';

vi.mock('@/composables/locations', () => ({
  useLocations: vi.fn().mockReturnValue({
    locationData: vi.fn().mockImplementation(identifier => {
      const val = get(identifier);
      return computed(() => ({
        identifier: val,
        name: val
      }));
    })
  })
}));

vi.mock('@/store/balances/manual', () => ({
  useManualBalancesStore: vi.fn().mockReturnValue({
    manualBalanceByLocation: ref([]),
    getBreakdown: vi.fn().mockReturnValue(
      computed(() => [
        {
          location: 'external',
          balance: {
            amount: bigNumberify(1000),
            usdValue: bigNumberify(2000)
          },
          address: '',
          tags: null
        },
        {
          location: 'kraken',
          balance: {
            amount: bigNumberify(1000),
            usdValue: bigNumberify(2000)
          },
          address: '',
          tags: null
        }
      ])
    ),
    getLocationBreakdown: vi.fn().mockReturnValue(
      computed(() => ({
        ETH: {
          amount: bigNumberify(1000),
          usdValue: bigNumberify(2000)
        }
      }))
    )
  })
}));

vi.mock('@/store/balances/exchanges', () => ({
  useExchangeBalancesStore: vi.fn().mockReturnValue({
    getBreakdown: vi.fn().mockReturnValue(
      computed(() => [
        {
          location: 'kraken',
          balance: {
            amount: bigNumberify(1000),
            usdValue: bigNumberify(2000)
          },
          address: '',
          tags: null
        }
      ])
    ),
    getLocationBreakdown: vi.fn().mockReturnValue(
      computed(() => ({
        ETH: {
          amount: bigNumberify(1000),
          usdValue: bigNumberify(2000)
        }
      }))
    ),
    getByLocationBalances: vi.fn()
  })
}));

vi.mock('@/composables/blockchain/account-balances/index', () => ({
  useAccountBalances: vi.fn().mockReturnValue({
    getBreakdown: vi.fn().mockReturnValue(
      computed(() => [
        {
          location: 'ethereum',
          address: '0xaddress1',
          balance: {
            amount: bigNumberify(1000),
            usdValue: bigNumberify(2000)
          },
          tags: null
        },
        {
          location: 'ethereum',
          address: '0xaddress2',
          balance: {
            amount: bigNumberify(2000),
            usdValue: bigNumberify(4000)
          },
          tags: null
        },
        {
          location: 'optimism',
          address: '0xaddress3',
          balance: {
            amount: bigNumberify(1000),
            usdValue: bigNumberify(2000)
          },
          tags: null
        }
      ])
    )
  })
}));

describe('EvmNativeTokenBreakdown.vue', () => {
  let wrapper: Wrapper<EvmNativeTokenBreakdown>;
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  const createWrapper = (options: ThisTypedMountOptions<any>) => {
    const vuetify = new Vuetify();
    return mount(EvmNativeTokenBreakdown, {
      pinia,
      vuetify,
      ...options
    });
  };

  test('should show correct entries', () => {
    wrapper = createWrapper({ propsData: { identifier: 'ETH' } });
    const expectedResult = [
      {
        location: 'ethereum',
        balance: { amount: bigNumberify(3000), usdValue: bigNumberify(6000) }
      },
      {
        location: 'kraken',
        balance: { amount: bigNumberify(2000), usdValue: bigNumberify(4000) }
      },
      {
        location: 'optimism',
        balance: { amount: bigNumberify(1000), usdValue: bigNumberify(2000) }
      },
      {
        location: 'external',
        balance: { amount: bigNumberify(1000), usdValue: bigNumberify(2000) }
      }
    ];

    expectedResult.forEach((result, index) => {
      const tr = wrapper.find(`tbody tr:nth-child(${index + 1})`);
      expect(tr.find('td:first-child').text()).toBe(result.location);
      expect(tr.find('td:nth-child(2)').text()).toBe(
        result.balance.amount.toFormat(2)
      );
      expect(tr.find('td:nth-child(3)').text()).toContain(
        result.balance.usdValue.toFormat(2)
      );
    });
  });

  test('should show correct entries for blockchainOnly=true', () => {
    wrapper = createWrapper({
      propsData: { identifier: 'ETH', blockchainOnly: true }
    });
    const expectedResult = [
      {
        location: 'ethereum',
        balance: { amount: bigNumberify(3000), usdValue: bigNumberify(6000) }
      },
      {
        location: 'optimism',
        balance: { amount: bigNumberify(1000), usdValue: bigNumberify(2000) }
      }
    ];

    expectedResult.forEach((result, index) => {
      const tr = wrapper.find(`tbody tr:nth-child(${index + 1})`);
      expect(tr.find('td:first-child').text()).toBe(result.location);
      expect(tr.find('td:nth-child(2)').text()).toBe(
        result.balance.amount.toFormat(2)
      );
      expect(tr.find('td:nth-child(3)').text()).toContain(
        result.balance.usdValue.toFormat(2)
      );
    });
  });
});
