/**
 * Sanitizes a path to prevent path traversal attacks and other security issues.
 *
 * @param pathname - The path to sanitize
 * @returns The sanitized path, or empty string if invalid
 */
export function sanitizePath(pathname: string): string {
  if (!pathname || typeof pathname !== 'string') {
    return '';
  }

  return pathname
    // Remove any path traversal attempts
    .replace(/\.{2,}/g, '') // Remove '..' sequences
    .replace(/\\{2,}|\/{2,}/g, '') // Remove multiple slashes/backslashes
    .replace(/^\\|^\//g, '') // Remove leading slashes
    .replace(/~/g, '') // Remove tilde characters
    .replace(/\0/g, '') // Remove null bytes
    .replace(/[\n\r]/g, '') // Remove newlines
    // Normalize path separators to forward slashes
    .replace(/\\/g, '/')
    // Remove any remaining dangerous characters
    .replace(/["*:<>?|]/g, '')
    .trim();
}
