import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import StakingPageLayout from '@/modules/staking/components/StakingPageLayout.vue';

const fetchPrices = vi.hoisted(() => vi.fn<(payload: { ignoreCache: boolean; selectedAssets: string[] }) => Promise<void>>());
const syncHistory = vi.hoisted(() => vi.fn<() => Promise<void>>());
const syncChain = vi.hoisted(() => ({ current: '' }));

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: (): { fetchPrices: typeof fetchPrices } => ({ fetchPrices }),
}));

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: (): Record<string, unknown> => ({
    getAddressName: (address: string): string | undefined => (address === '0xBad' ? 'bad staker' : undefined),
  }),
}));

vi.mock('@/modules/staking/use-staking-history-sync', async () => {
  const { computed } = await import('vue');
  return {
    useStakingHistorySync: (_reload: () => void, chain: string): Record<string, unknown> => {
      syncChain.current = chain;
      return {
        chainName: computed(() => 'Hyperliquid'),
        syncHistory,
        syncingHistory: computed(() => false),
      };
    },
  };
});

const HistoryEventsViewStub = defineComponent({
  name: 'HistoryEventsViewStub',
  props: { restrictions: { default: () => ({}), type: Object }, sectionTitle: { default: '', type: String } },
  template: '<div />',
});

describe('modules/staking/components/StakingPageLayout', () => {
  const refresh = vi.fn<() => Promise<void>>();

  function mountLayout(failedAddresses: string[] = []): VueWrapper {
    return mount(StakingPageLayout, {
      global: {
        stubs: {
          HistoryEventsView: HistoryEventsViewStub,
          RuiMenu: { template: '<div><slot name="activator" :attrs="{}" /><slot /></div>' },
          TablePageLayout: { template: '<div><slot name="buttons" /><slot /></div>' },
        },
      },
      props: {
        asset: 'HYPE',
        chain: 'hyperliquid',
        failedAddresses,
        loading: false,
        refresh,
        location: 'hyperliquid',
        restrictions: { location: 'hyperliquid' },
      },
      slots: { default: '<p data-testid="slot-content" />' },
    });
  }

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should refresh the positions and fetch the asset price using the cache when opened', async () => {
    mountLayout();
    await vi.waitFor(() => expect(refresh).toHaveBeenCalledOnce());

    expect(fetchPrices).toHaveBeenCalledWith({ ignoreCache: false, selectedAssets: ['HYPE'] });
  });

  it('should bypass the price cache when refreshed by the user', async () => {
    const wrapper = mountLayout();

    await wrapper.find('[data-testid=staking-refresh]').trigger('click');

    expect(fetchPrices).toHaveBeenLastCalledWith({ ignoreCache: true, selectedAssets: ['HYPE'] });
  });

  it('should offer the history sync of its own chain', async () => {
    const wrapper = mountLayout();

    await wrapper.find('[data-testid=staking-sync-history]').trigger('click');

    expect(syncChain.current).toBe('hyperliquid');
    expect(syncHistory).toHaveBeenCalledOnce();
  });

  it('should name the addresses that could not be loaded as the tables do', () => {
    const wrapper = mountLayout(['0xBad', '0xWorse']);

    expect(wrapper.find('[data-testid=staking-failed-addresses]').text()).toContain('bad staker, 0xWorse');
  });

  it('should not warn when every address was loaded', () => {
    const wrapper = mountLayout();

    expect(wrapper.find('[data-testid=staking-failed-addresses]').exists()).toBe(false);
  });

  it('should title the events as the other staking pages do and render the slot', () => {
    const wrapper = mountLayout();

    expect(wrapper.findComponent(HistoryEventsViewStub).props()).toMatchObject({
      restrictions: { location: 'hyperliquid' },
      sectionTitle: 'common.events',
    });
    expect(wrapper.find('[data-testid=slot-content]').exists()).toBe(true);
  });
});
