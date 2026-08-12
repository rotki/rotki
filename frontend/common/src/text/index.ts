/// <reference lib="dom" />

// Addresses and transaction hashes live in their own module: they are a self-contained group with
// a base58 decoder behind them, and together they took this file past the line cap.
export * from './address';

export * from './case';

export * from './hyperliquid';

/**
 *
 * @param {string} string - String to convert
 * @return {string} - String converted to sentence case
 * @example
 * toSentenceCase('this is a sentence'); // This is a sentence
 */
export function toSentenceCase(string: string): string {
  if (!string)
    return '';

  return string[0].toUpperCase() + string.slice(1);
}

/**
 *
 * @param {string} string - String to convert
 * @return {string} - String converted to text token, mostly used to matching keyword
 * @example
 * getTextToken('this is a sentence'); // thisisasentence
 */

export function getTextToken(string: string): string {
  if (!string)
    return '';

  return string.toLowerCase().trim().replace(/[^\dA-Za-z]/g, '');
}

/**
 *
 * @param {string} string - String to convert
 * @return {string} - String converted to snake case
 * @example
 * toSnakeCase('this is a sentence'); // this_is_a_sentence
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
 *
 * @param {string} string - String to convert
 * @return {string} - String converted to capital case
 * @example
 * toCapitalCase('this is a sentence'); // This Is A Sentence
 */
export function toCapitalCase(string: string): string {
  return string.replace(/\p{L}+('\p{L}+)?/gu, txt => txt.charAt(0).toUpperCase() + txt.slice(1));
}

/**
 *
 * @param {string} value - String to convert
 * @param {'capitalize' | 'sentence' | 'uppercase' | 'lowercase'} transform
 * @return {string} - String converted to human-readable case
 * @example
 * toHumanReadable('POLYGON_POS', 'sentence'); // Polygon Pos
 * @example
 * toHumanReadable('POLYGON_POS'); // POLYGON POS
 * @example
 * toHumanReadable('polygon_pos', 'uppercase'); // POLYGON POS
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
 * Returns the plural of an English word.
 *
 * @export
 * @param {string} word
 * @param {number} [amount]
 * @returns {string}
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
  // save some time in the case that singular and plural are the same
  if (uncountable.includes(word.toLowerCase()))
    return word;

  // check for irregular forms
  for (const w in irregular) {
    const pattern = new RegExp(`${w}$`, 'i');
    const replace = irregular[w];
    if (pattern.test(word))
      return word.replace(pattern, replace);
  }
  // check for matches using regular expressions
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

// Transform HTML code entities such as &bull; into “•”
export function decodeHtmlEntities(input: string): string {
  const doc = new DOMParser().parseFromString(input, 'text/html');
  return doc.documentElement.textContent || input;
}
