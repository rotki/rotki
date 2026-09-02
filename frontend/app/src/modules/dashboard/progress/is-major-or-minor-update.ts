import semver from 'semver';

/**
 * Whether a version change is a major or minor update rather than a patch.
 *
 * @param currentVersion - `null` when the version is not yet known
 * @param lastVersion - `null` on a first run, with no previous version recorded
 */
export function isMajorOrMinorUpdate(
  currentVersion: string | null,
  lastVersion: string | null,
): boolean {
  if (!lastVersion || !currentVersion)
    return false;

  const current = semver.coerce(currentVersion);
  const last = semver.coerce(lastVersion);

  if (!current || !last)
    return false;

  return semver.diff(last, current) === 'major' || semver.diff(last, current) === 'minor';
}
