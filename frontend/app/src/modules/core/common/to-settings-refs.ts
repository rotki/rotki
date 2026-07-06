import { type Ref, toRef } from 'vue';

export type SettingsRefs<T, E extends keyof T = never> = {
  readonly [K in Exclude<keyof T, E>]: Readonly<Ref<T[K]>>;
};

/**
 * Derives one readonly ref per property of a settings object, replacing the hand-written
 * `useComputedRef(settings, 'key')` line (and its matching return entry) that a settings store
 * previously needed for every property.
 *
 * Uses `toRef(getter)` rather than `computed()`: a getter ref allocates no reactive effect and no
 * cache, so creating dozens per store is cheaper than dozens of computeds. Each getter re-reads
 * through the ref, so replacing the whole settings object via the store's `update()` keeps every
 * derived ref in sync, and the source stays a plain `ref` (the stores `markRaw` their defaults to
 * avoid deep reactivity, which this preserves).
 *
 * Keys are read once from the ref's current value, which the stores initialise with the full
 * defaults, so every property is present. `exclude` drops properties that must stay off the public
 * store surface (e.g. `schemaVersion`).
 */
export function toSettingsRefs<T extends object, E extends keyof T = never>(
  settings: Ref<T>,
  exclude: readonly E[] = [],
): SettingsRefs<T, E> {
  const excluded = new Set<PropertyKey>(exclude);
  const refs: Partial<Record<keyof T, Readonly<Ref<T[keyof T]>>>> = {};
  // `Object.keys` widens to `string[]`, but the settings object owns exactly the keys of `T`, so
  // each entry is a `keyof T`. TypeScript cannot infer this from a runtime key walk.
  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- Object.keys loses the key type; the source object is exactly T
  for (const key of Object.keys(get(settings)) as (keyof T)[]) {
    if (!excluded.has(key))
      refs[key] = toRef(() => get(settings)[key]);
  }
  // The loop populates every non-excluded key of T, so `refs` satisfies the mapped return type.
  // TS cannot prove a runtime-built record over dynamic keys is complete, and the per-key value
  // type (`T[K]`) is narrower than the accumulator's union (`T[keyof T]`), so the widen goes via
  // `unknown`.
  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- record built over all keys of T matches the mapped type; not statically provable
  return refs as unknown as SettingsRefs<T, E>;
}
