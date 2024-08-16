<script setup lang="ts">
import {
  type MatchedKeyword,
  type SearchMatcher,
  dateDeserializer,
  dateSerializer,
  dateValidator,
} from '@/types/filtering';
import type { EthStakingCombinedFilter } from '@rotki/common';

const props = defineProps<{
  filter: EthStakingCombinedFilter | undefined;
}>();

const emit = defineEmits<{
  (e: 'update:filter', value?: EthStakingCombinedFilter): void;
}>();

enum Eth2StakingFilterKeys {
  START = 'start',
  END = 'end',
  STATUS = 'status',
}

enum Eth2StakingFilterValueKeys {
  START = 'fromTimestamp',
  END = 'toTimestamp',
  STATUS = 'status',
}

export type Matcher = SearchMatcher<Eth2StakingFilterKeys, Eth2StakingFilterValueKeys>;

export type Filters = MatchedKeyword<Eth2StakingFilterValueKeys>;

const validStatuses = ['exited', 'active', 'all'] as const;

function isValidStatus(status: string): status is (typeof validStatuses)[number] {
  return Array.prototype.includes.call(validStatuses, status);
}

const filters = ref<Filters>({});

const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());

const { t } = useI18n();

const matchers = computed<Matcher[]>(
  () =>
    [
      {
        key: Eth2StakingFilterKeys.START,
        keyValue: Eth2StakingFilterValueKeys.START,
        description: t('common.filter.start_date'),
        string: true,
        suggestions: () => [],
        hint: t('common.filter.date_hint', {
          format: getDateInputISOFormat(get(dateInputFormat)),
        }),
        validate: dateValidator(dateInputFormat),
        serializer: dateSerializer(dateInputFormat),
        deserializer: dateDeserializer(dateInputFormat),
      },
      {
        key: Eth2StakingFilterKeys.END,
        keyValue: Eth2StakingFilterValueKeys.END,
        description: t('common.filter.end_date'),
        string: true,
        suggestions: () => [],
        hint: t('common.filter.date_hint', {
          format: getDateInputISOFormat(get(dateInputFormat)),
        }),
        validate: dateValidator(dateInputFormat),
        serializer: dateSerializer(dateInputFormat),
        deserializer: dateDeserializer(dateInputFormat),
      },
      {
        key: Eth2StakingFilterKeys.STATUS,
        keyValue: Eth2StakingFilterValueKeys.STATUS,
        description: t('eth_validator_combined_filter.status'),
        string: true,
        suggestions: () => validStatuses.filter(x => x !== 'all'),
        validate: (status: string) => isValidStatus(status),
      },
    ] satisfies Matcher[],
);

function updateFilters(updatedFilters: Filters) {
  set(filters, updatedFilters);
  const { fromTimestamp, toTimestamp, status } = updatedFilters;

  assert(typeof fromTimestamp === 'string' || fromTimestamp === undefined);
  assert(typeof toTimestamp === 'string' || toTimestamp === undefined);
  assert((typeof status === 'string' && isValidStatus(status)) || status === undefined);

  emit('update:filter', {
    fromTimestamp: fromTimestamp ? parseInt(fromTimestamp) : undefined,
    toTimestamp: toTimestamp ? parseInt(toTimestamp) : undefined,
    status,
  });
}

watchImmediate(
  () => props.filter,
  (period) => {
    const updatedFilters = { ...get(filters) };

    if (period?.fromTimestamp)
      updatedFilters.fromTimestamp = period.fromTimestamp.toString();
    else delete updatedFilters.fromTimestamp;

    if (period?.toTimestamp)
      updatedFilters.toTimestamp = period.toTimestamp.toString();
    else delete updatedFilters.toTimestamp;

    updatedFilters.status = period?.status;

    set(filters, updatedFilters);
  },
);
</script>

<template>
  <TableFilter
    :matchers="matchers"
    :matches="filters"
    @update:matches="updateFilters($event)"
  />
</template>
