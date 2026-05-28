/**
 * Extracts a human-readable message from an unknown error without type assertion.
 */
export function errorMessage(error: unknown): string {
  if (error instanceof Error)
    return error.message;
  if (typeof error === 'string')
    return error;
  return String(error);
}

/**
 * Returns a NodeJS-style `code` from an error object, or undefined if not present.
 */
export function errorCode(error: unknown): string | undefined {
  if (!(error instanceof Error) || !('code' in error))
    return undefined;
  const code: unknown = error.code;
  return typeof code === 'string' ? code : undefined;
}

export function humanBytes(bytes: number): string {
  if (bytes < 1024)
    return `${bytes} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(1)} ${units[unit]}`;
}

/**
 * Renders a port number in ANSI bold for log output. Use everywhere a port is
 * surfaced to the developer so the number stands out from surrounding text.
 * `[22m` turns off bold without resetting other attributes.
 */
export function formatPort(port: number | string): string {
  return `[1m${port}[22m`;
}

/** Renders `host:port` with the port number bolded. */
export function formatHostPort(host: string, port: number | string): string {
  return `${host}:${formatPort(port)}`;
}

export function formatTable(rows: string[][]): string {
  if (rows.length === 0)
    return '';
  const widths = rows[0].map((_, col) => Math.max(...rows.map(r => r[col].length)));
  return rows.map(r => r.map((c, i) => c.padEnd(widths[i])).join('  ')).join('\n');
}
