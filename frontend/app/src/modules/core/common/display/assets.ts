import type { AssetSearchParams } from '@/modules/assets/api/use-asset-info-api';
import {
  type AssetBalance,
  type AssetInfoWithId,
  getAddressFromEvmIdentifier,
  getAddressFromHyperliquidTokenIdentifier,
  getAddressFromSolanaIdentifier,
  getTextToken,
  isEvmIdentifier,
  isHyperliquidTokenIdentifier,
  isSolanaTokenIdentifier,
  isValidEthAddress,
  isValidHyperliquidTokenAddress,
  isValidSolanaAddress,
  type Nullable,
} from '@rotki/common';
import {
  type AssetsWithId,
  EVM_TOKEN,
  NON_EVM_CHAIN_ASSET_TYPES,
} from '@/modules/assets/types';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
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

  let label = identifier;
  if (isEvmIdentifier(identifier))
    label = getAddressFromEvmIdentifier(identifier);
  else if (isHyperliquidTokenIdentifier(identifier))
    label = getAddressFromHyperliquidTokenIdentifier(identifier);

  return truncateAddress(label, 4);
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
 * Handles EVM, Solana, and Hyperliquid Core identifiers and addresses.
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

  if (isHyperliquidTokenIdentifier(keyword)) {
    return {
      address: getAddressFromHyperliquidTokenIdentifier(keyword),
      value: '',
    };
  }

  if (
    isValidEthAddress(keyword)
    || isValidHyperliquidTokenAddress(keyword)
    || isValidSolanaAddress(keyword)
  ) {
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

  if (NON_EVM_CHAIN_ASSET_TYPES[chain])
    return chain;

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
  const nonEvmAssetType = usedChain ? NON_EVM_CHAIN_ASSET_TYPES[usedChain] : undefined;

  return {
    assetType: nonEvmAssetType ?? (usedChain ? EVM_TOKEN : undefined),
    evmChain: nonEvmAssetType ? undefined : usedChain,
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
 * Ranks two strings by how well each matches a search keyword, as a comparator.
 *
 * @remarks
 * Levenshtein distance decides most of it, but two things outrank it, in order: a string that
 * matches from the *beginning* (for `hop`, `hop-protocol` beats `hoo`), then a string that merely
 * contains* the keyword (for `urv`, `curvy` beats `urw`).
 *
 * @param a - the first candidate
 * @param b - the second candidate
 * @param keyword - the search term; lower-cased and trimmed before comparison
 * @returns a negative number when `a` ranks higher, positive when `b` does, 0 when they tie
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

/**
 * Everything about one asset that a search can match, pre-tokenized.
 *
 * Tokenizing on every keystroke is what makes filtering a long balance list expensive, and the
 * inputs only change when the balances or the resolved metadata do. Building this once per asset
 * lets the filter itself be nothing but string compares.
 */
export interface AssetSearchTokens {
  address: string;
  identifier: string;
  name: string;
  symbol: string;
}

/**
 * Below this length a keyword is not tried against contract addresses.
 *
 * An address is hex, so a short keyword hits a great many of them by coincidence and buries the
 * name and symbol matches the user meant.
 */
const ADDRESS_KEYWORD_MIN_LENGTH = 4;

function assetContractAddress(identifier: string): string {
  if (isEvmIdentifier(identifier))
    return getAddressFromEvmIdentifier(identifier);
  if (isSolanaTokenIdentifier(identifier))
    return getAddressFromSolanaIdentifier(identifier);
  if (isHyperliquidTokenIdentifier(identifier))
    return getAddressFromHyperliquidTokenIdentifier(identifier);
  return '';
}

export function assetSearchTokens(
  identifier: string,
  info?: { name?: string | null; symbol?: string | null } | null,
): AssetSearchTokens {
  const standIn = getAssetNameFallback(identifier);
  const searchable = (value?: string | null): string => {
    const trimmed = value?.trim() ?? '';
    return trimmed && trimmed !== standIn ? getTextToken(trimmed) : '';
  };

  const name = searchable(info?.name);
  const symbol = searchable(info?.symbol);

  return {
    address: getTextToken(assetContractAddress(identifier)),
    identifier: getTextToken(identifier),
    name,
    symbol,
  };
}

/**
 * Both directions are a match: a fragment of the address is someone typing part of it, and an
 * address inside the keyword is someone pasting a whole identifier that carries it.
 */
function addressMatchesKeyword(address: string, keyword: string): boolean {
  if (!address)
    return false;
  return address.includes(keyword) || keyword.includes(address);
}

/**
 * Whether an asset matches a keyword, which must already be tokenized with `getTextToken`.
 *
 * @remarks
 * Matching an asset by its contract address is deliberate: pasting an address is how you look up a
 * token you have no name for, and it is the only handle an asset without metadata has.
 *
 * Metadata arrives asynchronously, so every arm here has to keep an unresolved asset matchable:
 * absent tokens fail open, a pasted identifier matches whole, and an asset with neither symbol nor
 * name falls back to its identifier. Tightening any of them makes a row appear and then vanish as
 * the asset resolves, or reports "no results" for something the list does contain.
 */
export function assetTokensMatch(tokens: AssetSearchTokens | undefined, keyword: string): boolean {
  if (!tokens)
    return true;

  if (keyword === tokens.identifier)
    return true;

  if (tokens.symbol.includes(keyword) || tokens.name.includes(keyword))
    return true;

  if (keyword.length < ADDRESS_KEYWORD_MIN_LENGTH)
    return false;

  if (addressMatchesKeyword(tokens.address, keyword))
    return true;

  if (!tokens.symbol && !tokens.name)
    return tokens.identifier.includes(keyword);

  return false;
}

/** Whether the keyword is the asset's whole symbol or name, rather than a fragment of it. */
export function assetTokensExactlyMatch(tokens: AssetSearchTokens | undefined, keyword: string): boolean {
  if (!tokens)
    return false;
  return tokens.symbol === keyword || tokens.name === keyword;
}

/**
 * Builds the debounced inline asset suggester for a filter input.
 *
 * @remarks
 * Ignored assets are filtered out, matching every other asset input. Leaving them in makes one
 * field behave two ways: an asset offered while typing would be missing from the checklist the
 * pill opens.
 */
export function assetSuggestions(assetSearch: (params: AssetSearchParams) => Promise<AssetsWithId>, location?: string): (keyword: string) => Promise<AssetsWithId> {
  let pending: AbortController | null = null;

  const { getEvmChainName, matchChain } = useSupportedChains();
  const { isAssetIgnored } = useAssetsStore();

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

    return result.filter(({ identifier }) => !isAssetIgnored(identifier));
  }, 200);
}
