export function stub<T>(partial?: Partial<T>): T {
  return partial != null ? (partial as T) : ({} as T);
}
