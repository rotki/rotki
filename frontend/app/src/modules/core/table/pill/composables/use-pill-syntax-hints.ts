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
 *
 * @remarks
 * The examples themselves stay literal and untranslated. `after`, `before` and `to` are the words
 * the parser knows, so a translated example is one the user copies and the bar then refuses.
 *
 * Each shape gets its own chip — upper bound, lower bound, span — and `before` earns one even
 * though `after` already shows the form. Which words the parser accepts is not guessable (`since`
 * and `until` work, `from` and `to` do not), and a chip for one direction alone reads as though
 * that is the only direction the bar supports.
 */
export function usePillSyntaxHints(): ComputedRef<SyntaxHints> {
  const { t } = useI18n({ useScope: 'global' });
  const dateInputFormat = useSetting('dateInputFormat');

  const exampleDate = computed<string>(() => convertFromTimestamp(EXAMPLE_TIMESTAMP, get(dateInputFormat)));
  const exampleEndDate = computed<string>(() => convertFromTimestamp(EXAMPLE_END_TIMESTAMP, get(dateInputFormat)));

  return computed<SyntaxHints>(() => ({
    examples: {
      [FilterValueTypes.DATE]: [
        `after ${get(exampleDate)}`,
        `before ${get(exampleDate)}`,
        `${get(exampleDate)} - ${get(exampleEndDate)}`,
      ],
      [FilterValueTypes.RANGE]: ['>100', '<10', '10 - 50'],
    },
    keywords: {
      [FilterValueTypes.DATE]: t('table_filter.pill.syntax.date_keywords'),
      [FilterValueTypes.RANGE]: t('table_filter.pill.syntax.range_keywords'),
    },
  }));
}
