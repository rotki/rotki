import type { BlockchainAccountGroupWithBalance } from '@/modules/accounts/blockchain-accounts';
import { startPromise } from '@shared/utils';
import { isDefined, watchImmediate } from '@vueuse/core';
import { get } from '@vueuse/shared';
import { computed, type ComputedRef, type MaybeRefOrGetter, type Ref, toValue, type WritableComputedRef } from 'vue';
import { type AccountGroupId, getGroupId, isXpubAccount } from '@/modules/accounts/account-utils';
import { AccountDetailsView, accountDetailsViews } from '@/modules/accounts/details/account-details-views';
import { useAccountDetailsRoute } from '@/modules/accounts/details/use-account-details-route';
import { useDrawerPresence } from '@/modules/accounts/details/use-drawer-presence';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';

interface UseAccountDetailsTargetOptions {
  /** The account category whose accounts the URL key is looked up in. */
  category: MaybeRefOrGetter<string>;
  /** Chains switched off per group, shared with the table row so both show the same scope. */
  chainExclusionFilter: MaybeRefOrGetter<Record<string, string[]>>;
}

interface UseAccountDetailsTargetReturn {
  /** The chains of the shown account the row keeps. */
  chains: ComputedRef<string[]>;
  /** Whether the row switched off some of the shown account's chains. */
  chainsFiltered: ComputedRef<boolean>;
  /** The tab on show: the one the URL asks for when the account offers it, else its first. */
  currentView: ComputedRef<AccountDetailsView>;
  emptyAddressCount: ComputedRef<number>;
  /** The id of the account on show. */
  groupId: ComputedRef<AccountGroupId | undefined>;
  /** Whether the URL names an account of the category; writing false closes it. */
  isOpen: WritableComputedRef<boolean>;
  /** Call once the drawer has slid out, to let go of the account it showed. */
  onClosed: () => void;
  openAccount: (id: string) => Promise<void>;
  /** The slide in is over, so the lists can mount. */
  ready: Readonly<Ref<boolean>>;
  /** The account on show, kept while the drawer slides out. */
  shownGroup: ComputedRef<BlockchainAccountGroupWithBalance | undefined>;
  /** The index of the tab on show; writing one puts its tab in the URL. */
  tabIndex: WritableComputedRef<number>;
  /** The tabs the shown account offers. */
  views: ComputedRef<AccountDetailsView[]>;
}

/**
 * The account the details drawer shows, read from the URL, and the tab it shows it on.
 *
 * @remarks
 * The account and tab are held while the drawer slides out, so the content does not change under
 * the closing animation. A key that names no account of the category is dropped from the URL once
 * every chain of the category has read its accounts.
 */
export function useAccountDetailsTarget(options: UseAccountDetailsTargetOptions): UseAccountDetailsTargetReturn {
  const { category, chainExclusionFilter } = options;

  const { isChainSettled } = useBlockchainAccountsStore();

  const { accountId, close, discard, open, setView, view } = useAccountDetailsRoute();
  const { getAccountsByCategory } = useBlockchainAccountData();
  const { chainIds } = useAccountCategoryHelper(() => toValue(category));
  const groups = getAccountsByCategory(() => toValue(category));

  const group = computed<BlockchainAccountGroupWithBalance | undefined>(() => {
    const id = get(accountId);
    return id ? get(groups).find(item => getGroupId(item) === id) : undefined;
  });

  /** The account open and the tab the URL asks for, held together so neither changes while the drawer slides out. */
  const opened = computed<{ group: BlockchainAccountGroupWithBalance; view?: AccountDetailsView } | undefined>(() => {
    const current = get(group);
    return current ? { group: current, view: get(view) } : undefined;
  });

  const { onClosed, ready, shown } = useDrawerPresence(opened);

  const shownGroup = computed<BlockchainAccountGroupWithBalance | undefined>(() => get(shown)?.group);

  /** Every chain of the category has finished its accounts read, so a missing account is really gone. */
  const accountsSettled = computed<boolean>(() => {
    const ids = get(chainIds);
    return ids.length > 0 && ids.every(chain => isChainSettled(chain));
  });

  const groupId = computed<AccountGroupId | undefined>(() => {
    const current = get(shownGroup);
    return current ? getGroupId(current) : undefined;
  });

  const chains = computed<string[]>(() => {
    const current = get(shownGroup);
    const id = get(groupId);
    if (!current || !id)
      return [];

    const excluded = toValue(chainExclusionFilter)[id] ?? [];
    return current.chains.filter(chain => !excluded.includes(chain));
  });

  const chainsFiltered = computed<boolean>(() => (get(shownGroup)?.chains.length ?? 0) > get(chains).length);

  /**
   * The derived addresses of an xpub that hold nothing, which the list hides until asked.
   *
   * @remarks
   * Wallets keep a gap of unused addresses past the last used one, so most of an xpub's addresses are
   * empty. When none holds anything there is nothing else to show, so nothing is hidden.
   */
  const emptyAddressCount = computed<number>(() => {
    const current = get(shownGroup);
    if (!current || !isXpubAccount(current) || current.fundedAddressCount === 0)
      return 0;
    return current.addressCount - current.fundedAddressCount;
  });

  const views = computed<AccountDetailsView[]>(() => {
    const current = get(shownGroup);
    return current ? accountDetailsViews(current) : [AccountDetailsView.ASSETS];
  });

  const currentView = computed<AccountDetailsView>(() => {
    const requested = get(shown)?.view;
    const offered = get(views);
    return requested && offered.includes(requested) ? requested : offered[0] ?? AccountDetailsView.ASSETS;
  });

  const modelTabIndex = computed<number>({
    get: () => get(views).indexOf(get(currentView)),
    set: (index: number) => {
      const next = get(views)[index];
      if (next)
        startPromise(setView(next));
    },
  });

  const modelIsOpen = computed<boolean>({
    get: () => isDefined(group),
    set: (value: boolean) => {
      if (!value)
        startPromise(close());
    },
  });

  /** A push while nothing shows, so Back closes it; a replace when it only switches the account. */
  async function openAccount(id: string): Promise<void> {
    await open(id, isDefined(group) ? 'replace' : 'push');
  }

  /** A key that names no account of this category (a stale link, a removed account) is dropped. */
  function discardUnknownAccount(): void {
    if (get(accountId) && get(accountsSettled) && !isDefined(group))
      startPromise(discard());
  }

  watchImmediate([accountId, accountsSettled, group], discardUnknownAccount);

  return {
    chains,
    chainsFiltered,
    currentView,
    emptyAddressCount,
    groupId,
    isOpen: modelIsOpen,
    onClosed,
    openAccount,
    ready,
    shownGroup,
    tabIndex: modelTabIndex,
    views,
  };
}
