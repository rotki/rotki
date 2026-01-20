/**
 * Creates a short hash from the input string using a simple hash function.
 * Returns a 6-character alphanumeric string.
 */
export function createShortHash(input: string): string {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    const char = input.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash).toString(36).slice(0, 6).padStart(6, '0');
}

/**
 * Creates a database identifier from the data directory and username.
 * Format: `{6-char-hash}.{username}` where hash is derived from dataDirectory only.
 */
export function createDatabaseIdentifier(dataDirectory: string, username: string): string {
  const hash = createShortHash(dataDirectory);
  return `${hash}.${username}`;
}
