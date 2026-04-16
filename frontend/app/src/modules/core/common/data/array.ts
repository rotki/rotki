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
