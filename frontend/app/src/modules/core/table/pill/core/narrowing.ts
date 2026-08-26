import type { OperatorLabels } from '@/modules/core/table/pill/core/operators';
import type { ActiveFilter, FieldDef, FilterValueType } from '@/modules/core/table/pill/core/types';
import { FilterValueTypes } from '@/modules/core/table/filtering';
import { pillOperator, pillValueSummary } from '@/modules/core/table/pill/core/format';
import { resolveText } from '@/modules/core/table/pill/core/text';

/** Offers the field itself: picking it adds an empty pill and opens its value editor. */
interface FieldSuggestion {
  readonly kind: 'field';
  readonly field: FieldDef;
  readonly label: string;
}

/** Offers one concrete value of a field: picking it applies the filter in a single step. */
interface ValueSuggestion {
  readonly kind: 'value';
  readonly field: FieldDef;
  readonly value: string;
  readonly label: string;
  /**
   * Muted secondary text telling two same-labelled values apart: the same symbol exists on every
   * chain, so a list of five `USDC` rows is unusable without it.
   */
  readonly caption?: string;
  /**
   * The chain this value belongs to, rendered as an icon after it. Carried on the suggestion
   * rather than resolved from the value, since a just-searched asset is not in any cache yet.
   */
  readonly chain?: string;
}

/**
 * Offers a whole filter read out of what was typed (`>100`, `15/01/2024`): picking it applies that
 * filter in one step, the same as a value row does. A separate kind because an amount or a date is
 * not one of a list of values, it is an operator and one or two bounds.
 */
interface FilterSuggestion {
  readonly kind: 'filter';
  readonly field: FieldDef;
  readonly filter: ActiveFilter;
  readonly label: string;
}

export type NarrowSuggestion = FieldSuggestion | ValueSuggestion | FilterSuggestion;

/** The values already filtered by, per field, offered to fields that have no option list. */
export type RecentValues = (field: FieldDef) => string[];

/**
 * What the bar says about the fields whose values are written rather than picked, keyed by value
 * type rather than by field: `>100` and `after 15/01/2024` read the same on every table, so the
 * copy belongs to the type and no table restates it.
 *
 * Already translated, and the date example is rendered in the user's own date format: a hint
 * showing `01/15/2024` to someone whose format is day-first teaches the wrong order.
 */
export interface SyntaxHints {
  /** Extra words a field of this type is findable by ("date time when"), beyond its own label. */
  readonly keywords?: Partial<Record<FilterValueType, string>>;
  /**
   * Worked examples of what can be typed, shown verbatim in the popover's footer. Literal, never
   * translated: the operator words the parser knows (`after`, `before`) are English, so a
   * translated example would not work when the user copies it.
   */
  readonly examples?: Partial<Record<FilterValueType, readonly string[]>>;
}

/**
 * The examples worth showing for the fields currently on offer.
 *
 * Only for the value types actually present: a table with no amount field must not advertise
 * `>100`, and one whose period pill is already set has nothing left to say about dates.
 */
export function syntaxExamples(fields: FieldDef[], hints?: SyntaxHints): string[] {
  const types = new Set(fields.filter(field => field.matchesTyped).map(field => field.valueType));
  return [...types].flatMap(type => hints?.examples?.[type] ?? []);
}

export interface NarrowLimits {
  /** Values offered per field, so one long option list cannot crowd out the others. */
  readonly perField: number;
  /** Total suggestions returned. */
  readonly total: number;
}

const DEFAULT_LIMITS: NarrowLimits = { perField: 5, total: 20 };

/**
 * Match rank, lower is better: a label that starts with the query beats one that merely
 * contains it, and a field beats one of its own values (the field is the broader answer).
 */
