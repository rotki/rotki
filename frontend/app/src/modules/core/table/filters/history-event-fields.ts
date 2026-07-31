import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { FilterValueTypes } from '@/modules/core/table/filtering';
import { decorateSharedField, type SharedFieldKind, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { HistoryEventFilterValueKeys, type Matcher } from '@/modules/core/table/filters/use-events-filter';
import { toDateFieldDef, toFieldDef, toParamFieldDef, toRangeFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import { DisplayKinds, type FieldDef, type ValueIcon } from '@/modules/core/table/pill/core/types';

type Translate = (key: string) => string;

/**
 * What history needs on top of the shared resolution every pill-bar table gets: the two mapping
 * lookups that only history events have.
 */
export interface HistoryFieldResolvers extends SharedFieldResolvers {
  readonly t: Translate;
  /** Raw event type (e.g. `informational`) -> its display name. */
  readonly resolveEventTypeName: (value: string) => string;
  /** Raw event subtype (e.g. `receive_wrapped`) -> its display name. */
  readonly resolveEventSubTypeName: (value: string) => string;
}

/**
 * Short, noun-style pill labels. The matcher `description` is a long "filter by …" hint that
 * reads badly on a pill, so each field gets a concise label keyed by its wire key.
 */
function shortLabels(t: Translate): Record<string, string> {
  return {
    [HistoryEventFilterValueKeys.ADDRESSES]: t('transactions.filter_field_labels.address'),
    [HistoryEventFilterValueKeys.ASSET]: t('transactions.filter_field_labels.asset'),
    [HistoryEventFilterValueKeys.ENTRY_TYPE]: t('transactions.filter_field_labels.entry_type'),
    [HistoryEventFilterValueKeys.EVENT_SUBTYPE]: t('transactions.filter_field_labels.event_subtype'),
    [HistoryEventFilterValueKeys.EVENT_TYPE]: t('transactions.filter_field_labels.event_type'),
    [HistoryEventFilterValueKeys.LOCATION]: t('transactions.filter_field_labels.location'),
    [HistoryEventFilterValueKeys.NOTES]: t('transactions.filter_field_labels.notes'),
    [HistoryEventFilterValueKeys.PROTOCOL]: t('transactions.filter_field_labels.protocol'),
    [HistoryEventFilterValueKeys.TX_HASHES]: t('transactions.filter_field_labels.tx_hash'),
    [HistoryEventFilterValueKeys.VALIDATOR_INDICES]: t('transactions.filter_field_labels.validator_index'),
  };
}

/**
 * The pill bar's presentation fields for history events: the same matchers, but with the two
 * amount matchers folded into one `range` pill and the two period matchers into one `date` pill,
 * and long matcher descriptions replaced by short pill labels.
 */
// Which of history's keys are fields other tables have too. Everything about how these render
// comes from the shared library, so a fix to the asset pill lands for every table at once.
const sharedKinds: Partial<Record<string, SharedFieldKind>> = {
  [HistoryEventFilterValueKeys.ADDRESSES]: SharedFieldKinds.ADDRESS,
  [HistoryEventFilterValueKeys.ASSET]: SharedFieldKinds.ASSET,
  [HistoryEventFilterValueKeys.ENTRY_TYPE]: SharedFieldKinds.TOKEN,
  [HistoryEventFilterValueKeys.LOCATION]: SharedFieldKinds.LOCATION,
  [HistoryEventFilterValueKeys.PROTOCOL]: SharedFieldKinds.PROTOCOL,
  [HistoryEventFilterValueKeys.TX_HASHES]: SharedFieldKinds.TX_HASH,
};

// What a validated free-text field wants, keyed by wire key, shown when its validator rejects.
function invalidHints(t: Translate): Partial<Record<string, string>> {
  return {
    [HistoryEventFilterValueKeys.ADDRESSES]: t('transactions.filter.invalid_address'),
    [HistoryEventFilterValueKeys.TX_HASHES]: t('transactions.filter.invalid_tx_hash'),
    [HistoryEventFilterValueKeys.VALIDATOR_INDICES]: t('transactions.filter.invalid_validator_index'),
  };
}

// String matchers with no option list: the user types the value(s) instead of picking them.
const freeTextKeys = new Set<string>([
  HistoryEventFilterValueKeys.ADDRESSES,
  HistoryEventFilterValueKeys.NOTES,
  HistoryEventFilterValueKeys.TX_HASHES,
  HistoryEventFilterValueKeys.VALIDATOR_INDICES,
]);

// The label resolvers only history has: its event type and subtype are looked up in mappings no
// other table carries. The rest come from the shared kinds above.
function labelResolvers(resolvers: HistoryFieldResolvers): Partial<Record<string, (value: string) => string>> {
  return {
    [HistoryEventFilterValueKeys.EVENT_SUBTYPE]: resolvers.resolveEventSubTypeName,
    [HistoryEventFilterValueKeys.EVENT_TYPE]: resolvers.resolveEventTypeName,
  };
}

// Applies the history-specific presentation (short label, display kind, label resolver, chain
// resolver, free-text flag) to a plain matcher field, keyed by its wire key.
function decorateMatcherField(
  field: FieldDef,
  key: string,
  labels: Record<string, string>,
  resolvers: HistoryFieldResolvers,
): FieldDef {
  const resolveLabelByKey = labelResolvers(resolvers);
  const hints = invalidHints(resolvers.t);
  return {
    ...decorateSharedField(field, sharedKinds[key], resolvers),
    ...(hints[key] ? { invalidHint: hints[key] } : {}),
    ...(labels[key] ? { label: labels[key] } : {}),
    ...(resolveLabelByKey[key] ? { resolveLabel: resolveLabelByKey[key] } : {}),
    ...(freeTextKeys.has(key) ? { freeText: true } : {}),
    // The action pill is the same two request keys under one verb, so it cannot sit beside these.
    ...(key === HistoryEventFilterValueKeys.EVENT_TYPE || key === HistoryEventFilterValueKeys.EVENT_SUBTYPE
      ? { excludes: ['action'] }
      : {}),
  };
}

export function toHistoryEventFields(matchers: Matcher[], resolvers: HistoryFieldResolvers): FieldDef[] {
  const { formatDate, parseDate, t } = resolvers;
  const labels = shortLabels(t);
  const result: FieldDef[] = [];
  for (const matcher of matchers) {
    const key = String(matcher.keyValue ?? matcher.key);
    if (key === HistoryEventFilterValueKeys.MIN_AMOUNT) {
      result.push(toRangeFieldDef({
        key: 'amount',
        label: t('transactions.filter_field_labels.amount'),
        lowerKey: HistoryEventFilterValueKeys.MIN_AMOUNT,
        upperKey: HistoryEventFilterValueKeys.MAX_AMOUNT,
      }));
      continue;
    }
    if (key === HistoryEventFilterValueKeys.START) {
      result.push(toDateFieldDef({
        formatBound: formatDate,
        parseBound: parseDate,
        key: 'period',
        label: t('transactions.filter_field_labels.period'),
        lowerKey: HistoryEventFilterValueKeys.START,
        upperKey: HistoryEventFilterValueKeys.END,
      }));
      continue;
    }
    // Second bound of each collapsed pair is already represented by the pill above.
    if (key === HistoryEventFilterValueKeys.MAX_AMOUNT || key === HistoryEventFilterValueKeys.END)
      continue;
    result.push(decorateMatcherField(toFieldDef(matcher), key, labels, resolvers));
  }
  return result;
}

/**
 * The history account filter (tracked-address `locationLabels`) as a param-bound pill field. It
 * lives outside `toHistoryEventFields` because it is an external filter, not a matcher, and is
 * only offered when the view is not already pinned to an external account set.
 */
/**
 * The history event state markers (matched / customized / imported / profit adjustment /
 * synthetic) as a param-bound pill field. Like the account field it is an external filter rather
 * than a matcher: it rides the `stateMarkers` param, which goes to both the request and the URL.
 *
 * Its values are read by their glyph and colour in the list it came from, so unlike the other
 * non-identity enums it keeps a per-value icon (`resolveIcon`).
 */
export function toHistoryStateField(
  t: Translate,
  states: string[],
  resolveLabel: (value: string) => string,
  resolveIcon: (value: string) => ValueIcon | undefined,
): FieldDef {
  return toParamFieldDef({
    key: 'state',
    label: t('transactions.filter_field_labels.state'),
    multiple: true,
    paramKey: 'stateMarkers',
    resolveIcon,
    resolveLabel,
    suggest: () => states,
    to: 'both',
  });
}

/**
 * The show-ignored-assets toggle as a param-bound boolean pill. A boolean field has no editor and
 * no value segment: adding the pill turns it on, removing it turns it off, which is the whole of
 * its state. The wire form stays inverted (`excludeIgnoredAssets`), handled by the param source.
 */
export function toHistoryIgnoredField(t: Translate): FieldDef {
  return toParamFieldDef({
    key: 'ignored',
    label: t('transactions.filter_field_labels.show_ignored'),
    multiple: false,
    paramKey: 'showIgnoredAssets',
    to: 'both',
    valueType: FilterValueTypes.BOOLEAN,
  });
}

/** One selectable action: a verb standing for exactly one event type/subtype pair. */
export interface ActionFieldOption {
  readonly verbKey: string;
  readonly label: string;
  readonly icon: ValueIcon;
}

/**
 * The event action (verb) as a param-bound pill. An action is one presentation of a single
 * `(eventType, eventSubtype)` pair — the same pairing the event form's action picker uses — so it
 * writes no wire filter of its own: the param source expands the verb into those two request keys.
 * The URL carries only the verb, which is what keeps the user's intent across a reload. Rebuilding
 * from raw types would lose whether they picked an action or set the two fields by hand.
 *
 * It excludes Type and Subtype, and they exclude it: all three drive the same two request keys.
 */
export function toHistoryActionField(t: Translate, actions: () => ActionFieldOption[]): FieldDef {
  // Computed, not a getter that rebuilds. `resolveLabel` and `resolveIcon` are called once per
  // candidate value while the bar narrows, so rebuilding the map inside them cost a full pass over
  // the actions for every value examined - quadratic in the number of verbs, on every keystroke,
  // and every object it allocated was thrown away immediately.
  const byVerb = computed<Map<string, ActionFieldOption>>(
    () => new Map(actions().map(action => [action.verbKey, action])),
  );
  const verbKeys = computed<string[]>(() => actions().map(action => action.verbKey));
  return toParamFieldDef({
    excludes: [HistoryEventFilterValueKeys.EVENT_TYPE, HistoryEventFilterValueKeys.EVENT_SUBTYPE],
    key: 'action',
    label: t('transactions.filter_field_labels.action'),
    multiple: false,
    paramKey: 'action',
    resolveIcon: (value: string): ValueIcon | undefined => get(byVerb).get(value)?.icon,
    resolveLabel: (value: string): string => get(byVerb).get(value)?.label ?? value,
    suggest: (): string[] => get(verbKeys),
    to: 'url',
  });
}

/** What the account field needs from the account store, grouped so the argument list stays short. */
export interface AccountFieldOptions {
  /** Tracked addresses, offered as the field's values. */
  readonly suggest: () => string[];
  /** Address -> the name shown on the pill, else the shortened address. */
  readonly resolveLabel: (value: string) => string;
  /** Address -> the muted address shown beside a name. */
  readonly resolveCaption: (value: string) => string | undefined;
  /** Address -> `address name tags`, so the bar can find an account by any of them. */
  readonly resolveKeywords: (value: string) => string | undefined;
}

/**
 * It offers its tracked addresses as values, so an account can be applied straight from the bar's
 * inline input the way a location or protocol can — matched on its address, name or ENS, none of
 * which the pill's own label reliably shows (it is a name, or a shortened, scrambled address).
 */
export function toHistoryAccountField(t: Translate, accounts: AccountFieldOptions): FieldDef {
  return toParamFieldDef({
    display: DisplayKinds.ACCOUNT,
    key: 'account',
    label: t('transactions.filter_field_labels.account'),
    multiple: true,
    paramKey: 'locationLabels',
    resolveCaption: accounts.resolveCaption,
    resolveKeywords: accounts.resolveKeywords,
    resolveLabel: accounts.resolveLabel,
    suggest: accounts.suggest,
    to: 'request',
  });
}
