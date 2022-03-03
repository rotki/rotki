export function deserializeApiErrorMessage(
  message: string
): { [key: string]: string[] } | undefined {
  try {
    return JSON.parse(message);
  } catch (e) {
    return undefined;
  }
}
