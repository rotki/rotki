import type { ActiveFilter, TypedFilterDraft } from '@/modules/core/table/pill/core/types';
import { FilterOps } from '@/modules/core/table/filtering';

/**
 * Readers of the bar's inline input for the fields with no option list to match against: an amount
 * and a date are written down rather than picked, so narrowing cannot rank them against labels.
 *
 * @remarks
 * A field owns the interpretation of what was typed, through `FieldDef.parseTyped`, the same way it
 * owns its label and icon resolution. That keeps this layer free of any table's or locale's notion
 * of what a date looks like: the timestamp parser is injected.
 *
 * @packageDocumentation
 */

/**
 * Turns a written date into the wire value a bound stores (for history, the unix second the
 * picker itself emits), or `undefined` when the text is not a date the user's format can express.
 */
export type ParseTimestamp = (value: string) => string | undefined;

const NUMBER = String.raw`\d+(?:\.\d+)?`;

/** `>100`, `>= 1.5`, `<50`. The `=>`/`=<` spellings are accepted because people type them. */
const COMPARISON = new RegExp(String.raw`^(>=|=>|>|<=|=<|<)\s*(${NUMBER})$`);

/** `10-50`, `10 .. 50`, `10 to 50`. */
const SPAN = new RegExp(String.raw`^(${NUMBER})\s*(?:\.\.|-|to)\s*(${NUMBER})$`, 'i');

const BARE_NUMBER = new RegExp(String.raw`^${NUMBER}$`);

/**
 * The words an amount bound can be written with: `over 100`, `less than 50`, `at least 10`.
 *
 * A date has had `after`/`before` from the start while an amount had only the symbols, which left
 * the bar contradicting itself: a typed `100` offers rows labelled `greater than 100` and
 * `less than 100`, and typing back what the row said did nothing at all.
 *
 * `than` is optional because people leave it out, and the pairs are listed rather than built from a
 * stem so that adding one is a decision rather than an accident of a regex.
 */
const RANGE_WORD = new RegExp(
  String.raw`^((?:more|greater|larger|bigger)(?:\s+than)?|over|above|at\s+least`
  + String.raw`|(?:less|smaller|lower|fewer)(?:\s+than)?|under|below|at\s+most|up\s+to)\s+(${NUMBER})$`,
  'i',
);

/** Which of {@link RANGE_WORD}'s markers name the upper bound. */
const RANGE_UPPER_WORDS = /^(?:less|smaller|lower|fewer|under|below|at\s+most|up\s+to)/i;

/**
 * A date written out in full: two matching separators, so `1.5` and `2024` stay amounts rather
 * than being read as half a date. Which side is the day is the injected parser's business, not
 * this pattern's. An optional time may follow.
 */
const WRITTEN_DATE = /^\d{1,4}([/.-])\d{1,2}\1\d{1,4}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?$/;

/** `> 15/01/2024`, `after 15/01/2024`, and the same for the upper bound. */
const DATE_COMPARISON = /^(>=|=>|>|<=|=<|<)\s*(.+)$/;
const DATE_WORD = /^(after|before|since|until)\s+(.+)$/i;

/** `15/01/2024 - 20/01/2024`. The separator needs spaces, or `15-01-2024` would split itself. */
const DATE_SPAN = /^(.+?)\s+(?:\.\.|-|to)\s+(.+)$/i;

const UPPER_BOUND_MARKERS = /^(?:<=|=<|<|before|until)$/i;

/** A comparison marker on its own, with nothing after it yet. */
const BARE_MARKER = /^(?:>=|=>|>|<=|=<|<)$/;

/** A comparison marker and whatever has been typed after it, which may be nothing. */
const COMPARISON_MARKER = /^(?:>=|=>|>|<=|=<|<)\s*(.*)$/;

/** A date word on its own, or one whose date is still being written. */
const DATE_WORD_STARTED = /^(?:after|before|since|until)\b/i;

/**
 * A date on its way to being written. Looser than {@link WRITTEN_DATE}, which wants a whole date,
 * but not loose enough to claim an amount: one separator counts only while nothing follows it
 * (`15.`, `15-`) or when it is a slash, which no amount contains. So `1.5` stays an amount and
 * `10-50` stays a span, while the second separator makes `15.01.` a date beyond doubt.
 */
const DATE_STARTED = /^\d{1,4}(?:[/.-]\d{0,4}[/.-]\d{0,4}|\/\d{0,2}|[.-])(?:\s.*)?$/;

/** A number on its way to being written, including the trailing dot of `1.`. */
const NUMBER_STARTED = /^\d+\.?\d*$/;

/** An amount word on its own, or one whose number is still being written. */
const RANGE_WORD_STARTED = /^(?:more|greater|larger|bigger|over|above|at|less|smaller|lower|fewer|under|below|up)\b/i;

/** A span whose second bound is still missing: `10 -`, `10 to`, `15/01/2024 ..`. */
const SPAN_STARTED = /\s*(?:\.\.|-|to)\s*$/i;

function rangeDraft(op: ActiveFilter['op'], min?: string, max?: string): TypedFilterDraft {
  return { op, range: { ...(min ? { min } : {}), ...(max ? { max } : {}) }, values: [] };
}

