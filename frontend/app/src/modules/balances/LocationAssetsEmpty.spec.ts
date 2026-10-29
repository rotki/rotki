import { mount, RouterLinkStub, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import LocationAssetsEmpty from '@/modules/balances/LocationAssetsEmpty.vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { ChainType } from '@/modules/core/api/types/chains';
import { useLocationStore } from '@/modules/core/common/use-location-store';

const chainTypes: Record<string, string | undefined> = {
  btc: ChainType.BITCOIN,
  eth: ChainType.EVM,
  unknown_type: undefined,
};

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({
    getChainAccountType: (chain: string): string | undefined => chainTypes[chain],
    matchChain: (location: string): string | undefined => (location in chainTypes ? location : undefined),
  })),
}));

const stubs = {
  RuiButton: { template: '<button data-testid="location-assets-empty-action"><slot /></button>' },
  RuiIcon: true,
  TableEmptyNotice: {
    props: {
      description: { required: true, type: String },
      icon: { required: true, type: String },
      title: { required: true, type: String },
    },
    template: '<div data-testid="notice" :data-icon="icon" :data-title="title" :data-description="description"><slot /></div>',
  },
};

function createWrapper(identifier: string, name: string): VueWrapper<InstanceType<typeof LocationAssetsEmpty>> {
  return mount(LocationAssetsEmpty, { global: { stubs }, props: { identifier, name } });
}

describe('modules/balances/LocationAssetsEmpty', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    const { allLocations } = storeToRefs(useLocationStore());
    set(allLocations, {
      cash: { label: 'Cash' },
      kraken: { isExchange: true, label: 'Kraken' },
    });
    useBankConnectionsStore().setConnections([{
      connector: 'fints',
      displayName: 'FinTS',
      identifier: 'c1',
      location: 'custom:ing',
      name: 'main',
      syncStatus: { authChallenge: null, authExpired: false, lastError: null, lastSyncTs: null, running: false },
    }]);
  });

  it('should name the location in the title', () => {
    const wrapper = createWrapper('kraken', 'Kraken');

    expect(wrapper.find('[data-testid=notice]').attributes('data-title')).toBe('locations.empty.title::Kraken');
  });

  it('should send an EVM chain to the add dialog of the EVM accounts page, on that chain', () => {
    const wrapper = createWrapper('eth', 'Ethereum');

    expect(wrapper.find('[data-testid=notice]').attributes('data-description')).toBe('locations.empty.chain::Ethereum');
    expect(wrapper.find('[data-testid=notice]').attributes('data-icon')).toBe('lu-wallet');
    expect(wrapper.text()).toContain('locations.empty.add_account');
    expect(wrapper.findComponent(RouterLinkStub).props('to')).toEqual({
      name: '/accounts/evm/[[tab]]',
      params: { tab: 'accounts' },
      query: { add: 'true', addressToAdd: [], chainToAdd: 'eth' },
    });
  });

  it('should send another chain to the add dialog of its own accounts page', () => {
    const wrapper = createWrapper('btc', 'Bitcoin');

    expect(wrapper.findComponent(RouterLinkStub).props('to')).toEqual({ path: '/accounts/bitcoin', query: { add: 'true' } });
  });

  it('should treat a chain without an account type as EVM', () => {
    const wrapper = createWrapper('unknown_type', 'Unknown');

    expect(wrapper.findComponent(RouterLinkStub).props('to')).toMatchObject({ name: '/accounts/evm/[[tab]]' });
  });

  it('should send a bank to the bank setup with the bank picked', () => {
    const wrapper = createWrapper('custom:ing', 'ING');

    expect(wrapper.find('[data-testid=notice]').attributes('data-description')).toBe('locations.empty.bank::ING');
    expect(wrapper.find('[data-testid=notice]').attributes('data-icon')).toBe('lu-landmark');
    expect(wrapper.text()).toContain('locations.empty.connect::ING');
    expect(wrapper.findComponent(RouterLinkStub).props('to')).toEqual({ path: '/api-keys/banks', query: { add: 'true', location: 'custom:ing' } });
  });

  it('should send an exchange to the exchange setup with the exchange picked', () => {
    const wrapper = createWrapper('kraken', 'Kraken');

    expect(wrapper.find('[data-testid=notice]').attributes('data-description')).toBe('locations.empty.exchange::Kraken');
    expect(wrapper.findComponent(RouterLinkStub).props('to')).toEqual({ path: '/api-keys/exchanges', query: { add: 'true', location: 'kraken' } });
  });

  it('should send any other location to the manual balance form', () => {
    const wrapper = createWrapper('cash', 'Cash');

    expect(wrapper.find('[data-testid=notice]').attributes('data-description')).toBe('locations.empty.manual::Cash');
    expect(wrapper.text()).toContain('locations.empty.add_manual');
    expect(wrapper.findComponent(RouterLinkStub).props('to')).toEqual({
      name: '/balances/manual/[[tab]]',
      params: { tab: 'assets' },
      query: { add: 'true' },
    });
  });
});
