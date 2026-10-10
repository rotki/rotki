import type { useSolanaStakeAccounts } from '@/modules/staking/solana/use-solana-stake-accounts';
import { Zero } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import SolanaPage from '@/modules/staking/solana/SolanaPage.vue';

const { fetchPrices, pageState, refresh } = await vi.hoisted(async () => {
  const { shallowRef } = await import('vue');
  return {
    fetchPrices: vi.fn<(payload: { ignoreCache: boolean; selectedAssets: string[] }) => Promise<void>>(),
    pageState: { error: shallowRef<string>('') },
    refresh: vi.fn<() => Promise<void>>(),
  };
});

vi.mock('@/modules/staking/solana/use-solana-stake-accounts', async () => {
  const { computed, shallowRef } = await import('vue');
  return {
    useSolanaStakeAccounts: (): ReturnType<typeof useSolanaStakeAccounts> => ({
      error: pageState.error,
      loading: shallowRef<boolean>(false),
      refresh,
      rows: computed(() => []),
      total: computed(() => Zero),
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

describe('modules/staking/solana/SolanaPage', () => {
  function mountPage(): VueWrapper {
    return mount(SolanaPage, {
      global: {
        stubs: {
          BalanceDisplay: true,
          HistoryEventsView: HistoryEventsViewStub,
          SolanaStakeAccountsTable: true,
          TablePageLayout: { template: '<div><slot name="buttons" /><slot /></div>' },
        },
      },
    });
  }

  beforeEach(() => {
    vi.clearAllMocks();
    pageState.error.value = '';
  });

  it('should only list the solana staking events of the solana staking counterparty', () => {
    const wrapper = mountPage();

    expect(wrapper.findComponent(HistoryEventsViewStub).props('restrictions')).toEqual({
      entryTypes: ['solana event'],
      onlyChains: ['solana'],
      protocols: ['solana-stake'],
    });
  });

  it('should load the stake accounts and the SOL price when opened', async () => {
    mountPage();
    await vi.waitFor(() => expect(refresh).toHaveBeenCalledOnce());

    expect(fetchPrices).toHaveBeenCalledWith({ ignoreCache: false, selectedAssets: ['SOL'] });
  });

  it('should bypass the price cache when refreshed by the user', async () => {
    const wrapper = mountPage();

    await wrapper.find('[data-testid=solana-refresh]').trigger('click');

    expect(fetchPrices).toHaveBeenLastCalledWith({ ignoreCache: true, selectedAssets: ['SOL'] });
  });

  it('should show why the query failed', () => {
    pageState.error.value = 'rpc down';
    const wrapper = mountPage();

    expect(wrapper.find('[data-testid=solana-staking-error]').text()).toContain('rpc down');
  });

  it('should not show an error when the query succeeded', () => {
    const wrapper = mountPage();

    expect(wrapper.find('[data-testid=solana-staking-error]').exists()).toBe(false);
  });
});
