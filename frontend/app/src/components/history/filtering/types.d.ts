export interface SearchMatcher<K> {
  readonly key: K;
  readonly description: string;
  readonly hint?: string;
  readonly validate: (value: string) => boolean;
  readonly suggestions: () => string[];
}

export type MatchedKeyword<T extends string> = {
  readonly [key in T]?: string;
};

export type Suggestion = {
  readonly index: number;
  readonly total: number;
  readonly suggestion: string;
};
