const MIN_SCRAMBLE_MULTIPLIER = 1;

/**
 * Bounds the multiplier every scramble function is computed against.
 *
 * @remarks
 * Below 1 a scrambled value comes out *smaller* than the real one, and at 0 it collapses to zero
 * and hides nothing. The setting is user-editable and written through unvalidated, so this is the
 * correctness boundary rather than the inputs. Small values are lifted rather than clamped flat,
 * so they stay distinct from one another.
 *
 * @param multiplier - the raw setting value, which may be negative, zero or not a number
 * @returns a multiplier of at least {@link MIN_SCRAMBLE_MULTIPLIER}
 */
export function normalizeScrambleMultiplier(multiplier: number): number {
  if (!Number.isFinite(multiplier) || multiplier < 0)
    return MIN_SCRAMBLE_MULTIPLIER;

  return multiplier < MIN_SCRAMBLE_MULTIPLIER ? multiplier + MIN_SCRAMBLE_MULTIPLIER : multiplier;
}

/**
 * Picks the multiplier a session scrambles with when the user has not chosen one.
 *
 * @returns a value in [1, 10] with three decimals
 */
export function generateRandomScrambleMultiplier(): number {
  return Math.floor(1000 + Math.random() * 9000) / 1000;
}
