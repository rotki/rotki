import { z, type ZodType } from 'zod';

export interface MatchingSettingsMessages {
  toleranceMax: string;
  toleranceMin: string;
  timeRangeMin: string;
}

/** The bounds the backend accepts, as percentages and hours rather than as it stores them. */
const TOLERANCE_MIN = 0.0001;
const TOLERANCE_MAX = 100;
const TIME_RANGE_MIN_HOURS = 1;

/**
 * The inputs hold text, so the bound is checked on the number it parses to.
 *
 * A field that holds nothing yet is left alone: the old rules only reported a value that was out of
 * range, never one that was missing, and the menu writes on every keystroke.
 */
function boundedNumber(min: number, max: number, messages: { tooSmall: string; tooLarge: string }): ZodType<string> {
  return z.string().superRefine((value, ctx) => {
    if (value.trim() === '')
      return;

    const parsed = Number(value);
    if (Number.isNaN(parsed))
      return;

    if (parsed < min)
      ctx.addIssue({ code: 'custom', message: messages.tooSmall });

    if (parsed > max)
      ctx.addIssue({ code: 'custom', message: messages.tooLarge });
  });
}

/** A percentage of the amount, between a ten-thousandth of a percent and all of it. */
export function tolerancePercentageSchema(messages: MatchingSettingsMessages): ZodType<string> {
  return boundedNumber(TOLERANCE_MIN, TOLERANCE_MAX, {
    tooLarge: messages.toleranceMax,
    tooSmall: messages.toleranceMin,
  });
}

/** Hours either side of the movement. Anything under one would match almost nothing. */
export function timeRangeHoursSchema(messages: MatchingSettingsMessages): ZodType<string> {
  return boundedNumber(TIME_RANGE_MIN_HOURS, Number.POSITIVE_INFINITY, {
    tooLarge: messages.timeRangeMin,
    tooSmall: messages.timeRangeMin,
  });
}

/** The messages a value fails on, empty when it is accepted. */
export function checkSetting(schema: ZodType<string>, value: string): string[] {
  const result = schema.safeParse(value);
  return result.success ? [] : result.error.issues.map(issue => issue.message);
}
