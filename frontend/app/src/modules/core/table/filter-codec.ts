import type {
  MatchedKeyword,
  MatchedKeywordWithBehaviour,
  SearchMatcher,
  Suggestion,
} from '@/modules/core/table/filtering';
import { arrayify } from '@/modules/core/common/data/array';

/**
 * The pure filter codec: the two transforms between the chip selection (the editing
 * model) and the backend `matches` object (the wire/URL shape). Extracted from
 * `useFilterSelection.updateMatches` / `restoreSelection`, minus the ref writes and the
 * `emit`, so the round-trip is testable with no Vue, no DOM, no mount.
 *
 * This is the Stage 4 `useFilterModel` Layer-1 core (see the design spec). The first
 * cut keeps the current `Suggestion[]` model and matcher resolvers; the `FieldDef` /
 * `ActiveFilter[]` modernization (operators, range/date collapse) is the later pill-bar
 * schema phase.
 */

type AnyMatcher = SearchMatcher<string, string>;

type MatcherResolver = (key: string | undefined) => AnyMatcher | undefined;

export interface MatchesFromSelectionResult {
  matches: Partial<MatchedKeyword<string>>;
  /** The subset of the input that produced a valid match, in input order. */
  validSelection: Suggestion[];
}

/** One chip -> its wire value, or `undefined` when the chip is invalid and must be dropped. */
function serializeChip(entry: Suggestion, matcher: AnyMatcher): string | boolean | undefined {
  if ('string' in matcher) {
    if (typeof entry.value !== 'string' || !matcher.validate(entry.value))
      return undefined;
    const serialized = matcher.serializer?.(entry.value) ?? entry.value;
    return entry.exclude ? `!${serialized}` : serialized;
  }
  if ('asset' in matcher)
    return typeof entry.value !== 'string' ? entry.value.identifier : entry.value;
  return true;
}

/**
 * state -> matches. Serializes each chip through its matcher (string validate + optional
 * serializer + `!` exclusion; asset -> identifier; boolean -> true), grouping `multiple`
 * matchers into arrays. Chips that fail are dropped and excluded from `validSelection`.
 */
export function matchesFromSelection(
  selection: Suggestion[],
  matcherForKey: MatcherResolver,
): MatchesFromSelectionResult {
  const matches: Partial<MatchedKeyword<string>> = {};
  const validSelection: Suggestion[] = [];

  for (const entry of selection) {
    const matcher = matcherForKey(entry.key);
    if (!matcher)
      continue;

    const transformed = serializeChip(entry, matcher);
    if (!transformed)
      continue;

    validSelection.push(entry);

    const valueKey = matcher.keyValue ?? matcher.key;
    if (matcher.multiple) {
      // `multiple` matchers are string/asset, so their serialized value is always a string.
      const existing = matches[valueKey];
      const values = Array.isArray(existing) ? existing : [];
      values.push(String(transformed));
      matches[valueKey] = values;
    }
    else {
      matches[valueKey] = transformed;
    }
  }

  return { matches, validSelection };
}

/**
 * A resolved asset value cannot be rebuilt from its identifier, so the prior selection is reused when
 * one exists. Takes the key and deserializer rather than the matcher, since the caller has already
 * narrowed it to the asset variant.
 */
function deserializeAssetValue(
  value: string | boolean,
  key: string,
  deserializer: ((value: string) => Suggestion['value']) | undefined,
  previous: Suggestion[],
): { value: Suggestion['value']; exclude: boolean } | undefined {
  const prev = previous.find(item => item.key === key);
  if (prev)
    return { exclude: false, value: prev.value };

  if (typeof value !== 'string')
    return undefined;

  return { exclude: false, value: deserializer?.(value) ?? value };
}

/** One wire value -> a decoded chip value + exclusion, or `undefined` to skip it. */
function deserializeValue(
  value: string | boolean,
  matcher: AnyMatcher,
  previous: Suggestion[],
): { value: Suggestion['value']; exclude: boolean } | undefined {
  if ('asset' in matcher)
    return deserializeAssetValue(value, matcher.key, matcher.deserializer, previous);

  if ('boolean' in matcher || typeof value === 'boolean')
    return { exclude: false, value: true };

  if (typeof value !== 'string')
    return undefined;

  const excluded = value.startsWith('!');
  const normalized = excluded ? value.substring(1) : value;
  return { exclude: excluded, value: matcher.deserializer?.(normalized) ?? normalized };
}

/**
 * matches -> state. Rebuilds the chip selection from the wire object, resolving `!`
 * exclusion and each matcher's deserializer. `previous` carries the prior selection so a
 * resolved asset value survives the round-trip (an asset identifier alone cannot rebuild
 * its display info). A key with no matcher, or an empty value, is skipped.
 */
export function selectionFromMatches(
  matches: MatchedKeywordWithBehaviour<string>,
  matcherForKeyValue: MatcherResolver,
  previous: Suggestion[] = [],
): Suggestion[] {
  const selection: Suggestion[] = [];

  for (const [key, value] of Object.entries(matches)) {
    const matcher = matcherForKeyValue(key);
    if (!(matcher && value))
      continue;

    for (const raw of arrayify(value)) {
      // Behaviour-wrapped values ({ behaviour, values }) are not chips; the pill schema
      // will model exclusion as an operator. For now, skip them as the old codec did.
      if (typeof raw !== 'string' && typeof raw !== 'boolean')
        continue;

      const decoded = deserializeValue(raw, matcher, previous);
      if (decoded === undefined)
        continue;

      selection.push({
        asset: 'asset' in matcher,
        exclude: decoded.exclude,
        index: 0,
        key: matcher.key,
        total: 1,
        value: decoded.value,
      });
    }
  }

  return selection;
}
