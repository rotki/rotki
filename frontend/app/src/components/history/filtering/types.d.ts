export interface SearchMatcher<T> {
  readonly key: string;
  readonly matchingProperty: keyof T;
  readonly description: string;
  readonly validator: (value: string) => boolean;
}

export type MatchedKeyword<T> = {
  readonly [key in keyof T]: string;
};
