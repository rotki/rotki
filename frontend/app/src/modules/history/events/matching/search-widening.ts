/** Seven days, matching the time field's own max. */
export const MAX_SEARCH_HOURS = 168;

/** Raising this past 100 changes nothing: a full 100% either side already excludes no candidate. */
export const MAX_TOLERANCE_PERCENTAGE = 100;

export interface SearchCriteria {
  /** How far either side of the unmatched entry to look, in hours. */
  hours: string;
  /** How far the amounts may differ, as a percentage. */
  tolerance: string;
}

/**
 * Whether either criterion still has room to grow.
 *
 * @remarks
 * A criterion that is not a number at all compares false either way, so it counts as having no
 * room. An empty field is not that case: it reads as zero, which does have room, though doubling
 * it leaves it at zero.
 *
 * @param criteria - the search as the fields currently hold it
 * @returns whether widening would change either criterion
 */
export function canWidenSearch({ hours, tolerance }: SearchCriteria): boolean {
  return Number(hours) < MAX_SEARCH_HOURS || Number(tolerance) < MAX_TOLERANCE_PERCENTAGE;
}

/**
 * The search after the user asks to widen it: both criteria doubled, each capped at its own max.
 *
 * @remarks
 * A criterion that does not parse is left exactly as typed rather than reset, so widening never
 * throws away what the user was in the middle of entering.
 *
 * @param criteria - the search as the fields currently hold it
 * @returns the replacement values, as the strings the fields hold
 */
export function widenedSearch({ hours, tolerance }: SearchCriteria): SearchCriteria {
  return {
    hours: doubleUpTo(hours, MAX_SEARCH_HOURS),
    tolerance: doubleUpTo(tolerance, MAX_TOLERANCE_PERCENTAGE),
  };
}

function doubleUpTo(value: string, max: number): string {
  const parsed = Number(value);
  if (Number.isNaN(parsed))
    return value;

  return Math.min(parsed * 2, max).toString();
}
