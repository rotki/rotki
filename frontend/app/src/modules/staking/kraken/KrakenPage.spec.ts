import { createTestExchange } from '@test/utils/create-data';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import KrakenPage from '@/modules/staking/kraken/KrakenPage.vue';
import { useKrakenStakingStore } from '@/modules/staking/use-kraken-staking-store';
import '@test/i18n';

const { fetchEvents, refreshPrices } = vi.hoisted(() => ({
  fetchEvents: vi.fn(),
  refreshPrices: vi.fn(),
}));

vi.mock('vue-router', () => ({
  useRouter: (): Record<string, unknown> => ({ push: vi.fn() }),
}));

vi.mock('@/modules/staking/kraken/use-kraken-staking-operations', () => ({
  useKrakenStakingOperations: (): Record<string, unknown> => ({ fetchEvents, updatePagination: vi.fn() }),
}));

vi.mock('@/modules/assets/prices/use-price-refresh', () => ({
  usePriceRefresh: (): Record<string, unknown> => ({ refreshPrices }),
}));

vi.mock('@/modules/premium/use-premium', () => ({
  usePremium: (): unknown => ref<boolean>(true),
}));

vi.mock('@/modules/history/events/use-history-events-section', () => ({
  provideHistoryEventsSection: (): Record<string, unknown> => ({ reload: vi.fn() }),
}));

describe('krakenPage', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof KrakenPage>>;

  function createWrapper(): VueWrapper<InstanceType<typeof KrakenPage>> {
    return mount(KrakenPage, {
      global: {
        plugins: [pinia],
        stubs: {
          KrakenStaking: { template: '<div data-testid="kraken-staking" />' },
          StakingLocationTitle: true,
          TablePageLayout: { template: '<div><slot name="buttons" /><slot /></div>' },
        },
      },
    });
  }

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();
    fetchEvents.mockResolvedValue(undefined);
    refreshPrices.mockResolvedValue(undefined);
    useConnectedExchangesStore().setConnectedExchanges([createTestExchange('kraken', 'Kraken')]);
  });

  it('should show the events with no alert while the read succeeded', async () => {
    wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('[data-testid=kraken-staking]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=kraken-staking-fetch-error]').exists()).toBe(false);
  });

  it('should say why the events could not be read above them, and read again from there', async () => {
    wrapper = createWrapper();
    await flushPromises();
    set(storeToRefs(useKrakenStakingStore()).fetchError, new Error('backend down'));
    await flushPromises();
    fetchEvents.mockClear();

    const alert = wrapper.find('[data-testid=kraken-staking-fetch-error]');
    expect(alert.text()).toContain('backend down');
    expect(wrapper.find('[data-testid=kraken-staking]').exists()).toBe(true);

    await alert.find('[data-testid=failure-strip-retry]').trigger('click');
    await flushPromises();
    expect(fetchEvents).toHaveBeenCalledOnce();
  });
});
