/**
 *
 * @param {string} string - String to convert
 * @return {string} - String converted to sentence case
 * @example
 * toSentenceCase('this is a sentence'); // This is a sentence
 */
export const toSentenceCase = (string: string): string => {
  if (!string) {
    return '';
  }
  return string[0].toUpperCase() + string.slice(1);
};

/**
 *
 * @param {string} string - String to convert
 * @return {string} - String converted to snake case
 * @example
 * toSnakeCase('this is a sentence'); // this_is_a_sentence
 */
export const toSnakeCase = (string: string): string => {
  if (!string) {
    return '';
  }

  return string.toLowerCase().replace(/ /g, '_');
};

/**
 *
 * @param {string} string - String to convert
 * @return {string} - String converted to capital case
 * @example
 * toCapitalCase('this is a sentence'); // This Is A Sentence
 */
export const toCapitalCase = (string: string): string =>
  string.replace(
    /\p{L}+('\p{L}+)?/gu,
    txt => txt.charAt(0).toUpperCase() + txt.slice(1)
  );

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
export const toHumanReadable = (
  value: string,
  transform?: 'capitalize' | 'sentence' | 'uppercase' | 'lowercase'
): string => {
  if (!value) {
    return '';
  }

  if (!transform) {
    return value.replace(/_/g, ' ');
  }

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
};

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
export const transformCase = (key: string, camelCase = false): string => {
  if (camelCase) {
    return key.includes('_')
      ? key.replace(/_(.)/gu, (_, p1) => p1.toUpperCase())
      : key;
  }

  return key.replace(/([A-Z])/gu, (_, p1, offset, string) => {
    const nextCharOffset = offset + 1;
    if (
      (nextCharOffset < string.length &&
        /([A-Z])/.test(string[nextCharOffset])) ||
      nextCharOffset === string.length
    ) {
      return p1;
    }
    return `_${p1.toLowerCase()}`;
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
  const plural: Record<string, string> = {
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
  const irregular: Record<string, string> = {
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
  if (uncountable.includes(word.toLowerCase())) {
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
  if (!address) {
    return '';
  }
  return address.replace(/[^\da-z]+/gi, '');
};

export const isValidEthAddress = (address?: string): boolean => {
  if (!address) {
    return false;
  }
  return !!address.match(/^0x[\dA-Fa-f]{40}$/);
};

export const isValidTxHash = (address?: string): boolean => {
  if (!address) {
    return false;
  }
  return !!address.match(/^0x[\dA-Fa-f]{64}$/);
};

export const consistOfNumbers = (text?: string): boolean => {
  if (!text) {
    return false;
  }

  return !!text.match(/^\d+$/);
};

// Transform HTML code entities such as &bull; into “•”
export const decodeHtmlEntities = (input: string): string => {
  const doc = new DOMParser().parseFromString(input, 'text/html');
  return doc.documentElement.textContent || input;
};
