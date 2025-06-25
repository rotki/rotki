import type { FilterSchema } from '@/composables/use-pagination-filter/types';
import type { MatchedKeywordWithBehaviour, SearchMatcher } from '@/types/filtering';
import { arrayify } from '@/utils/array';
import { z } from 'zod/v4';

enum EthValidatorAccountFilterKeys {
  INDEX = 'validator_index',
  PUBLIC_KEY = 'public_key',
  STATUS = 'status',
}

enum EthValidatorAccountFilterValueKeys {
  INDEX = 'index',
  PUBLIC_KEY = 'publicKey',
  STATUS = 'status',
}

export type Matcher = SearchMatcher<EthValidatorAccountFilterKeys, EthValidatorAccountFilterValueKeys>;

export type Filters = MatchedKeywordWithBehaviour<EthValidatorAccountFilterValueKeys>;

export const validStatuses = ['exited', 'active', 'consolidated', 'all'] as const;

export function isValidStatus(status: string): status is (typeof validStatuses)[number] {
  return Array.prototype.includes.call(validStatuses, status);
}

export function useEthValidatorAccountFilter(t: ReturnType<typeof useI18n>['t']): FilterSchema<Filters, Matcher> {
  const filters = ref<Filters>({});

  const matchers = computed<Matcher[]>(() => [{
    description: t('common.validator_index'),
    key: EthValidatorAccountFilterKeys.INDEX,
    keyValue: EthValidatorAccountFilterValueKeys.INDEX,
    multiple: true,
    string: true,
    suggestions: (): string[] => [],
    validate: (): boolean => true,
  }, {
    description: t('eth2_input.public_key'),
    key: EthValidatorAccountFilterKeys.PUBLIC_KEY,
    keyValue: EthValidatorAccountFilterValueKeys.PUBLIC_KEY,
    multiple: true,
    string: true,
    suggestions: (): string[] => [],
    validate: (): true => true,
  }, {
    description: t('eth_validator_combined_filter.status'),
    key: EthValidatorAccountFilterKeys.STATUS,
    keyValue: EthValidatorAccountFilterValueKeys.STATUS,
    multiple: true,
    string: true,
    suggestions: (): ('exited' | 'active' | 'consolidated')[] => validStatuses.filter(x => x !== 'all'),
    validate: (status: string): boolean => isValidStatus(status),
  }]);

  const OptionalMultipleString = z
    .array(z.string())
    .or(z.string())
    .transform(arrayify)
    .optional();

  const RouteFilterSchema = z.object({
    [EthValidatorAccountFilterValueKeys.INDEX]: OptionalMultipleString,
    [EthValidatorAccountFilterValueKeys.PUBLIC_KEY]: OptionalMultipleString,
    [EthValidatorAccountFilterValueKeys.STATUS]: OptionalMultipleString,
  });

  return {
    filters,
    matchers,
    RouteFilterSchema,
  };
}
