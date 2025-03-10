import type { FilterSchema } from '@/composables/use-pagination-filter/types';
import type { MatchedKeyword, SearchMatcher } from '@/types/filtering';
import { isValidEthAddress } from '@rotki/common';
import { z } from 'zod';

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
    description: t('assets.filter.name'),
    hint: t('assets.filter.name_hint'),
    key: AddressBookFilterKeys.NAME,
    keyValue: AddressBookFilterValueKeys.NAME,
    string: true,
    suggestions: (): string[] => [],
    validate: (): boolean => true,
  }, {
    description: t('assets.filter.address'),
    key: AddressBookFilterKeys.ADDRESS,
    keyValue: AddressBookFilterValueKeys.ADDRESS,
    multiple: true,
    string: true,
    suggestions: (): string[] => [],
    validate: (address: string): boolean => isValidEthAddress(address),
  }]);

  const OptionalString = z.string().optional();
  const RouteFilterSchema = z.object({
    [AddressBookFilterValueKeys.ADDRESS]: OptionalString,
    [AddressBookFilterValueKeys.NAME]: OptionalString,
  });

  return {
    filters,
    matchers,
    RouteFilterSchema,
  };
}
