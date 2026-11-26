import type { AccountManageState } from '@/modules/accounts/blockchain/use-account-manage';
import { Blockchain } from '@rotki/common';
import { get, set } from '@vueuse/shared';
import { computed, type ComputedRef, type MaybeRefOrGetter, onMounted, type Ref, ref, toValue } from 'vue';
import { type AddAccountSeed, parseAddAccountLink } from '@/modules/accounts/add-account-link';
import { createNewAccountForChain } from '@/modules/accounts/blockchain/new-account-state';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { useAddQuery } from '@/modules/core/common/use-add-query';

interface UseEvmAccountAddReturn {
  account: Ref<AccountManageState | undefined>;
  usedChainIds: ComputedRef<string[]>;
  createNewBlockchainAccount: (seed?: AddAccountSeed) => void;
}

/**
 * The add/edit dialog state of the EVM accounts page: which chains the open tab offers, opening the
 * dialog, and opening it from an add link once the page is mounted.
 *
 * @param isAccountsTabSelected - whether the accounts tab is open rather than the validators tab
 */
export function useEvmAccountAdd(isAccountsTabSelected: MaybeRefOrGetter<boolean>): UseEvmAccountAddReturn {
  /** Bound to the dialog with `v-model`, so the page writes it as well. */
  const modelAccount = ref<AccountManageState>();

  const { chainIds } = useAccountCategoryHelper('evm');

  const usedChainIds = computed<string[]>(() => {
    if (toValue(isAccountsTabSelected)) {
      return [
        'all',
        ...get(chainIds),
      ];
    }

    return [Blockchain.ETH2];
  });

  /**
   * Opens the add dialog, optionally holding addresses on a chain. A chain the tab does not offer is
   * ignored rather than trusted, so a link cannot open the dialog on something it cannot add to.
   */
  function createNewBlockchainAccount({ addresses, chain }: AddAccountSeed = { addresses: [] }): void {
    const usable = get(usedChainIds);
    const state = createNewAccountForChain(chain && usable.includes(chain) ? chain : usable[0]);

    if (addresses.length > 0 && state.type === 'account')
      state.data = addresses.map(address => ({ address, tags: null }));

    set(modelAccount, state);
  }

  const { consumeAddQuery } = useAddQuery((query) => {
    createNewBlockchainAccount(parseAddAccountLink(query));
  });

  onMounted(async () => {
    await consumeAddQuery();
  });

  return {
    account: modelAccount,
    createNewBlockchainAccount,
    usedChainIds,
  };
}
