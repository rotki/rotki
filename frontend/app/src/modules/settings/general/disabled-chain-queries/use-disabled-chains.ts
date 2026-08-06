import { get } from '@vueuse/core';
import { useSetting } from '@/modules/settings/use-setting';

interface AccountLike {
  chain: string;
  address: string;
}

export interface UseDisabledChainsReturn {
  /** True when the whole chain is switched off, i.e. every address on it is excluded. */
  isChainExcluded: (chain: string) => boolean;
  /** True when this address is excluded on this chain, whether by an address rule or a chain one. */
  isAddressExcluded: (chain: string, address: string) => boolean;
  /** Drop every account the user excluded. Keeps the input order and identity of what survives. */
  filterAccounts: <T extends AccountLike>(accounts: T[]) => T[];
}

/**
 * Read side of the `disabledChainQueries` setting: "is this chain/address switched off?".
 *
 * Backend contract, and the part that is easy to get wrong: the setting is
 * `Record<chainId, address[]>` where an **empty array disables the entire chain** and a non-empty
 * one disables only those addresses on it. A missing key means the chain is fully enabled.
 *
 * Lives next to the setting rather than in the feature that first needed it: history, the sync
 * panel and (later) balances all have to answer the same question, and a second copy of the
 * empty-array rule is how the two surfaces drift apart.
 *
 * Comparisons are case-insensitive on both chain and address. The setting is written from tracked
 * accounts while the sync panel's addresses arrive over the websocket, so a case-only difference
 * between the two would silently defeat a rule the user did set. No two distinct addresses differ
 * only by case in any chain rotki supports.
 */
export function useDisabledChains(): UseDisabledChainsReturn {
  const disabledChainQueries = useSetting('disabledChainQueries');

  const rules = computed<Record<string, Set<string>>>(() => {
    const entries = Object.entries(get(disabledChainQueries)).map(
      ([chain, addresses]): [string, Set<string>] => [
        chain.toLowerCase(),
        new Set(addresses.map(address => address.toLowerCase())),
      ],
    );
    return Object.fromEntries(entries);
  });

  const ruleFor = (chain: string): Set<string> | undefined => get(rules)[chain.toLowerCase()];

  const isChainExcluded = (chain: string): boolean => ruleFor(chain)?.size === 0;

  const isAddressExcluded = (chain: string, address: string): boolean => {
    const rule = ruleFor(chain);
    if (rule === undefined)
      return false;
    return rule.size === 0 || rule.has(address.toLowerCase());
  };

  const filterAccounts = <T extends AccountLike>(accounts: T[]): T[] =>
    accounts.filter(({ address, chain }) => !isAddressExcluded(chain, address));

  return {
    filterAccounts,
    isAddressExcluded,
    isChainExcluded,
  };
}
