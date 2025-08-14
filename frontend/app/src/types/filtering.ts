import { z } from 'zod/v4';
import { AssetInfoWithId, type AssetsWithId } from '@/types/asset';

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
  // Suggestions to show in the table filter. Default is 5. Set to -1 to show all.
  readonly suggestionsToShow?: number;
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
  exclude: z.boolean().optional(),
  key: z.string(),
  value: AssetInfoWithId.or(z.string()).or(z.boolean()),
});

export type BaseSuggestion = z.infer<typeof BaseSuggestion>;

export const Suggestion = BaseSuggestion.extend({
  asset: z.boolean(),
  index: z.number(),
  total: z.number(),
});

export type Suggestion = z.infer<typeof Suggestion>;

export enum SavedFilterLocation {
  HISTORY_EVENTS = 'historyEvents',
  BLOCKCHAIN_ACCOUNTS = 'blockchainAccounts',
  ETH_VALIDATORS = 'ethValidators',
}