const RANK_FIELD_PREFIX = 0;
const RANK_VALUE_PREFIX = 1;
const RANK_FIELD_SUBSTRING = 2;
const RANK_VALUE_SUBSTRING = 3;
// A typed-value offer is ranked last: it always matches, so it must never crowd out a real one.
const RANK_TYPED_VALUE = 4;
// Below everything that matched something concrete: guidance is what a field offers when it has
// nothing to answer with yet, so any real match is a better answer than telling the user the syntax.
const RANK_GUIDANCE = 5;

/**
 * How many filters one field may offer for a single query. Two is what an ambiguous bare number
 * needs ("at least" and "at most"); more than that and one field's guesses would crowd the list.
 */
const TYPED_FILTER_CAP = 2;

function rankOf(label: string, query: string, prefixRank: number, substringRank: number): number | undefined {
  const haystack = label.toLowerCase();
  if (haystack.startsWith(query))
    return prefixRank;
  if (haystack.includes(query))
    return substringRank;
  return undefined;
}

/**
 * The values a field can offer from a list. Only synchronous option lists qualify: a free-text
 * field has no list (it offers what was typed instead, see `typedValueSuggestion`) and an asset
 * field resolves its options over the network, which the pure core does not do.
 */
function suggestibleValues(field: FieldDef): string[] {
  if (field.freeText || field.valueType !== FilterValueTypes.ENUM || !field.suggest)
    return [];
  return field.suggest();
}

/**
 * A free-text field has no options to match against, so it offers what was typed as the value
 * itself: paste a transaction hash and the row to filter by it is right there. The field's own
 * validator decides whether the query is a plausible value, which keeps a half-typed hash from
 * being offered as a real one.
 *
 * The typed text is echoed as-is rather than through the field's display resolver: a row that
 * answers what the user typed has to show what they typed.
 */
function typedValueSuggestion(field: FieldDef, query: string): NarrowSuggestion | undefined {
  if (!field.freeText || (field.validate && !field.validate(query)))
    return undefined;
  return { field, kind: 'value', label: query, value: query };
}

/**
 * The filters a field reads out of the typed query, labelled the way the resulting pill will read
 * so the row and the pill it produces cannot disagree. The operator is shown unless it is the
 * field's default, exactly as on a pill, so a `between` row reads `10 - 50` and a `gt` one reads
 * `greater than 10`.
 */
function typedFilterMatches(field: FieldDef, typed: string, operatorLabels: OperatorLabels): Ranked[] {
  if (!field.parseTyped)
    return [];

  return field.parseTyped(typed).slice(0, TYPED_FILTER_CAP).map((draft) => {
    const filter: ActiveFilter = { ...draft, fieldKey: field.key };
    const op = pillOperator(field, filter);
    const operator = op ? operatorLabels[op] : undefined;
    const summary = pillValueSummary(field, filter);
    return {
      rank: RANK_TYPED_VALUE,
      suggestion: { field, filter, kind: 'filter', label: operator ? `${operator} ${summary}` : summary },
    };
  });
}

/**
 * Every field offered as itself, which is what the bar shows before anything is typed: clicking
 * into the input is the discoverable entry point, so it lists what can be filtered on rather
 * than an empty state.
 */
export function fieldSuggestions(fields: FieldDef[]): NarrowSuggestion[] {
  return fields.map(field => fieldRow(field, resolveText(field.label)));
}

/** One field as a row. The typed syntax is stated by the popover's footer, not per row. */
function fieldRow(field: FieldDef, label: string): FieldSuggestion {
  return { field, kind: 'field', label };
}

/**
 * Cross-field narrowing for the bar's inline input: one query ranked against every field
 * label and every field's option labels at once, so typing `eth` surfaces both the Asset
 * field and the concrete `ETH` value without the user picking a field first.
 *
 * Pure: options and their display labels come off the `FieldDef`, never from a store.
 *
 * @param query - what the user typed; blank yields nothing, so the bar shows no popover
 * @param fields - the fields still available; callers pass the ones without an active filter
 * @param limits - caps on how many suggestions come back
 * @returns suggestions, best match first
 */
