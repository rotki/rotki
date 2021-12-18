export interface SearchMatcher<K, T = void> {
  readonly key: K;
  readonly keyValue?: T;
  readonly description: string;
  readonly hint?: string;
  readonly validate: (value: string) => boolean;
  readonly suggestions: () => string[];
  readonly transformer?: (value: string) => string;
}

export type MatchedKeyword<T extends string> = {
  [key in T]?: string;
};

export type Suggestion = {
  readonly index: number;
  readonly total: number;
  readonly suggestion: string;
};
