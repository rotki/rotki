class AssertionError extends Error {
  constructor(msg: string) {
    super(msg);
    this.name = 'AssertionError';
  }
}

export function assert(condition: any, msg?: string): asserts condition {
  if (!condition) {
    throw new AssertionError(msg ?? 'AssertionError');
  }
}
