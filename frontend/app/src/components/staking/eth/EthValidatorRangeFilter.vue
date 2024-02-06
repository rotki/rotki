<script setup lang="ts">
import {
  type MatchedKeyword,
  type SearchMatcher,
  dateDeserializer,
  dateSerializer,
  dateValidator,
} from '@/types/filtering';
import type { EthStakingPeriod } from '@rotki/common/lib/staking/eth2';
import type { ComputedRef } from 'vue';

const props = defineProps<{
  period: EthStakingPeriod | undefined;
}>();

const emit = defineEmits<{
  (e: 'update:period', value?: EthStakingPeriod): void;
}>();

enum Eth2StakingFilterKeys {
  START = 'start',
  END = 'end',
}

enum Eth2StakingFilterValueKeys {
  START = 'fromTimestamp',
  END = 'toTimestamp',
}

export type Matcher = SearchMatcher<
  Eth2StakingFilterKeys,
  Eth2StakingFilterValueKeys
>;

export type Filters = MatchedKeyword<Eth2StakingFilterValueKeys>;

const filters: Ref<Filters> = ref({});

const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());

const { t } = useI18n();

const matchers: ComputedRef<Matcher[]> = computed(
  () =>
    [
      {
        key: Eth2StakingFilterKeys.START,
        keyValue: Eth2StakingFilterValueKeys.START,
        description: t('closed_trades.filter.start_date'),
        string: true,
        suggestions: () => [],
        hint: t('closed_trades.filter.date_hint', {
          format: getDateInputISOFormat(get(dateInputFormat)),
        }),
        validate: dateValidator(dateInputFormat),
        serializer: dateSerializer(dateInputFormat),
        deserializer: dateDeserializer(dateInputFormat),
      },
      {
        key: Eth2StakingFilterKeys.END,
        keyValue: Eth2StakingFilterValueKeys.END,
        description: t('closed_trades.filter.end_date'),
        string: true,
        suggestions: () => [],
        hint: t('closed_trades.filter.date_hint', {
          format: getDateInputISOFormat(get(dateInputFormat)),
        }),
        validate: dateValidator(dateInputFormat),
        serializer: dateSerializer(dateInputFormat),
        deserializer: dateDeserializer(dateInputFormat),
      },
    ] satisfies Matcher[],
);

function updateFilters(updatedFilters: Filters) {
  set(filters, updatedFilters);
  const { fromTimestamp, toTimestamp } = updatedFilters;

  assert(typeof fromTimestamp === 'string' || fromTimestamp === undefined);
  assert(typeof toTimestamp === 'string' || toTimestamp === undefined);

  emit('update:period', {
    fromTimestamp: fromTimestamp ? parseInt(fromTimestamp) : undefined,
    toTimestamp: toTimestamp ? parseInt(toTimestamp) : undefined,
  });
}

watch(() => props.period, (period) => {
  const updatedFilters = { ...get(filters) };

  if (period?.fromTimestamp)
    updatedFilters.fromTimestamp = period.fromTimestamp.toString();
  else
    delete updatedFilters.fromTimestamp;

  if (period?.toTimestamp)
    updatedFilters.toTimestamp = period.toTimestamp.toString();
  else
    delete updatedFilters.toTimestamp;

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
