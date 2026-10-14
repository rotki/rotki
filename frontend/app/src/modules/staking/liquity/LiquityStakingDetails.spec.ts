import type { useLiquityStakingDetails } from '@/modules/staking/liquity/use-liquity-staking-details';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import LiquityStakingDetails from '@/modules/staking/liquity/LiquityStakingDetails.vue';

interface DetailsState {
  loading: boolean;
  proxies: Record<string, string[]> | null;
}

const detailsState = vi.hoisted((): DetailsState => ({
  loading: false,
  proxies: null,
}));

const ProxyInfoStub = defineComponent({
  name: 'LiquityProxyInformationStub',
  props: { proxyInformation: { default: undefined, type: Object } },
  template: '<div data-testid="proxy-info" />',
});

const AccountSelectorStub = defineComponent({
  name: 'BlockchainAccountSelectorStub',
  props: { field: { default: undefined, type: Object }, modelValue: { default: () => [], type: Array }, source: { default: undefined, type: Object } },
  template: '<div data-testid="account-selector" />',
});

const HistoryViewStub = defineComponent({
  name: 'HistoryEventsViewStub',
  props: { restrictions: { default: undefined, type: Object }, sectionTitle: { default: '', type: String } },
  template: '<div data-testid="history-view" />',
});

vi.mock('@/modules/staking/liquity/use-liquity-staking-details', async () => {
  const { computed, ref } = await import('vue');
  return {
    useLiquityStakingDetails: (): ReturnType<typeof useLiquityStakingDetails> => ({
      accountFilter: computed(() => [{ address: '0xaaa', chain: 'eth' }]),
      aggregatedStake: computed(() => null),
      aggregatedStakingPool: computed(() => null),
      aggregatedStatistic: computed(() => null),
      availableAddresses: computed(() => ['0xaaa']),
      loading: computed(() => detailsState.loading),
      modelSelectedAccounts: ref([]),
      proxyInformation: computed(() => detailsState.proxies),
    }),
  };
});

describe('modules/staking/liquity/LiquityStakingDetails', () => {
  let wrapper: VueWrapper<InstanceType<typeof LiquityStakingDetails>>;

  function mountComponent(): VueWrapper<InstanceType<typeof LiquityStakingDetails>> {
    return mount(LiquityStakingDetails, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: {
          BlockchainAccountSelector: AccountSelectorStub,
          HistoryEventsView: HistoryViewStub,
          LiquityPools: { props: ['pool'], template: '<div data-testid="pools" />' },
          LiquityProxyInformation: ProxyInfoStub,
          LiquityStake: { props: ['stake'], template: '<div data-testid="stake" />' },
          LiquityStatistics: { props: ['statistic', 'pool'], template: '<div data-testid="statistics" />' },
          TablePageLayout: { props: ['title', 'child'], template: '<div><slot name="buttons" /><slot /></div>' },
        },
      },
      props: { chainName: 'Ethereum', syncingHistory: false },
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    detailsState.loading = false;
    detailsState.proxies = null;
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should ask its parent to refresh, rather than refreshing itself', async () => {
    wrapper = mountComponent();

    await wrapper.find('[data-testid=liquity-refresh]').trigger('click');

    expect(wrapper.emitted('refresh')).toEqual([[]]);
  });

  it('should offer the addresses that hold a position to the account selector', () => {
    wrapper = mountComponent();

    expect(wrapper.findComponent(AccountSelectorStub).props('source')).toMatchObject({
      usableAddresses: ['0xaaa'],
    });
  });

  it('should restrict the events view to liquity on the selected accounts', () => {
    wrapper = mountComponent();

    expect(wrapper.findComponent(HistoryViewStub).props('restrictions')).toMatchObject({
      externalAccounts: [{ address: '0xaaa', chain: 'eth' }],
      protocols: ['liquity'],
    });
  });

  it('should leave a refresh\'s progress to the task dock', () => {
    detailsState.loading = true;

    wrapper = mountComponent();

    expect(wrapper.find('[data-testid=liquity-query-status]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=liquity-refresh]').exists()).toBe(true);
  });

  describe('the proxy section', () => {
    it('should stay hidden with no proxies', () => {
      wrapper = mountComponent();

      expect(wrapper.findComponent(ProxyInfoStub).exists()).toBe(false);
    });

    it('should show the proxies once there are some', () => {
      detailsState.proxies = { '0xaaa': ['0xproxy'] };

      wrapper = mountComponent();

      expect(wrapper.findComponent(ProxyInfoStub).props('proxyInformation')).toEqual({ '0xaaa': ['0xproxy'] });
    });
  });
});
