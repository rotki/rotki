import semver from 'semver';

/**
 * Compares two version strings using semver.
 * @returns negative if a < b, 0 if equal, positive if a > b. Returns 0 if either is invalid.
 */
export function compareVersions(a: string, b: string): number {
  const coercedA = semver.coerce(a);
  const coercedB = semver.coerce(b);

  if (!coercedA || !coercedB)
    return 0;

  return semver.compare(coercedA, coercedB);
}
