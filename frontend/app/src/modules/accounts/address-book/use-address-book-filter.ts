import type { MatchedKeyword } from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';

export const AddressBookFilterKeys = {
  ADDRESS: 'address',
  NAME: 'nameSubstring',
} as const;

export type AddressBookFilterKey = typeof AddressBookFilterKeys[keyof typeof AddressBookFilterKeys];

export type Filters = MatchedKeyword<AddressBookFilterKey>;

export function useAddressBookFilter(): FilterSchema<Filters> {
  const modelFilters = ref<Filters>({});

  return {
    filters: modelFilters,
  };
}
