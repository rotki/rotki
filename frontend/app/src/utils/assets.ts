import type { AssetSearchParams } from '@/composables/api/assets/info';
import type { AssetNameReturn, AssetSymbolReturn } from '@/composables/assets/retrieval';
import type { AssetInfoWithId, AssetsWithId } from '@/types/asset';
import type { DateFormat } from '@/types/date-format';
import type { ComputedRef, Ref } from 'vue';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import {
  assert,
  type AssetBalance,
  type AssetInfo,
  getAddressFromEvmIdentifier,
  getTextToken,
  isEvmIdentifier,
  isValidEthAddress,
  type Nullable,
} from '@rotki/common';

function levenshtein(a: string, b: string): number {
  let tmp;
  if (a.length === 0)
    return b.length;

  if (b.length === 0)
    return a.length;

  if (a.length > b.length) {
    tmp = a;
    a = b;
    b = tmp;
  }

  let i: number;
  let j: number;
  let res = 0;
  const alen = a.length;
  const blen = b.length;
  const row = new Array(alen);
  for (i = 0; i <= alen; i++) row[i] = i;

  for (i = 1; i <= blen; i++) {
    res = i;
    for (j = 1; j <= alen; j++) {
      tmp = row[j - 1];
      row[j - 1] = res;
      res = b[i - 1] === a[j - 1] ? tmp : Math.min(tmp + 1, Math.min(res + 1, row[j] + 1));
    }
  }
  return res;
}

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
export function compareTextByKeyword(a: string, b: string, keyword: string): number {
  const search = keyword.toLocaleLowerCase().trim();
  const keywordA = a.toLocaleLowerCase().trim();
  const keywordB = b.toLocaleLowerCase().trim();

  if (keywordA === search)
    return -1;

  if (keywordB === search)
    return 1;

  let rankA = levenshtein(search, keywordA);
  let rankB = levenshtein(search, keywordB);

  const keywordAHaystackIndex = keywordA.indexOf(search);
  const keywordANeedleIndex = search.indexOf(keywordA);
  const keywordBHaystackIndex = keywordB.indexOf(search);
  const keywordBNeedleIndex = search.indexOf(keywordB);

  const aLength = keywordA.length;
  const bLength = keywordB.length;

  if (keywordAHaystackIndex === 0 || keywordANeedleIndex === 0)
    rankA -= aLength + 1;
  else if (keywordAHaystackIndex > 0 || keywordANeedleIndex > 0)
    rankA -= aLength;

  if (keywordBHaystackIndex === 0 || keywordBNeedleIndex === 0)
    rankB -= bLength + 1;
  else if (keywordBHaystackIndex > 0 || keywordBNeedleIndex > 0)
    rankB -= bLength;

  return rankA - rankB;
}

export function getSortItems<T extends AssetBalance>(getInfo: (identifier: string) => AssetInfo | null) {
  return (items: T[], sortBy: (keyof AssetBalance)[], sortDesc: boolean[]): T[] => {
    const sortByElement = sortBy[0];
    const sortByDesc = sortDesc[0];
    return items.sort((a, b) => {
      if (sortByElement === 'asset') {
        const aAsset = getInfo(a.asset);
        const bAsset = getInfo(b.asset);
        assert(aAsset && bAsset);
        const bSymbol = bAsset.symbol || '';
        const aSymbol = aAsset.symbol || '';
        return sortByDesc ? bSymbol.toLowerCase().localeCompare(aSymbol) : aSymbol.toLowerCase().localeCompare(bSymbol);
      }

      const aElement = a[sortByElement];
      const bElement = b[sortByElement];
      return (sortByDesc ? bElement.minus(aElement) : aElement.minus(bElement)).toNumber();
    });
  };
}

export function assetFilterByKeyword(
  item: Nullable<AssetBalance>,
  search: string,
  assetName: AssetNameReturn,
  assetSymbol: AssetSymbolReturn,
): boolean {
  const keyword = getTextToken(search);
  if (!keyword || !item)
    return true;

  const name = getTextToken(get(assetName(item.asset)));
  const symbol = getTextToken(get(assetSymbol(item.asset)));
  return symbol.includes(keyword) || name.includes(keyword);
}

export function assetSuggestions(assetSearch: (params: AssetSearchParams) => Promise<AssetsWithId>, evmChain?: string): (value: string) => Promise<AssetsWithId> {
  let pending: AbortController | null = null;

  return useDebounceFn(async (value: string) => {
    if (pending) {
      pending.abort();
      pending = null;
    }

    pending = new AbortController();

    let keyword = value;
    let address;

    if (isEvmIdentifier(value)) {
      keyword = '';
      address = getAddressFromEvmIdentifier(value);
    }

    else if (isValidEthAddress(value)) {
      keyword = '';
      address = value;
    }

    const result = await assetSearch({
      address,
      evmChain,
      limit: 10,
      signal: pending.signal,
      value: keyword,
    });
    pending = null;
    return result;
  }, 200);
}

export function assetDeserializer(assetInfo: (identifier: string) => ComputedRef<AssetInfo | null>): (identifier: string) => AssetInfoWithId | null {
  return (identifier: string): AssetInfoWithId | null => {
    const asset = get(assetInfo(identifier));
    if (!asset)
      return null;

    return {
      ...asset,
      identifier,
    };
  };
}

export function dateValidator(dateInputFormat: Ref<DateFormat>): (value: string) => boolean {
  return (value: string) => value.length > 0 && !isNaN(convertToTimestamp(value, get(dateInputFormat)));
}

export function dateSerializer(dateInputFormat: Ref<DateFormat>): (date: string) => string {
  return (date: string) => convertToTimestamp(date, get(dateInputFormat)).toString();
}

export function dateDeserializer(dateInputFormat: Ref<DateFormat>): (timestamp: string) => string {
  return (timestamp: string) => convertFromTimestamp(parseInt(timestamp), get(dateInputFormat));
}
