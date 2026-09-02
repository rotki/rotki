/// <reference lib="dom" />

export * from './address';

export * from './case';

export * from './hyperliquid';

/**
 * Upper-cases the first character, leaving the rest of the string untouched.
 *
 * @example
 * ```ts
 * toSentenceCase('this is a sentence'); // This is a sentence
 * ```
 */
export function toSentenceCase(string: string): string {
  if (!string)
    return '';

  return string[0].toUpperCase() + string.slice(1);
}

/**
 * Reduces a string to a comparable token: lower-cased, with everything but letters and digits
 * stripped. Used for keyword matching, where spacing and punctuation must not affect a hit.
 *
 * @example
 * ```ts
 * getTextToken('this is a sentence'); // thisisasentence
 * ```
 */
export function getTextToken(string: string): string {
  if (!string)
    return '';

  return string.toLowerCase().trim().replace(/[^\dA-Za-z]/g, '');
}

/**
 * Converts a string to snake_case, splitting on both capitals and whitespace.
 *
 * @example
 * ```ts
 * toSnakeCase('this is a sentence'); // this_is_a_sentence
 * ```
 */
export function toSnakeCase(string: string): string {
  if (!string)
    return '';

  return string
    .replace(/([A-Z])/g, '_$1')
    .toLowerCase()
    .replace(/^_/, '')
    .replace(/\s+/g, '_');
}

/**
 * Upper-cases the first letter of every word, keeping apostrophes inside a word intact.
 *
 * @example
 * ```ts
 * toCapitalCase('this is a sentence'); // This Is A Sentence
 * ```
 */
export function toCapitalCase(string: string): string {
  return string.replace(/\p{L}+('\p{L}+)?/gu, txt => txt.charAt(0).toUpperCase() + txt.slice(1));
}

/**
 * Turns an identifier into display text by replacing underscores with spaces.
 *
 * @param value - the identifier to convert
 * @param transform - the casing to apply afterwards; omitted, the existing casing is left as it is
 * @example
 * ```ts
 * toHumanReadable('POLYGON_POS', 'sentence');  // Polygon Pos
 * toHumanReadable('POLYGON_POS');              // POLYGON POS
 * toHumanReadable('polygon_pos', 'uppercase'); // POLYGON POS
 * ```
 */
export function toHumanReadable(
  value: string,
  transform?: 'capitalize' | 'sentence' | 'uppercase' | 'lowercase',
): string {
  if (!value)
    return '';

  if (!transform)
    return value.replace(/_/g, ' ');

  switch (transform) {
    case 'uppercase':
      return value.toUpperCase().replace(/_/g, ' ');
    case 'lowercase':
      return value.toLowerCase().replace(/_/g, ' ');
    case 'sentence':
      return toSentenceCase(value.replace(/_/g, ' '));
    case 'capitalize':
      return toCapitalCase(value.replace(/_/g, ' '));
  }
}

/**
 * Returns the plural of an English word, by rule rather than by dictionary.
 *
 * @param word - the singular form
 * @param amount - when exactly `1`, the word is returned unchanged; any other value, or none,
 * pluralises
 */
export function pluralize(word: string, amount?: number): string {
  if (amount !== undefined && amount === 1)
    return word;

  const plural: Record<string, string> = {
    '(?:([^f])fe|([lr])f)$': '$1$2ves',
    '([^aeiouy]|qu)y$': '$1ies',
    '([^s]+)$': '$1s',
    '([m|l])ouse$': '$1ice',
    '([ti])um$': '$1a',
    '(alias)$': '$1es',
    '(ax|test)is$': '$1es',
    '(bu)s$': '$1ses',
    '(hive)$': '$1s',
    '(matr|vert|ind)ix|ex$': '$1ices',
    '(octop)us$': '$1i',
    '(quiz)$': '$1zes',
    '(shea|lea|loa|thie)f$': '$1ves',
    '(tomat|potat|ech|her|vet)o$': '$1oes',
    '(us)$': '$1es',
    '(x|ch|ss|sh)$': '$1es',
    '^(ox)$': '$1en',
    'sis$': 'ses',
  };
  const irregular: Record<string, string> = {
    child: 'children',
    foot: 'feet',
    goose: 'geese',
    man: 'men',
    move: 'moves',
    person: 'people',
    sex: 'sexes',
    tooth: 'teeth',
  };
  const uncountable: string[] = [
    'sheep',
    'fish',
    'deer',
    'moose',
    'series',
    'species',
    'money',
    'rice',
    'information',
    'equipment',
    'bison',
    'cod',
    'offspring',
    'pike',
    'salmon',
    'shrimp',
    'swine',
    'trout',
    'aircraft',
    'hovercraft',
    'staking',
    'spacecraft',
    'sugar',
    'tuna',
    'you',
    'wood',
  ];
  if (uncountable.includes(word.toLowerCase()))
    return word;

  for (const w in irregular) {
    const pattern = new RegExp(`${w}$`, 'i');
    const replace = irregular[w];
    if (pattern.test(word))
      return word.replace(pattern, replace);
  }
  for (const reg in plural) {
    const pattern = new RegExp(reg, 'i');
    if (pattern.test(word))
      return word.replace(pattern, plural[reg]);
  }
  return word;
}

export function pluralizeLastWord(sentence: string): string {
  const words = sentence.split(' ');

  const lastIndex = words.length - 1;

  words[lastIndex] = pluralize(words[lastIndex]);

  return words.join(' ');
}

export function consistOfNumbers(text?: string): boolean {
  if (!text)
    return false;

  return /^\d+$/.test(text);
}

export function isValidUrl(text?: string): boolean {
  if (!text)
    return false;

  return /^https?:\/\/(www\.)?[\w#%+.:=@~-]{1,256}\.[\d()A-Za-z]{1,6}\b([\w#%&()+./:=?@~-]*)$/.test(text);
}

/**
 * Resolves HTML character entities such as `&bull;` to the characters they stand for.
 *
 * @remarks
 * Parses through the DOM, so it needs a browser environment and will strip any markup the input
 * happens to carry rather than escaping it. Input that parses to nothing is returned unchanged.
 */
export function decodeHtmlEntities(input: string): string {
  const doc = new DOMParser().parseFromString(input, 'text/html');
  return doc.documentElement.textContent || input;
}
