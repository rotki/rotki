const MINUTES_PER_HOUR = 60;
const HOURS_PER_DAY = 24;
const SECONDS_PER_MINUTE = 60;
const SECONDS_PER_HOUR = MINUTES_PER_HOUR * SECONDS_PER_MINUTE;
const SECONDS_PER_DAY = HOURS_PER_DAY * SECONDS_PER_HOUR;

export const GapUnit = {
  DAYS: 'days',
  HOURS: 'hours',
  MINUTES: 'minutes',
} as const;

export type GapUnit = typeof GapUnit[keyof typeof GapUnit];

interface DivergenceGap {
  unit: GapUnit;
  count: number;
  /** False when rounding moved the count away from the real gap. */
  exact: boolean;
}

/**
 * Time between two boundary events, rounded to the nearest whole unit.
 *
 * @remarks
 * A unit is used only while its rounded count stays below the next unit, so 23h40m reads as one
 * day rather than 24 hours. Anything under half a minute comes back as zero minutes, and the order
 * of the two timestamps does not matter. `exact` tells a rounded count from a true one.
 *
 * @param fromSeconds - one event timestamp, in seconds
 * @param toSeconds - the other event timestamp, in seconds
 */
export function divergenceGap(fromSeconds: number, toSeconds: number): DivergenceGap {
  const seconds = Math.abs(toSeconds - fromSeconds);
  const gapOf = (unit: GapUnit, unitSeconds: number): DivergenceGap => {
    const count = Math.round(seconds / unitSeconds);
    return { count, exact: count * unitSeconds === seconds, unit };
  };

  const minutes = gapOf(GapUnit.MINUTES, SECONDS_PER_MINUTE);
  if (minutes.count < MINUTES_PER_HOUR)
    return minutes;
  const hours = gapOf(GapUnit.HOURS, SECONDS_PER_HOUR);
  if (hours.count < HOURS_PER_DAY)
    return hours;
  return gapOf(GapUnit.DAYS, SECONDS_PER_DAY);
}
