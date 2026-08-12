import type { AccountPayload, XpubAccountPayload } from '@/modules/accounts/blockchain-accounts';
import { msg } from '@/message-key';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { ACCOUNTS_ADD_LANE_PREFIX, ACCOUNTS_REMOVE_LANE_PREFIX, familyLane } from '@/modules/task-center/core/orchestrator/spec';
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
 * The lane caps additions at 2 per chain. Concurrency lives there and nowhere else, as the warning
 * on `DECODE_LANE` requires.
 */
export const accountAddActivity = defineActivity<AccountSubject, readonly [string, string]>({
  key: subject => [subject.chain, targetKey(subject.target)],
  kind: ActivityKind.ACCOUNTS,
  lane: subject => familyLane(ACCOUNTS_ADD_LANE_PREFIX, subject.chain),
  part: ActivityPart.ADD,
});

/**
 * A CSV import, as one activity parenting every addition it makes. Keyed by source so two imports
 * are two runs; there is only one source today, and naming it keeps the id from being kind-only.
 *
 * It is the outermost umbrella: an import fans out over rows, and a row with several addresses fans
 * out again under its own per-chain umbrella.
 */
export const accountImportActivity = defineActivity<{ source: string }, readonly [string]>({
  key: subject => [subject.source],
  kind: ActivityKind.ACCOUNTS,
  part: ActivityPart.IMPORT,
});

/**
 * Removing accounts. Same key shape, for the same reason: a plain account delete and an xpub delete
 * on one chain both minted `accounts:remove:<chain>`, so an overlap deduped the second onto the
 * first while the UI still dropped its rows.
 */
export const accountRemoveActivity = defineActivity<AccountSubject, readonly [string, string]>({
  key: subject => [subject.chain, targetKey(subject.target)],
  kind: ActivityKind.ACCOUNTS,
  lane: subject => familyLane(ACCOUNTS_REMOVE_LANE_PREFIX, subject.chain),
  part: ActivityPart.REMOVE,
});

/**
 * Removing one address across a whole account category ("every EVM chain"), which is a different
 * subject: the broad component is a category, not a chain. Its own descriptor rather than a reuse
 * of {@link accountRemoveActivity}, so the subject stays honest about what it holds.
 *
 * The key opens with the literal `category` part so these ids cannot be confused with chain-scoped
 * ones by a prefix reader. Keying straight off the category name would have left the two apart only
 * because no chain happens to be called `evm` — incidental, and invisible once it stopped being
 * true.
 */
export const accountAgnosticRemoveActivity = defineActivity<{ category: string; address: string }, readonly [ActivityPart, string, string]>({
  key: subject => [ActivityPart.CATEGORY, subject.category, subject.address],
  kind: ActivityKind.ACCOUNTS,
  // Same family as the chain-scoped removal: the family caps one active lane, so an agnostic
  // removal and a per-chain one still take turns rather than racing each other.
  lane: subject => familyLane(ACCOUNTS_REMOVE_LANE_PREFIX, subject.category),
  part: ActivityPart.REMOVE,
});
