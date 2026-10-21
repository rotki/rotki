import type { useEthStakingAccess } from '@/modules/staking/eth/use-eth-staking-access';
import type { useEthStakingRefresh } from '@/modules/staking/eth/use-eth-staking-refresh';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import EthStakingPage from '@/modules/staking/eth/EthStakingPage.vue';

const { access, refresh } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    access: { allowed: ref<boolean>(true), enabled: ref<boolean>(true) },
    refresh: vi.fn<(userInitiated?: boolean) => Promise<void>>(async () => {}),
  };
});

vi.mock('@/modules/staking/eth/use-eth-staking-access', async () => {
  const { logicAnd } = await import('@vueuse/math');
  const { Module } = await import('@/modules/session/use-module-enabled');
  return {
    useEthStakingAccess: (): ReturnType<typeof useEthStakingAccess> => ({
      allowed: access.allowed,
      available: logicAnd(access.allowed, access.enabled),
      enabled: access.enabled,
      module: Module.ETH2,
    }),
  };
});

vi.mock('@/modules/staking/eth/use-eth-staking-refresh', async () => {
  const { computed, ref } = await import('vue');
  return {
    useEthStakingRefresh: (): ReturnType<typeof useEthStakingRefresh> => ({
      blockProductionLoading: computed<boolean>(() => false),
      lastRefresh: ref<number>(0),
      performanceRefreshing: computed<boolean>(() => false),
      refresh,
      refreshing: computed<boolean>(() => false),
    }),
  };
});

vi.mock('@/modules/staking/eth/use-eth-staking-page-refresh', async () => {
  const { computed } = await import('vue');
  return {
    useEthStakingPageRefresh: vi.fn(() => ({
      chainName: computed<string>(() => 'Ethereum'),
      refreshPage: vi.fn(),
      refreshing: computed<boolean>(() => false),
      syncHistory: vi.fn(),
      syncingHistory: computed<boolean>(() => false),
    })),
  };
});

vi.mock('@/modules/staking/eth/use-eth-staking-performance', async () => {
  const { computed, ref } = await import('vue');
  return {
    useEthStakingPerformance: vi.fn(() => ({
      getPerformance: vi.fn(() => ({ entriesTotal: 0 })),
      performance: computed(() => ({ entriesFound: 0, entriesTotal: 0, sums: {}, validators: [] })),
      performanceLoading: ref<boolean>(false),
      performancePagination: ref({ limit: 10, offset: 0 }),
      refreshPerformance: vi.fn(),
    })),
  };
});

vi.mock('@/modules/staking/eth/use-eth-validator-management', async () => {
  const { ref } = await import('vue');
  return {
    useEthValidatorManagement: vi.fn(() => ({
      fetchValidatorsWithFilter: vi.fn(async () => {}),
      modelFilter: ref({}),
      modelSelection: ref({ accounts: [] }),
      setTotal: vi.fn(),
      total: ref<number>(0),
    })),
  };
});

vi.mock('@/modules/settings/api-keys/external/use-external-api-keys', () => ({
  useExternalApiKeys: vi.fn(() => ({ getApiKey: vi.fn(() => 'key') })),
}));

vi.mock('@/modules/settings/use-setting', async () => {
  const { ref } = await import('vue');
  return {
    useSetting: vi.fn(() => ref<string>('')),
  };
});

vi.mock('@/modules/premium/premium', async () => {
  const { defineComponent } = await import('vue');
  return {
    EthStaking: defineComponent({ name: 'EthStakingStub', template: '<div data-testid="eth-staking" />' }),
  };
});

const PlaceholderStub = defineComponent({
  name: 'EthStakingPagePlaceholderStub',
  template: '<div data-testid="no-premium" />',
});

const ModuleNotActiveStub = defineComponent({
  name: 'ModuleNotActiveStub',
  props: { modules: { default: () => [], type: Array } },
  template: '<div data-testid="module-not-active" />',
});

const HeaderActionsStub = defineComponent({
  name: 'EthStakingHeaderActionsStub',
  template: '<div data-testid="header-actions" />',
});

describe('modules/staking/eth/EthStakingPage', () => {
  async function mountPage(): Promise<VueWrapper<InstanceType<typeof EthStakingPage>>> {
    const wrapper = mount(EthStakingPage, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: {
          AccountFormApiKeyAlert: true,
          EthStakingFilterBar: true,
          EthStakingHeaderActions: HeaderActionsStub,
          EthStakingPagePlaceholder: PlaceholderStub,
          ModuleNotActive: ModuleNotActiveStub,
          StakingLocationTitle: true,
          TablePageLayout: { template: '<div><slot name="title" /><slot name="buttons" /><slot /></div>' },
        },
      },
    });
    await flushPromises();
    return wrapper;
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(access.allowed, true);
    set(access.enabled, true);
  });

  describe('without premium', () => {
    beforeEach(() => {
      set(access.allowed, false);
    });

    it('should not load staking data behind the premium gate, even with the module on', async () => {
      const wrapper = await mountPage();

      expect(wrapper.findComponent(PlaceholderStub).exists()).toBe(true);
      expect(refresh).not.toHaveBeenCalled();
    });

    it('should not offer the refresh actions', async () => {
      const wrapper = await mountPage();

      expect(wrapper.findComponent(HeaderActionsStub).exists()).toBe(false);
    });
  });

  describe('with premium but the module off', () => {
    beforeEach(() => {
      set(access.enabled, false);
    });

    it('should ask for the module and load nothing', async () => {
      const wrapper = await mountPage();

      expect(wrapper.findComponent(ModuleNotActiveStub).exists()).toBe(true);
      expect(refresh).not.toHaveBeenCalled();
    });
  });

  describe('with premium and the module on', () => {
    it('should load the staking data once, as a background refresh', async () => {
      const wrapper = await mountPage();

      expect(wrapper.findComponent(HeaderActionsStub).exists()).toBe(true);
      expect(refresh).toHaveBeenCalledOnce();
      expect(refresh).toHaveBeenCalledWith(false);
    });
  });
});
