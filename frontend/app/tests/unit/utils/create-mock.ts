import { vi } from 'vitest';

/**
 * Deeply-partial shape accepted as overrides. Every property is optional and
 * recursively partial; function properties keep their call signature so a
 * `vi.fn()` (or any implementation) can be supplied directly.
 */
export type DeepPartial<T> = T extends (...args: infer A) => infer R
  ? (...args: A) => R
  : T extends object
    ? { [K in keyof T]?: DeepPartial<T[K]> }
    : T;

// Properties that must never be auto-mocked: `then`/`catch`/`finally` would make
// the mock look thenable (so `await mock` hangs), and the inspection hooks would
// break `console.log(mock)` / util.inspect. Returning undefined for them keeps
// the proxy inert to the runtime.
const passthroughUndefined = new Set<PropertyKey>([
  'then',
  'catch',
  'finally',
  'asymmetricMatch',
  'inspect',
  Symbol.iterator,
  Symbol.asyncIterator,
  Symbol.toPrimitive,
  Symbol.for('nodejs.util.inspect.custom'),
]);

function createProxy(overrides: Record<PropertyKey, unknown>): unknown {
  const cache = new Map<PropertyKey, unknown>();

  return new Proxy(vi.fn(), {
    get(target, prop, receiver) {
      if (prop in overrides)
        return overrides[prop];

      if (passthroughUndefined.has(prop))
        return undefined;

      // Expose the underlying vi.fn()'s own members (mock, mockReturnValue, …)
      // so the returned value behaves as a real Vitest mock function.
      if (prop in target)
        return Reflect.get(target, prop, receiver);

      // Lazily materialise (and cache) a nested mock so deep access such as
      // `event.sender.send` resolves to a callable mock as well.
      if (!cache.has(prop))
        cache.set(prop, createProxy({}));

      return cache.get(prop);
    },
  });
}

/**
 * Creates a deeply-mocked stand-in for `T` for use in unit tests.
 *
 * Every accessed property resolves to a `vi.fn()` (callable and further
 * proxyable), so class or branded types that cannot be constructed in a unit
 * test — e.g. `LogService` or `Electron.IpcMainInvokeEvent` — can be supplied
 * where the real type is expected. Pass `overrides` to pin specific
 * properties/implementations.
 *
 * The single assertion below is unavoidable and intentionally contained here:
 * a runtime `Proxy` cannot be statically proven to be `T`. Keeping it in this
 * one helper means test files stay assertion-free.
 */
export function createMock<T>(overrides?: DeepPartial<T>): T {
  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- a runtime Proxy cannot be proven to satisfy the branded/class type T; contained to this helper
  return createProxy(overrides ?? {}) as T;
}
