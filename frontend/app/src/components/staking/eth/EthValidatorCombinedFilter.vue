<script setup lang="ts">
import type {
  MatchedKeyword,
  SearchMatcher,

} from '@/types/filtering';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { dateDeserializer, dateSerializer, dateValidator } from '@/utils/assets';
import { getDateInputISOFormat } from '@/utils/date';
import { assert, type EthStakingCombinedFilter } from '@rotki/common';

const props = withDefaults(
  defineProps<{
    filter?: EthStakingCombinedFilter;
    disableStatus?: boolean;
  }>(),
  {
    disableStatus: false,
  },
);

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

const { t } = useI18n({ useScope: 'global' });

const matchers = computed<Matcher[]>(
  () =>
    [
      {
        description: t('common.filter.start_date'),
        deserializer: dateDeserializer(dateInputFormat),
        hint: t('common.filter.date_hint', {
          format: getDateInputISOFormat(get(dateInputFormat)),
        }),
        key: Eth2StakingFilterKeys.START,
        keyValue: Eth2StakingFilterValueKeys.START,
        serializer: dateSerializer(dateInputFormat),
        string: true,
        suggestions: () => [],
        validate: dateValidator(dateInputFormat),
      },
      {
        description: t('common.filter.end_date'),
        deserializer: dateDeserializer(dateInputFormat),
        hint: t('common.filter.date_hint', {
          format: getDateInputISOFormat(get(dateInputFormat)),
        }),
        key: Eth2StakingFilterKeys.END,
        keyValue: Eth2StakingFilterValueKeys.END,
        serializer: dateSerializer(dateInputFormat),
        string: true,
        suggestions: () => [],
        validate: dateValidator(dateInputFormat),
      },
      {
        description: t('eth_validator_combined_filter.status'),
        key: Eth2StakingFilterKeys.STATUS,
        keyValue: Eth2StakingFilterValueKeys.STATUS,
        string: true,
        suggestions: () => validStatuses.filter(x => x !== 'all'),
        validate: (status: string) => isValidStatus(status),
      },
    ] satisfies Matcher[],
);

function updateFilters(updatedFilters: Filters) {
  set(filters, updatedFilters);
  const { fromTimestamp, status, toTimestamp } = updatedFilters;

  assert(typeof fromTimestamp === 'string' || fromTimestamp === undefined);
  assert(typeof toTimestamp === 'string' || toTimestamp === undefined);
  assert((typeof status === 'string' && isValidStatus(status)) || status === undefined);

  emit('update:filter', {
    fromTimestamp: fromTimestamp ? parseInt(fromTimestamp) : undefined,
    status,
    toTimestamp: toTimestamp ? parseInt(toTimestamp) : undefined,
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
