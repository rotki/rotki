import semver from 'semver';

/**
 * Checks if the version change is a major or minor update (not just a patch)
 * @param currentVersion The current version string
 * @param lastVersion The previous version string
 * @returns True if it's a major or minor update, false otherwise
 */
export function isMajorOrMinorUpdate(currentVersion: string | null, lastVersion: string | null): boolean {
  if (!lastVersion || !currentVersion)
    return false;

  const current = semver.coerce(currentVersion);
  const last = semver.coerce(lastVersion);

  if (!current || !last)
    return false;

  return semver.diff(last, current) === 'major' || semver.diff(last, current) === 'minor';
}
