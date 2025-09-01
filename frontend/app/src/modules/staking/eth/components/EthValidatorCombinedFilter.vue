<script setup lang="ts">
import type {
  MatchedKeyword,
  SearchMatcher,

} from '@/types/filtering';
import { assert, type EthStakingCombinedFilter } from '@rotki/common';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import { isValidStatus, validStatuses } from '@/composables/filters/eth-validator';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { dateDeserializer, dateSerializer, dateValidator } from '@/utils/assets';
import { getDateInputISOFormat } from '@/utils/date';

const filter = defineModel<EthStakingCombinedFilter | undefined>('filter', { required: true });

withDefaults(defineProps<{
  disableStatus?: boolean;
}>(), {
  disableStatus: false,
});

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

const filters = ref<Filters>({});

const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());

const { t } = useI18n({ useScope: 'global' });

const matchers = computed<Matcher[]>(() => [{
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
}, {
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
}, {
  description: t('eth_validator_combined_filter.status'),
  key: Eth2StakingFilterKeys.STATUS,
  keyValue: Eth2StakingFilterValueKeys.STATUS,
  string: true,
  suggestions: () => validStatuses.filter(x => x !== 'all'),
  validate: (status: string) => isValidStatus(status),
}] satisfies Matcher[]);

function updateFilters(updatedFilters: Filters) {
  set(filters, updatedFilters);
  const { fromTimestamp, status, toTimestamp } = updatedFilters;

  assert(typeof fromTimestamp === 'string' || fromTimestamp === undefined);
  assert(typeof toTimestamp === 'string' || toTimestamp === undefined);
  assert((typeof status === 'string' && isValidStatus(status)) || status === undefined);

  set(filter, {
    fromTimestamp: fromTimestamp ? parseInt(fromTimestamp) : undefined,
    status,
    toTimestamp: toTimestamp ? parseInt(toTimestamp) : undefined,
  });
}

watchImmediate(filter, (period) => {
  const updatedFilters = { ...get(filters) };

  if (period?.fromTimestamp)
    updatedFilters.fromTimestamp = period.fromTimestamp.toString();
  else delete updatedFilters.fromTimestamp;

  if (period?.toTimestamp)
    updatedFilters.toTimestamp = period.toTimestamp.toString();
  else
    delete updatedFilters.toTimestamp;

  updatedFilters.status = period?.status;

  set(filters, updatedFilters);
});
</script>

<template>
  <TableFilter
    :matchers="matchers"
    :matches="filters"
    @update:matches="updateFilters($event)"
  />
</template>