interface Ranked {
  readonly rank: number;
  readonly suggestion: NarrowSuggestion;
}

/**
 * The field itself, when its label matches, or failing that when one of the words its value type
 * is known by does. A period field is labelled `Period`, so `date`, `time` and `when` found nothing
 * at all; the type keywords are what make it reachable under the word the user actually has in mind.
 * A keyword hit ranks as a substring match, never a prefix one, so a visible label always wins.
 *
 * The blob is a bag of words and is matched only where a word begins: searched as one string it
 * hands back the field for any fragment sitting inside a keyword, and `in` (in `since`) or `an`
 * (in `range`) then put Period and Amount above every real value match on a two-letter query.
 * From a word start rather than per token, so the multi-word keywords (`at least`, `at most`)
 * stay reachable, and by prefix, so the list still narrows while the user types a keyword out.
 */
function keywordMatch(keywords: string | undefined, needle: string): boolean {
  if (!keywords)
    return false;
  const blob = keywords.toLowerCase();
  return [...blob.matchAll(/\S+/g)].some(word => blob.startsWith(needle, word.index));
}

function fieldMatch(field: FieldDef, needle: string, hints?: SyntaxHints): Ranked | undefined {
  const label = resolveText(field.label);
  const rank = rankOf(label, needle, RANK_FIELD_PREFIX, RANK_FIELD_SUBSTRING);
  if (rank !== undefined)
    return { rank, suggestion: fieldRow(field, label) };

  return keywordMatch(hints?.keywords?.[field.valueType], needle)
    ? { rank: RANK_FIELD_SUBSTRING, suggestion: fieldRow(field, label) }
    : undefined;
}

/**
 * The field offered for a query that is heading towards a filter on it but is not one yet.
 *
 * Typing `after`, `>` or `15/01` parses to nothing, and nothing is what the popover showed: an
 * empty list, which says the bar does not take typed dates when in fact it does and the user was
 * one keystroke away. Offering the field keeps the footer's syntax on screen beside it.
 */
function guidanceMatch(field: FieldDef, typed: string): Ranked | undefined {
  if (!field.matchesTyped?.(typed))
    return undefined;
  return { rank: RANK_GUIDANCE, suggestion: fieldRow(field, resolveText(field.label)) };
}

/**
 * Matches from a field's own option list, under their display labels — and, failing that, under
 * whatever extra text the field exposes for the value (`resolveKeywords`). The label is not always
 * what the user has in hand: an account shows a name or a shortened, scrambled address, so an ENS
 * name or a pasted full address only matches through the keywords. A keyword hit ranks as a
 * substring match, never a prefix one, so a visible label always wins over hidden text.
 */
function rankValue(field: FieldDef, label: string, value: string, needle: string): number | undefined {
  const rank = rankOf(label, needle, RANK_VALUE_PREFIX, RANK_VALUE_SUBSTRING);
  if (rank !== undefined)
    return rank;
  const keywords = field.resolveKeywords?.(value)?.toLowerCase();
  return keywords?.includes(needle) ? RANK_VALUE_SUBSTRING : undefined;
}

function listMatches(field: FieldDef, needle: string, perField: number): Ranked[] {
  const matches: Ranked[] = [];
  for (const value of suggestibleValues(field)) {
    if (matches.length >= perField)
      break;
    const label = field.resolveLabel ? field.resolveLabel(value) : value;
    const rank = rankValue(field, label, value, needle);
    if (rank === undefined)
      continue;
    // Only set when there is one: an explicit `caption: undefined` is a different object.
    const caption = field.resolveCaption?.(value);
    matches.push({ rank, suggestion: { field, kind: 'value', label, value, ...(caption ? { caption } : {}) } });
  }
  return matches;
}

/**
 * Matches among the values this field has already been filtered by.
 *
 * Matched on the stored value but shown through the field's resolver, like every other value row.
 * The two differ for exactly the fields this list serves: an address resolves to a shortened and,
 * in privacy mode, scrambled form, so labelling the row with the raw value would put the real
 * address on screen while the pill it creates hides it.
 */
