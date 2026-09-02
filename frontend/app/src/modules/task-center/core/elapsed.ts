const SECOND = 1000;
const MINUTE = 60 * SECOND;
const HOUR = 60 * MINUTE;

/**
 * How long a running activity has been going, as a compact badge.
 *
 * @remarks
 * Elapsed rather than an absolute timestamp, because the question a live task list answers is which
 * leaf is stuck. Unit-free digits on purpose: no i18n key, so it cannot drift between locales, and
 * it fits the narrow column the row leaves for it.
 *
 * @param milliseconds - elapsed duration; a negative value is clamped to zero
 * @returns `14s`, `3m 12s` or `1h 04m`, depending on magnitude
 */
export function formatElapsed(milliseconds: number): string {
  const safe = Math.max(0, milliseconds);

  if (safe < MINUTE)
    return `${Math.floor(safe / SECOND)}s`;

  if (safe < HOUR) {
    const minutes = Math.floor(safe / MINUTE);
    const seconds = Math.floor((safe % MINUTE) / SECOND);
    return `${minutes}m ${seconds.toString().padStart(2, '0')}s`;
  }

  const hours = Math.floor(safe / HOUR);
  const minutes = Math.floor((safe % HOUR) / MINUTE);
  return `${hours}h ${minutes.toString().padStart(2, '0')}m`;
}
