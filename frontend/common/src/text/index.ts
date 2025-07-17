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

  return string.toLowerCase().replace(/ /g, '_');
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
 * Transforms keys/text between camel and snake cases
 * @param {string} key - string to transform
 * @param {boolean} camelCase - flag to decide whether to return camelCase (true) or snake_case (false)
 * @returns {string}
 * @example
 * transformCase('loremIpsum'); // lorem_ipsum
 * @example
 * transformCase('lorem_ipsum', true); // loremIpsum
 */
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

export function isValidEthAddress(address?: string): boolean {
  if (!address)
    return false;

  return /^0x[\dA-Fa-f]{40}$/.test(address);
}

export function isValidBtcAddress(address?: string): boolean {
  if (!address)
    return false;

  // P2PKH addresses (starts with 1) and P2SH addresses (starts with 3)
  if (/^[13][1-9A-HJ-NP-Za-km-z]{25,34}$/.test(address))
    return true;

  // Bech32 addresses (starts with bc1)
  return /^bc1[02-9ac-hj-np-z]{7,87}$/.test(address);
}

export function isValidBchAddress(address?: string): boolean {
  if (!address)
    return false;

  // Legacy format (same as Bitcoin P2PKH and P2SH)
  if (/^[13][1-9A-HJ-NP-Za-km-z]{25,34}$/.test(address))
    return true;

  // CashAddr format (starts with bitcoincash:)
  if (/^bitcoincash:[02-9ac-hj-np-z]{42,}$/.test(address))
    return true;

  // CashAddr format without prefix
  return /^[pq][02-9ac-hj-np-z]{41,}$/.test(address);
}

export function isValidSolanaAddress(address?: string): boolean {
  if (!address)
    return false;

  // Solana addresses are base58 encoded and should be 32-44 characters long
  // They use the base58 alphabet: 123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz
  return /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(address);
}

export function isValidTxHash(address?: string): boolean {
  if (!address)
    return false;

  return /^0x[\dA-Fa-f]{64}$/.test(address);
}

export function consistOfNumbers(text?: string): boolean {
  if (!text)
    return false;

  return /^\d+$/.test(text);
}

export function isValidUrl(text?: string): boolean {
  if (!text)
    return false;

  return /^https?:\/\/(www\.)?[\w#%+.:=@~-]{1,256}(\.[\d()A-Za-z]{1,6})?\b([\w#%&()+./:=?@~-]*)$/.test(text);
}

// Transform HTML code entities such as &bull; into “•”
export function decodeHtmlEntities(input: string): string {
  const doc = new DOMParser().parseFromString(input, 'text/html');
  return doc.documentElement.textContent || input;
}
