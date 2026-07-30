import type { ActiveFilter, TypedFilterDraft } from '@/modules/core/table/pill/core/types';
import { FilterOps } from '@/modules/core/table/filtering';

/**
 * Readers of the bar's inline input for the fields that have no option list to match against:
 * an amount and a date are not picked from a list, they are written down. Typing `>100` or
 * `15/01/2024` used to offer nothing at all, since narrowing could only rank a query against
 * labels and option values.
 *
 * A field owns the interpretation of what was typed (`FieldDef.parseTyped`), the same way it owns
 * its label and icon resolution, so this layer stays free of any table's or locale's notion of
 * what a date looks like: the timestamp parser is injected.
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
 * The wire value for one written date, gated by the shape check first: the injected parser is
 * lenient (it reads `1.5` as a day and a month), so it is only asked about text that already
 * looks like a whole date.
 */
function boundOf(text: string, parse: ParseTimestamp): string | undefined {
  const trimmed = text.trim();
  return WRITTEN_DATE.test(trimmed) ? parse(trimmed) : undefined;
}
