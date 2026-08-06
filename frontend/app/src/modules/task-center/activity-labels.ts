import { type MessageKey, msg } from '@/message-key';
import { type ActivityKind, type ActivityPart, ActivityKind as Kind, ActivityPart as Part, type TranslatableText } from './core/types';

/**
 * Descriptions for activities whose kind alone does not say what they are doing.
 *
 * Mirrors `core/kinds.ts`'s group-title table, with two differences that are deliberate:
 *
 * 1. It lives outside `core/`, because it needs `msg.$t` as a *value* and `@/message-key` imports
 *    the i18n singleton. The pure core must keep its no-i18n-at-runtime property.
 * 2. It is keyed by **kind then part**, not by part alone. A description is a function of both:
 *    `EXPORT` belongs to four kinds, and "Exporting user assets" cannot serve accounting rules.
 *
 * Every activity gets a short description saying what it is doing — a bare value ("Ethereum",
 * "EUR") tells the reader nothing the row does not already show. Values belong *inside* the
 * sentence as named params ("Querying the {chain} network"), never appended to it.
 *
 * A description must not repeat its group title: under "Blockchain balances", "Querying balances
 * for Ethereum" says "balances" twice, while "Querying the Ethereum network" adds the verb and the
 * target. Keep them succinct and verb-first.
 *
 * Producers whose text is already a full sentence built elsewhere (e.g. the oracle cache's
 * "Creating cache entry from {fromAsset} to {toAsset} on {source}") pass that string straight
 * through rather than duplicating it here.
 */
const ACTIVITY_LABEL: Partial<Record<ActivityKind, Partial<Record<ActivityPart, MessageKey>>>> = {
  [Kind.ACCOUNTING_RULES]: {
    [Part.EXPORT]: msg.$t('task_center.activity.accounting_rules.export'),
    [Part.IMPORT]: msg.$t('task_center.activity.accounting_rules.import'),
    [Part.RESET]: msg.$t('task_center.activity.accounting_rules.reset'),
  },
  [Kind.ACCOUNTS]: {
    [Part.DETECT]: msg.$t('task_center.activity.accounts.detect'),
    [Part.ENS]: msg.$t('task_center.activity.accounts.ens'),
  },
  [Kind.ASSETS]: {
    [Part.ERC20]: msg.$t('task_center.activity.assets.erc20'),
    [Part.EXPORT]: msg.$t('task_center.activity.assets.export'),
    [Part.IMPORT]: msg.$t('task_center.activity.assets.import'),
    [Part.NFTS]: msg.$t('task_center.activity.assets.nfts'),
    [Part.UPDATE]: msg.$t('task_center.activity.assets.update'),
    [Part.VERSIONS]: msg.$t('task_center.activity.assets.versions'),
  },
  [Kind.GNOSIS_PAY]: {
    [Part.NONCE]: msg.$t('task_center.activity.gnosis_pay.nonce'),
    [Part.VERIFY]: msg.$t('task_center.activity.gnosis_pay.verify'),
  },
  [Kind.HISTORY_EVENTS]: {
    [Part.BRIDGE]: msg.$t('task_center.activity.history_events.bridge'),
    [Part.EXPORT]: msg.$t('task_center.activity.history_events.export'),
    [Part.MATCH]: msg.$t('task_center.activity.history_events.match'),
    [Part.UNDECODED]: msg.$t('task_center.activity.history_events.undecoded'),
  },
  // Parallel siblings: four facets of one protocol, shown together. The contrast between them is
  // the information, so they stay terse where a lone activity would get a sentence.
  [Kind.LIQUITY]: {
    [Part.BALANCES]: msg.$t('task_center.activity.liquity.balances'),
    [Part.POOLS]: msg.$t('task_center.activity.liquity.pools'),
    [Part.STAKING]: msg.$t('task_center.activity.liquity.staking'),
    [Part.STATISTICS]: msg.$t('task_center.activity.liquity.statistics'),
  },
  [Kind.PNL_REPORT]: {
    [Part.EXPORT]: msg.$t('task_center.activity.pnl_report.export'),
    [Part.IMPORT]: msg.$t('task_center.activity.pnl_report.import'),
  },
  [Kind.STAKING]: {
    [Part.KRAKEN]: msg.$t('task_center.activity.staking.kraken'),
    [Part.PERFORMANCE]: msg.$t('task_center.activity.staking.performance'),
    [Part.VALIDATORS]: msg.$t('task_center.activity.staking.validators'),
  },
};

/**
 * Description for `(kind, part)`, as a {@link TranslatableText} the render layer resolves with its
 * own `t`. Returns `undefined` when the pair has no entry, which is the shape
 * `ActivitySpec.subtitle` already expects for "no subtitle".
 *
 * Parameters are named and placed *inside* the sentence by the message itself
 * ("Retrieving token details for {address} ({chain})"), never appended by this helper — translators
 * decide where a value belongs, and never see a punctuation-only string.
 */
export function activityLabel(
  kind: ActivityKind,
  part: ActivityPart,
  params?: Record<string, unknown>,
  plural?: number,
): TranslatableText | undefined {
  const key = ACTIVITY_LABEL[kind]?.[part];
  return key === undefined ? undefined : { key, params, plural };
}

/**
 * Description for a kind that has no distinguishing part — a singleton activity whose group title
 * still does not say what it does (historical balances, latest prices).
 */
export function activityLabelFor(key: MessageKey, params?: Record<string, unknown>, plural?: number): TranslatableText {
  return { key, params, plural };
}
