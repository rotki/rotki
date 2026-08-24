import { get } from '@vueuse/core';
import { toChainKey } from '@/modules/core/common/chains';
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
 * Comparisons are case-insensitive on both chain and address, because the two sides are written by
 * different parties: the rule comes from the settings dialog, while what it is matched against
 * arrives over the websocket. Addresses are the case that bites - nothing normalizes them on the
 * way in, so a checksummed address on the wire against a lower-cased one in the rule would silently
 * defeat a rule the user did set. Chains go through {@link toChainKey}, which also folds the
 * separator, since the same chain is spelled `polygon_pos`, `POLYGON_POS` or `polygonPos`
 * depending on who wrote it.
 *
 * No two distinct addresses differ only by case in any chain rotki supports, so folding case cannot
 * over-match.
 */
export function useDisabledChains(): UseDisabledChainsReturn {
  const disabledChainQueries = useSetting('disabledChainQueries');

  const rules = computed<Record<string, Set<string>>>(() => {
    const entries = Object.entries(get(disabledChainQueries)).map(
      ([chain, addresses]): [string, Set<string>] => [
        toChainKey(chain),
        new Set(addresses.map(address => address.toLowerCase())),
      ],
    );
    return Object.fromEntries(entries);
  });

  const ruleFor = (chain: string): Set<string> | undefined => get(rules)[toChainKey(chain)];

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
