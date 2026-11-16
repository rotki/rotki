const MAX_UPDATER_ERROR_LENGTH = 500;

/**
 * electron-updater puts the whole HTTP response into its error messages. For a failed check of
 * the releases feed that is the release notes of every rotki release, thousands of log lines per
 * error. The first line already names the failure and its HTTP status, so only that is kept.
 */
export function summarizeUpdaterError(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error);
  const firstLine = message.split('\n', 1)[0].trim();
  if (firstLine.length > MAX_UPDATER_ERROR_LENGTH)
    return `${firstLine.slice(0, MAX_UPDATER_ERROR_LENGTH)}… (truncated)`;

  if (firstLine.length < message.trim().length)
    return `${firstLine} (details truncated)`;

  return firstLine;
}
