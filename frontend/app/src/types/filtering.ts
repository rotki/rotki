import { z } from 'zod';
import { AssetInfoWithId, type AssetsWithId } from '@/types/asset';
import type { AssetInfo } from '@rotki/common/lib/data';
import type { DateFormat } from '@/types/date-format';

export enum FilterBehaviour {
  INCLUDE = 'include',
  EXCLUDE = 'exclude',
}

export interface FilterObjectWithBehaviour<T> {
  behaviour?: FilterBehaviour;
  values: T;
}

export type StringSuggestion = () => string[];

export type AssetSuggestion = (value: string) => Promise<AssetsWithId>;

interface BaseMatcher<K, KV = void> {
  readonly key: K;
  readonly keyValue?: KV;
  readonly description: string;
  readonly hint?: string;
  readonly multiple?: boolean;
}

export interface StringSuggestionMatcher<K, KV = void> extends BaseMatcher<K, KV> {
  readonly string: true;
  readonly suggestions: StringSuggestion;
  readonly validate: (value: string) => boolean;
  readonly serializer?: (value: string) => string;
  readonly deserializer?: (value: string) => string;
  readonly allowExclusion?: boolean;
  readonly behaviourRequired?: boolean;
}

interface AssetSuggestionMatcher<K, KV = void> extends BaseMatcher<K, KV> {
  readonly asset: true;
  readonly suggestions: AssetSuggestion;
  readonly deserializer?: (value: string) => AssetInfoWithId | null;
}

interface BooleanSuggestionMatcher<K, KV = void> extends BaseMatcher<K, KV> {
  readonly boolean: true;
}

export type SearchMatcher<K, KV = void> =
  | StringSuggestionMatcher<K, KV>
  | AssetSuggestionMatcher<K, KV>
  | BooleanSuggestionMatcher<K, KV>;

export type MatchedKeyword<T extends string> = {
  [key in T]?: string | string[] | boolean;
};

export type MatchedKeywordWithBehaviour<T extends string> = {
  [key in T]?: string | string[] | boolean | FilterObjectWithBehaviour<string | string[] | boolean>;
};

export const BaseSuggestion = z.object({
  key: z.string(),
  value: AssetInfoWithId.or(z.string()).or(z.boolean()),
  exclude: z.boolean().optional(),
});

export type BaseSuggestion = z.infer<typeof BaseSuggestion>;

export const Suggestion = BaseSuggestion.extend({
  index: z.number(),
  total: z.number(),
  asset: z.boolean(),
});

export type Suggestion = z.infer<typeof Suggestion>;

export enum SavedFilterLocation {
  HISTORY_TRADES = 'historyTrades',
  HISTORY_DEPOSITS_WITHDRAWALS = 'historyDepositsWithdrawals',
  HISTORY_EVENTS = 'historyEvents',
  BLOCKCHAIN_ACCOUNTS = 'blockchainAccounts',
  ETH_VALIDATORS = 'ethValidators',
}

export function assetSuggestions(assetSearch: (keyword: string, limit: number) => Promise<AssetsWithId>) {
  return async (value: string) => await assetSearch(value, 5);
}

export function assetDeserializer(assetInfo: (identifier: string) => ComputedRef<AssetInfo | null>) {
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

export function dateValidator(dateInputFormat: Ref<DateFormat>) {
  return (value: string) => value.length > 0 && !isNaN(convertToTimestamp(value, get(dateInputFormat)));
}

export function dateSerializer(dateInputFormat: Ref<DateFormat>) {
  return (date: string) => convertToTimestamp(date, get(dateInputFormat)).toString();
}

export function dateDeserializer(dateInputFormat: Ref<DateFormat>) {
  return (timestamp: string) => convertFromTimestamp(parseInt(timestamp), get(dateInputFormat));
}
