export function deserializeApiErrorMessage(
  message: string
): Record<string, string[]> | undefined {
  try {
    return JSON.parse(message);
  } catch {
    return undefined;
  }
}
