/**
 * Converts a stringified JSON returned from the API to JSON.
 *
 * Use {@link ApiValidationError} in the catch clause instead.
 * @param message a stringified json message
 * @deprecated it should be replaced with handling of ApiValidationError
 */
export function deserializeApiErrorMessage(
  message: string
): Record<string, string[]> | undefined {
  try {
    return JSON.parse(message);
  } catch {
    return undefined;
  }
}
