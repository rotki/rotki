import { z } from 'zod';
import { type MatchedKeyword, type SearchMatcher } from '@/types/filtering';

enum AddressBookFilterKeys {
  NAME = 'name',
  ADDRESS = 'address'
}

enum AddressBookFilterValueKeys {
  NAME = 'nameSubstring',
  ADDRESS = 'address'
}

export type Matcher = SearchMatcher<
  AddressBookFilterKeys,
  AddressBookFilterValueKeys
>;

export type Filters = MatchedKeyword<AddressBookFilterValueKeys>;

export const useAddressBookFilter = () => {
  const filters: Ref<Filters> = ref({});

  const { t } = useI18n();

  const matchers: ComputedRef<Matcher[]> = computed(() => [
    {
      key: AddressBookFilterKeys.NAME,
      keyValue: AddressBookFilterValueKeys.NAME,
      description: t('assets.filter.name'),
      hint: t('assets.filter.name_hint'),
      string: true,
      suggestions: () => [],
      validate: () => true
    },
    {
      key: AddressBookFilterKeys.ADDRESS,
      keyValue: AddressBookFilterValueKeys.ADDRESS,
      description: t('assets.filter.address'),
      string: true,
      multiple: true,
      suggestions: () => [],
      validate: (address: string) => isValidEthAddress(address)
    }
  ]);

  const updateFilter = (newFilters: Filters) => {
    set(filters, newFilters);
  };

  const OptionalString = z.string().optional();
  const RouteFilterSchema = z.object({
    [AddressBookFilterValueKeys.NAME]: OptionalString,
    [AddressBookFilterValueKeys.ADDRESS]: OptionalString
  });

  return {
    filters,
    matchers,
    updateFilter,
    RouteFilterSchema
  };
};
