import type { AccountAdditionDetail } from '@/modules/accounts/accounts.activity';
import type { EvmAccountsResult } from '@/modules/core/api/types/accounts';

/** The backend's word for "every EVM chain" in a chain list. */
const ALL_CHAINS = 'all';

/**
 * Why an address was added nowhere, as the key of the reason its row shows.
 *
 * @remarks
 * The key rather than a message, and never the address: the dock merges skipped rows by reason, and
 * the row's own label already names the address.
 */
export const EvmSkipReason = {
  EXISTED: 'existed',
  NO_ACTIVITY: 'no_activity',
} as const;

export type EvmSkipReason = typeof EvmSkipReason[keyof typeof EvmSkipReason];

/**
 * What one address's "every EVM chain" addition came to.
 *
 * - `added`: tracked on at least one chain, whatever happened on the others
 * - `skipped`: tracked nowhere, and nothing went wrong
 * - `failed`: tracked nowhere, because checking or tracking it failed on the chains it is active on
 */
export type EvmAdditionOutcome =
  | { readonly type: 'added'; readonly detail: AccountAdditionDetail }
  | { readonly type: 'skipped'; readonly reason: EvmSkipReason }
  | { readonly type: 'failed'; readonly chains: readonly string[] };

/**
 * One address's chains under a result key. The request adds a single address, so each record holds
 * at most one entry; an absent key and an empty record both mean no chains.
 */
function chainsOf(record: Record<string, string[]> | undefined): string[] {
  return Object.values(record ?? {})[0] ?? [];
}

/**
 * Classifies the backend's answer for one address.
 *
 * @remarks
 * An address with no activity on any chain is added **nowhere**: the backend does not track it on
 * mainnet by default, so it never reaches the accounts table. That is why it settles as skipped with
 * a reason rather than as a quiet success.
 */
export function evmAdditionOutcome(result: EvmAccountsResult): EvmAdditionOutcome {
  const added = chainsOf(result.added);
  const failed = chainsOf(result.failed);
  const noActivity = chainsOf(result.noActivity);

  if (added.length === 0) {
    if (failed.length > 0)
      return { chains: failed, type: 'failed' };

    return { reason: noActivity.length > 0 ? EvmSkipReason.NO_ACTIVITY : EvmSkipReason.EXISTED, type: 'skipped' };
  }

  const everyChain = added.length === 1 && added[0] === ALL_CHAINS;
  return {
    detail: {
      added: everyChain ? [] : added,
      everyChain,
      existed: chainsOf(result.existed),
      failed,
      noActivity,
    },
    type: 'added',
  };
}
