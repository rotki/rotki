import type { MatchedKeyword } from '@/modules/core/table/filtering';

export const AddressBookFilterKeys = {
  ADDRESS: 'address',
  NAME: 'nameSubstring',
} as const;

export type AddressBookFilterKey = typeof AddressBookFilterKeys[keyof typeof AddressBookFilterKeys];

export type Filters = MatchedKeyword<AddressBookFilterKey>;
