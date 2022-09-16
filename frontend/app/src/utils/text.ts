/**
 *
 * @param {string} string - String to convert
 * @return {string} - String converted to sentence case
 * @example
 * toSentenceCase('this is a sentence'); // This is a sentence
 */
export const toSentenceCase = (string: string): string => {
  if (!string) return '';
  return string[0].toUpperCase() + string.slice(1);
};

/**
 *
 * @param {string} string - String to convert
 * @return {string} - String converted to capital case
 * @example
 * toCapitalCase('this is a sentence'); // This Is A Sentence
 */
export const toCapitalCase = (string: string): string => {
  return string.replace(/\p{L}+('\p{L}+)?/gu, function (txt) {
    return txt.charAt(0).toUpperCase() + txt.slice(1);
  });
};

/**
 * Returns the plural of an English word.
 *
 * @export
 * @param {string} word
 * @param {number} [amount]
 * @returns {string}
 */
export const pluralize = (word: string, amount?: number): string => {
  if (amount !== undefined && amount === 1) {
    return word;
  }
  const plural: { [key: string]: string } = {
    '(quiz)$': '$1zes',
    '^(ox)$': '$1en',
    '([m|l])ouse$': '$1ice',
    '(matr|vert|ind)ix|ex$': '$1ices',
    '(x|ch|ss|sh)$': '$1es',
    '([^aeiouy]|qu)y$': '$1ies',
    '(hive)$': '$1s',
    '(?:([^f])fe|([lr])f)$': '$1$2ves',
    '(shea|lea|loa|thie)f$': '$1ves',
    sis$: 'ses',
    '([ti])um$': '$1a',
    '(tomat|potat|ech|her|vet)o$': '$1oes',
    '(bu)s$': '$1ses',
    '(alias)$': '$1es',
    '(octop)us$': '$1i',
    '(ax|test)is$': '$1es',
    '(us)$': '$1es',
    '([^s]+)$': '$1s'
  };
  const irregular: { [key: string]: string } = {
    move: 'moves',
    foot: 'feet',
    goose: 'geese',
    sex: 'sexes',
    child: 'children',
    man: 'men',
    tooth: 'teeth',
    person: 'people'
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
    'wood'
  ];
  // save some time in the case that singular and plural are the same
  if (uncountable.indexOf(word.toLowerCase()) >= 0) {
    return word;
  }
  // check for irregular forms
  for (const w in irregular) {
    const pattern = new RegExp(`${w}$`, 'i');
    const replace = irregular[w];
    if (pattern.test(word)) {
      return word.replace(pattern, replace);
    }
  }
  // check for matches using regular expressions
  for (const reg in plural) {
    const pattern = new RegExp(reg, 'i');
    if (pattern.test(word)) {
      return word.replace(pattern, plural[reg]);
    }
  }
  return word;
};

export const pluralizeLastWord = (sentence: string): string => {
  const words = sentence.split(' ');

  const lastIndex = words.length - 1;

  words[lastIndex] = pluralize(words[lastIndex]);

  return words.join(' ');
};

export const sanitizeAddress = (address?: string): string => {
  if (!address) return '';
  return address.replace(/[^A-Z0-9]+/gi, '');
};

export const isValidEthAddress = (address?: string): boolean => {
  if (!address) return false;
  return !!address.match(/^0x[a-fA-F0-9]{40}$/);
};

export const isValidTxHash = (address?: string): boolean => {
  if (!address) return false;
  return !!address.match(/^0x[a-fA-F0-9]{64}$/);
};
