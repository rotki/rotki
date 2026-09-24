import { accountAddActivity, EVM_PSEUDO_CHAIN } from '@/modules/accounts/accounts.activity';
import { decodeActivity, targetedDecodeActivity } from '@/modules/history/events/tx/decode-activity';
import { accountSyncActivity, bankEventsActivity, chainSyncActivity, exchangeEventsActivity } from '@/modules/history/events/tx/sync-activity';
import { type Activity, ActivityKind, ActivityPart, activityParts, makeActivityId } from '@/modules/task-center/core/types';

/** What an activity acts on, in the raw spelling its id carries, for the icons and links a row shows. */
export interface ActivitySubject {
  /** A chain id (`eth`), never the display name a subtitle carries. */
  readonly chain?: string;
  /** Linked to an explorer only when {@link chain} is present too. */
  readonly address?: string;
  /** An exchange or bank location (`kraken`). */
  readonly location?: string;
}

type SubjectReader = (activity: Activity, parts: string[]) => ActivitySubject | undefined;

function syncSubject(activity: Activity, [chain, address]: string[]): ActivitySubject | undefined {
  if (chain === undefined)
    return undefined;
  if (address === undefined)
    return chainSyncActivity.id({ chain }) === activity.id ? { chain } : undefined;
  return accountSyncActivity.id({ address, chain }) === activity.id ? { address, chain } : undefined;
}

function decodeSubject(activity: Activity, [chain, part, scope]: string[]): ActivitySubject | undefined {
  if (chain === undefined)
    return undefined;
  const whole = decodeActivity.id({ chain, ignoreCache: part === ActivityPart.PULL }) === activity.id;
  const targeted = scope !== undefined && targetedDecodeActivity.id({ chain, txRefs: scope.split(',') }) === activity.id;
  return whole || targeted ? { chain } : undefined;
}

function eventsSubject(activity: Activity, [location, name]: string[]): ActivitySubject | undefined {
  if (location === undefined || name === undefined)
    return undefined;
  const descriptor = activity.kind === ActivityKind.BANK_EVENTS ? bankEventsActivity : exchangeEventsActivity;
  return descriptor.id({ location, name }) === activity.id ? { location } : undefined;
}

/** A chain's balance job is `[chain]` or `[chain, detect, …]`; the run over several chains is `[run, …]`. */
function chainBalancesSubject(_activity: Activity, [chain, part]: string[]): ActivitySubject | undefined {
  if (chain === undefined || chain === ActivityPart.RUN)
    return undefined;
  return part === undefined || part === ActivityPart.DETECT ? { chain } : undefined;
}

function detectionSubject(activity: Activity, [chain, address]: string[]): ActivitySubject | undefined {
  if (chain === undefined || address === undefined)
    return undefined;
  return makeActivityId(ActivityKind.TOKEN_DETECTION, chain, address) === activity.id ? { address, chain } : undefined;
}

/**
 * One address being added, `[add, chain, address]`. A bulk umbrella or an xpub fails the id check
 * and reads nothing.
 *
 * @remarks
 * The id check cannot tell two other shapes from a single address, so they are refused here: a
 * payload of several addresses, joined with `,` into that one part, and a bulk umbrella, whose last
 * part is the batch marker. The "every EVM chain" pseudo-chain is left out of the subject: it has no
 * icon and no explorer, so the row gets the bare address.
 */
function additionSubject(activity: Activity, [, chain, address]: string[]): ActivitySubject | undefined {
  if (chain === undefined || address === undefined || address === ActivityPart.BATCH || address.includes(','))
    return undefined;
  if (accountAddActivity.id({ chain, target: { address, kind: 'address' } }) !== activity.id)
    return undefined;
  return chain === EVM_PSEUDO_CHAIN ? { address } : { address, chain };
}

function exchangeBalancesSubject(activity: Activity, [location]: string[]): ActivitySubject | undefined {
  if (location === undefined)
    return undefined;
  return makeActivityId(ActivityKind.EXCHANGE_BALANCES, location) === activity.id ? { location } : undefined;
}

/** The kinds whose ids name a chain, an account or a location, each read the way its producer builds it. */
const READERS: Partial<Record<ActivityKind, SubjectReader>> = {
  [ActivityKind.ACCOUNTS]: additionSubject,
  [ActivityKind.BANK_EVENTS]: eventsSubject,
  [ActivityKind.BLOCKCHAIN_BALANCES]: chainBalancesSubject,
  [ActivityKind.EXCHANGE_BALANCES]: exchangeBalancesSubject,
  [ActivityKind.EXCHANGE_EVENTS]: eventsSubject,
  [ActivityKind.TOKEN_DETECTION]: detectionSubject,
  [ActivityKind.TX_DECODING]: decodeSubject,
  [ActivityKind.TX_SYNC]: syncSubject,
};

/**
 * What an activity acts on, recovered from its id.
 *
 * @remarks
 * Read from the id rather than the subtitle: the subtitle carries display text (`Ethereum`,
 * `Kraken`), while an icon or an explorer link needs the raw value. Where a descriptor mints the
 * id, the recovered subject is checked by minting the id again, so a run or umbrella that shares a
 * kind is never mistaken for one subject.
 */
export function activitySubject(activity: Activity): ActivitySubject | undefined {
  return READERS[activity.kind]?.(activity, activityParts(activity.id));
}
