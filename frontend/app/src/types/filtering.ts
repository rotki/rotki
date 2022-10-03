import { AssetInfoWithId, AssetsWithId } from '@/types/assets';

export type StringSuggestion = () => string[];
export type AssetSuggestion = (value: string) => Promise<AssetsWithId>;

interface BaseMatcher<K, KV = void> {
  readonly key: K;
  readonly keyValue?: KV;
  readonly description: string;
  readonly hint?: string;
  readonly multiple?: boolean;
}

interface StringSuggestionMatcher<K, KV = void> extends BaseMatcher<K, KV> {
  readonly string?: true;
  readonly suggestions: StringSuggestion;
  readonly validate: (value: string) => boolean;
  readonly transformer?: (value: string) => string;
}

interface AssetSuggestionMatcher<K, KV = void> extends BaseMatcher<K, KV> {
  readonly asset?: true;
  readonly suggestions: AssetSuggestion;
}

export type SearchMatcher<K, KV = void> =
  | StringSuggestionMatcher<K, KV>
  | AssetSuggestionMatcher<K, KV>;

export type MatchedKeyword<T extends string> = {
  [key in T]?: string | string[];
};

export interface Suggestion {
  readonly index: number;
  readonly total: number;
  readonly key: string;
  readonly value: AssetInfoWithId | string;
}
