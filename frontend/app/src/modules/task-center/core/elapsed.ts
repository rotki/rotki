const SECOND = 1000;
const MINUTE = 60 * SECOND;
const HOUR = 60 * MINUTE;

/**
 * How long a running activity has been going, as a compact badge (`14s`, `3m 12s`, `1h 04m`).
 *
 * The panel used to print an absolute `LLL` timestamp per row ("August 7, 2026 3:42 PM") on work
 * that had started four seconds earlier. Nobody reads a live task list to learn the date; the
 * question a reader has is which leaf is stuck, and only elapsed time answers it.
 *
 * Unit-free digits on purpose — no i18n key, so it cannot drift between locales, and it stays
 * legible in the narrow column the row leaves for it.
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
