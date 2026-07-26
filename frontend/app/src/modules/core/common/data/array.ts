/**
 *
 * @param {T | T[]} item - Individual item or array
 * @return {T[]} - Return array of {item} if it's not an array
 * @example
 * arrayify('test'); // ['test']
 * arrayify(['test']); // ['test']
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
 * @return the own enumerable keys, typed as keys of {object}
 * @example
 * objectKeys({ a: 1, b: 2 }); // ('a' | 'b')[]
 */
export function objectKeys<T extends object>(object: T): (keyof T)[] {
  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- the whole point of the helper
  return Object.keys(object) as (keyof T)[];
}
