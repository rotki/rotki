interface SemanticVersion {
  major: number;
  minor: number;
  patch: number;
}

/**
 * Parses a semantic version string (e.g., "1.40.1") into its components
 * @param version The version string to parse
 * @returns The parsed version components or null if invalid
 */
export function parseVersion(version: string): SemanticVersion | null {
  const match = version.match(/^(\d+)\.(\d+)\.(\d+)/);
  if (!match)
    return null;

  return {
    major: Number.parseInt(match[1]),
    minor: Number.parseInt(match[2]),
    patch: Number.parseInt(match[3]),
  };
}

/**
 * Checks if the version change is a major or minor update (not just a patch)
 * @param currentVersion The current version string
 * @param lastVersion The previous version string
 * @returns True if it's a major or minor update, false otherwise
 */
export function isMajorOrMinorUpdate(currentVersion: string | null, lastVersion: string | null): boolean {
  if (!lastVersion || !currentVersion)
    return false;

  const current = parseVersion(currentVersion);
  const last = parseVersion(lastVersion);

  if (!current || !last)
    return false;

  return current.major !== last.major || current.minor !== last.minor;
}