function recentMatches(field: FieldDef, needle: string, perField: number, recent: string[]): Ranked[] {
  const matches: Ranked[] = [];
  for (const value of recent) {
    if (matches.length >= perField)
      break;
    const rank = rankOf(value, needle, RANK_VALUE_PREFIX, RANK_VALUE_SUBSTRING);
    if (rank !== undefined) {
      const label = field.resolveLabel ? field.resolveLabel(value) : value;
      matches.push({ rank, suggestion: { field, kind: 'value', label, value } });
    }
  }
  return matches;
}

/** Everything one query is ranked against, gathered so the per-field pass takes one parameter. */
interface RankContext {
  readonly needle: string;
  readonly typed: string;
  readonly operatorLabels: OperatorLabels;
  readonly limits: NarrowLimits;
  readonly recentValues?: RecentValues;
  readonly hints?: SyntaxHints;
}

/** Every way one field can answer the query, in one list. */
function rankField(field: FieldDef, context: RankContext): Ranked[] {
  const { hints, limits, needle, operatorLabels, recentValues, typed } = context;
  const remembered = recentValues?.(field) ?? [];
  const matched = fieldMatch(field, needle, hints);
  // Read as a whole filter, for the fields whose values are written rather than picked.
  const parsed = typedFilterMatches(field, typed, operatorLabels);
  // Guidance only when the query yielded nothing on this field: a query that already reads as a
  // filter gets the filter itself, and repeating the field beneath it says nothing new.
  const guidance = parsed.length === 0 && !matched ? guidanceMatch(field, typed) : undefined;
  const typedValue = typedValueSuggestion(field, typed);

  return [
    ...(matched ? [matched] : []),
    ...listMatches(field, needle, limits.perField),
    // A value used before beats the raw typed one: it is a value known to have been wanted.
    ...recentMatches(field, needle, limits.perField, remembered),
    ...parsed,
    ...(guidance ? [guidance] : []),
    // Already offered as a remembered value; do not repeat it as the typed one.
    ...(typedValue && !remembered.includes(typed) ? [{ rank: RANK_TYPED_VALUE, suggestion: typedValue }] : []),
  ];
}

/**
 * Cross-field narrowing for the bar's inline input: one query ranked against every field label,
 * every field's option labels, and every value the field was filtered by before, so typing `eth`
 * surfaces both the Asset field and the concrete `ETH` value without picking a field first.
 *
 * Pure: options, display labels and remembered values all arrive as parameters, never from a store.
 *
 * @param query - what the user typed; blank yields nothing, so the bar shows no popover
 * @param fields - the fields still available; callers pass the ones without an active filter
 * @param operatorLabels - already-translated operator labels, for the rows read out of the query
 * @param limits - caps on how many suggestions come back
 * @param recentValues - values already filtered by, per field, for those with no option list
 * @param hints - per-value-type keywords and syntax examples for the fields that are typed into
 * @returns suggestions, best match first
 */
export function searchFieldsAndValues(
  query: string,
  fields: FieldDef[],
  operatorLabels: OperatorLabels,
  limits: NarrowLimits = DEFAULT_LIMITS,
  recentValues?: RecentValues,
  hints?: SyntaxHints,
): NarrowSuggestion[] {
  const needle = query.toLowerCase().trim();
  if (!needle)
    return [];

  const typed = query.trim();
  const ranked = fields.flatMap(field => rankField(field, { hints, limits, needle, operatorLabels, recentValues, typed }));

  // Stable within a rank, so fields keep their declared order and values keep their option order.
  return ranked
    .map((entry, index) => ({ ...entry, index }))
    .sort((a, b) => (a.rank - b.rank) || (a.index - b.index))
    .slice(0, limits.total)
    .map(entry => entry.suggestion);
}
