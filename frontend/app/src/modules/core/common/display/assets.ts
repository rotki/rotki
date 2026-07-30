import type { AssetSearchParams } from '@/modules/assets/api/use-asset-info-api';
import {
  type AssetBalance,
  type AssetInfoWithId,
  getAddressFromEvmIdentifier,
  getAddressFromSolanaIdentifier,
  getTextToken,
  isEvmIdentifier,
  isSolanaTokenIdentifier,
  isValidEthAddress,
  isValidSolanaAddress,
  type Nullable,
} from '@rotki/common';
import { type AssetsWithId, EVM_TOKEN, SOLANA_CHAIN, SOLANA_TOKEN } from '@/modules/assets/types';
import { getAssetNameFallback } from '@/modules/assets/use-resolve-asset-identifier';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

/**
 * Whether a resolved symbol or name is a real one, rather than the `EVM Token: 0x…` stand-in an
 * unresolved asset is given. That stand-in is non-empty, so a truthiness check alone says "named"
 * for exactly the assets that have no name.
 */
export function hasAssetMetadata(identifier: string, value?: Nullable<string>): boolean {
  const trimmed = value?.trim();
  if (!trimmed)
    return false;
  return trimmed !== identifier && trimmed !== getAssetNameFallback(identifier);
}

/**
 * The label for an asset that may have no symbol: its symbol when it has one, else its shortened
 * contract address.
 *
 * A raw identifier is unusable as a label — `eip155:1/erc20:0x214AF1443f6bB9FFB2bDcF301c762Df28Dd7f818`
 * swamps a pill or a suggestion row, and so does the `EVM Token: 0x…` an unresolved asset resolves
 * to. The shortened address is the usual display for an asset without metadata, and is what rotki
 * already shows for any unnamed address. A non-EVM identifier has no address to extract, so it is
 * truncated as-is.
 */
export function assetDisplayLabel(identifier: string, symbol?: Nullable<string>): string {
  if (hasAssetMetadata(identifier, symbol))
    return symbol!.trim();
  return truncateAddress(getAddressFromEvmIdentifier(identifier) || identifier, 4);
}

/**
 * The muted secondary text for an asset row: its name, when that is a real name.
 *
 * An asset with no metadata is given a stand-in name, so using it unguarded puts the same raw
 * address in both the label and the caption. Nothing is better than a duplicate of what the row
 * already shows.
 */
export function assetDisplayCaption(identifier: string, name?: Nullable<string>): string | undefined {
  return hasAssetMetadata(identifier, name) ? name!.trim() : undefined;
}

interface ParsedAssetKeyword {
  value: string;
  address?: string;
}

/**
 * Parses an asset search keyword to extract value and address.
 * Handles EVM identifiers, Solana addresses, and Ethereum addresses.
 */
export function parseAssetSearchKeyword(keyword: string): ParsedAssetKeyword {
  if (isEvmIdentifier(keyword)) {
    return {
      address: getAddressFromEvmIdentifier(keyword),
      value: '',
    };
  }

  if (isSolanaTokenIdentifier(keyword)) {
    return {
      address: getAddressFromSolanaIdentifier(keyword),
      value: '',
    };
  }

  if (isValidEthAddress(keyword) || isValidSolanaAddress(keyword)) {
    return {
      address: keyword,
      value: '',
    };
  }

  return { value: keyword };
}

/**
 * Sanitizes a chain identifier by matching it against supported chains
 * and returning the appropriate EVM chain name.
 */
export function getSanitizedChain(
  chain: string | undefined,
  matchChain: (chain: string) => string | undefined,
  getEvmChainName: (chain: string) => string | undefined,
): string | undefined {
  if (!chain) {
    return undefined;
  }

  const matchedChain = matchChain(chain);
  if (!matchedChain) {
    return undefined;
  }

  return getEvmChainName(matchedChain) ?? matchedChain;
}

/**
 * Gets asset search parameters based on chain type.
 */
export function getAssetSearchTypeParams(usedChain: string | undefined): { assetType?: string; evmChain?: string } {
  let assetType: string | undefined;
  if (usedChain === SOLANA_CHAIN)
    assetType = SOLANA_TOKEN;
  else if (usedChain)
    assetType = EVM_TOKEN;

  return {
    assetType,
    evmChain: usedChain === SOLANA_CHAIN ? undefined : usedChain,
  };
}

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

  const clearedSearch = getTextToken(search);
  const keywordAIncludes = getTextToken(keywordA).includes(clearedSearch);
  const keywordBIncludes = getTextToken(keywordB).includes(clearedSearch);

  const length = search.length;

  rankA -= (Number(keywordAHaystackIndex === 0) + Number(keywordANeedleIndex === 0) + (keywordAIncludes ? length : 0));
  rankB -= (Number(keywordBHaystackIndex === 0) + Number(keywordBNeedleIndex === 0) + (keywordBIncludes ? length : 0));

  return rankA - rankB;
}

export function getSortItems<T extends AssetBalance>(getInfo: (identifier: string) => AssetInfoWithId | null) {
  return (items: T[], sortBy: (keyof AssetBalance)[], sortDesc: boolean[]): T[] => {
    const sortByElement = sortBy[0];
    const sortByDesc = sortDesc[0];
    return items.sort((a, b) => {
      if (sortByElement === 'asset') {
        const aAsset = getInfo(a.asset);
        const bAsset = getInfo(b.asset);
        const bSymbol = bAsset?.symbol ?? b.asset;
        const aSymbol = aAsset?.symbol ?? a.asset;
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
  getAssetInfo: (identifier: string | undefined) => { name?: string | null; symbol?: string | null } | null,
): boolean {
  const keyword = getTextToken(search);
  if (!keyword || !item)
    return true;

  const info = getAssetInfo(item.asset);
  const name = getTextToken(info?.name ?? '');
  const symbol = getTextToken(info?.symbol ?? '');
  return symbol.includes(keyword) || name.includes(keyword);
}

export function assetSuggestions(assetSearch: (params: AssetSearchParams) => Promise<AssetsWithId>, location?: string): (keyword: string) => Promise<AssetsWithId> {
  let pending: AbortController | null = null;

  const { getEvmChainName, matchChain } = useSupportedChains();

  return useDebounceFn(async (keyword: string) => {
    if (pending) {
      pending.abort();
      pending = null;
    }

    pending = new AbortController();

    const { address, value } = parseAssetSearchKeyword(keyword);
    const usedChain = getSanitizedChain(location, matchChain, getEvmChainName);

    const result = await assetSearch({
      address,
      ...getAssetSearchTypeParams(usedChain),
      limit: 10,
      signal: pending.signal,
      value,
    });
    pending = null;
    return result;
  }, 200);
}
