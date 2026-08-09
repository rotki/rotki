/** Whether a filter's values are the ones to keep or the ones to leave out, as the backend takes it. */
export const FilterBehaviours = {
  EXCLUDE: 'exclude',
  INCLUDE: 'include',
} as const;

export type FilterBehaviour = typeof FilterBehaviours[keyof typeof FilterBehaviours];

export interface FilterObjectWithBehaviour<T> {
  behaviour?: FilterBehaviour;
  values: T;
}

/** The pill editor a field maps to, declared by the field. */
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

export type MatchedKeyword<T extends string> = {
  [key in T]?: string | string[] | boolean;
};

export type MatchedKeywordWithBehaviour<T extends string> = {
  [key in T]?: string | string[] | boolean | FilterObjectWithBehaviour<string | string[] | boolean>;
};

/**
 * The tables whose filters a user can save under a name. The values are stored in the user's own
 * settings, so they are a wire form: renaming one orphans everything saved under it.
 */
export const SavedFilterLocations = {
  BLOCKCHAIN_ACCOUNTS: 'blockchainAccounts',
  ETH_VALIDATORS: 'ethValidators',
  HISTORY_EVENTS: 'historyEvents',
} as const;

export type SavedFilterLocation = typeof SavedFilterLocations[keyof typeof SavedFilterLocations];
