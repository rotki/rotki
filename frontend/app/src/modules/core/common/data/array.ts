/**
 * Wraps a single item in an array, and passes an array through unchanged.
 *
 * @param item - the item or array to normalise
 * @returns the array form; a falsy single item yields an empty array rather than `[item]`
 * @example
 * ```ts
 * arrayify('test');   // ['test']
 * arrayify(['test']); // ['test']
 * arrayify(undefined); // []
 * ```
 */
export function arrayify<T>(item: T | T[]): T[] {
  if (!Array.isArray(item)) {
    if (item)
      return [item];
    return [];
  }

  return item;
}

/**
 * `Object.keys` typed against the object it was given.
 *
 * It returns `string[]` because a value may carry keys its type does not declare, so every caller
 * that wants to index back into the same object has to widen the key itself. Doing that once here
 * keeps the assertion in a single reviewed place, and callers that cannot trust the object should
 * match against the returned keys rather than assume one.
 *
 * @param object - the object to read the keys of
 * @returns its own enumerable keys, typed as `keyof T` rather than `string[]`
 * @example
 * ```ts
 * objectKeys({ a: 1, b: 2 }); // ('a' | 'b')[]
 * ```
 */
export function objectKeys<T extends object>(object: T): (keyof T)[] {
  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- the whole point of the helper
  return Object.keys(object) as (keyof T)[];
}
