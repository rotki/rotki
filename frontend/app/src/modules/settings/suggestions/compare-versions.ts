import semver from 'semver';

/**
 * Compares two version strings with semver, coercing each first.
 *
 * @returns a standard comparator result: negative when `a` sorts first, positive when `b` does, 0
 * when they are equal. Also 0 when *either* string fails to coerce, so an unparsable version
 * reads as equal rather than raising.
 */
export function compareVersions(a: string, b: string): number {
  const coercedA = semver.coerce(a);
  const coercedB = semver.coerce(b);

  if (!coercedA || !coercedB)
    return 0;

  return semver.compare(coercedA, coercedB);
}
