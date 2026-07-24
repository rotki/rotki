class AssertionError extends Error {
  constructor(msg: string, options?: ErrorOptions) {
    super(msg, options);
    this.name = 'AssertionError';
  }
}

export function assert(condition: any, msg?: string): asserts condition {
  if (!condition)
    throw new AssertionError(msg ?? 'AssertionError');
}
