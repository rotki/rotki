import type { AssetsWithId } from '@/modules/assets/types';
import { AssetInfoWithId } from '@rotki/common';
import { z } from 'zod';

export enum FilterBehaviour {
  INCLUDE = 'include',
  EXCLUDE = 'exclude',
}

export interface FilterObjectWithBehaviour<T> {
  behaviour?: FilterBehaviour;
  values: T;
}

/**
 * The pill editor a field maps to. Derivable from the matcher discriminant for
 * `asset`/`boolean`/`string` (→ `enum`); `range` and `date` are opt-in via `valueType`.
 */
export const FilterValueTypes = {
  ASSET: 'asset',
  BOOLEAN: 'boolean',
  DATE: 'date',
  ENUM: 'enum',
  RANGE: 'range',
} as const;

export type FilterValueType = typeof FilterValueTypes[keyof typeof FilterValueTypes];

/** Comparison operators a pill can express. The first allowed op is the default (hidden on the pill). */
export const FilterOps = {
  AFTER: 'after',
  BEFORE: 'before',
  BETWEEN: 'between',
  GT: 'gt',
  IS: 'is',
  IS_NOT: 'is_not',
  LT: 'lt',
} as const;

export type FilterOp = typeof FilterOps[keyof typeof FilterOps];

type StringSuggestion = () => string[];

type AssetSuggestion = (value: string) => Promise<AssetsWithId>;

interface BaseMatcher<K, KV = void> {
  readonly key: K;
  readonly keyValue?: KV;
  readonly description: string;
  readonly hint?: string;
  readonly multiple?: boolean;
  /**
   * Suggestions to show in the table filter. Default is 5. Set to -1 to show all.
   */
  readonly suggestionsToShow?: number;
  /**
   * Pill editor this field maps to. Optional: when omitted the pill layer derives it
   * from the discriminant (`asset`/`boolean` → same, `string` → `enum`). Set explicitly
   * only for the opt-in types (`range`, `date`).
   */
  readonly valueType?: FilterValueType;
  /**
   * Allowed comparison operators, most-default first. Optional: the pill layer falls back
   * to the per-`valueType` defaults when omitted.
   */
  readonly operators?: readonly FilterOp[];
}

export interface StringSuggestionMatcher<K, KV = void> extends BaseMatcher<K, KV> {
  readonly string: true;
  readonly suggestions: StringSuggestion;
  readonly validate: (value: string) => boolean;
  readonly serializer?: (value: string) => string;
  readonly deserializer?: (value: string) => string;
  readonly allowExclusion?: boolean;
  readonly behaviourRequired?: boolean;
  /**
   * When true, suggestions are filtered using substring matching instead of Levenshtein ordering,
   * and validation only passes when a matching suggestion exists.
   */
  readonly strictMatching?: boolean;
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

export function createEmptySuggestion(): Suggestion {
  return {
    asset: false,
    index: 0,
    key: '',
    total: 0,
    value: '',
  };
}

export enum SavedFilterLocation {
  HISTORY_EVENTS = 'historyEvents',
  BLOCKCHAIN_ACCOUNTS = 'blockchainAccounts',
  ETH_VALIDATORS = 'ethValidators',
}
