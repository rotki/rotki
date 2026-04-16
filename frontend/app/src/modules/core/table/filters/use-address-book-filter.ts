import type { MatchedKeyword, SearchMatcher } from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';
import { z } from 'zod/v4';
import { arrayify } from '@/modules/core/common/data/array';

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

  const { t } = useI18n({ useScope: 'global' });

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
    validate: (): boolean => true,
  }]);

  const OptionalString = z.string().optional();
  const OptionalMultipleString = z
    .array(z.string())
    .or(z.string())
    .transform(arrayify)
    .optional();

  const RouteFilterSchema = z.object({
    [AddressBookFilterValueKeys.ADDRESS]: OptionalMultipleString,
    [AddressBookFilterValueKeys.NAME]: OptionalString,
  });

  return {
    filters,
    matchers,
    RouteFilterSchema,
  };
}
