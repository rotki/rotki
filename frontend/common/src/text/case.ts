/**
 * The type-level counterpart of `transformCase(key, true)`.
 */
export type CamelCase<S extends string> = S extends `${infer P1}_${infer P2}${infer P3}`
  ? `${P1}${Uppercase<P2>}${CamelCase<P3>}`
  : S;

/**
 * Transforms keys/text between camel and snake cases
 * @param {string} key - string to transform
 * @param {boolean} camelCase - flag to decide whether to return camelCase (true) or snake_case (false)
 * @returns {string}
 * @example
 * transformCase('loremIpsum'); // lorem_ipsum
 * @example
 * transformCase('lorem_ipsum', true); // loremIpsum
 */
export function transformCase<S extends string>(key: S, camelCase: true): CamelCase<S>;

export function transformCase(key: string, camelCase?: boolean): string;

export function transformCase(key: string, camelCase = false): string {
  if (camelCase)
    return key.includes('_') ? key.replace(/_(.)/gu, (_, p1) => p1.toUpperCase()) : key;

  return key.replace(/([A-Z])/gu, (_, p1, offset, string) => {
    const nextCharOffset = offset + 1;
    if ((nextCharOffset < string.length && /([A-Z])/.test(string[nextCharOffset])) || nextCharOffset === string.length)
      return p1;

    return `_${p1.toLowerCase()}`;
  });
}
