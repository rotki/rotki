const FALLBACK_SCRAMBLE_MULTIPLIER = 1;

/**
 * Guards the multiplier every scramble function is computed against.
 *
 * @remarks
 * At 0 every scrambled value collapses to zero and hides nothing, and a negative multiplier flips
 * the sign. The setting is user-editable and written through unvalidated, so this is the
 * correctness boundary rather than the inputs. Any positive value is used as given, including one
 * below 1, which scrambles amounts downwards.
 *
 * @param multiplier - the raw setting value, which may be negative, zero or not a number
 * @returns the multiplier when it is a positive finite number, otherwise {@link FALLBACK_SCRAMBLE_MULTIPLIER}
 */
export function normalizeScrambleMultiplier(multiplier: number): number {
  if (!Number.isFinite(multiplier) || multiplier <= 0)
    return FALLBACK_SCRAMBLE_MULTIPLIER;

  return multiplier;
}

/**
 * Picks the multiplier a session scrambles with when the user has not chosen one.
 *
 * @returns a value in [1, 10] with three decimals
 */
export function generateRandomScrambleMultiplier(): number {
  return Math.floor(1000 + Math.random() * 9000) / 1000;
}
