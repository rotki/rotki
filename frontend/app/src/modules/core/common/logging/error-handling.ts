/**
 * Extracts a human-readable message from an unknown thrown value.
 * Pure function — no logging or side effects.
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error)
    return error.message;
  if (typeof error === 'string')
    return error;
  if (error && typeof error === 'object' && 'message' in error)
    return String(error.message);
  return 'Unknown error occurred';
}
