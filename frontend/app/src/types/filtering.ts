import { type ComputedRef, type Ref } from 'vue';
import { type AssetInfo } from '@rotki/common/lib/data';
import { type AssetInfoWithId, type AssetsWithId } from '@/types/asset';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import { type DateFormat } from '@/types/date-format';

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
  readonly string: true;
  readonly suggestions: StringSuggestion;
  readonly validate: (value: string) => boolean;
  readonly serializer?: (value: string) => string;
  readonly deserializer?: (value: string) => string;
}

interface AssetSuggestionMatcher<K, KV = void> extends BaseMatcher<K, KV> {
  readonly asset: true;
  readonly suggestions: AssetSuggestion;
  readonly deserializer?: (value: string) => AssetInfoWithId | null;
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
  readonly asset: boolean;
  readonly value: AssetInfoWithId | string;
}

export const assetSuggestions =
  (assetSearch: (keyword: string, limit: number) => Promise<AssetsWithId>) =>
  async (value: string) =>
    await assetSearch(value, 5);

export const assetDeserializer =
  (assetInfo: (identifier: string) => ComputedRef<AssetInfo | null>) =>
  (identifier: string): AssetInfoWithId | null => {
    const asset = get(assetInfo(identifier));
    if (!asset) {
      return null;
    }

    return {
      ...asset,
      identifier
    };
  };

export const dateValidator =
  (dateInputFormat: Ref<DateFormat>) => (value: string) => {
    return (
      value.length > 0 &&
      !isNaN(convertToTimestamp(value, get(dateInputFormat)))
    );
  };

export const dateSerializer =
  (dateInputFormat: Ref<DateFormat>) => (date: string) =>
    convertToTimestamp(date, get(dateInputFormat)).toString();

export const dateDeserializer =
  (dateInputFormat: Ref<DateFormat>) => (timestamp: string) =>
    convertFromTimestamp(parseInt(timestamp), true, get(dateInputFormat));
