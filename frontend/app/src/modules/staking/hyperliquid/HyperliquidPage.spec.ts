import type { useHyperliquidStaking } from '@/modules/staking/hyperliquid/use-hyperliquid-staking';
import { Zero } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import HyperliquidPage from '@/modules/staking/hyperliquid/HyperliquidPage.vue';

const { fetchPrices, pageState, refresh } = await vi.hoisted(async () => {
  const { shallowRef } = await import('vue');
  return {
    fetchPrices: vi.fn<(payload: { ignoreCache: boolean; selectedAssets: string[] }) => Promise<void>>(),
    pageState: { error: shallowRef<string>('') },
    refresh: vi.fn<() => Promise<void>>(),
  };
});

vi.mock('@/modules/staking/hyperliquid/use-hyperliquid-staking', async () => {
  const { computed, shallowRef } = await import('vue');
  return {
    useHyperliquidStaking: (): ReturnType<typeof useHyperliquidStaking> => ({
      error: pageState.error,
      loading: shallowRef<boolean>(false),
      refresh,
      rows: computed(() => []),
      total: computed(() => ({ delegated: Zero, pendingWithdrawal: Zero, undelegated: Zero })),
    }),
  };
});

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: (): { fetchPrices: typeof fetchPrices } => ({ fetchPrices }),
}));

const HistoryEventsViewStub = defineComponent({
  name: 'HistoryEventsViewStub',
  props: { restrictions: { default: () => ({}), type: Object } },
  template: '<div />',
});

describe('modules/staking/hyperliquid/HyperliquidPage', () => {
  function mountPage(): VueWrapper {
    return mount(HyperliquidPage, {
      global: {
        stubs: {
          BalanceDisplay: true,
          HistoryEventsView: HistoryEventsViewStub,
          HyperliquidStakingTable: true,
          TablePageLayout: { template: '<div><slot name="buttons" /><slot /></div>' },
        },
      },
    });
  }

  beforeEach(() => {
    vi.clearAllMocks();
    pageState.error.value = '';
  });

  it('should list the staking and delegation events of the core hyperliquid location only', () => {
    const wrapper = mountPage();

    expect(wrapper.findComponent(HistoryEventsViewStub).props('restrictions')).toEqual({
      entryTypes: ['history event'],
      eventTypes: ['staking', 'informational'],
      location: 'hyperliquid',
    });
  });

  it('should load the staking accounts and the HYPE price when opened', async () => {
    mountPage();
    await vi.waitFor(() => expect(refresh).toHaveBeenCalledOnce());

    expect(fetchPrices).toHaveBeenCalledWith({ ignoreCache: false, selectedAssets: ['HYPE'] });
  });

  it('should bypass the price cache when refreshed by the user', async () => {
    const wrapper = mountPage();

    await wrapper.find('[data-testid=hyperliquid-refresh]').trigger('click');

    expect(fetchPrices).toHaveBeenLastCalledWith({ ignoreCache: true, selectedAssets: ['HYPE'] });
  });

  it('should show why the query failed', () => {
    pageState.error.value = 'api down';
    const wrapper = mountPage();

    expect(wrapper.find('[data-testid=hyperliquid-staking-error]').text()).toContain('api down');
  });

  it('should not show an error when the query succeeded', () => {
    const wrapper = mountPage();

    expect(wrapper.find('[data-testid=hyperliquid-staking-error]').exists()).toBe(false);
  });
});
