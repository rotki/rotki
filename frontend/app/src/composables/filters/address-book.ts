import { z } from 'zod';
import type { MatchedKeyword, SearchMatcher } from '@/types/filtering';
import type { FilterSchema } from '@/composables/filter-paginate';

enum AddressBookFilterKeys {
  NAME = 'name',
  ADDRESS = 'address',
}

enum AddressBookFilterValueKeys {
  NAME = 'nameSubstring',
  ADDRESS = 'address',
}

export type Matcher = SearchMatcher<AddressBookFilterKeys, AddressBookFilterValueKeys>;

export type Filters = MatchedKeyword<AddressBookFilterValueKeys>;

export function useAddressBookFilter(): FilterSchema<Filters, Matcher> {
  const filters = ref<Filters>({});

  const { t } = useI18n();

  const matchers = computed<Matcher[]>(() => [{
    key: AddressBookFilterKeys.NAME,
    keyValue: AddressBookFilterValueKeys.NAME,
    description: t('assets.filter.name'),
    hint: t('assets.filter.name_hint'),
    string: true,
    suggestions: (): string[] => [],
    validate: (): boolean => true,
  }, {
    key: AddressBookFilterKeys.ADDRESS,
    keyValue: AddressBookFilterValueKeys.ADDRESS,
    description: t('assets.filter.address'),
    string: true,
    multiple: true,
    suggestions: (): string[] => [],
    validate: (address: string): boolean => isValidEthAddress(address),
  }]);

  const OptionalString = z.string().optional();
  const RouteFilterSchema = z.object({
    [AddressBookFilterValueKeys.NAME]: OptionalString,
    [AddressBookFilterValueKeys.ADDRESS]: OptionalString,
  });

  return {
    filters,
    matchers,
    RouteFilterSchema,
  };
}
