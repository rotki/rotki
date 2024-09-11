import { z } from 'zod';
import type { MatchedKeywordWithBehaviour, SearchMatcher } from '@/types/filtering';
import type { FilterSchema } from '@/composables/filter-paginate';

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

const validStatuses = ['exited', 'active', 'all'] as const;

function isValidStatus(status: string): status is (typeof validStatuses)[number] {
  return Array.prototype.includes.call(validStatuses, status);
}

export function useEthValidatorAccountFilter(t: ReturnType<typeof useI18n>['t']): FilterSchema<Filters, Matcher> {
  const filters = ref<Filters>({});

  const matchers = computed<Matcher[]>(() => [
    {
      key: EthValidatorAccountFilterKeys.INDEX,
      keyValue: EthValidatorAccountFilterValueKeys.INDEX,
      description: t('common.validator_index'),
      multiple: true,
      string: true,
      suggestions: (): string[] => [],
      validate: (): boolean => true,
    },
    {
      key: EthValidatorAccountFilterKeys.PUBLIC_KEY,
      keyValue: EthValidatorAccountFilterValueKeys.PUBLIC_KEY,
      description: t('eth2_input.public_key'),
      multiple: true,
      string: true,
      suggestions: (): string[] => [],
      validate: (): true => true,
    },
    {
      key: EthValidatorAccountFilterKeys.STATUS,
      keyValue: EthValidatorAccountFilterValueKeys.STATUS,
      description: t('eth_validator_combined_filter.status'),
      multiple: true,
      string: true,
      suggestions: (): ('exited' | 'active')[] => validStatuses.filter(x => x !== 'all'),
      validate: (status: string): boolean => isValidStatus(status),
    },
  ]);

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
    matchers,
    filters,
    RouteFilterSchema,
  };
}
