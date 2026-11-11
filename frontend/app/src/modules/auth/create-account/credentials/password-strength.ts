export const PasswordStrength = {
  EMPTY: 'empty',
  FAIR: 'fair',
  GOOD: 'good',
  STRONG: 'strong',
  WEAK: 'weak',
} as const;

export type PasswordStrength = typeof PasswordStrength[keyof typeof PasswordStrength];

const FAIR_LENGTH = 8;
const GOOD_LENGTH = 12;
const STRONG_LENGTH = 16;

/**
 * Rates a password by its length alone.
 *
 * @remarks
 * Length is what makes a password hard to guess, which is why a passphrase is the advice. The rating
 * only informs: a weak password is still accepted.
 */
export function passwordStrength(password: string): PasswordStrength {
  const length = [...password].length;
  if (length === 0)
    return PasswordStrength.EMPTY;
  if (length < FAIR_LENGTH)
    return PasswordStrength.WEAK;
  if (length < GOOD_LENGTH)
    return PasswordStrength.FAIR;
  if (length < STRONG_LENGTH)
    return PasswordStrength.GOOD;
  return PasswordStrength.STRONG;
}

const SCORES: Record<PasswordStrength, number> = {
  empty: 0,
  fair: 2,
  good: 3,
  strong: 4,
  weak: 1,
};

/** How many of the meter's four segments a rating fills. */
export function strengthScore(strength: PasswordStrength): number {
  return SCORES[strength];
}
