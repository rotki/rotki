import type { AccountPayload, XpubAccountPayload } from '@/modules/accounts/blockchain-accounts';
import { msg } from '@/message-key';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { ActivityKind, ActivityPart, type ActivityText } from '@/modules/task-center/core/types';

/**
 * The pseudo-chain an "add to every EVM chain" request is tracked under. Not a real chain, so it
 * has no entry in the supported-chain list; it exists so such a request has an identity and a lane
 * like any per-chain one. Declared here because the id, the lane and any batch umbrella must all
 * agree on it, and a bare `'EVM'` at three call sites cannot.
 */
export const EVM_PSEUDO_CHAIN = 'EVM';

/**
 * What an account operation acts on. A union rather than loose strings because the identity of the
 * work differs per variant: an address is identified by itself, an xpub only by the pair of the key
 * and its derivation path. Keying an xpub by the key alone deduped two genuinely different
 * additions onto one promise.
 */
export type AccountTarget =
  | { readonly kind: 'address'; readonly address: string }
  | { readonly kind: 'addresses'; readonly addresses: readonly string[] }
  | { readonly kind: 'xpub'; readonly xpub: string; readonly derivationPath?: string };

export interface AccountSubject {
  readonly chain: string;
  readonly target: AccountTarget;
}

/**
 * The narrow half of an activity key: what is being acted on, as one part.
 *
 * Joined with `,` rather than the id separator so `activityParts` recovers the set as a single
 * part instead of shredding it into members — the same reason `redecodeFlow` joins its chains that
 * way.
 */
export function targetKey(target: AccountTarget): string {
  switch (target.kind) {
    case 'address':
      return target.address;
    case 'addresses':
      return target.addresses.join(',');
    case 'xpub':
      return `${target.xpub}/${target.derivationPath ?? ''}`;
  }
}

/**
 * The subtitles account activities render under, beside the ids they belong to.
 *
 * Labels live with the descriptor for the same reason the readers do: the subtitle describes the
 * same subject the id is built from, and splitting them across files is how they drift.
 */
export const accountActivityLabel = {
  add: (address: string): ActivityText => activityLabelFor(msg.$t('task_center.activity.accounts.add'), { address }),
  remove: (address: string): ActivityText => activityLabelFor(msg.$t('task_center.activity.accounts.remove'), { address }),
  removeCount: (count: number): ActivityText =>
    activityLabelFor(msg.$t('task_center.activity.accounts.remove_count'), { count }, count),
  removeXpub: (xpub: string): ActivityText => activityLabelFor(msg.$t('task_center.activity.accounts.remove_xpub'), { xpub }),
} as const;

/**
 * The target an addition payload acts on. The one place that knows an xpub payload is identified by
 * its key *and* derivation path, so no producer has to remember it.
 */
export function accountTargetOf(payload: AccountPayload[] | XpubAccountPayload): AccountTarget {
  if ('xpub' in payload)
    return { derivationPath: payload.xpub.derivationPath, kind: 'xpub', xpub: payload.xpub.xpub };

  return { addresses: payload.map(item => item.address), kind: 'addresses' };
}

/**
 * Adding accounts. Keyed `(chain, target)`: a bulk add fans out over one chain, and `submitTask`
 * dedups on id identity, so a chain-only id collapsed every address after the first onto the
 * first's promise and reported them added without ever sending them.
 *
 * ⚠️ No lane yet: `addMultipleAccounts` still throttles itself with
 * `awaitParallelExecution(..., 2)`. Declaring a lane cap here as well would put two mechanisms on
 * one piece of work, which is what the warning on `DECODE_LANE` is about. The lane arrives when
 * that limiter is removed, not before.
 */
export const accountAddActivity = defineActivity<AccountSubject, readonly [string, string]>({
  key: subject => [subject.chain, targetKey(subject.target)],
  kind: ActivityKind.ACCOUNTS,
  part: ActivityPart.ADD,
});

/**
 * Removing accounts. Same key shape, for the same reason: a plain account delete and an xpub delete
 * on one chain both minted `accounts:remove:<chain>`, so an overlap deduped the second onto the
 * first while the UI still dropped its rows.
 */
export const accountRemoveActivity = defineActivity<AccountSubject, readonly [string, string]>({
  key: subject => [subject.chain, targetKey(subject.target)],
  kind: ActivityKind.ACCOUNTS,
  part: ActivityPart.REMOVE,
});

/**
 * Removing one address across a whole account category ("every EVM chain"), which is a different
 * subject: the broad component is a category, not a chain. Its own descriptor rather than a reuse
 * of {@link accountRemoveActivity}, so the subject stays honest about what it holds.
 *
 * ⚠️ It shares the `accounts:remove` keyspace with the chain-scoped removals. Nothing collides
 * today because no chain is named after a category, but the two are only kept apart by that.
 */
export const accountAgnosticRemoveActivity = defineActivity<{ category: string; address: string }, readonly [string, string]>({
  key: subject => [subject.category, subject.address],
  kind: ActivityKind.ACCOUNTS,
  part: ActivityPart.REMOVE,
});
