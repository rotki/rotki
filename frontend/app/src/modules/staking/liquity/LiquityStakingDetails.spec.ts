import type { StatsPriceQueryData } from '@/modules/core/messaging/types';
import type { useLiquityStakingDetails } from '@/modules/staking/liquity/use-liquity-staking-details';
import type { ActivitySteps } from '@/modules/task-center/core/types';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import LiquityStakingDetails from '@/modules/staking/liquity/LiquityStakingDetails.vue';

interface DetailsState {
  loading: boolean;
  priceStatus: StatsPriceQueryData | undefined;
  proxies: Record<string, string[]> | null;
  queryStatus: ActivitySteps | undefined;
}

const detailsState = vi.hoisted((): DetailsState => ({
  loading: false,
  priceStatus: undefined,
  proxies: null,
  queryStatus: undefined,
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
      liquityHistoricPriceStatus: computed(() => detailsState.priceStatus),
      loading: computed(() => detailsState.loading),
      modelSelectedAccounts: ref([]),
      proxyInformation: computed(() => detailsState.proxies),
      stakingQueryStatus: computed(() => detailsState.queryStatus),
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
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    detailsState.loading = false;
    detailsState.priceStatus = undefined;
    detailsState.proxies = null;
    detailsState.queryStatus = undefined;
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should ask its parent to refresh, rather than refreshing itself', async () => {
    wrapper = mountComponent();

    await wrapper.find('[data-testid=liquity-refresh]').trigger('click');

    expect(wrapper.emitted('refresh')).toEqual([[true]]);
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

  describe('the proxy section', () => {
    it('should stay hidden with no proxies and nothing loading', () => {
      wrapper = mountComponent();

      expect(wrapper.findComponent(ProxyInfoStub).exists()).toBe(false);
      expect(wrapper.find('[data-testid=liquity-query-status]').exists()).toBe(false);
    });

    it('should show the proxies once there are some', () => {
      detailsState.proxies = { '0xaaa': ['0xproxy'] };

      wrapper = mountComponent();

      expect(wrapper.findComponent(ProxyInfoStub).props('proxyInformation')).toEqual({ '0xaaa': ['0xproxy'] });
    });
  });

  describe('the query progress', () => {
    it('should stay hidden while loading with no progress to report', () => {
      detailsState.loading = true;

      wrapper = mountComponent();

      expect(wrapper.find('[data-testid=liquity-query-status]').exists()).toBe(false);
    });

    it('should show once loading and a staking count is known', () => {
      detailsState.loading = true;
      detailsState.queryStatus = { current: 3, total: 10 };

      wrapper = mountComponent();

      expect(wrapper.find('[data-testid=liquity-query-status]').exists()).toBe(true);
    });

    it('should show for a historic price count alone', () => {
      detailsState.loading = true;
      detailsState.priceStatus = { counterparty: 'liquity', processed: 2, total: 5 };

      wrapper = mountComponent();

      expect(wrapper.find('[data-testid=liquity-query-status]').exists()).toBe(true);
    });

    it('should stay hidden when a count is known but nothing is loading', () => {
      detailsState.queryStatus = { current: 3, total: 10 };

      wrapper = mountComponent();

      expect(wrapper.find('[data-testid=liquity-query-status]').exists()).toBe(false);
    });
  });
});