function dateDraft(op: ActiveFilter['op'], from?: string, to?: string): TypedFilterDraft {
  return { date: { ...(from ? { from } : {}), ...(to ? { to } : {}) }, op, values: [] };
}

/**
 * The filters a numeric field can offer for what was typed.
 *
 * A bare number is ambiguous on purpose and yields both directions: `100` cannot say whether the
 * user means at least or at most, and guessing one would be wrong half the time. An explicit
 * comparison or a span says it outright and yields exactly one.
 */
export function parseRangeQuery(query: string): TypedFilterDraft[] {
  const typed = query.trim();

  const comparison = COMPARISON.exec(typed);
  if (comparison) {
    const [, marker, amount] = comparison;
    return marker.includes('<')
      ? [rangeDraft(FilterOps.LT, undefined, amount)]
      : [rangeDraft(FilterOps.GT, amount)];
  }

  // After the symbols and before the span: a span always leads with its lower bound, so a query
  // opening with a word cannot be one.
  const worded = RANGE_WORD.exec(typed);
  if (worded) {
    const [, marker, amount] = worded;
    return RANGE_UPPER_WORDS.test(marker)
      ? [rangeDraft(FilterOps.LT, undefined, amount)]
      : [rangeDraft(FilterOps.GT, amount)];
  }

  const span = SPAN.exec(typed);
  if (span) {
    const [, first, second] = span;
    // Written the wrong way round is still clear about which two bounds are meant, and the editor
    // rejects a max below its min, so a reversed span would otherwise offer a filter it refuses.
    const ascending = Number(first) <= Number(second);
    return [rangeDraft(FilterOps.BETWEEN, ascending ? first : second, ascending ? second : first)];
  }

  if (BARE_NUMBER.test(typed))
    return [rangeDraft(FilterOps.GT, typed), rangeDraft(FilterOps.LT, undefined, typed)];

  return [];
}

/** The filters a date field can offer, in the same shape and for the same reasons. */
export function parseDateQuery(query: string, parse: ParseTimestamp): TypedFilterDraft[] {
  const typed = query.trim();

  const prefixed = DATE_COMPARISON.exec(typed) ?? DATE_WORD.exec(typed);
  if (prefixed) {
    const [, marker, rest] = prefixed;
    const bound = boundOf(rest, parse);
    if (!bound)
      return [];
    return UPPER_BOUND_MARKERS.test(marker)
      ? [dateDraft(FilterOps.BEFORE, undefined, bound)]
      : [dateDraft(FilterOps.AFTER, bound)];
  }

  const span = DATE_SPAN.exec(typed);
  if (span) {
    const from = boundOf(span[1], parse);
    const to = boundOf(span[2], parse);
    return from && to ? [dateDraft(FilterOps.BETWEEN, from, to)] : [];
  }

  const bound = boundOf(typed, parse);
  if (!bound)
    return [];
  return [dateDraft(FilterOps.AFTER, bound), dateDraft(FilterOps.BEFORE, undefined, bound)];
}

/**
 * Whether the query is on its way to a date filter, whether or not it is one yet.
 *
 * The counterpart of {@link parseDateQuery} for what has been typed *so far*. A half-written date
 * parses to nothing, and showing nothing for it reads as "this field cannot be typed into" rather
 * than "keep going". A field that says yes here is offered with its syntax example instead.
 *
 * Wider than the parser on purpose, and narrower than "any text": it must not claim a bare number,
 * which belongs to the amount fields.
 */
export function looksLikeDateQuery(query: string): boolean {
  const typed = query.trim();
  if (!typed)
    return false;
  if (DATE_WORD_STARTED.test(typed))
    return true;
  // A bare marker is ambiguous between a date and an amount, so both fields claim it and the user
  // sees the two syntaxes side by side, which is exactly the ambiguity they are in.
  if (BARE_MARKER.test(typed))
    return true;

  // A half-written span needs no case of its own: whatever follows the first date is swallowed by
  // `DATE_STARTED`, and matching a trailing separator on its own would claim every word ending in
  // `to` or `-`.
  const prefixed = DATE_COMPARISON.exec(typed);
  return DATE_STARTED.test((prefixed ? prefixed[2] : typed).trim());
}

/** {@link looksLikeDateQuery} for an amount: a marker, a partial number, or a half-written span. */
export function looksLikeRangeQuery(query: string): boolean {
  const typed = query.trim();
  if (!typed)
    return false;
  if (BARE_MARKER.test(typed) || RANGE_WORD_STARTED.test(typed))
    return true;

  const prefixed = COMPARISON_MARKER.exec(typed);
  const rest = (prefixed ? prefixed[1] : typed).trim();
  // A span still missing its upper bound (`10 -`) keeps the number in front of the separator.
  const head = rest.replace(SPAN_STARTED, '').trim();
  return NUMBER_STARTED.test(head);
}

/**
 * The wire value for one written date, gated by the shape check first: the injected parser is
 * lenient (it reads `1.5` as a day and a month), so it is only asked about text that already
 * looks like a whole date.
 */
function boundOf(text: string, parse: ParseTimestamp): string | undefined {
  const trimmed = text.trim();
  return WRITTEN_DATE.test(trimmed) ? parse(trimmed) : undefined;
}
