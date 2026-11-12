import { PasswordIssue, scanPasswordPatterns } from '@/modules/auth/create-account/credentials/password-patterns';

export const PasswordStrength = {
  EMPTY: 'empty',
  FAIR: 'fair',
  GOOD: 'good',
  STRONG: 'strong',
  WEAK: 'weak',
} as const;

export type PasswordStrength = typeof PasswordStrength[keyof typeof PasswordStrength];

export interface PasswordRating {
  strength: PasswordStrength;
  /** The most guessable pattern found, when it kept the password from rating strong. */
  issue?: PasswordIssue;
}

const FAIR_LENGTH = 8;
const GOOD_LENGTH = 12;
const STRONG_LENGTH = 16;

/** The order issues are reported in, most damaging first. */
const ISSUE_PRIORITY: readonly PasswordIssue[] = [
  PasswordIssue.COMMON_WORD,
  PasswordIssue.CONTAINS_USERNAME,
  PasswordIssue.SEQUENCE,
  PasswordIssue.REPEATS,
  PasswordIssue.DIGITS_ONLY,
];

function strengthForLength(length: number): PasswordStrength {
  if (length < FAIR_LENGTH)
    return PasswordStrength.WEAK;
  if (length < GOOD_LENGTH)
    return PasswordStrength.FAIR;
  if (length < STRONG_LENGTH)
    return PasswordStrength.GOOD;
  return PasswordStrength.STRONG;
}

/** One rating lower, never below weak. */
function weaker(strength: PasswordStrength): PasswordStrength {
  if (strength === PasswordStrength.STRONG)
    return PasswordStrength.GOOD;
  if (strength === PasswordStrength.GOOD)
    return PasswordStrength.FAIR;
  return PasswordStrength.WEAK;
}

/**
 * Rates a password by how much of it an attacker would have to guess.
 *
 * @remarks
 * Length still decides the rating, but counted after every predictable run (a common word, the
 * profile name, `aaa`, `abc`, `qwerty`, `abcabc`) shrinks to a single character, and digits alone
 * drop one rating. A passphrase of unrelated words passes untouched. The rating only informs: a
 * weak password is still accepted.
 *
 * @param password - the password as typed
 * @param username - the profile name, which the password should not contain
 */
export function ratePassword(password: string, username = ''): PasswordRating {
  if (password.length === 0)
    return { strength: PasswordStrength.EMPTY };

  const { effectiveLength, issues } = scanPasswordPatterns(password, username);
  const byLength = strengthForLength(effectiveLength);
  const strength = issues.has(PasswordIssue.DIGITS_ONLY) ? weaker(byLength) : byLength;

  const issue = ISSUE_PRIORITY.find(found => issues.has(found));
  if (strength === PasswordStrength.STRONG || !issue)
    return { strength };

  return { issue, strength };
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
