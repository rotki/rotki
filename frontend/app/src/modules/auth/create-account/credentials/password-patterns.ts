export const PasswordIssue = {
  COMMON_WORD: 'common_word',
  CONTAINS_USERNAME: 'contains_username',
  DIGITS_ONLY: 'digits_only',
  REPEATS: 'repeats',
  SEQUENCE: 'sequence',
} as const;

export type PasswordIssue = typeof PasswordIssue[keyof typeof PasswordIssue];

/** Look-alike substitutions undone before matching words, so `p@ssw0rd` still reads as `password`. */
const LOOKALIKES = new Map<string, string>([
  ['!', 'i'],
  ['$', 's'],
  ['0', 'o'],
  ['1', 'i'],
  ['3', 'e'],
  ['4', 'a'],
  ['5', 's'],
  ['7', 't'],
  ['@', 'a'],
]);

/**
 * Words at the top of every leaked-password list, plus the crypto ones a rotki user is likely to
 * reach for. Written after look-alike substitution, so `trustno1` is listed as `trustnoi`.
 */
const COMMON_WORDS: readonly string[] = [
  'admin',
  'bitcoin',
  'crypto',
  'dragon',
  'ethereum',
  'football',
  'hello',
  'iloveyou',
  'letmein',
  'login',
  'master',
  'monkey',
  'passw',
  'princess',
  'rotki',
  'satoshi',
  'secret',
  'shadow',
  'sunshine',
  'superman',
  'trustnoi',
  'wallet',
  'welcome',
];

const KEYBOARD_ROWS: readonly string[] = [
  'asdfghjkl',
  'azertyuiop',
  'qwertyuiop',
  'qwertzuiop',
  'yxcvbnm',
  'zxcvbnm',
].flatMap(row => [row, [...row].reverse().join('')]);

const MIN_RUN = 3;

const MIN_KEYBOARD_RUN = 4;

const MIN_USERNAME_LENGTH = 3;

/** Past this the quadratic search for repeated blocks costs more than the hint is worth. */
const MAX_BLOCK_SCAN_LENGTH = 64;

export interface PatternScan {
  /** Characters left once every predictable run is reduced to its first character. */
  effectiveLength: number;
  issues: ReadonlySet<PasswordIssue>;
}

class PatternMarker {
  readonly predictable: boolean[];
  readonly issues = new Set<PasswordIssue>();

  constructor(length: number) {
    this.predictable = Array.from<boolean>({ length }).fill(false);
  }

  /** Marks `[from, to)` as adding nothing to the password, and records why. */
  mark(from: number, to: number, issue: PasswordIssue): void {
    for (let index = from; index < to; index++)
      this.predictable[index] = true;
    this.issues.add(issue);
  }
}

function occurrences(chars: readonly string[], word: readonly string[]): number[] {
  const found: number[] = [];
  for (let start = 0; start + word.length <= chars.length; start++) {
    if (word.every((char, offset) => chars[start + offset] === char))
      found.push(start);
  }
  return found;
}

function markWords(marker: PatternMarker, normal: readonly string[], words: readonly string[], issue: PasswordIssue): void {
  for (const word of words) {
    const letters = [...word];
    for (const start of occurrences(normal, letters))
      marker.mark(start + 1, start + letters.length, issue);
  }
}

/**
 * Marks runs where each character follows from the previous one, keeping the first of each.
 *
 * @remarks
 * `follows` covers both `aaa` (same character) and `abc` or `321` (constant step of one code point),
 * given the step between the run's first two characters. Neighbouring runs share their turning
 * character, so `abcdcba` reduces to one.
 */
function markRuns(marker: PatternMarker, lower: readonly string[], follows: (previous: number, current: number, step: number) => boolean, issue: PasswordIssue): void {
  const points = lower.map(char => char.codePointAt(0) ?? 0);
  let start = 0;
  while (start < points.length - 1) {
    const step = points[start + 1] - points[start];
    let end = start + 1;
    while (end < points.length && follows(points[end - 1], points[end], step))
      end++;
    if (end - start >= MIN_RUN) {
      marker.mark(start + 1, end, issue);
      start = end - 1;
    }
    else {
      start++;
    }
  }
}

function markKeyboardRuns(marker: PatternMarker, lower: readonly string[]): void {
  for (let start = 0; start < lower.length; start++) {
    let longest = 0;
    for (let end = start + MIN_KEYBOARD_RUN; end <= lower.length; end++) {
      const run = lower.slice(start, end).join('');
      if (!KEYBOARD_ROWS.some(row => row.includes(run)))
        break;
      longest = end - start;
    }
    if (longest > 0)
      marker.mark(start + 1, start + longest, PasswordIssue.SEQUENCE);
  }
}

/** Marks a block that directly repeats the one before it, as in `abcabc` or `passpass`. */
function markRepeatedBlocks(marker: PatternMarker, lower: readonly string[]): void {
  if (lower.length > MAX_BLOCK_SCAN_LENGTH)
    return;
  for (let size = 2; size * 2 <= lower.length; size++) {
    for (let start = 0; start + size * 2 <= lower.length; start++) {
      const repeats = lower.slice(start, start + size).every((char, offset) => lower[start + size + offset] === char);
      if (repeats)
        marker.mark(start + size, start + size * 2, PasswordIssue.REPEATS);
    }
  }
}

/**
 * Finds the parts of a password an attacker tries first: common words, the profile name,
 * repeats, alphabet and keyboard sequences, and digits alone.
 *
 * @param password - the password as typed
 * @param username - the profile name; ignored when shorter than three characters
 */
export function scanPasswordPatterns(password: string, username: string): PatternScan {
  const lower = Array.from(password, char => char.toLowerCase());
  const normal = lower.map(char => LOOKALIKES.get(char) ?? char);
  const marker = new PatternMarker(lower.length);

  markWords(marker, normal, COMMON_WORDS, PasswordIssue.COMMON_WORD);

  const name = Array.from(username.trim().toLowerCase(), char => LOOKALIKES.get(char) ?? char).join('');
  if ([...name].length >= MIN_USERNAME_LENGTH)
    markWords(marker, normal, [name], PasswordIssue.CONTAINS_USERNAME);

  markRuns(marker, lower, (previous, current) => previous === current, PasswordIssue.REPEATS);
  markRuns(marker, lower, (previous, current, step) => Math.abs(step) === 1 && current - previous === step, PasswordIssue.SEQUENCE);
  markKeyboardRuns(marker, lower);
  markRepeatedBlocks(marker, lower);

  if (/^\d+$/.test(password))
    marker.issues.add(PasswordIssue.DIGITS_ONLY);

  return {
    effectiveLength: marker.predictable.filter(predictable => !predictable).length,
    issues: marker.issues,
  };
}
