export interface SearchMatcher<T> {
  readonly key: string;
  readonly matchingProperty: keyof T;
  readonly description: string;
  readonly validator: (value: string) => boolean;
  readonly suggestions: () => string[];
}

export type MatchedKeyword<T> = {
  readonly [key in keyof T]: string;
};

export type Suggestion = {
  readonly index: number;
  readonly total: number;
  readonly suggestion: string;
};
