import type { MaybeRef } from 'vue';
import type { BlockchainAccountGroupRequestPayload } from '@/modules/accounts/blockchain-accounts';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getXpubGroupId } from '@/modules/accounts/account-utils';
import AccountGroupDetailsTable from '@/modules/accounts/AccountGroupDetailsTable.vue';

const { fetchGroupAccounts } = vi.hoisted(() => ({
  fetchGroupAccounts: vi.fn<(payload: BlockchainAccountGroupRequestPayload) => Promise<unknown>>(),
}));

vi.mock('@/modules/balances/blockchain/use-blockchain-account-data', async () => {
  const { get } = await import('@vueuse/shared');
  return {
    useBlockchainAccountData: (): object => ({
      fetchGroupAccounts: async (payload: MaybeRef<BlockchainAccountGroupRequestPayload>): Promise<unknown> => fetchGroupAccounts(get(payload)),
    }),
  };
});

vi.mock('@/modules/accounts/use-blockchain-account-loading', () => ({
  useBlockchainAccountLoading: (): object => ({}),
}));

function render(emptyCount: number): VueWrapper {
  const pinia = createPinia();
  setActivePinia(pinia);
  return mount(AccountGroupDetailsTable, {
    global: {
      plugins: [pinia],
      stubs: {
        AccountBalanceDetails: true,
        AccountBalancesTable: true,
        RuiButton: { emits: ['click'], template: '<button @click="$emit(\'click\')"><slot /></button>' },
      },
    },
    props: { category: 'bitcoin', chains: ['btc'], emptyCount, group: 'xpub', groupId: getXpubGroupId({ xpub: 'xpub1' }, 'btc'), selected: undefined },
  });
}

/** Whether the last request left out the accounts holding nothing. */
function lastAskedForFunded(): boolean | undefined {
  return fetchGroupAccounts.mock.lastCall?.[0].onlyFunded;
}

describe('accountGroupDetailsTable', () => {
  beforeEach(() => {
    fetchGroupAccounts.mockReset();
    fetchGroupAccounts.mockResolvedValue(ok({ data: [], found: 0, limit: -1, total: 0, totalValue: undefined }));
  });

  it('should hide the empty accounts, say how many, and list them all once asked', async () => {
    const wrapper = render(39);
    await flushPromises();

    expect(lastAskedForFunded()).toBe(true);
    expect(wrapper.find('[data-testid=account-group-empty-toggle]').text()).toContain('account_balances.xpub.empty_hidden::39');

    await wrapper.find('[data-testid=account-group-show-empty]').trigger('click');
    await flushPromises();

    expect(lastAskedForFunded()).toBeUndefined();
    expect(wrapper.find('[data-testid=account-group-empty-toggle]').text()).toBe('account_balances.xpub.hide_empty');
  });

  it('should list every account and offer no toggle when nothing is to be hidden', async () => {
    const wrapper = render(0);
    await flushPromises();

    expect(lastAskedForFunded()).toBeUndefined();
    expect(wrapper.find('[data-testid=account-group-empty-toggle]').exists()).toBe(false);
  });
});
