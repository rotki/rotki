import { AssetBalance } from '@rotki/common';
import { AssetInfo } from '@rotki/common/lib/data';
import { assert } from '@/utils/assertions';

const levenshtein = (a: string, b: string) => {
  let tmp;
  if (a.length === 0) {
    return b.length;
  }
  if (b.length === 0) {
    return a.length;
  }
  if (a.length > b.length) {
    tmp = a;
    a = b;
    b = tmp;
  }

  let i: number,
    j: number,
    res: number = 0;
  const alen = a.length,
    blen = b.length,
    row = Array(alen);
  for (i = 0; i <= alen; i++) {
    row[i] = i;
  }

  for (i = 1; i <= blen; i++) {
    res = i;
    for (j = 1; j <= alen; j++) {
      tmp = row[j - 1];
      row[j - 1] = res;
      res =
        b[i - 1] === a[j - 1]
          ? tmp
          : Math.min(tmp + 1, Math.min(res + 1, row[j] + 1));
    }
  }
  return res;
};

/**
 *
 * @param {string} a - First string to compare
 * @param {string} b - Second string to compare
 * @param {string} keyword
 *
 * @return {number} - Rank comparison between string `a` to keyword and string `b` to keyword.
 *
 * @description
 * This method use levenshtein to compare the string, but with little modifications.
 * This method will prioritize this thing (in order) other than the value from levenshtein:
 * 1. It will prioritize string that match from beginning (i.e. for keyword `hop`, it prioritizes string `hop-protocol` higher than string `hoo`)
 * 2. It will prioritize string that contain the keyword (i.e. for keyword `urv`, it prioritizes string `curvy`, higher than string `urw`)
 */
export const compareSymbols = (a: string, b: string, keyword: string) => {
  const search = keyword.toLocaleLowerCase().trim();
  const keywordA = a.toLocaleLowerCase().trim();
  const keywordB = b.toLocaleLowerCase().trim();

  if (keywordA === search) return -1;
  if (keywordB === search) return 1;

  let rankA = levenshtein(search, keywordA);
  let rankB = levenshtein(search, keywordB);

  const keywordAHaystackIndex = keywordA.indexOf(search);
  const keywordANeedleIndex = search.indexOf(keywordA);
  const keywordBHaystackIndex = keywordB.indexOf(search);
  const keywordBNeedleIndex = search.indexOf(keywordB);

  const length = search.length;

  if (keywordAHaystackIndex === 0 || keywordANeedleIndex === 0) {
    rankA -= length + 1;
  } else if (keywordAHaystackIndex > 0 || keywordANeedleIndex > 0) {
    rankA -= length;
  }

  if (keywordBHaystackIndex === 0 || keywordBNeedleIndex === 0) {
    rankB -= length + 1;
  } else if (keywordBHaystackIndex > 0 || keywordBNeedleIndex > 0) {
    rankB -= length;
  }

  return rankA - rankB;
};

export const getSortItems = (
  getInfo: (identifier: string) => AssetInfo | null
) => {
  return (
    items: AssetBalance[],
    sortBy: (keyof AssetBalance)[],
    sortDesc: boolean[]
  ): AssetBalance[] => {
    const sortByElement = sortBy[0];
    const sortByDesc = sortDesc[0];
    return items.sort((a, b) => {
      if (sortByElement === 'asset') {
        const aAsset = getInfo(a.asset);
        const bAsset = getInfo(b.asset);
        assert(aAsset && bAsset);
        const bSymbol = bAsset.symbol || '';
        const aSymbol = aAsset.symbol || '';
        return sortByDesc
          ? bSymbol.toLowerCase().localeCompare(aSymbol)
          : aSymbol.toLowerCase().localeCompare(bSymbol);
      }

      const aElement = a[sortByElement];
      const bElement = b[sortByElement];
      return (
        sortByDesc ? bElement.minus(aElement) : aElement.minus(bElement)
      ).toNumber();
    });
  };
};

export const isEvmIdentifier = (identifier?: string) => {
  if (!identifier) return false;
  return identifier.startsWith('eip155');
};

export const getAddressFromEvmIdentifier = (identifier?: string) => {
  if (!identifier) return '';
  return identifier.split(':')[2] ?? '';
};

export const createEvmIdentifierFromAddress = (
  address: string,
  chain: string = '1'
) => {
  return `eip155:${chain}/erc20:${address}`;
};

export const getValidSelectorFromEvmAddress = (address: string) => {
  return address.replace(/[^a-z0-9]/gi, '');
};
