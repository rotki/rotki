import type { ComputedRef } from 'vue';
import type { SyntaxHints } from '@/modules/core/table/pill/core/narrowing';
import { convertFromTimestamp } from '@/modules/core/common/data/date';
import { FilterValueTypes } from '@/modules/core/table/filtering';
import { useSetting } from '@/modules/settings/use-setting';

/**
 * The date the syntax example is written with: a real, past date whose day is past the twelfth, so
 * it cannot be misread as the month and the example states the user's field order unambiguously.
 * Past, because the bound parser refuses a future date and an example nobody can copy is worse than
 * none (`dateBoundParser`).
 *
 * Local midnight, not a fixed unix second: the formatter appends ` HH:mm` to any timestamp that is
 * not on midnight *locally*, so a fixed instant would grow a time of day in most of the world and
 * the example would read `15/01/2024 14:00`.
 */
const EXAMPLE_TIMESTAMP = new Date(2024, 0, 15).getTime() / 1000;

/** The upper bound of the range example, five days on, so the two dates are visibly a span. */
const EXAMPLE_END_TIMESTAMP = new Date(2024, 0, 20).getTime() / 1000;

/**
 * What the bar says about the fields that are typed into rather than picked from.
 *
 * These fields were undiscoverable: nothing on screen said a date or an amount could be written
 * into the bar, the field is labelled `Period` rather than `Date`, and a half-written date matched
 * nothing at all. The keywords make the fields reachable under the words people actually use, and
 * the examples state the syntax on the field's own row.
 *
 * Per value type, not per table: `>100` reads the same everywhere, so no table restates it. The
 * pure narrowing core takes these as a parameter, the same way it takes the operator labels.
 */
export function usePillSyntaxHints(): ComputedRef<SyntaxHints> {
  const { t } = useI18n({ useScope: 'global' });
  const dateInputFormat = useSetting('dateInputFormat');

  // In the user's own format: an example reading `01/15/2024` to someone who writes dates
  // day-first teaches the wrong order, and the order is the whole thing the example is for.
  const exampleDate = computed<string>(() => convertFromTimestamp(EXAMPLE_TIMESTAMP, get(dateInputFormat)));
  const exampleEndDate = computed<string>(() => convertFromTimestamp(EXAMPLE_END_TIMESTAMP, get(dateInputFormat)));

  return computed<SyntaxHints>(() => ({
    // Literal, and deliberately not translated: `after` and `to` are the words the parser knows,
    // so a translated example would be one the user copies and the bar then refuses. The operator
    // forms lead, because the bare date alone never showed that an operator was possible at all.
    examples: {
      // `before` earns its own chip even though `after` shows the shape: which words the parser
      // knows is not guessable (`since` and `until` work, `from` and `to` do not), and its only
      // other route was reading it off a bare date's result rows — which are *translated*, while
      // the parser only knows the English words, so that route does not survive a locale change.
      [FilterValueTypes.DATE]: [
        `after ${get(exampleDate)}`,
        `before ${get(exampleDate)}`,
        `${get(exampleDate)} - ${get(exampleEndDate)}`,
      ],
      // One per shape, the same as the dates above: an upper bound, a lower bound, a span. Nothing
      // else on screen distinguishes them, and a chip for only one direction reads as though that
      // is the direction the bar supports.
      [FilterValueTypes.RANGE]: ['>100', '<10', '10 - 50'],
    },
    keywords: {
      [FilterValueTypes.DATE]: t('table_filter.pill.syntax.date_keywords'),
      [FilterValueTypes.RANGE]: t('table_filter.pill.syntax.range_keywords'),
    },
  }));
}
