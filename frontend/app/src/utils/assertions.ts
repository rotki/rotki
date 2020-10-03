class AssertionError extends Error {}

export function assert(condition: any, msg?: string): asserts condition {
  if (!condition) {
    throw new AssertionError(msg ?? 'AssertionError');
  }
}
