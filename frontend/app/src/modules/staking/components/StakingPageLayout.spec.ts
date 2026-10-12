import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import StakingPageLayout from '@/modules/staking/components/StakingPageLayout.vue';

const fetchPrices = vi.hoisted(() => vi.fn<(payload: { ignoreCache: boolean; selectedAssets: string[] }) => Promise<void>>());

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: (): { fetchPrices: typeof fetchPrices } => ({ fetchPrices }),
}));

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
          TablePageLayout: { template: '<div><slot name="buttons" /><slot /></div>' },
        },
      },
      props: {
        asset: 'HYPE',
        eventsTitle: 'Events',
        failedAddresses,
        loading: false,
        refresh,
        restrictions: { location: 'hyperliquid' },
        title: 'Hyperliquid',
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

  it('should warn which addresses could not be loaded', () => {
    const wrapper = mountLayout(['0xBad', '0xWorse']);

    expect(wrapper.find('[data-testid=staking-failed-addresses]').text()).toContain('0xBad, 0xWorse');
  });

  it('should not warn when every address was loaded', () => {
    const wrapper = mountLayout();

    expect(wrapper.find('[data-testid=staking-failed-addresses]').exists()).toBe(false);
  });

  it('should pass the restrictions and title to the history events and render the slot', () => {
    const wrapper = mountLayout();

    expect(wrapper.findComponent(HistoryEventsViewStub).props()).toMatchObject({
      restrictions: { location: 'hyperliquid' },
      sectionTitle: 'Events',
    });
    expect(wrapper.find('[data-testid=slot-content]').exists()).toBe(true);
  });
});
