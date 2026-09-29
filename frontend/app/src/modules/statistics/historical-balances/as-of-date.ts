import dayjs from 'dayjs';

/** A calendar day in the user's timezone, as `YYYY-MM-DD`. */
export type DateKey = string;

const DATE_KEY_FORMAT = 'YYYY-MM-DD';

const DATE_KEY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

export const AsOfPreset = {
  TODAY: 'today',
  END_OF_LAST_YEAR: 'end-of-last-year',
  END_OF_YEAR_BEFORE: 'end-of-year-before',
} as const;

export type AsOfPreset = typeof AsOfPreset[keyof typeof AsOfPreset];

/**
 * The day a timestamp falls on.
 *
 * @param timestamp - unix seconds
 */
export function toDateKey(timestamp: number): DateKey {
  return dayjs.unix(timestamp).format(DATE_KEY_FORMAT);
}

/** The value as a day, or undefined when it is not a real `YYYY-MM-DD` date (a route query, say). */
export function parseDateKey(value: unknown): DateKey | undefined {
  if (typeof value !== 'string' || !DATE_KEY_PATTERN.test(value))
    return undefined;
  const date = dayjs(value);
  return date.isValid() && date.format(DATE_KEY_FORMAT) === value ? value : undefined;
}

/**
 * The timestamp that stands for a whole day: its last second, or now when the day is today.
 *
 * @remarks
 * Balances as of a day mean after everything that happened on it, so the end of the day is the
 * natural reading. Today's end is still in the future, and nothing after now exists yet.
 *
 * @param day - the day to read balances at
 * @param now - the current time in unix seconds
 * @returns unix seconds
 */
export function asOfTimestamp(day: DateKey, now: number): number {
  return Math.min(dayjs(day).endOf('day').unix(), now);
}

/**
 * The day a quick-pick preset names, counted from now.
 *
 * @param preset - which quick pick
 * @param now - the current time in unix seconds
 */
export function presetDateKey(preset: AsOfPreset, now: number): DateKey {
  const today = dayjs.unix(now);
  switch (preset) {
    case AsOfPreset.TODAY:
      return today.format(DATE_KEY_FORMAT);
    case AsOfPreset.END_OF_LAST_YEAR:
      return today.subtract(1, 'year').endOf('year').format(DATE_KEY_FORMAT);
    case AsOfPreset.END_OF_YEAR_BEFORE:
      return today.subtract(2, 'year').endOf('year').format(DATE_KEY_FORMAT);
  }
}
